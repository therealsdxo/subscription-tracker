"""Customer + address endpoint tests (tech_doc.md §3.3, §4.1)."""

from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

ADDR = {
    "address_line": "12 MG Road",
    "area": "Indiranagar",
    "city": "Bengaluru",
    "pincode": "560038",
}
CUST = {"name": "Asha Rao", "phone": "+91 90000 11111", "addresses": [ADDR]}


async def _create(client: AsyncClient, headers: dict[str, str], **overrides: object) -> dict:
    resp = await client.post("/api/v1/customers", headers=headers, json={**CUST, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_customer_assigns_code_and_primary_address(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    body = await _create(client, auth_headers(staff_user))
    assert body["data"]["customer_code"] == "CUST-000001"
    assert body["data"]["phone"] == "+919000011111"  # normalized
    assert body["warnings"] == []

    detail = await client.get(
        f"/api/v1/customers/{body['data']['id']}", headers=auth_headers(staff_user)
    )
    addresses = detail.json()["addresses"]
    assert len(addresses) == 1 and addresses[0]["is_primary"] is True


async def test_create_requires_address(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    resp = await client.post(
        "/api/v1/customers",
        headers=auth_headers(staff_user),
        json={"name": "No Address", "phone": "9999999999", "addresses": []},
    )
    assert resp.status_code == 422


async def test_phone_uniqueness_conflict(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(staff_user)
    await _create(client, h)
    resp = await client.post(
        "/api/v1/customers",
        headers=h,
        json={**CUST, "name": "Someone Else", "phone": "+91-90000-11111"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PHONE_TAKEN"


async def test_email_uniqueness_conflict(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(staff_user)
    await _create(client, h, email="asha@example.com")
    resp = await client.post(
        "/api/v1/customers",
        headers=h,
        json={**CUST, "phone": "9000022222", "email": "ASHA@example.com"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_duplicate_name_returns_warning_but_creates(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(staff_user)
    await _create(client, h)
    resp = await client.post(
        "/api/v1/customers",
        headers=h,
        json={**CUST, "phone": "9000033333", "name": "  asha   rao "},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["warnings"][0]["code"] == "POSSIBLE_DUPLICATE"
    assert "CUST-000001" in body["warnings"][0]["message"]


async def test_soft_delete_hides_and_reactivate_restores(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(admin_user)
    cust = (await _create(client, h))["data"]

    d = await client.post(
        f"/api/v1/customers/{cust['id']}/deactivate", headers=h, json={"reason": "moved away"}
    )
    assert d.status_code == 200 and d.json()["is_active"] is False

    assert (await client.get("/api/v1/customers", headers=h)).json()["total"] == 1
    active_only = await client.get("/api/v1/customers?is_active=true", headers=h)
    assert active_only.json()["total"] == 0
    inactive = await client.get("/api/v1/customers?is_active=false", headers=h)
    assert inactive.json()["total"] == 1

    r = await client.post(f"/api/v1/customers/{cust['id']}/reactivate", headers=h)
    assert r.json()["is_active"] is True


async def test_staff_cannot_deactivate(
    client: AsyncClient,
    admin_user: User,
    staff_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    cust = (await _create(client, auth_headers(admin_user)))["data"]
    resp = await client.post(
        f"/api/v1/customers/{cust['id']}/deactivate",
        headers=auth_headers(staff_user),
        json={"reason": "x"},
    )
    assert resp.status_code == 403


async def test_address_crud_and_single_primary(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(staff_user)
    cust = (await _create(client, h))["data"]
    cid = cust["id"]

    add = await client.post(
        f"/api/v1/customers/{cid}/addresses",
        headers=h,
        json={**ADDR, "address_line": "9 Church St", "is_primary": True},
    )
    assert add.status_code == 201 and add.json()["is_primary"] is True

    addresses = (await client.get(f"/api/v1/customers/{cid}/addresses", headers=h)).json()
    primaries = [a for a in addresses if a["is_primary"]]
    assert len(primaries) == 1 and primaries[0]["address_line"] == "9 Church St"

    # Deleting the non-primary original is fine.
    original_id = next(a["id"] for a in addresses if not a["is_primary"])
    assert (
        await client.delete(f"/api/v1/customers/{cid}/addresses/{original_id}", headers=h)
    ).status_code == 204

    # Now only one active address remains — deleting it is blocked.
    remaining_id = primaries[0]["id"]
    blocked = await client.delete(
        f"/api/v1/customers/{cid}/addresses/{remaining_id}", headers=h
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "LAST_ADDRESS"


async def test_search_by_name_and_code(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(staff_user)
    await _create(client, h)
    await _create(client, h, name="Bhavna Iyer", phone="9000044444")

    by_name = await client.get("/api/v1/customers?q=bhavna", headers=h)
    assert by_name.json()["total"] == 1
    by_code = await client.get("/api/v1/customers?code=CUST-000001", headers=h)
    assert by_code.json()["total"] == 1


async def test_audit_rows_written(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    h = auth_headers(admin_user)
    cust = (await _create(client, h))["data"]
    await client.patch(
        f"/api/v1/customers/{cust['id']}", headers=h, json={"notes": "VIP"}
    )
    await client.post(
        f"/api/v1/customers/{cust['id']}/deactivate", headers=h, json={"reason": "x"}
    )
    actions = (
        (
            await db_session.execute(
                select(AuditLog.action).where(AuditLog.entity_type == "customer")
            )
        )
        .scalars()
        .all()
    )
    assert set(actions) == {"CUSTOMER_CREATED", "CUSTOMER_UPDATED", "CUSTOMER_DEACTIVATED"}
