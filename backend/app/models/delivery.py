"""``deliveries``, ``planned_skips``, ``holidays`` (tech_doc.md §3.3, §6)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import DeliveryStatus, TimeSlot

_delivery_status = SAEnum(DeliveryStatus, name="delivery_status", native_enum=True)
_time_slot = SAEnum(TimeSlot, name="time_slot", native_enum=True)


class Delivery(TimestampMixin, Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "delivery_date",
            "time_slot",
            name="one_per_slot_per_day",
        ),
        CheckConstraint("meal_quantity >= 1", name="meal_quantity_positive"),
        CheckConstraint("meals_deducted >= 0", name="meals_deducted_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[TimeSlot] = mapped_column(_time_slot, nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        _delivery_status, nullable=False, server_default=text("'SCHEDULED'")
    )
    meal_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    meals_deducted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recorded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reversed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rescheduled_to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Delivery id={self.id} sub={self.subscription_id} "
            f"{self.delivery_date} {self.status.value}>"
        )


class PlannedSkip(Base):
    __tablename__ = "planned_skips"
    __table_args__ = (
        CheckConstraint(
            "skip_date_to >= skip_date_from", name="skip_range_ordered"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skip_date_from: Mapped[date] = mapped_column(Date, nullable=False)
    skip_date_to: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    holiday_date: Mapped[date] = mapped_column(
        Date, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
