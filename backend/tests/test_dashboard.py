"""Dashboard summary tests (tech_doc.md §9.4)."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient

from app.models.user import User
from tests.test_subscriptions import make_customer, make_package, sub_payload


async def test_empty_system_returns_zeros(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    r = await client.get("/api/v1/dashboard/summary", headers=auth_headers(admin_user))
    assert r.status_code == 200
    assert r.json() == {
        "active_subscriptions": 0,
        "todays_meals_planned": 0,
        "delivered_today": 0,
        "expiring_soon": 0,
        "outstanding_dues_total": "0.00",
    }


async def test_summary_reflects_activity(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
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
        json={"amount": "2000.00", "payment_method": "UPI"},
    )
    # A delivery generated + marked for today.
    today = date.today().isoformat()
    await client.post("/api/v1/deliveries/generate", headers=h, json={"date": today})
    listed = await client.get(f"/api/v1/deliveries?date={today}", headers=h)
    if listed.json()["total"]:
        did = listed.json()["items"][0]["id"]
        await client.patch(
            f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
        )

    s = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert s["active_subscriptions"] == 1
    assert s["outstanding_dues_total"] == "4500.00"  # 6500 - 2000
    # Only assert delivery counts when today was an open day.
    if listed.json()["total"]:
        assert s["delivered_today"] == 1
        assert s["todays_meals_planned"] >= 1


async def test_expiring_soon_counted(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h, number_of_meals=3)  # ≤ 5 meals → expiring
    cid, aid = await make_customer(client, h)
    await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date="2026-09-01"),
    )
    s = (await client.get("/api/v1/dashboard/summary", headers=h)).json()
    assert s["expiring_soon"] == 1


async def test_dashboard_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/dashboard/summary")).status_code == 401
