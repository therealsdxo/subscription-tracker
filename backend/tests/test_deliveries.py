"""Delivery generation, recording, reversal, planned skips (tech_doc.md §6)."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus
from app.models.subscription import Subscription
from app.models.user import User
from tests.test_subscriptions import make_customer, make_package, sub_payload

# 25-meal / 50-day package starting Tue 01 Sep 2026 → window 01 Sep … 21 Oct.
START = "2026-09-01"
MONDAY = "2026-09-07"      # open day inside the window
TUESDAY = "2026-09-08"     # weekly closed day
WEDNESDAY = "2026-09-09"

Headers = dict[str, str]


@pytest.fixture
async def sub(client: AsyncClient, admin_user: User, auth_headers) -> dict[str, object]:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    body = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date=START),
    )).json()
    return {"h": h, "id": body["id"], "customer_id": cid, "package_id": pkg,
            "address_id": aid}


async def _generate(client: AsyncClient, h: Headers, d: str) -> dict:
    r = await client.post("/api/v1/deliveries/generate", headers=h, json={"date": d})
    assert r.status_code == 200, r.text
    return r.json()


# --- generation -----------------------------------------------------


async def test_generate_creates_one_scheduled_and_is_idempotent(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h = sub["h"]
    first = await _generate(client, h, MONDAY)
    assert first == {"date": MONDAY, "created": 1, "open_day": True}

    again = await _generate(client, h, MONDAY)
    assert again["created"] == 0

    listed = await client.get(f"/api/v1/deliveries?date={MONDAY}", headers=h)
    assert listed.json()["total"] == 1
    row = listed.json()["items"][0]
    assert row["status"] == "SCHEDULED"
    assert row["meal_quantity"] == 1
    assert row["customer_code"] == "CUST-000001"


async def test_no_generation_on_closed_weekday(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    result = await _generate(client, sub["h"], TUESDAY)
    assert result == {"date": TUESDAY, "created": 0, "open_day": False}
    listed = await client.get(f"/api/v1/deliveries?date={TUESDAY}", headers=sub["h"])
    assert listed.json()["total"] == 0


async def test_no_generation_on_holiday(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h = sub["h"]
    await client.post(
        "/api/v1/holidays", headers=h, json={"holiday_date": WEDNESDAY, "name": "Onam"}
    )
    result = await _generate(client, h, WEDNESDAY)
    assert result["created"] == 0 and result["open_day"] is False


async def test_specific_weekdays_frequency(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(
            cid, pkg, aid, start_date=START,
            delivery_frequency="SPECIFIC_WEEKDAYS", delivery_weekdays=[1],  # Mondays
        ),
    )
    assert (await _generate(client, h, MONDAY))["created"] == 1
    assert (await _generate(client, h, WEDNESDAY))["created"] == 0


async def test_planned_skip_suppresses_generation(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    await client.post(
        f"/api/v1/subscriptions/{sid}/skips",
        headers=h,
        json={"skip_date_from": MONDAY, "skip_date_to": MONDAY, "reason": "away"},
    )
    assert (await _generate(client, h, MONDAY))["created"] == 0


async def test_no_generation_for_paused_subscription(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    await client.post(
        f"/api/v1/subscriptions/{sid}/pause", headers=h, json={"reason": "x"}
    )
    assert (await _generate(client, h, MONDAY))["created"] == 0


# --- recording outcomes -------------------------------------------


async def _one_delivery(client: AsyncClient, h: Headers, d: str) -> int:
    await _generate(client, h, d)
    listed = await client.get(f"/api/v1/deliveries?date={d}", headers=h)
    return int(listed.json()["items"][0]["id"])


async def test_mark_delivered_decrements_balance(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    did = await _one_delivery(client, h, MONDAY)

    r = await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "DELIVERED"
    assert r.json()["meals_deducted"] == 1

    detail = await client.get(f"/api/v1/subscriptions/{sid}", headers=h)
    assert detail.json()["meals_remaining"] == 24
    assert detail.json()["meals_consumed"] == 1


async def test_multi_meal_delivery(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    s = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date=START, meals_per_delivery=2),
    )).json()
    did = await _one_delivery(client, h, MONDAY)
    r = await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    assert r.json()["meals_deducted"] == 2
    detail = await client.get(f"/api/v1/subscriptions/{s['id']}", headers=h)
    assert detail.json()["meals_remaining"] == 23


async def test_delivered_completes_when_balance_hits_zero(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h, number_of_meals=1)
    cid, aid = await make_customer(client, h)
    s = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date=START),
    )).json()
    did = await _one_delivery(client, h, MONDAY)
    await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    detail = await client.get(f"/api/v1/subscriptions/{s['id']}", headers=h)
    assert detail.json()["status"] == "COMPLETED"
    assert detail.json()["meals_remaining"] == 0


async def test_skipped_does_not_touch_balance(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    did = await _one_delivery(client, h, MONDAY)
    await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "SKIPPED"}
    )
    detail = await client.get(f"/api/v1/subscriptions/{sid}", headers=h)
    assert detail.json()["meals_remaining"] == 25


async def test_delivered_blocked_on_cancelled_subscription(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    did = await _one_delivery(client, h, MONDAY)
    await client.post(
        f"/api/v1/subscriptions/{sid}/cancel", headers=h, json={"reason": "x"}
    )
    r = await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SUBSCRIPTION_NOT_ACTIVE"


async def test_double_mark_delivered_is_rejected(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    did = await _one_delivery(client, h, MONDAY)
    assert (await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )).status_code == 200
    second = await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DELIVERY_FINALISED"
    detail = await client.get(f"/api/v1/subscriptions/{sid}", headers=h)
    assert detail.json()["meals_remaining"] == 24  # moved exactly once


# --- reversal ---------------------------------------------------


async def test_reverse_restores_balance_and_reopens(
    client: AsyncClient,
    db_session: AsyncSession,
    sub: dict[str, object],
) -> None:
    h, sid = sub["h"], sub["id"]
    did = await _one_delivery(client, h, MONDAY)
    await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    r = await client.post(
        f"/api/v1/deliveries/{did}/reverse", headers=h, json={"reason": "wrong entry"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SCHEDULED"
    assert r.json()["reversed"] is True
    assert r.json()["meals_deducted"] == 0

    detail = await client.get(f"/api/v1/subscriptions/{sid}", headers=h)
    assert detail.json()["meals_remaining"] == 25

    actions = (
        (await db_session.execute(
            select(AuditLog.action).where(AuditLog.entity_type == "delivery")
        )).scalars().all()
    )
    assert "DELIVERY_REVERSED" in actions


async def test_reverse_rolls_completed_back_to_active(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h, number_of_meals=1)
    cid, aid = await make_customer(client, h)
    s = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date=START),
    )).json()
    did = await _one_delivery(client, h, MONDAY)
    await client.patch(
        f"/api/v1/deliveries/{did}", headers=h, json={"status": "DELIVERED"}
    )
    assert (await client.get(
        f"/api/v1/subscriptions/{s['id']}", headers=h
    )).json()["status"] == "COMPLETED"

    await client.post(
        f"/api/v1/deliveries/{did}/reverse", headers=h, json={"reason": "oops"}
    )
    detail = await client.get(f"/api/v1/subscriptions/{s['id']}", headers=h)
    assert detail.json()["status"] == "ACTIVE"
    assert detail.json()["meals_remaining"] == 1


async def test_cannot_reverse_non_delivered(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h = sub["h"]
    did = await _one_delivery(client, h, MONDAY)
    r = await client.post(
        f"/api/v1/deliveries/{did}/reverse", headers=h, json={"reason": "x"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NOT_REVERSIBLE"


# --- holidays / skips cancel existing deliveries ---------------


async def test_adding_holiday_cancels_existing_deliveries(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h = sub["h"]
    did = await _one_delivery(client, h, MONDAY)
    await client.post(
        "/api/v1/holidays", headers=h, json={"holiday_date": MONDAY, "name": "Strike"}
    )
    got = await client.get(f"/api/v1/deliveries?date={MONDAY}", headers=h)
    row = next(r for r in got.json()["items"] if r["id"] == did)
    assert row["status"] == "CANCELLED"


async def test_adding_skip_cancels_existing_deliveries(
    client: AsyncClient, sub: dict[str, object]
) -> None:
    h, sid = sub["h"], sub["id"]
    await _one_delivery(client, h, MONDAY)
    await client.post(
        f"/api/v1/subscriptions/{sid}/skips",
        headers=h,
        json={"skip_date_from": MONDAY, "skip_date_to": MONDAY},
    )
    got = await client.get(f"/api/v1/deliveries?date={MONDAY}", headers=h)
    assert got.json()["items"][0]["status"] == "SKIPPED"


# --- RBAC -----------------------------------------------------


async def test_staff_can_record_admin_only_for_holidays(
    client: AsyncClient,
    sub: dict[str, object],
    staff_user: User,
    auth_headers,
) -> None:
    staff_h = auth_headers(staff_user)
    did = await _one_delivery(client, sub["h"], MONDAY)

    assert (await client.patch(
        f"/api/v1/deliveries/{did}", headers=staff_h, json={"status": "DELIVERED"}
    )).status_code == 200
    assert (await client.post(
        "/api/v1/holidays",
        headers=staff_h,
        json={"holiday_date": WEDNESDAY, "name": "x"},
    )).status_code == 403


async def test_generation_uses_row_lock_across_transactions(
    _engine, admin_user: User, staff_user: User
) -> None:
    """Two real transactions marking the same delivery DELIVERED — the balance
    moves exactly once."""
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services import delivery_service

    # Build committed fixture data on its own connection.
    async with AsyncSession(_engine, expire_on_commit=False) as s:
        from app.core.security import hash_password
        from app.models.customer import Customer, CustomerAddress
        from app.models.enums import (
            DeliveryFrequency,
            PackageStatus,
            SubscriptionStatus,
            TimeSlot,
            UserRole,
        )
        from app.models.package import Package
        from app.models.user import User as U

        u = U(email="conc@example.com", full_name="C",
              password_hash=hash_password("x" * 10), role=UserRole.ADMIN, is_active=True)
        cust = Customer(customer_code="CUST-900001", name="Conc", phone="900900900",
                        is_active=True)
        addr = CustomerAddress(address_line="1", area="A", city="B", pincode="560001",
                               is_primary=True, is_active=True)
        cust.addresses.append(addr)
        pkg = Package(package_code="PKG-90001", name="P", number_of_meals=25,
                      validity_days=50, base_price=0, tax_amount=0, final_price=0,
                      status=PackageStatus.ACTIVE)
        s.add_all([u, cust, pkg])
        await s.flush()
        sub = Subscription(
            subscription_code="SUB-900001", customer_id=cust.id, package_id=pkg.id,
            subscription_number=1, status=SubscriptionStatus.ACTIVE,
            start_date=date(2026, 9, 1), original_end_date=date(2026, 10, 21),
            expected_end_date=date(2026, 10, 21), snapshot_package_name="P",
            snapshot_number_of_meals=25, snapshot_validity_days=50,
            snapshot_base_price=0, snapshot_tax_amount=0, snapshot_final_price=0,
            meals_allocated=25, meals_consumed=0, meals_adjustment=0,
            delivery_frequency=DeliveryFrequency.DAILY, meals_per_delivery=1,
            delivery_time_slots=[TimeSlot.MORNING], snapshot_delivery_address={},
        )
        s.add(sub)
        await s.flush()
        deliv = Delivery(subscription_id=sub.id, customer_id=cust.id,
                         delivery_date=date(2026, 9, 7), time_slot=TimeSlot.MORNING,
                         status=DeliveryStatus.SCHEDULED, meal_quantity=1)
        s.add(deliv)
        await s.commit()
        did, sid, uid = deliv.id, sub.id, u.id

    async def _mark() -> str:
        async with AsyncSession(_engine, expire_on_commit=False) as s:
            try:
                await delivery_service.set_status(
                    s, did, new_status=DeliveryStatus.DELIVERED, time_slot=None,
                    notes=None, rescheduled_to_date=None, time_slot_note=None,
                    actor_id=uid,
                )
                await s.commit()
                return "ok"
            except Exception as exc:  # noqa: BLE001
                await s.rollback()
                return type(exc).__name__

    try:
        results = await asyncio.gather(_mark(), _mark())
        assert results.count("ok") == 1, results

        async with AsyncSession(_engine, expire_on_commit=False) as s:
            row = await s.get(Subscription, sid)
            assert row is not None
            await s.refresh(row, ["meals_remaining"])
            assert row.meals_consumed == 1
            assert row.meals_remaining == 24
    finally:
        from sqlalchemy import text

        async with AsyncSession(_engine) as s:
            await s.execute(text("DELETE FROM audit_logs WHERE entity_type = 'delivery'"))
            await s.execute(text("DELETE FROM deliveries WHERE id = :i"), {"i": did})
            await s.execute(
                text("DELETE FROM subscriptions WHERE id = :i"), {"i": sid}
            )
            await s.execute(
                text("DELETE FROM customer_addresses WHERE customer_id IN "
                     "(SELECT id FROM customers WHERE customer_code = 'CUST-900001')")
            )
            await s.execute(
                text("DELETE FROM customers WHERE customer_code = 'CUST-900001'")
            )
            await s.execute(text("DELETE FROM packages WHERE package_code = 'PKG-90001'"))
            await s.execute(text("DELETE FROM users WHERE id = :i"), {"i": uid})
            await s.commit()
