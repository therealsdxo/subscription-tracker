"""Payments and refunds (tech_doc.md §4.6, §7).

Payment state is derived from the ``payments`` / ``refunds`` rows and never
gates activation or delivery recording (BR-27).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.payment import Payment, Refund
from app.models.subscription import Subscription
from app.repositories import payment_repo, subscription_repo
from app.schemas.payment import PaymentCreate, PaymentSummary, RefundCreate
from app.services import audit_service
from app.services.subscription_service import business_today

_ZERO = Decimal("0.00")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_summary(
    *,
    final_price: Decimal,
    meals_allocated: int,
    meals_remaining: int,
    total_paid: Decimal,
    total_refunded: Decimal,
) -> PaymentSummary:
    net_paid = total_paid - total_refunded
    outstanding = max(final_price - net_paid, _ZERO)

    if total_refunded > 0:
        status = PaymentStatus.REFUNDED
    elif total_paid == 0:
        status = PaymentStatus.UNPAID
    elif net_paid >= final_price:
        status = PaymentStatus.PAID
    else:
        status = PaymentStatus.PARTIALLY_PAID

    suggested = (
        _q(final_price * Decimal(meals_remaining) / Decimal(meals_allocated))
        if meals_allocated
        else _ZERO
    )
    return PaymentSummary(
        payment_status=status,
        total_paid=_q(total_paid),
        total_refunded=_q(total_refunded),
        net_paid=_q(net_paid),
        outstanding_amount=_q(outstanding),
        suggested_refund=suggested,
    )


async def summary(session: AsyncSession, sub: Subscription) -> PaymentSummary:
    total_paid, total_refunded = await payment_repo.totals(session, sub.id)
    return _build_summary(
        final_price=sub.snapshot_final_price,
        meals_allocated=sub.meals_allocated,
        meals_remaining=sub.meals_remaining,
        total_paid=total_paid,
        total_refunded=total_refunded,
    )


async def summaries_for(
    session: AsyncSession, subs: Sequence[Subscription]
) -> dict[int, PaymentSummary]:
    totals = await payment_repo.totals_for_many(session, [s.id for s in subs])
    return {
        s.id: _build_summary(
            final_price=s.snapshot_final_price,
            meals_allocated=s.meals_allocated,
            meals_remaining=s.meals_remaining,
            total_paid=totals[s.id][0],
            total_refunded=totals[s.id][1],
        )
        for s in subs
    }


async def _get_subscription(session: AsyncSession, subscription_id: int) -> Subscription:
    sub = await subscription_repo.get_by_id(session, subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found")
    return sub


def _resolve_date(supplied: date | None) -> date:
    today = business_today()
    if supplied is None:
        return today
    if supplied > today:
        raise ValidationError("The date cannot be in the future")
    return supplied


async def record_payment(
    session: AsyncSession,
    subscription_id: int,
    payload: PaymentCreate,
    *,
    actor_id: int | None,
) -> Payment:
    sub = await _get_subscription(session, subscription_id)
    payment = Payment(
        subscription_id=sub.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        payment_date=_resolve_date(payload.payment_date),
        notes=payload.notes,
        recorded_by=actor_id,
    )
    session.add(payment)
    await session.flush()
    await audit_service.record(
        session,
        action="PAYMENT_RECORDED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={
            "payment_id": payment.id,
            "amount": str(payment.amount),
            "method": payment.payment_method.value,
        },
    )
    return payment


async def issue_refund(
    session: AsyncSession,
    subscription_id: int,
    payload: RefundCreate,
    *,
    actor_id: int | None,
) -> Refund:
    sub = await _get_subscription(session, subscription_id)
    total_paid, total_refunded = await payment_repo.totals(session, sub.id)
    net_paid = total_paid - total_refunded
    if payload.amount > net_paid:
        raise ValidationError(
            "A refund cannot exceed the net amount paid "
            f"(net paid: {_q(net_paid)})",
            code="REFUND_EXCEEDS_PAID",
        )

    refund = Refund(
        subscription_id=sub.id,
        amount=payload.amount,
        refund_date=_resolve_date(payload.refund_date),
        reason=payload.reason,
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        recorded_by=actor_id,
    )
    session.add(refund)
    await session.flush()
    await audit_service.record(
        session,
        action="REFUND_ISSUED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={
            "refund_id": refund.id,
            "amount": str(refund.amount),
            "reason": refund.reason,
        },
    )
    return refund


async def payments_view(
    session: AsyncSession, subscription_id: int
) -> tuple[PaymentSummary, list[Payment], list[Refund]]:
    sub = await _get_subscription(session, subscription_id)
    return (
        await summary(session, sub),
        await payment_repo.payments_for(session, sub.id),
        await payment_repo.refunds_for(session, sub.id),
    )


async def list_payments(
    session: AsyncSession,
    *,
    subscription_id: int | None,
    customer_id: int | None,
    method: PaymentMethod | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> tuple[list[Payment], int]:
    return await payment_repo.list_payments(
        session,
        subscription_id=subscription_id,
        customer_id=customer_id,
        method=method,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


async def get_payment(session: AsyncSession, payment_id: int) -> Payment:
    payment = await payment_repo.get_payment(session, payment_id)
    if payment is None:
        raise NotFoundError("Payment not found")
    return payment
