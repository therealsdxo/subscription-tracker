"""CSV exports (tech_doc.md §9.3).

Each function yields CSV text row-by-row using the caller's session. The router
joins the chunks and returns them as ``text/csv``. At v1 scale (≤ 10k rows) the
full document is small; true chunked streaming would need a session that
outlives the request handler.
"""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Iterable
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerAddress
from app.models.delivery import Delivery
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.repositories import payment_repo
from app.services import payment_service
from app.services.subscription_service import business_today


class _Sink:
    def __init__(self) -> None:
        self._buf = io.StringIO()
        self._writer = csv.writer(self._buf, lineterminator="\r\n")

    def row(self, values: Iterable[Any]) -> str:
        self._writer.writerow(list(values))
        chunk = self._buf.getvalue()
        self._buf.seek(0)
        self._buf.truncate(0)
        return chunk


async def customers_csv(session: AsyncSession) -> AsyncIterator[str]:
    sink = _Sink()
    yield sink.row(
        [
            "customer_code", "name", "phone", "email", "dietary_preference",
            "allergies", "is_active", "created_at", "address_line", "area",
            "city", "pincode",
        ]
    )
    stmt = (
        select(Customer, CustomerAddress)
        .outerjoin(
            CustomerAddress,
            (CustomerAddress.customer_id == Customer.id)
            & CustomerAddress.is_primary.is_(True)
            & CustomerAddress.is_active.is_(True),
        )
        .order_by(Customer.id)
    )
    for customer, a in (await session.execute(stmt)).all():
        yield sink.row(
            [
                customer.customer_code,
                customer.name,
                customer.phone,
                customer.email or "",
                customer.default_dietary_preference.value
                if customer.default_dietary_preference
                else "",
                customer.allergies or "",
                customer.is_active,
                customer.created_at.date().isoformat(),
                a.address_line if a else "",
                a.area if a else "",
                a.city if a else "",
                a.pincode if a else "",
            ]
        )


async def subscriptions_csv(session: AsyncSession) -> AsyncIterator[str]:
    sink = _Sink()
    yield sink.row(
        [
            "subscription_code", "customer_code", "customer_name", "status",
            "package_name", "start_date", "expected_end_date",
            "meals_allocated", "meals_consumed", "meals_remaining",
            "final_price", "payment_status", "outstanding_amount",
        ]
    )
    ids = list((await session.execute(select(Subscription.id))).scalars().all())
    totals = await payment_repo.totals_for_many(session, ids)
    stmt = (
        select(Subscription, Customer)
        .join(Customer, Subscription.customer_id == Customer.id)
        .order_by(Subscription.id)
    )
    for sub, customer in (await session.execute(stmt)).all():
        paid, refunded = totals[sub.id]
        summary = payment_service.compute_summary(
            final_price=sub.snapshot_final_price,
            meals_allocated=sub.meals_allocated,
            meals_remaining=sub.meals_remaining,
            total_paid=paid,
            total_refunded=refunded,
        )
        yield sink.row(
            [
                sub.subscription_code,
                customer.customer_code,
                customer.name,
                sub.status.value,
                sub.snapshot_package_name,
                sub.start_date.isoformat(),
                sub.expected_end_date.isoformat(),
                sub.meals_allocated,
                sub.meals_consumed,
                sub.meals_remaining,
                f"{sub.snapshot_final_price:.2f}",
                summary.payment_status.value,
                f"{summary.outstanding_amount:.2f}",
            ]
        )


async def payments_csv(session: AsyncSession) -> AsyncIterator[str]:
    sink = _Sink()
    yield sink.row(
        [
            "payment_id", "subscription_code", "customer_code", "amount",
            "method", "reference_number", "payment_date", "recorded_by",
        ]
    )
    stmt = (
        select(Payment, Subscription, Customer)
        .join(Subscription, Payment.subscription_id == Subscription.id)
        .join(Customer, Subscription.customer_id == Customer.id)
        .order_by(Payment.payment_date, Payment.id)
    )
    for payment, sub, customer in (await session.execute(stmt)).all():
        yield sink.row(
            [
                payment.id,
                sub.subscription_code,
                customer.customer_code,
                f"{payment.amount:.2f}",
                payment.payment_method.value,
                payment.reference_number or "",
                payment.payment_date.isoformat(),
                payment.recorded_by or "",
            ]
        )


async def deliveries_csv(
    session: AsyncSession, on_date: date | None = None
) -> AsyncIterator[str]:
    day = on_date or business_today()
    sink = _Sink()
    yield sink.row(
        [
            "delivery_date", "time_slot", "status", "subscription_code",
            "customer_name", "area", "meal_quantity", "meals_deducted",
        ]
    )
    stmt = (
        select(Delivery, Subscription, Customer)
        .join(Subscription, Delivery.subscription_id == Subscription.id)
        .join(Customer, Delivery.customer_id == Customer.id)
        .where(Delivery.delivery_date == day)
        .order_by(Delivery.time_slot, Customer.name, Delivery.id)
    )
    for delivery, sub, customer in (await session.execute(stmt)).all():
        area = (sub.snapshot_delivery_address or {}).get("area", "")
        yield sink.row(
            [
                delivery.delivery_date.isoformat(),
                delivery.time_slot.value,
                delivery.status.value,
                sub.subscription_code,
                customer.name,
                area,
                delivery.meal_quantity,
                delivery.meals_deducted,
            ]
        )
