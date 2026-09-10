"""Payment / refund tests (tech_doc.md §4.6, §7)."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from tests.test_subscriptions import make_customer, make_package, sub_payload

Headers = dict[str, str]
_phone_seq = iter(range(9000000100, 9000009999))


async def _make_subscription(
    client: AsyncClient, h: Headers, **pkg_over: object
) -> int:
    pkg = await make_package(client, h, **pkg_over)
    cid, aid = await make_customer(client, h, phone=str(next(_phone_seq)))
    body = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date="2026-09-01"),
    )).json()
    return int(body["id"])


async def _pay(client: AsyncClient, h: Headers, sid: int, amount: str) -> dict:
    r = await client.post(
        f"/api/v1/subscriptions/{sid}/payments",
        headers=h,
        json={"amount": amount, "payment_method": "UPI"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _summary(client: AsyncClient, h: Headers, sid: int) -> dict:
    return (await client.get(f"/api/v1/subscriptions/{sid}", headers=h)).json()


async def test_unpaid_when_no_payments(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    s = await _summary(client, h, sid)
    assert s["payment_status"] == "UNPAID"
    assert s["total_paid"] == "0.00"
    assert s["outstanding_amount"] == "6500.00"


async def test_partial_then_full_payment(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)

    await _pay(client, h, sid, "2500.00")
    s = await _summary(client, h, sid)
    assert s["payment_status"] == "PARTIALLY_PAID"
    assert s["outstanding_amount"] == "4000.00"

    await _pay(client, h, sid, "4000.00")
    s = await _summary(client, h, sid)
    assert s["payment_status"] == "PAID"
    assert s["net_paid"] == "6500.00"
    assert s["outstanding_amount"] == "0.00"


async def test_overpayment_clamps_outstanding(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    await _pay(client, h, sid, "7000.00")
    s = await _summary(client, h, sid)
    assert s["payment_status"] == "PAID"
    assert s["outstanding_amount"] == "0.00"


async def test_refund_marks_refunded_and_reduces_net_paid(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    await _pay(client, h, sid, "6500.00")

    r = await client.post(
        f"/api/v1/subscriptions/{sid}/refunds",
        headers=h,
        json={"amount": "1500.00", "reason": "cancelled early", "payment_method": "UPI"},
    )
    assert r.status_code == 201, r.text

    s = await _summary(client, h, sid)
    assert s["payment_status"] == "REFUNDED"
    assert s["net_paid"] == "5000.00"
    assert s["outstanding_amount"] == "1500.00"

    actions = (
        (await db_session.execute(
            select(AuditLog.action).where(AuditLog.entity_type == "subscription")
        )).scalars().all()
    )
    assert {"PAYMENT_RECORDED", "REFUND_ISSUED"} <= set(actions)


async def test_refund_cannot_exceed_net_paid(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    await _pay(client, h, sid, "2000.00")
    r = await client.post(
        f"/api/v1/subscriptions/{sid}/refunds",
        headers=h,
        json={"amount": "2500.00", "reason": "x", "payment_method": "CASH"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "REFUND_EXCEEDS_PAID"


async def test_payment_allowed_on_cancelled_subscription(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    await client.post(
        f"/api/v1/subscriptions/{sid}/cancel", headers=h, json={"reason": "x"}
    )
    await _pay(client, h, sid, "6500.00")  # late payment — still accepted
    assert (await _summary(client, h, sid))["payment_status"] == "PAID"


async def test_staff_can_pay_but_not_refund(
    client: AsyncClient,
    admin_user: User,
    staff_user: User,
    auth_headers,
) -> None:
    admin_h = auth_headers(admin_user)
    staff_h = auth_headers(staff_user)
    sid = await _make_subscription(client, admin_h)

    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/payments",
        headers=staff_h,
        json={"amount": "500.00", "payment_method": "CASH"},
    )).status_code == 201

    assert (await client.post(
        f"/api/v1/subscriptions/{sid}/refunds",
        headers=staff_h,
        json={"amount": "100.00", "reason": "x", "payment_method": "CASH"},
    )).status_code == 403


async def test_dues_filter(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    paid_sid = await _make_subscription(client, h)
    await _pay(client, h, paid_sid, "6500.00")
    _owing_sid = await _make_subscription(client, h)

    listed = await client.get("/api/v1/subscriptions?dues=true", headers=h)
    ids = {row["id"] for row in listed.json()["items"]}
    assert _owing_sid in ids
    assert paid_sid not in ids


async def test_suggested_refund_is_prorated_but_not_applied(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h, number_of_meals=25)
    await _pay(client, h, sid, "6500.00")
    # No deliveries → 25 of 25 meals remain → suggested_refund == full price.
    s = await _summary(client, h, sid)
    assert s["suggested_refund"] == "6500.00"
    # It is guidance only: the status is still PAID, outstanding still 0.
    assert s["payment_status"] == "PAID"
    assert s["outstanding_amount"] == "0.00"


async def test_payment_lookup_endpoints(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    payment = await _pay(client, h, sid, "1000.00")

    listed = await client.get(
        f"/api/v1/payments?subscription_id={sid}", headers=h
    )
    assert listed.json()["total"] == 1

    one = await client.get(f"/api/v1/payments/{payment['id']}", headers=h)
    assert one.json()["amount"] == "1000.00"

    view = await client.get(f"/api/v1/subscriptions/{sid}/payments", headers=h)
    body = view.json()
    assert body["summary"]["payment_status"] == "PARTIALLY_PAID"
    assert len(body["payments"]) == 1 and body["refunds"] == []


async def test_future_dated_payment_rejected(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    sid = await _make_subscription(client, h)
    future = (date.today().replace(year=date.today().year + 1)).isoformat()
    r = await client.post(
        f"/api/v1/subscriptions/{sid}/payments",
        headers=h,
        json={"amount": "100.00", "payment_method": "CASH", "payment_date": future},
    )
    assert r.status_code == 422


async def test_customer_detail_current_subscription_has_payment_status(
    client: AsyncClient, admin_user: User, auth_headers
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    body = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date="2026-09-01"),
    )).json()
    await _pay(client, h, body["id"], "3000.00")

    detail = (await client.get(f"/api/v1/customers/{cid}", headers=h)).json()
    assert detail["subscriptions"]["current"]["payment_status"] == "PARTIALLY_PAID"
    assert detail["subscriptions"]["current"]["outstanding_amount"] == "3500.00"
