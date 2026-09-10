"""Business closed-day calendar (tech_doc.md §6.7, BR-28).

The weekly closed day is the ``closed_weekday`` setting; this table holds one-off
holidays. Adding one cancels any non-terminal deliveries already scheduled for
that date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.delivery import Holiday
from app.models.enums import DeliveryStatus
from app.repositories import delivery_repo
from app.services import audit_service


async def list_holidays(
    session: AsyncSession, *, start: date | None, end: date | None
) -> list[Holiday]:
    return await delivery_repo.list_holidays(session, start=start, end=end)


async def add_holiday(
    session: AsyncSession, holiday_date: date, name: str, *, actor_id: int | None
) -> Holiday:
    holiday = Holiday(holiday_date=holiday_date, name=name, created_by=actor_id)
    session.add(holiday)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "A holiday is already recorded for this date", code="HOLIDAY_EXISTS"
        ) from exc

    cancelled = 0
    for delivery in await delivery_repo.non_terminal_on_date(session, holiday_date):
        delivery.status = DeliveryStatus.CANCELLED
        delivery.notes = (
            f"{delivery.notes}; holiday: {name}" if delivery.notes else f"holiday: {name}"
        )
        cancelled += 1
    await session.flush()

    await audit_service.record(
        session,
        action="HOLIDAY_ADDED",
        entity_type="holiday",
        entity_id=holiday.id,
        actor_id=actor_id,
        metadata={"date": holiday_date.isoformat(), "cancelled_deliveries": cancelled},
    )
    return holiday


async def remove_holiday(
    session: AsyncSession, holiday_id: int, *, actor_id: int | None
) -> None:
    holiday = await delivery_repo.get_holiday(session, holiday_id)
    if holiday is None:
        raise NotFoundError("Holiday not found")
    await session.delete(holiday)
    await session.flush()
    await audit_service.record(
        session,
        action="HOLIDAY_REMOVED",
        entity_type="holiday",
        entity_id=holiday_id,
        actor_id=actor_id,
    )
