"""Subscription lifecycle tests (tech_doc.md §4.3–§4.5, §4.8)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import SubscriptionEventType
from app.models.subscription import Subscription, SubscriptionEvent
from app.models.user import User

Headers = dict[str, str]
MakeHeaders = Callable[[User], Headers]

PKG = {
    "name": "25 Meal Package",
    "number_of_meals": 25,
    "validity_days": 50,
    "base_price": "6500.00",
    "tax_amount": "0.00",
}
ADDR = {
    "address_line": "12 MG Road",
    "area": "Indiranagar",
    "city": "Bengaluru",
    "pincode": "560038",
}


async def make_package(client: AsyncClient, h: Headers, **over: object) -> int:
    r = await client.post("/api/v1/packages", headers=h, json={**PKG, **over})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def make_customer(client: AsyncClient, h: Headers, **over: object) -> tuple[int, int]:
    body = {"name": "Asha Rao", "phone": "+91 90000 00001", "addresses": [ADDR]}
    body.update(over)
    r = await client.post("/api/v1/customers", headers=h, json=body)
    assert r.status_code == 201, r.text
    cid = int(r.json()["data"]["id"])
    detail = await client.get(f"/api/v1/customers/{cid}", headers=h)
    aid = int(detail.json()["addresses"][0]["id"])
    return cid, aid


def sub_payload(customer_id: int, package_id: int, address_id: int, **over: object) -> dict:
    body = {
        "customer_id": customer_id,
        "package_id": package_id,
        "start_date": date.today().isoformat(),
        "delivery_frequency": "DAILY",
        "delivery_time_slots": ["MORNING"],
        "delivery_address_id": address_id,
    }
    body.update(over)
    return body


@pytest.fixture
async def ctx(
    client: AsyncClient, admin_user: User, auth_headers: MakeHeaders
) -> dict[str, object]:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    return {"h": h, "package_id": pkg, "customer_id": cid, "address_id": aid}


# --- creation & snapshot ---------------------------------------------


async def test_create_snapshots_package_and_assigns_code(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    r = await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subscription_code"] == "SUB-000001"
    assert body["status"] == "ACTIVE"
    assert body["snapshot_package_name"] == "25 Meal Package"
    assert body["snapshot_number_of_meals"] == 25
    assert body["meals_allocated"] == 25
    assert body["meals_remaining"] == 25
    assert body["subscription_number"] == 1

    # Editing the package afterwards must not touch the subscription (BR-5).
    await client.patch(
        f"/api/v1/packages/{ctx['package_id']}",
        headers=h,
        json={"name": "Renamed", "base_price": "9999.00"},
    )
    got = await client.get(f"/api/v1/subscriptions/{body['id']}", headers=h)
    assert got.json()["snapshot_package_name"] == "25 Meal Package"
    assert got.json()["snapshot_final_price"] == "6500.00"


async def test_original_end_date_is_calendar_days(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    r = await client.post(
        "/api/v1/subscriptions",
        headers=ctx["h"],
        json=sub_payload(
            ctx["customer_id"],
            ctx["package_id"],
            ctx["address_id"],
            start_date="2026-09-01",
        ),
    )
    assert r.status_code == 201
    # 25-meal / 50-day package starting Tue 01 Sep 2026 -> 21 Oct 2026 (tech_doc §4.3).
    assert r.json()["original_end_date"] == "2026-10-21"
    assert r.json()["expected_end_date"] == "2026-10-21"


async def test_subscription_number_increments_per_customer(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h, cid, pid, aid = (
        ctx["h"], ctx["customer_id"], ctx["package_id"], ctx["address_id"]
    )
    first = await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )
    second = await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )
    assert first.json()["subscription_number"] == 1
    assert second.json()["subscription_number"] == 2


# --- one-ACTIVE / PENDING queueing ---------------------------------


async def test_second_subscription_is_pending(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h, cid, pid, aid = (
        ctx["h"], ctx["customer_id"], ctx["package_id"], ctx["address_id"]
    )
    a = await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )
    b = await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )
    assert a.json()["status"] == "ACTIVE"
    assert b.json()["status"] == "PENDING"


async def test_cancel_activates_next_pending(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h, cid, pid, aid = (
        ctx["h"], ctx["customer_id"], ctx["package_id"], ctx["address_id"]
    )
    a = (await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )).json()
    b = (await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )).json()

    await client.post(
        f"/api/v1/subscriptions/{a['id']}/cancel", headers=h, json={"reason": "moved"}
    )
    b_after = await client.get(f"/api/v1/subscriptions/{b['id']}", headers=h)
    assert b_after.json()["status"] == "ACTIVE"


# --- pause / resume / extend --------------------------------------


async def test_resume_extends_expiry_by_paused_days(
    client: AsyncClient, db_session: AsyncSession, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )).json()
    original_end = date.fromisoformat(sub["expected_end_date"])

    await client.post(
        f"/api/v1/subscriptions/{sub['id']}/pause", headers=h, json={"reason": "travel"}
    )
    # Backdate the pause so resume sees elapsed days.
    ev = (
        await db_session.execute(
            select(SubscriptionEvent).where(
                SubscriptionEvent.subscription_id == sub["id"],
                SubscriptionEvent.event_type == SubscriptionEventType.PAUSED,
            )
        )
    ).scalar_one()
    ev.pause_start = date.today() - timedelta(days=5)
    await db_session.flush()

    resumed = await client.post(
        f"/api/v1/subscriptions/{sub['id']}/resume", headers=h, json={}
    )
    assert resumed.json()["status"] == "ACTIVE"
    assert date.fromisoformat(resumed.json()["expected_end_date"]) == (
        original_end + timedelta(days=5)
    )


async def test_expired_then_extended_reactivates(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    start = (date.today() - timedelta(days=400)).isoformat()
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(
            ctx["customer_id"], ctx["package_id"], ctx["address_id"], start_date=start
        ),
    )).json()

    got = await client.get(f"/api/v1/subscriptions/{sub['id']}", headers=h)
    assert got.json()["status"] == "EXPIRED"

    future = (date.today() + timedelta(days=30)).isoformat()
    ext = await client.post(
        f"/api/v1/subscriptions/{sub['id']}/extend",
        headers=h,
        json={"new_end_date": future, "reason": "goodwill"},
    )
    assert ext.json()["status"] == "ACTIVE"
    assert ext.json()["expected_end_date"] == future


async def test_pause_requires_active(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h, cid, pid, aid = (
        ctx["h"], ctx["customer_id"], ctx["package_id"], ctx["address_id"]
    )
    await client.post("/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid))
    pending = (await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid)
    )).json()
    r = await client.post(
        f"/api/v1/subscriptions/{pending['id']}/pause", headers=h, json={"reason": "x"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NOT_ACTIVE"


# --- meal adjustments --------------------------------------------


async def test_negative_adjustment_to_zero_completes(
    client: AsyncClient, db_session: AsyncSession, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )).json()

    r = await client.post(
        f"/api/v1/subscriptions/{sub['id']}/meal-adjustments",
        headers=h,
        json={"quantity": -25, "reason": "correction"},
    )
    assert r.status_code == 200
    assert r.json()["meals_remaining"] == 0
    assert r.json()["status"] == "COMPLETED"

    actions = (
        (await db_session.execute(
            select(AuditLog.action).where(AuditLog.entity_type == "subscription")
        )).scalars().all()
    )
    assert "MEAL_ADJUSTED" in actions


async def test_adjustment_cannot_make_balance_negative(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )).json()
    r = await client.post(
        f"/api/v1/subscriptions/{sub['id']}/meal-adjustments",
        headers=h,
        json={"quantity": -26, "reason": "oops"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NEGATIVE_BALANCE"


# --- RBAC ------------------------------------------------------


async def test_staff_cannot_extend_cancel_or_adjust(
    client: AsyncClient,
    ctx: dict[str, object],
    staff_user: User,
    auth_headers: MakeHeaders,
) -> None:
    admin_h = ctx["h"]
    staff_h = auth_headers(staff_user)
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=admin_h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )).json()
    sid = sub["id"]

    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/extend",
        headers=staff_h,
        json={"days": 5, "reason": "x"},
    )).status_code == 403
    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/cancel", headers=staff_h, json={"reason": "x"}
    )).status_code == 403
    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/meal-adjustments",
        headers=staff_h,
        json={"quantity": 1, "reason": "x"},
    )).status_code == 403
    # STAFF can still pause.
    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/pause", headers=staff_h, json={"reason": "x"}
    )).status_code == 200


# --- renewal ------------------------------------------------


async def test_renew_creates_linked_pending_with_different_package(
    client: AsyncClient, db_session: AsyncSession, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    other_pkg = await make_package(
        client, h, name="50 Meal", number_of_meals=50, validity_days=100
    )
    sub = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )).json()

    renewed = await client.post(
        f"/api/v1/subscriptions/{sub['id']}/renew",
        headers=h,
        json={
            "package_id": other_pkg,
            "start_date": date.today().isoformat(),
            "delivery_frequency": "DAILY",
            "delivery_time_slots": ["MORNING"],
            "delivery_address_id": ctx["address_id"],
        },
    )
    assert renewed.status_code == 201, renewed.text
    body = renewed.json()
    assert body["status"] == "PENDING"
    assert body["previous_subscription_id"] == sub["id"]
    assert body["snapshot_number_of_meals"] == 50
    assert body["meals_remaining"] == 50  # no carry-over

    row = await db_session.get(Subscription, body["id"])
    assert row is not None
    events = (await client.get(
        f"/api/v1/subscriptions/{body['id']}/events", headers=h
    )).json()
    assert {e["event_type"] for e in events} == {"RENEWED"}


# --- package referenced -----------------------------------


async def test_used_package_cannot_be_deleted(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )
    r = await client.delete(f"/api/v1/packages/{ctx['package_id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "PACKAGE_IN_USE"


async def test_inactive_package_cannot_be_assigned(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h = ctx["h"]
    await client.post(f"/api/v1/packages/{ctx['package_id']}/deactivate", headers=h)
    r = await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(ctx["customer_id"], ctx["package_id"], ctx["address_id"]),
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "PACKAGE_INACTIVE"


# --- customer detail summary --------------------------


async def test_customer_detail_includes_subscription_summary(
    client: AsyncClient, ctx: dict[str, object]
) -> None:
    h, cid, pid, aid = (
        ctx["h"], ctx["customer_id"], ctx["package_id"], ctx["address_id"]
    )
    await client.post("/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid))
    # A queued renewal must not hide the ACTIVE subscription in the summary.
    await client.post("/api/v1/subscriptions", headers=h, json=sub_payload(cid, pid, aid))
    detail = (await client.get(f"/api/v1/customers/{cid}", headers=h)).json()
    assert detail["subscriptions"]["current"]["status"] == "ACTIVE"
    assert detail["subscriptions"]["past_count"] == 0
