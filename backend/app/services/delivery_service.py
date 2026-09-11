"""Delivery generation, outcome recording, reversal, and planned skips.

tech_doc.md §6. Only a ``DELIVERED`` outcome moves ``subscriptions.meals_consumed``
(BR-16); reversing one restores the exact amount (BR-30). No deliveries on the
weekly closed day or a holiday (BR-28), and none against a subscription that is
not ACTIVE (BR-29).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.customer import Customer
from app.models.delivery import Delivery, PlannedSkip
from app.models.enums import (
    DELIVERY_PROGRESS_STATUSES,
    TERMINAL_DELIVERY_STATUSES,
    DeliveryFrequency,
    DeliveryStatus,
    SubscriptionStatus,
)
from app.models.subscription import Subscription
from app.repositories import delivery_repo, subscription_repo
from app.services import audit_service, settings_service, subscription_service

business_today = subscription_service.business_today
_DS = DeliveryStatus
_SS = SubscriptionStatus


# --- open days ---------------------------------------------------------


async def is_open_day(session: AsyncSession, d: date) -> bool:
    if d.weekday() == await settings_service.closed_weekday_index(session):
        return False
    return not await delivery_repo.is_holiday(session, d)


def _due_on(sub: Subscription, d: date) -> bool:
    if sub.delivery_frequency is DeliveryFrequency.DAILY:
        return True
    if sub.delivery_frequency is DeliveryFrequency.SPECIFIC_WEEKDAYS:
        return d.isoweekday() in (sub.delivery_weekdays or [])
    dates = (sub.custom_schedule or {}).get("dates", [])
    return d.isoformat() in dates


# --- generation -------------------------------------------------------


async def generate(
    session: AsyncSession, on_date: date, *, actor_id: int | None
) -> dict[str, object]:
    if not await is_open_day(session, on_date):
        return {"date": on_date.isoformat(), "created": 0, "open_day": False}

    created = 0
    for sub in await subscription_repo.active_in_window(session, on_date=on_date):
        if not _due_on(sub, on_date):
            continue
        if await delivery_repo.skip_covers(session, sub.id, on_date):
            continue
        qty = min(sub.meals_per_delivery, sub.meals_remaining)
        for slot in sub.delivery_time_slots:
            stmt = (
                pg_insert(Delivery)
                .values(
                    subscription_id=sub.id,
                    customer_id=sub.customer_id,
                    delivery_date=on_date,
                    time_slot=slot,
                    status=_DS.SCHEDULED,
                    meal_quantity=qty,
                )
                .on_conflict_do_nothing(
                    index_elements=["subscription_id", "delivery_date", "time_slot"]
                )
                .returning(Delivery.id)
            )
            if (await session.execute(stmt)).scalar_one_or_none() is not None:
                created += 1

    await session.flush()
    if created:
        await audit_service.record(
            session,
            action="DELIVERIES_GENERATED",
            entity_type="delivery",
            entity_id=None,
            actor_id=actor_id,
            metadata={"date": on_date.isoformat(), "created": created},
        )
    return {"date": on_date.isoformat(), "created": created, "open_day": True}


# --- reads -----------------------------------------------------------


async def list_for_date(
    session: AsyncSession,
    *,
    on_date: date,
    status: DeliveryStatus | None,
    area: str | None,
    time_slot: object | None,
    subscription_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Delivery, Subscription, Customer]], int]:
    return await delivery_repo.list_for_date(
        session,
        on_date=on_date,
        status=status,
        area=area,
        time_slot=time_slot,
        subscription_id=subscription_id,
        limit=limit,
        offset=offset,
    )


async def for_subscription(
    session: AsyncSession, subscription_id: int
) -> list[Delivery]:
    if await subscription_repo.get_by_id(session, subscription_id) is None:
        raise NotFoundError("Subscription not found")
    return await delivery_repo.for_subscription(session, subscription_id)


# --- outcome recording ----------------------------------------------


async def _locked_subscription(
    session: AsyncSession, subscription_id: int
) -> Subscription:
    sub = (
        await session.execute(
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .with_for_update()
        )
    ).scalar_one()
    return sub


async def _locked_delivery(session: AsyncSession, delivery_id: int) -> Delivery:
    """Row-lock the delivery so two concurrent recorders serialise (BR-16, §6.2)."""
    delivery = (
        await session.execute(
            select(Delivery).where(Delivery.id == delivery_id).with_for_update()
        )
    ).scalar_one_or_none()
    if delivery is None:
        raise NotFoundError("Delivery not found")
    return delivery


async def set_status(
    session: AsyncSession,
    delivery_id: int,
    *,
    new_status: DeliveryStatus | None,
    time_slot: object | None,
    notes: str | None,
    rescheduled_to_date: date | None,
    time_slot_note: str | None,
    actor_id: int | None,
) -> Delivery:
    delivery = await _locked_delivery(session, delivery_id)

    if time_slot is not None:
        delivery.time_slot = time_slot  # type: ignore[assignment]
    if notes is not None:
        delivery.notes = notes
    del time_slot_note  # slot note lives on the subscription, not the delivery

    action = "DELIVERY_UPDATED"
    if new_status is not None:
        action = await _apply_status(
            session,
            delivery,
            new_status,
            rescheduled_to_date=rescheduled_to_date,
            actor_id=actor_id,
        )

    await session.flush()
    await audit_service.record(
        session,
        action=action,
        entity_type="delivery",
        entity_id=delivery.id,
        actor_id=actor_id,
        metadata={"status": delivery.status.value},
    )
    return delivery


async def _apply_status(
    session: AsyncSession,
    delivery: Delivery,
    new_status: DeliveryStatus,
    *,
    rescheduled_to_date: date | None,
    actor_id: int | None,
) -> str:
    if delivery.status in TERMINAL_DELIVERY_STATUSES:
        raise ConflictError(
            "This delivery is already finalised", code="DELIVERY_FINALISED"
        )

    sub = await _locked_subscription(session, delivery.subscription_id)

    if (
        new_status in DELIVERY_PROGRESS_STATUSES
        and sub.status is not _SS.ACTIVE
    ):
        raise ConflictError(
            "The subscription is not active — no delivery can be recorded "
            "against it",
            code="SUBSCRIPTION_NOT_ACTIVE",
        )

    if new_status is _DS.DELIVERED:
        if business_today() > sub.expected_end_date:
            raise ConflictError(
                "The subscription window has ended", code="SUBSCRIPTION_WINDOW_ENDED"
            )
        deducted = min(delivery.meal_quantity, sub.meals_remaining)
        sub.meals_consumed += deducted
        delivery.meals_deducted = deducted
        delivery.status = _DS.DELIVERED
        delivery.delivered_at = datetime.now(UTC)
        delivery.recorded_by = actor_id
        await session.flush()
        await subscription_service.recompute_after_meal_change(
            session, sub, actor_id=actor_id
        )
        return "DELIVERY_RECORDED"

    if new_status is _DS.RESCHEDULED:
        assert rescheduled_to_date is not None  # schema-enforced
        if rescheduled_to_date <= delivery.delivery_date:
            raise ValidationError("rescheduled_to_date must be in the future")
        if not await is_open_day(session, rescheduled_to_date):
            raise ValidationError("rescheduled_to_date falls on a closed day")
        delivery.status = _DS.RESCHEDULED
        delivery.rescheduled_to_date = rescheduled_to_date
        return "DELIVERY_UPDATED"

    # SKIPPED / CANCELLED / FAILED / PREPARING / OUT_FOR_DELIVERY
    delivery.status = new_status
    return "DELIVERY_UPDATED"


async def reverse(
    session: AsyncSession, delivery_id: int, reason: str, *, actor_id: int | None
) -> Delivery:
    delivery = await _locked_delivery(session, delivery_id)
    if delivery.status is not _DS.DELIVERED or delivery.reversed:
        raise ConflictError(
            "Only a recorded delivery that has not been reversed can be reversed",
            code="NOT_REVERSIBLE",
        )

    sub = await _locked_subscription(session, delivery.subscription_id)
    restored = delivery.meals_deducted
    sub.meals_consumed -= restored

    delivery.meals_deducted = 0
    delivery.delivered_at = None
    delivery.recorded_by = None
    delivery.status = _DS.SCHEDULED
    delivery.reversed = True
    delivery.reversal_reason = reason
    delivery.reversed_by = actor_id
    delivery.reversed_at = datetime.now(UTC)
    await session.flush()

    await audit_service.record(
        session,
        action="DELIVERY_REVERSED",
        entity_type="delivery",
        entity_id=delivery.id,
        actor_id=actor_id,
        metadata={"reason": reason, "restored_meals": restored},
    )
    await subscription_service.recompute_after_meal_change(
        session, sub, actor_id=actor_id
    )
    return delivery


# --- planned skips --------------------------------------------------


async def list_planned_skips(
    session: AsyncSession, subscription_id: int
) -> list[PlannedSkip]:
    if await subscription_repo.get_by_id(session, subscription_id) is None:
        raise NotFoundError("Subscription not found")
    return await delivery_repo.skips_for_subscription(session, subscription_id)


async def add_planned_skip(
    session: AsyncSession,
    subscription_id: int,
    *,
    skip_from: date,
    skip_to: date,
    reason: str | None,
    actor_id: int | None,
) -> PlannedSkip:
    sub = await subscription_repo.get_by_id(session, subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found")
    if sub.status in (_SS.COMPLETED, _SS.EXPIRED, _SS.CANCELLED):
        raise ConflictError(
            "Cannot add a planned skip to a finished subscription",
            code="SUBSCRIPTION_FINISHED",
        )

    skip = PlannedSkip(
        subscription_id=subscription_id,
        skip_date_from=skip_from,
        skip_date_to=skip_to,
        reason=reason,
        created_by=actor_id,
    )
    session.add(skip)

    for delivery in await delivery_repo.non_terminal_in_range(
        session, subscription_id, skip_from, skip_to
    ):
        delivery.status = _DS.SKIPPED
        delivery.notes = _joined_note(delivery.notes, "planned skip")
    await session.flush()

    await audit_service.record(
        session,
        action="PLANNED_SKIP_ADDED",
        entity_type="subscription",
        entity_id=subscription_id,
        actor_id=actor_id,
        metadata={"from": skip_from.isoformat(), "to": skip_to.isoformat()},
    )
    return skip


async def remove_planned_skip(
    session: AsyncSession, subscription_id: int, skip_id: int, *, actor_id: int | None
) -> None:
    skip = await delivery_repo.get_skip(session, subscription_id, skip_id)
    if skip is None:
        raise NotFoundError("Planned skip not found")
    await session.delete(skip)
    await session.flush()
    await audit_service.record(
        session,
        action="PLANNED_SKIP_REMOVED",
        entity_type="subscription",
        entity_id=subscription_id,
        actor_id=actor_id,
        metadata={"skip_id": skip_id},
    )


def _joined_note(existing: str | None, addition: str) -> str:
    return f"{existing}; {addition}" if existing else addition
