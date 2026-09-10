"""Query helpers for ``payments`` and ``refunds``."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentMethod
from app.models.payment import Payment, Refund
from app.models.subscription import Subscription

_ZERO = Decimal("0")


async def get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    return await session.get(Payment, payment_id)


async def payments_for(
    session: AsyncSession, subscription_id: int
) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.subscription_id == subscription_id)
        .order_by(Payment.payment_date, Payment.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def refunds_for(
    session: AsyncSession, subscription_id: int
) -> list[Refund]:
    stmt = (
        select(Refund)
        .where(Refund.subscription_id == subscription_id)
        .order_by(Refund.refund_date, Refund.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def totals(
    session: AsyncSession, subscription_id: int
) -> tuple[Decimal, Decimal]:
    """(total_paid, total_refunded) for one subscription."""
    paid = (
        await session.execute(
            select(func.coalesce(func.sum(Payment.amount), _ZERO)).where(
                Payment.subscription_id == subscription_id
            )
        )
    ).scalar_one()
    refunded = (
        await session.execute(
            select(func.coalesce(func.sum(Refund.amount), _ZERO)).where(
                Refund.subscription_id == subscription_id
            )
        )
    ).scalar_one()
    return Decimal(paid), Decimal(refunded)


async def totals_for_many(
    session: AsyncSession, subscription_ids: Sequence[int]
) -> dict[int, tuple[Decimal, Decimal]]:
    """Batched (total_paid, total_refunded) keyed by subscription id."""
    result: dict[int, tuple[Decimal, Decimal]] = {
        sid: (_ZERO, _ZERO) for sid in subscription_ids
    }
    if not subscription_ids:
        return result

    for sid, paid in (
        await session.execute(
            select(Payment.subscription_id, func.sum(Payment.amount))
            .where(Payment.subscription_id.in_(subscription_ids))
            .group_by(Payment.subscription_id)
        )
    ).all():
        result[sid] = (Decimal(paid), result[sid][1])

    for sid, refunded in (
        await session.execute(
            select(Refund.subscription_id, func.sum(Refund.amount))
            .where(Refund.subscription_id.in_(subscription_ids))
            .group_by(Refund.subscription_id)
        )
    ).all():
        result[sid] = (result[sid][0], Decimal(refunded))

    return result


def outstanding_expr() -> ColumnElement[bool]:
    """Correlated predicate: this subscription still has an outstanding balance."""
    paid = (
        select(func.coalesce(func.sum(Payment.amount), _ZERO))
        .where(Payment.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    refunded = (
        select(func.coalesce(func.sum(Refund.amount), _ZERO))
        .where(Refund.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    return Subscription.snapshot_final_price > (paid - refunded)


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
    stmt = select(Payment)
    if customer_id is not None:
        stmt = stmt.join(
            Subscription, Payment.subscription_id == Subscription.id
        ).where(Subscription.customer_id == customer_id)
    if subscription_id is not None:
        stmt = stmt.where(Payment.subscription_id == subscription_id)
    if method is not None:
        stmt = stmt.where(Payment.payment_method == method)
    if date_from is not None:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Payment.payment_date <= date_to)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total
