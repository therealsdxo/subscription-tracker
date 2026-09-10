"""Query helpers for ``subscriptions`` and its child tables."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription, SubscriptionEvent

_ACTIVE_LIKE = (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED)
_NON_TERMINAL = (
    SubscriptionStatus.PENDING,
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.PAUSED,
)
_TERMINAL = (
    SubscriptionStatus.COMPLETED,
    SubscriptionStatus.EXPIRED,
    SubscriptionStatus.CANCELLED,
)


async def get_by_id(session: AsyncSession, subscription_id: int) -> Subscription | None:
    return await session.get(Subscription, subscription_id)


async def get_with_events(
    session: AsyncSession, subscription_id: int
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.id == subscription_id)
        .options(selectinload(Subscription.events))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active_for_customer(
    session: AsyncSession, customer_id: int
) -> Subscription | None:
    stmt = select(Subscription).where(
        Subscription.customer_id == customer_id,
        Subscription.status == SubscriptionStatus.ACTIVE,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_for_customer(session: AsyncSession, customer_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.customer_id == customer_id)
    )
    return (await session.execute(stmt)).scalar_one()


async def next_pending_for_customer(
    session: AsyncSession, customer_id: int, *, on_date: date
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(
            Subscription.customer_id == customer_id,
            Subscription.status == SubscriptionStatus.PENDING,
            Subscription.start_date <= on_date,
        )
        .order_by(Subscription.start_date, Subscription.id)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def customer_summary(
    session: AsyncSession, customer_id: int
) -> tuple[Subscription | None, int]:
    # Prefer the ACTIVE / PAUSED subscription; fall back to the most recent
    # PENDING one.
    order = case(
        (Subscription.status == SubscriptionStatus.ACTIVE, 0),
        (Subscription.status == SubscriptionStatus.PAUSED, 1),
        else_=2,
    )
    current = (
        await session.execute(
            select(Subscription)
            .where(
                Subscription.customer_id == customer_id,
                Subscription.status.in_(_NON_TERMINAL),
            )
            .order_by(order, Subscription.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    past = (
        await session.execute(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.customer_id == customer_id,
                Subscription.status.in_(_TERMINAL),
            )
        )
    ).scalar_one()
    return current, past


async def package_in_use(session: AsyncSession, package_id: int) -> bool:
    stmt = select(
        select(Subscription.id).where(Subscription.package_id == package_id).exists()
    )
    return bool((await session.execute(stmt)).scalar_one())


async def due_for_activation(
    session: AsyncSession, *, on_date: date
) -> list[Subscription]:
    stmt = (
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.PENDING,
            Subscription.start_date <= on_date,
        )
        .order_by(Subscription.customer_id, Subscription.start_date, Subscription.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def overdue(session: AsyncSession, *, on_date: date) -> list[Subscription]:
    stmt = select(Subscription).where(
        Subscription.status.in_(_ACTIVE_LIKE),
        Subscription.expected_end_date < on_date,
    )
    return list((await session.execute(stmt)).scalars().all())


async def active_in_window(
    session: AsyncSession, *, on_date: date
) -> list[Subscription]:
    """ACTIVE subscriptions eligible for a delivery on ``on_date`` (tech_doc §6.1)."""
    stmt = (
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.start_date <= on_date,
            Subscription.expected_end_date >= on_date,
            Subscription.meals_remaining > 0,
        )
        .order_by(Subscription.id)
    )
    return list((await session.execute(stmt)).scalars().all())


def _search_stmt(
    *,
    status: SubscriptionStatus | None,
    customer_id: int | None,
    expiring: bool,
    dues: bool,
    today: date,
    days_threshold: int,
    meals_threshold: int,
) -> tuple[Select[tuple[Subscription]], Select[tuple[int]]]:
    conditions = []
    if status is not None:
        conditions.append(Subscription.status == status)
    if customer_id is not None:
        conditions.append(Subscription.customer_id == customer_id)
    if expiring:
        conditions.append(Subscription.status.in_(_ACTIVE_LIKE))
        conditions.append(
            or_(
                Subscription.expected_end_date <= today + timedelta(days=days_threshold),
                Subscription.meals_remaining <= meals_threshold,
            )
        )
    if dues:
        from app.repositories.payment_repo import outstanding_expr

        conditions.append(outstanding_expr())
    stmt = select(Subscription)
    count_stmt = select(func.count()).select_from(Subscription)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    return stmt, count_stmt


async def search(
    session: AsyncSession,
    *,
    status: SubscriptionStatus | None,
    customer_id: int | None,
    expiring: bool,
    dues: bool,
    today: date,
    days_threshold: int,
    meals_threshold: int,
    limit: int,
    offset: int,
) -> tuple[list[Subscription], int]:
    stmt, count_stmt = _search_stmt(
        status=status,
        customer_id=customer_id,
        expiring=expiring,
        dues=dues,
        today=today,
        days_threshold=days_threshold,
        meals_threshold=meals_threshold,
    )
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (
            await session.execute(
                stmt.order_by(Subscription.id).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total


async def events_for(
    session: AsyncSession, subscription_id: int
) -> list[SubscriptionEvent]:
    stmt = (
        select(SubscriptionEvent)
        .where(SubscriptionEvent.subscription_id == subscription_id)
        .order_by(SubscriptionEvent.id)
    )
    return list((await session.execute(stmt)).scalars().all())
