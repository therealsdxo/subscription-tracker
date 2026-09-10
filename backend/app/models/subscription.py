"""``subscriptions``, ``subscription_events``, ``meal_adjustments``.

tech_doc.md §3.1, §3.3, §4.3–§4.5. Deliveries and payments (which will decrement
``meals_consumed`` / derive payment status) are added in later milestones.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    DeliveryFrequency,
    DietaryPreference,
    SubscriptionEventType,
    SubscriptionStatus,
    TimeSlot,
)

_subscription_status = SAEnum(
    SubscriptionStatus, name="subscription_status", native_enum=True
)
_delivery_frequency = SAEnum(
    DeliveryFrequency, name="delivery_frequency", native_enum=True
)
_time_slot = SAEnum(TimeSlot, name="time_slot", native_enum=True)
_event_type = SAEnum(
    SubscriptionEventType, name="subscription_event_type", native_enum=True
)


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("meals_per_delivery >= 1", name="meals_per_delivery_positive"),
        CheckConstraint(
            "snapshot_number_of_meals >= 1", name="snapshot_meals_positive"
        ),
        CheckConstraint("meals_consumed >= 0", name="meals_consumed_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        _subscription_status, nullable=False
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    snapshot_package_name: Mapped[str] = mapped_column(String(200), nullable=False)
    snapshot_package_description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    snapshot_number_of_meals: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_validity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    snapshot_tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    snapshot_final_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    meals_allocated: Mapped[int] = mapped_column(Integer, nullable=False)
    meals_consumed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    meals_adjustment: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    meals_remaining: Mapped[int] = mapped_column(
        Integer,
        Computed("meals_allocated + meals_adjustment - meals_consumed", persisted=True),
        nullable=False,
    )

    delivery_frequency: Mapped[DeliveryFrequency] = mapped_column(
        _delivery_frequency, nullable=False
    )
    delivery_weekdays: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True
    )
    custom_schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    meals_per_delivery: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    delivery_time_slot: Mapped[TimeSlot] = mapped_column(_time_slot, nullable=False)
    delivery_time_slot_note: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    delivery_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True
    )
    snapshot_delivery_address: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    snapshot_dietary_preference: Mapped[DietaryPreference | None] = mapped_column(
        SAEnum(DietaryPreference, name="dietary_pref", native_enum=True), nullable=True
    )
    subscription_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    previous_subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    events: Mapped[list[SubscriptionEvent]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionEvent.id",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Subscription {self.subscription_code} {self.status.value}>"


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[SubscriptionEventType] = mapped_column(_event_type, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    pause_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    pause_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    paused_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    old_expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    performed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    subscription: Mapped[Subscription] = relationship(back_populates="events")


class MealAdjustment(Base):
    __tablename__ = "meal_adjustments"
    __table_args__ = (CheckConstraint("quantity <> 0", name="quantity_non_zero"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    performed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
