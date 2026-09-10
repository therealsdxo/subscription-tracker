"""Package endpoint tests (tech_doc.md §4.2)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

VALID = {
    "name": "25 Meal Package",
    "description": "Starter",
    "number_of_meals": 25,
    "validity_days": 50,
    "base_price": "6500.00",
    "tax_amount": "0.00",
}


async def _create(client: AsyncClient, headers: dict[str, str], **overrides: object) -> dict:
    resp = await client.post("/api/v1/packages", headers=headers, json={**VALID, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_package_computes_final_price_and_code(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    body = await _create(
        client, auth_headers(admin_user), base_price="6500.00", tax_amount="500.00"
    )
    assert body["package_code"] == "PKG-00001"
    assert body["final_price"] == "7000.00"
    assert body["status"] == "ACTIVE"


async def test_codes_are_sequential(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(admin_user)
    a = await _create(client, h, name="A")
    b = await _create(client, h, name="B")
    assert (a["package_code"], b["package_code"]) == ("PKG-00001", "PKG-00002")


@pytest.mark.parametrize(
    "field,value",
    [
        ("number_of_meals", 0),
        ("number_of_meals", 501),
        ("validity_days", 0),
        ("validity_days", 731),
        ("base_price", "-1.00"),
    ],
)
async def test_bounds_rejected(
    client: AsyncClient,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
    field: str,
    value: object,
) -> None:
    resp = await client.post(
        "/api/v1/packages", headers=auth_headers(admin_user), json={**VALID, field: value}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_staff_cannot_write_packages(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    resp = await client.post("/api/v1/packages", headers=auth_headers(staff_user), json=VALID)
    assert resp.status_code == 403


async def test_staff_can_read_packages(
    client: AsyncClient,
    admin_user: User,
    staff_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    await _create(client, auth_headers(admin_user))
    resp = await client.get("/api/v1/packages", headers=auth_headers(staff_user))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_update_recomputes_final_price(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(admin_user)
    pkg = await _create(client, h)
    resp = await client.patch(
        f"/api/v1/packages/{pkg['id']}", headers=h, json={"tax_amount": "325.00"}
    )
    assert resp.status_code == 200
    assert resp.json()["final_price"] == "6825.00"


async def test_activate_deactivate(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(admin_user)
    pkg = await _create(client, h)
    d = await client.post(f"/api/v1/packages/{pkg['id']}/deactivate", headers=h)
    assert d.json()["status"] == "INACTIVE"
    a = await client.post(f"/api/v1/packages/{pkg['id']}/activate", headers=h)
    assert a.json()["status"] == "ACTIVE"

    listed = await client.get("/api/v1/packages?status=INACTIVE", headers=h)
    assert listed.json()["total"] == 0


async def test_delete_unreferenced_package(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    h = auth_headers(admin_user)
    pkg = await _create(client, h)
    resp = await client.delete(f"/api/v1/packages/{pkg['id']}", headers=h)
    assert resp.status_code == 204
    assert (await client.get(f"/api/v1/packages/{pkg['id']}", headers=h)).status_code == 404


async def test_audit_rows_written(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    h = auth_headers(admin_user)
    pkg = await _create(client, h)
    await client.patch(f"/api/v1/packages/{pkg['id']}", headers=h, json={"name": "X"})
    await client.post(f"/api/v1/packages/{pkg['id']}/deactivate", headers=h)
    actions = (
        (await db_session.execute(select(AuditLog.action).where(AuditLog.entity_type == "package")))
        .scalars()
        .all()
    )
    assert set(actions) == {"PACKAGE_CREATED", "PACKAGE_UPDATED", "PACKAGE_DEACTIVATED"}
