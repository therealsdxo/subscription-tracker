"""Query helpers for ``deliveries``, ``planned_skips`` and ``holidays``."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.delivery import Delivery, Holiday, PlannedSkip
from app.models.enums import TERMINAL_DELIVERY_STATUSES
from app.models.subscription import Subscription


async def get_by_id(session: AsyncSession, delivery_id: int) -> Delivery | None:
    return await session.get(Delivery, delivery_id)


async def for_subscription(
    session: AsyncSession, subscription_id: int
) -> list[Delivery]:
    stmt = (
        select(Delivery)
        .where(Delivery.subscription_id == subscription_id)
        .order_by(Delivery.delivery_date, Delivery.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_for_date(
    session: AsyncSession,
    *,
    on_date: date,
    status: object | None,
    area: str | None,
    time_slot: object | None,
    subscription_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Delivery, Subscription, Customer]], int]:
    stmt = (
        select(Delivery, Subscription, Customer)
        .join(Subscription, Delivery.subscription_id == Subscription.id)
        .join(Customer, Delivery.customer_id == Customer.id)
        .where(Delivery.delivery_date == on_date)
    )
    if status is not None:
        stmt = stmt.where(Delivery.status == status)
    if time_slot is not None:
        stmt = stmt.where(Delivery.time_slot == time_slot)
    if subscription_id is not None:
        stmt = stmt.where(Delivery.subscription_id == subscription_id)
    if area:
        stmt = stmt.where(
            Subscription.snapshot_delivery_address["area"].astext.ilike(f"%{area}%")
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(Delivery.time_slot, Customer.name, Delivery.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [(d, s, c) for (d, s, c) in rows], total  # noqa: C416


async def non_terminal_in_range(
    session: AsyncSession, subscription_id: int, start: date, end: date
) -> list[Delivery]:
    stmt = select(Delivery).where(
        Delivery.subscription_id == subscription_id,
        Delivery.delivery_date >= start,
        Delivery.delivery_date <= end,
        Delivery.status.notin_(TERMINAL_DELIVERY_STATUSES),
    )
    return list((await session.execute(stmt)).scalars().all())


async def non_terminal_on_date(
    session: AsyncSession, on_date: date
) -> list[Delivery]:
    stmt = select(Delivery).where(
        Delivery.delivery_date == on_date,
        Delivery.status.notin_(TERMINAL_DELIVERY_STATUSES),
    )
    return list((await session.execute(stmt)).scalars().all())


# --- planned skips -----------------------------------------------------


async def skip_covers(
    session: AsyncSession, subscription_id: int, on_date: date
) -> bool:
    stmt = select(
        select(PlannedSkip.id)
        .where(
            PlannedSkip.subscription_id == subscription_id,
            PlannedSkip.skip_date_from <= on_date,
            PlannedSkip.skip_date_to >= on_date,
        )
        .exists()
    )
    return bool((await session.execute(stmt)).scalar_one())


async def skips_for_subscription(
    session: AsyncSession, subscription_id: int
) -> list[PlannedSkip]:
    stmt = (
        select(PlannedSkip)
        .where(PlannedSkip.subscription_id == subscription_id)
        .order_by(PlannedSkip.skip_date_from, PlannedSkip.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_skip(
    session: AsyncSession, subscription_id: int, skip_id: int
) -> PlannedSkip | None:
    stmt = select(PlannedSkip).where(
        PlannedSkip.id == skip_id, PlannedSkip.subscription_id == subscription_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


# --- holidays ---------------------------------------------------------


async def is_holiday(session: AsyncSession, on_date: date) -> bool:
    stmt = select(
        select(Holiday.id).where(Holiday.holiday_date == on_date).exists()
    )
    return bool((await session.execute(stmt)).scalar_one())


async def holiday_on(session: AsyncSession, on_date: date) -> Holiday | None:
    stmt = select(Holiday).where(Holiday.holiday_date == on_date)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_holiday(session: AsyncSession, holiday_id: int) -> Holiday | None:
    return await session.get(Holiday, holiday_id)


async def list_holidays(
    session: AsyncSession, *, start: date | None, end: date | None
) -> list[Holiday]:
    stmt = select(Holiday).order_by(Holiday.holiday_date)
    if start is not None:
        stmt = stmt.where(Holiday.holiday_date >= start)
    if end is not None:
        stmt = stmt.where(Holiday.holiday_date <= end)
    return list((await session.execute(stmt)).scalars().all())
