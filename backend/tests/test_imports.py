"""CSV customer import tests (tech_doc.md §10.7)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.user import User
from tests.test_subscriptions import make_package

GOOD = (
    "name,phone,email,address_line,area,city,pincode\n"
    "Asha Rao,9000000001,asha@example.com,1 MG Rd,Indiranagar,Bengaluru,560038\n"
    "Bhavna Iyer,9000000002,,2 Church St,Ashok Nagar,Bengaluru,560001\n"
)


def _file(text: str) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("customers.csv", text.encode(), "text/csv")}


async def test_validate_does_not_write(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    r = await client.post(
        "/api/v1/imports/customers?mode=validate", headers=h, files=_file(GOOD)
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "total": 2, "valid": 2, "invalid": 0, "committed": False,
        "created_customers": 0, "created_subscriptions": 0, "errors": [],
    }
    count = (
        await db_session.execute(select(func.count()).select_from(Customer))
    ).scalar_one()
    assert count == 0


async def test_commit_creates_customers_and_addresses(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    r = await client.post(
        "/api/v1/imports/customers?mode=commit", headers=h, files=_file(GOOD)
    )
    assert r.status_code == 200
    assert r.json()["committed"] is True
    assert r.json()["created_customers"] == 2

    listed = await client.get("/api/v1/customers", headers=h)
    assert listed.json()["total"] == 2
    detail = await client.get(
        f"/api/v1/customers/{listed.json()['items'][0]['id']}", headers=h
    )
    assert len(detail.json()["addresses"]) == 1


async def test_in_file_duplicate_phone_reported(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    dup = (
        "name,phone,address_line,area,city,pincode\n"
        "A,9000000009,1 X,Y,Z,560001\n"
        "B,9000000009,2 X,Y,Z,560001\n"
    )
    r = await client.post(
        "/api/v1/imports/customers?mode=validate", headers=h, files=_file(dup)
    )
    body = r.json()
    assert body["invalid"] == 1
    assert body["errors"][0]["field"] == "phone"


async def test_commit_with_errors_writes_nothing(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    bad = (
        "name,phone,address_line,area,city,pincode\n"
        "Valid,9000000010,1 X,Y,Z,560001\n"
        ",9000000011,2 X,Y,Z,560001\n"  # missing name
    )
    r = await client.post(
        "/api/v1/imports/customers?mode=commit", headers=h, files=_file(bad)
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "IMPORT_HAS_ERRORS"
    count = (
        await db_session.execute(select(func.count()).select_from(Customer))
    ).scalar_one()
    assert count == 0


async def test_missing_required_column(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    r = await client.post(
        "/api/v1/imports/customers?mode=validate",
        headers=h,
        files=_file("name,phone\nA,9000000001\n"),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "IMPORT_BAD_FILE"


async def test_commit_with_subscription_columns(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    await make_package(client, h)  # PKG-00001, ACTIVE
    csv_text = (
        "name,phone,address_line,area,city,pincode,package_code,start_date\n"
        "Chandra,9000000020,1 X,Y,Bengaluru,560001,PKG-00001,2026-09-01\n"
    )
    r = await client.post(
        "/api/v1/imports/customers?mode=commit", headers=h, files=_file(csv_text)
    )
    assert r.status_code == 200, r.text
    assert r.json()["created_subscriptions"] == 1
    subs = (
        await db_session.execute(select(func.count()).select_from(Subscription))
    ).scalar_one()
    assert subs == 1


async def test_import_requires_admin(
    client: AsyncClient, staff_user: User, auth_headers
) -> None:
    r = await client.post(
        "/api/v1/imports/customers",
        headers=auth_headers(staff_user),
        files=_file(GOOD),
    )
    assert r.status_code == 403
