"""Subscription lifecycle (tech_doc.md §4.3–§4.5, §4.8).

The service owns every invariant: snapshot-on-create, calendar-day expiry,
one-ACTIVE-per-customer with PENDING queueing, pause/resume/extend/cancel,
meal adjustments, and the hybrid status recompute.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.customer import Customer, CustomerAddress
from app.models.enums import (
    DeliveryFrequency,
    DietaryPreference,
    PackageStatus,
    SubscriptionEventType,
    SubscriptionStatus,
    TimeSlot,
)
from app.models.package import Package
from app.models.subscription import MealAdjustment, Subscription, SubscriptionEvent
from app.repositories import subscription_repo
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionRenew,
    SubscriptionUpdate,
)
from app.services import audit_service, code_service, customer_service, package_service

_S = SubscriptionStatus


def business_today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


# --- helpers -------------------------------------------------------------


def _snapshot_address(addr: CustomerAddress) -> dict[str, Any]:
    return {
        "address_id": addr.id,
        "label": addr.label,
        "address_line": addr.address_line,
        "area": addr.area,
        "city": addr.city,
        "pincode": addr.pincode,
        "landmark": addr.landmark,
        "delivery_notes": addr.delivery_notes,
    }


def _add_event(
    session: AsyncSession,
    sub: Subscription,
    event_type: SubscriptionEventType,
    *,
    effective_date: date,
    performed_by: int | None,
    reason: str | None = None,
    pause_start: date | None = None,
    pause_end: date | None = None,
    paused_days: int | None = None,
    old_expected_end_date: date | None = None,
    new_expected_end_date: date | None = None,
) -> None:
    session.add(
        SubscriptionEvent(
            subscription_id=sub.id,
            event_type=event_type,
            reason=reason,
            effective_date=effective_date,
            pause_start=pause_start,
            pause_end=pause_end,
            paused_days=paused_days,
            old_expected_end_date=old_expected_end_date,
            new_expected_end_date=new_expected_end_date,
            performed_by=performed_by,
        )
    )


async def _reload(session: AsyncSession, subscription_id: int) -> Subscription:
    """Re-fetch with events eagerly loaded, for the detail response."""
    sub = await subscription_repo.get_with_events(session, subscription_id)
    if sub is None:  # pragma: no cover - just mutated it
        raise NotFoundError("Subscription not found")
    return sub


async def _refresh_balance(session: AsyncSession, sub: Subscription) -> None:
    await session.refresh(sub, ["meals_remaining"])


async def _sync_expiry(
    session: AsyncSession, sub: Subscription, *, actor_id: int | None
) -> bool:
    """Expire an ACTIVE/PAUSED subscription that is past its expected end date."""
    today = business_today()
    if sub.status in (_S.ACTIVE, _S.PAUSED) and today > sub.expected_end_date:
        sub.status = _S.EXPIRED
        sub.actual_end_date = sub.expected_end_date
        _add_event(
            session, sub, SubscriptionEventType.EXPIRED,
            effective_date=today, performed_by=actor_id,
        )
        await session.flush()
        await audit_service.record(
            session,
            action="SUBSCRIPTION_EXPIRED",
            entity_type="subscription",
            entity_id=sub.id,
            actor_id=actor_id,
        )
        return True
    return False


async def _sync_completion(
    session: AsyncSession, sub: Subscription, *, actor_id: int | None
) -> None:
    await _refresh_balance(session, sub)
    today = business_today()
    if sub.meals_remaining <= 0 and sub.status == _S.ACTIVE:
        sub.status = _S.COMPLETED
        sub.actual_end_date = today
        _add_event(
            session, sub, SubscriptionEventType.COMPLETED,
            effective_date=today, performed_by=actor_id,
        )
        await session.flush()
    elif (
        sub.meals_remaining > 0
        and sub.status == _S.COMPLETED
        and today <= sub.expected_end_date
    ):
        if await subscription_repo.get_active_for_customer(session, sub.customer_id):
            return
        sub.status = _S.ACTIVE
        sub.actual_end_date = None
        _add_event(
            session, sub, SubscriptionEventType.ACTIVATED,
            effective_date=today, performed_by=actor_id,
        )
        await session.flush()


async def recompute_after_meal_change(
    session: AsyncSession, sub: Subscription, *, actor_id: int | None
) -> None:
    """Public entry point for other services (deliveries) that move the balance.

    Completes a subscription that hits zero, or revives a ``COMPLETED`` one whose
    balance went back positive within its window.
    """
    await _sync_completion(session, sub, actor_id=actor_id)


async def _activate_next(
    session: AsyncSession, customer_id: int, *, actor_id: int | None
) -> None:
    if await subscription_repo.get_active_for_customer(session, customer_id):
        return
    nxt = await subscription_repo.next_pending_for_customer(
        session, customer_id, on_date=business_today()
    )
    if nxt is None:
        return
    nxt.status = _S.ACTIVE
    _add_event(
        session, nxt, SubscriptionEventType.ACTIVATED,
        effective_date=business_today(), performed_by=actor_id,
    )
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_ACTIVATED",
        entity_type="subscription",
        entity_id=nxt.id,
        actor_id=actor_id,
    )


def _resolve_address(customer: Customer, address_id: int) -> CustomerAddress:
    addr = next(
        (a for a in customer.addresses if a.id == address_id and a.is_active), None
    )
    if addr is None:
        raise ValidationError(
            "delivery_address_id is not an active address of this customer",
            code="INVALID_ADDRESS",
        )
    return addr


def _effective_frequency_fields(
    *,
    frequency: DeliveryFrequency,
    weekdays: list[int] | None,
    custom_schedule: dict[str, Any] | None,
) -> None:
    if frequency is DeliveryFrequency.SPECIFIC_WEEKDAYS and not weekdays:
        raise ValidationError("delivery_weekdays is required for SPECIFIC_WEEKDAYS")
    if frequency is DeliveryFrequency.CUSTOM and not custom_schedule:
        raise ValidationError("custom_schedule is required for CUSTOM frequency")


# --- reads --------------------------------------------------------------


async def get_subscription(
    session: AsyncSession, subscription_id: int, *, actor_id: int | None = None
) -> Subscription:
    sub = await subscription_repo.get_with_events(session, subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found")
    if await _sync_expiry(session, sub, actor_id=actor_id):
        sub = await _reload(session, subscription_id)
    return sub


async def list_subscriptions(
    session: AsyncSession,
    *,
    status: SubscriptionStatus | None,
    customer_id: int | None,
    expiring: bool,
    dues: bool = False,
    limit: int,
    offset: int,
) -> tuple[list[Subscription], int]:
    from app.services import settings_service

    days_t, meals_t = await settings_service.expiry_thresholds(session)
    return await subscription_repo.search(
        session,
        status=status,
        customer_id=customer_id,
        expiring=expiring,
        dues=dues,
        today=business_today(),
        days_threshold=days_t,
        meals_threshold=meals_t,
        limit=limit,
        offset=offset,
    )


async def list_events(
    session: AsyncSession, subscription_id: int
) -> list[SubscriptionEvent]:
    await get_subscription(session, subscription_id)
    return await subscription_repo.events_for(session, subscription_id)


async def customer_summary(
    session: AsyncSession, customer_id: int
) -> tuple[Subscription | None, int]:
    current, past = await subscription_repo.customer_summary(session, customer_id)
    if current is not None and await _sync_expiry(session, current, actor_id=None):
        # It just expired — it is now a past subscription.
        current, past = None, past + 1
    return current, past


# --- create / renew ----------------------------------------------------


async def _build_and_persist(
    session: AsyncSession,
    *,
    customer: Customer,
    package: Package,
    start_date: date,
    address: CustomerAddress,
    frequency: DeliveryFrequency,
    weekdays: list[int] | None,
    custom_schedule: dict[str, Any] | None,
    meals_per_delivery: int,
    time_slots: list[TimeSlot],
    time_slot_note: str | None,
    dietary_override: DietaryPreference | None,
    notes: str | None,
    previous_subscription_id: int | None,
    actor_id: int | None,
) -> Subscription:
    _effective_frequency_fields(
        frequency=frequency, weekdays=weekdays, custom_schedule=custom_schedule
    )
    today = business_today()
    has_active = (
        await subscription_repo.get_active_for_customer(session, customer.id)
        is not None
    )
    status = _S.PENDING if (has_active or start_date > today) else _S.ACTIVE

    original_end = start_date + timedelta(days=package.validity_days)
    number = await subscription_repo.count_for_customer(session, customer.id) + 1

    sub = Subscription(
        subscription_code=await code_service.next_code(session, "subscription"),
        customer_id=customer.id,
        package_id=package.id,
        subscription_number=number,
        status=status,
        start_date=start_date,
        original_end_date=original_end,
        expected_end_date=original_end,
        snapshot_package_name=package.name,
        snapshot_package_description=package.description,
        snapshot_number_of_meals=package.number_of_meals,
        snapshot_validity_days=package.validity_days,
        snapshot_base_price=package.base_price,
        snapshot_tax_amount=package.tax_amount,
        snapshot_final_price=package.final_price,
        meals_allocated=package.number_of_meals,
        meals_consumed=0,
        meals_adjustment=0,
        delivery_frequency=frequency,
        delivery_weekdays=weekdays,
        custom_schedule=custom_schedule,
        meals_per_delivery=meals_per_delivery,
        delivery_time_slots=time_slots,
        delivery_time_slot_note=time_slot_note,
        delivery_address_id=address.id,
        snapshot_delivery_address=_snapshot_address(address),
        snapshot_dietary_preference=(
            dietary_override or customer.default_dietary_preference
        ),
        subscription_notes=notes,
        previous_subscription_id=previous_subscription_id,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(sub)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "Customer already has an active subscription", code="ACTIVE_EXISTS"
        ) from exc

    await _refresh_balance(session, sub)
    _add_event(
        session, sub,
        SubscriptionEventType.RENEWED
        if previous_subscription_id
        else SubscriptionEventType.CREATED,
        effective_date=today,
        performed_by=actor_id,
    )
    if status == _S.ACTIVE:
        _add_event(
            session, sub, SubscriptionEventType.ACTIVATED,
            effective_date=today, performed_by=actor_id,
        )
    await session.flush()

    await audit_service.record(
        session,
        action="SUBSCRIPTION_RENEWED" if previous_subscription_id
        else "SUBSCRIPTION_CREATED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        after={
            "subscription_code": sub.subscription_code,
            "customer_id": customer.id,
            "package_id": package.id,
            "status": sub.status.value,
        },
    )
    await _sync_expiry(session, sub, actor_id=actor_id)
    return await _reload(session, sub.id)


async def _resolve_package(session: AsyncSession, package_id: int) -> Package:
    package = await package_service.get_package(session, package_id)
    if package.status is not PackageStatus.ACTIVE:
        raise ConflictError(
            "This package is inactive and cannot be assigned to a new subscription",
            code="PACKAGE_INACTIVE",
        )
    return package


async def create_subscription(
    session: AsyncSession, payload: SubscriptionCreate, *, actor_id: int | None
) -> Subscription:
    customer = await customer_service.get_customer(session, payload.customer_id)
    if not customer.is_active:
        raise ConflictError("Customer is not active", code="CUSTOMER_INACTIVE")
    package = await _resolve_package(session, payload.package_id)
    address = _resolve_address(customer, payload.delivery_address_id)

    return await _build_and_persist(
        session,
        customer=customer,
        package=package,
        start_date=payload.start_date,
        address=address,
        frequency=payload.delivery_frequency,
        weekdays=payload.delivery_weekdays,
        custom_schedule=payload.custom_schedule,
        meals_per_delivery=payload.meals_per_delivery,
        time_slots=payload.delivery_time_slots,
        time_slot_note=payload.delivery_time_slot_note,
        dietary_override=payload.dietary_preference_override,
        notes=payload.subscription_notes,
        previous_subscription_id=None,
        actor_id=actor_id,
    )


async def renew_subscription(
    session: AsyncSession,
    subscription_id: int,
    payload: SubscriptionRenew,
    *,
    actor_id: int | None,
) -> Subscription:
    source = await get_subscription(session, subscription_id, actor_id=actor_id)
    customer = await customer_service.get_customer(session, source.customer_id)
    if not customer.is_active:
        raise ConflictError("Customer is not active", code="CUSTOMER_INACTIVE")
    package = await _resolve_package(session, payload.package_id)
    address = _resolve_address(customer, payload.delivery_address_id)

    return await _build_and_persist(
        session,
        customer=customer,
        package=package,
        start_date=payload.start_date,
        address=address,
        frequency=payload.delivery_frequency,
        weekdays=payload.delivery_weekdays,
        custom_schedule=payload.custom_schedule,
        meals_per_delivery=payload.meals_per_delivery,
        time_slots=payload.delivery_time_slots,
        time_slot_note=payload.delivery_time_slot_note,
        dietary_override=payload.dietary_preference_override,
        notes=payload.subscription_notes,
        previous_subscription_id=source.id,
        actor_id=actor_id,
    )


# --- edits & lifecycle -------------------------------------------------


async def update_subscription(
    session: AsyncSession,
    subscription_id: int,
    payload: SubscriptionUpdate,
    *,
    actor_id: int | None,
) -> Subscription:
    sub = await get_subscription(session, subscription_id, actor_id=actor_id)
    if sub.status in (_S.COMPLETED, _S.EXPIRED, _S.CANCELLED):
        raise ConflictError(
            "A finished subscription cannot be edited", code="SUBSCRIPTION_FINISHED"
        )
    data = payload.model_dump(exclude_unset=True)

    if "subscription_notes" in data:
        sub.subscription_notes = data["subscription_notes"]
    if "meals_per_delivery" in data and data["meals_per_delivery"] is not None:
        sub.meals_per_delivery = data["meals_per_delivery"]
    if "delivery_time_slots" in data and data["delivery_time_slots"] is not None:
        sub.delivery_time_slots = data["delivery_time_slots"]
    if "delivery_time_slot_note" in data:
        sub.delivery_time_slot_note = data["delivery_time_slot_note"]
    if "delivery_frequency" in data and data["delivery_frequency"] is not None:
        sub.delivery_frequency = data["delivery_frequency"]
    if "delivery_weekdays" in data:
        sub.delivery_weekdays = data["delivery_weekdays"]
    if "custom_schedule" in data:
        sub.custom_schedule = data["custom_schedule"]

    _effective_frequency_fields(
        frequency=sub.delivery_frequency,
        weekdays=sub.delivery_weekdays,
        custom_schedule=sub.custom_schedule,
    )

    if data.get("delivery_address_id") is not None:
        customer = await customer_service.get_customer(session, sub.customer_id)
        address = _resolve_address(customer, data["delivery_address_id"])
        sub.delivery_address_id = address.id
        sub.snapshot_delivery_address = _snapshot_address(address)

    sub.updated_by = actor_id
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_UPDATED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        after=data,
    )
    return await _reload(session, subscription_id)


async def pause_subscription(
    session: AsyncSession, subscription_id: int, reason: str, *, actor_id: int | None
) -> Subscription:
    sub = await get_subscription(session, subscription_id, actor_id=actor_id)
    if sub.status is not _S.ACTIVE:
        raise ConflictError(
            "Only an active subscription can be paused", code="NOT_ACTIVE"
        )
    today = business_today()
    sub.status = _S.PAUSED
    sub.updated_by = actor_id
    _add_event(
        session, sub, SubscriptionEventType.PAUSED,
        effective_date=today, performed_by=actor_id,
        reason=reason, pause_start=today,
    )
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_PAUSED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={"reason": reason},
    )
    return await _reload(session, subscription_id)


async def resume_subscription(
    session: AsyncSession, subscription_id: int, *, actor_id: int | None
) -> Subscription:
    sub = await subscription_repo.get_with_events(session, subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found")
    if sub.status is not _S.PAUSED:
        raise ConflictError(
            "Only a paused subscription can be resumed", code="NOT_PAUSED"
        )
    today = business_today()
    last_pause = next(
        (
            e
            for e in reversed(sub.events)
            if e.event_type is SubscriptionEventType.PAUSED
        ),
        None,
    )
    pause_start = last_pause.pause_start if last_pause and last_pause.pause_start else today
    paused_days = max((today - pause_start).days, 0)
    old_end = sub.expected_end_date
    sub.expected_end_date = old_end + timedelta(days=paused_days)
    sub.status = _S.ACTIVE
    sub.updated_by = actor_id
    _add_event(
        session, sub, SubscriptionEventType.RESUMED,
        effective_date=today, performed_by=actor_id,
        pause_start=pause_start, pause_end=today, paused_days=paused_days,
        old_expected_end_date=old_end, new_expected_end_date=sub.expected_end_date,
    )
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_RESUMED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={"paused_days": paused_days},
    )
    await _sync_expiry(session, sub, actor_id=actor_id)
    return await _reload(session, subscription_id)


async def extend_subscription(
    session: AsyncSession,
    subscription_id: int,
    *,
    days: int | None,
    new_end_date: date | None,
    reason: str,
    actor_id: int | None,
) -> Subscription:
    sub = await get_subscription(session, subscription_id, actor_id=actor_id)
    if sub.status in (_S.COMPLETED, _S.CANCELLED):
        raise ConflictError(
            "A completed or cancelled subscription cannot be extended",
            code="SUBSCRIPTION_FINISHED",
        )
    old_end = sub.expected_end_date
    target = old_end + timedelta(days=days) if days is not None else new_end_date
    assert target is not None
    if target <= old_end:
        raise ValidationError("The new expiry date must be later than the current one")

    revived = False
    if sub.status is _S.EXPIRED and target >= business_today():
        if await subscription_repo.get_active_for_customer(session, sub.customer_id):
            raise ConflictError(
                "Customer already has an active subscription", code="ACTIVE_EXISTS"
            )
        sub.status = _S.ACTIVE
        sub.actual_end_date = None
        revived = True

    sub.expected_end_date = target
    sub.updated_by = actor_id
    _add_event(
        session, sub, SubscriptionEventType.EXTENDED,
        effective_date=business_today(), performed_by=actor_id, reason=reason,
        old_expected_end_date=old_end, new_expected_end_date=target,
    )
    if revived:
        _add_event(
            session, sub, SubscriptionEventType.ACTIVATED,
            effective_date=business_today(), performed_by=actor_id,
        )
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_EXTENDED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        before={"expected_end_date": old_end.isoformat()},
        after={"expected_end_date": target.isoformat()},
        metadata={"reason": reason},
    )
    return await _reload(session, subscription_id)


async def cancel_subscription(
    session: AsyncSession, subscription_id: int, reason: str, *, actor_id: int | None
) -> Subscription:
    sub = await get_subscription(session, subscription_id, actor_id=actor_id)
    if sub.status in (_S.COMPLETED, _S.CANCELLED):
        raise ConflictError(
            "This subscription is already finished", code="SUBSCRIPTION_FINISHED"
        )
    today = business_today()
    sub.status = _S.CANCELLED
    sub.cancelled_at = datetime.now(UTC)
    sub.cancelled_by = actor_id
    sub.cancellation_reason = reason
    sub.actual_end_date = today
    sub.updated_by = actor_id
    _add_event(
        session, sub, SubscriptionEventType.CANCELLED,
        effective_date=today, performed_by=actor_id, reason=reason,
    )
    await session.flush()
    await audit_service.record(
        session,
        action="SUBSCRIPTION_CANCELLED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={"reason": reason},
    )
    await _activate_next(session, sub.customer_id, actor_id=actor_id)
    return await _reload(session, subscription_id)


async def adjust_meals(
    session: AsyncSession,
    subscription_id: int,
    *,
    quantity: int,
    reason: str,
    actor_id: int | None,
) -> Subscription:
    sub = await get_subscription(session, subscription_id, actor_id=actor_id)
    if sub.status is _S.CANCELLED:
        raise ConflictError(
            "Meals cannot be adjusted on a cancelled subscription",
            code="SUBSCRIPTION_CANCELLED",
        )
    prospective = (
        sub.meals_allocated + sub.meals_adjustment + quantity - sub.meals_consumed
    )
    if prospective < 0:
        raise ValidationError(
            "This adjustment would make the meal balance negative",
            code="NEGATIVE_BALANCE",
        )

    sub.meals_adjustment += quantity
    sub.updated_by = actor_id
    session.add(
        MealAdjustment(
            subscription_id=sub.id,
            quantity=quantity,
            reason=reason,
            performed_by=actor_id,
        )
    )
    await session.flush()
    await audit_service.record(
        session,
        action="MEAL_ADJUSTED",
        entity_type="subscription",
        entity_id=sub.id,
        actor_id=actor_id,
        metadata={"quantity": quantity, "reason": reason},
    )
    await _sync_completion(session, sub, actor_id=actor_id)
    return await _reload(session, subscription_id)
