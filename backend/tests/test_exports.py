"""CSV export tests (tech_doc.md §9.3)."""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from tests.test_subscriptions import make_customer, make_package, sub_payload


async def _seed(client: AsyncClient, h: dict[str, str]) -> int:
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date="2026-09-01"),
    )).json()
    await client.post(
        f"/api/v1/subscriptions/{sub['id']}/payments",
        headers=h,
        json={"amount": "1000.00", "payment_method": "CASH"},
    )
    return int(sub["id"])


async def test_customers_csv(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    await _seed(client, h)
    r = await client.get("/api/v1/exports/customers.csv", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="customers.csv"' in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("customer_code,name,phone,email")
    assert len(lines) == 2
    assert "CUST-000001" in lines[1]
    assert "Indiranagar" in lines[1]  # primary address area


async def test_subscriptions_csv_includes_payment_columns(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    await _seed(client, h)
    r = await client.get("/api/v1/exports/subscriptions.csv", headers=h)
    header, row = r.text.strip().splitlines()
    assert "payment_status" in header and "outstanding_amount" in header
    assert "PARTIALLY_PAID" in row
    assert "5500.00" in row  # 6500 - 1000


async def test_payments_csv(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    await _seed(client, h)
    r = await client.get("/api/v1/exports/payments.csv", headers=h)
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("payment_id,subscription_code")
    assert len(lines) == 2
    assert "1000.00" in lines[1]


async def test_deliveries_csv_honours_date_filter(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    await _seed(client, h)
    monday = "2026-09-07"
    await client.post("/api/v1/deliveries/generate", headers=h, json={"date": monday})

    r = await client.get(f"/api/v1/exports/deliveries.csv?date={monday}", headers=h)
    assert f'filename="deliveries-{monday}.csv"' in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("delivery_date,time_slot,status")
    assert len(lines) == 2 and monday in lines[1]

    empty = await client.get("/api/v1/exports/deliveries.csv?date=2026-09-08", headers=h)
    assert len(empty.text.strip().splitlines()) == 1  # header only


async def test_export_requires_staff(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/exports/customers.csv")).status_code == 401
