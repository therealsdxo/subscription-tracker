"""Delivery, planned-skip and holiday schemas (tech_doc.md §6, §8)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DeliveryStatus, TimeSlot


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    customer_id: int
    delivery_date: date
    time_slot: TimeSlot
    status: DeliveryStatus
    meal_quantity: int
    meals_deducted: int
    delivered_at: datetime | None
    recorded_by: int | None
    reversed: bool
    reversal_reason: str | None
    rescheduled_to_date: date | None
    notes: str | None
    created_at: datetime


class DeliveryListRow(DeliveryOut):
    """A daily-list row, enriched with customer + address context."""

    subscription_code: str
    customer_name: str
    customer_code: str
    area: str | None
    address_line: str | None


class GenerateRequest(BaseModel):
    date: date


class GenerateResult(BaseModel):
    date: date
    created: int
    open_day: bool


_SETTABLE = {
    DeliveryStatus.PREPARING,
    DeliveryStatus.OUT_FOR_DELIVERY,
    DeliveryStatus.DELIVERED,
    DeliveryStatus.SKIPPED,
    DeliveryStatus.CANCELLED,
    DeliveryStatus.FAILED,
    DeliveryStatus.RESCHEDULED,
}


class DeliveryUpdate(BaseModel):
    status: DeliveryStatus | None = None
    time_slot: TimeSlot | None = None
    time_slot_note: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)
    rescheduled_to_date: date | None = None

    @model_validator(mode="after")
    def _check(self) -> DeliveryUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("no fields to update")
        if self.status is not None and self.status not in _SETTABLE:
            raise ValueError(f"cannot set status to {self.status.value}")
        if (
            self.status is DeliveryStatus.RESCHEDULED
            and self.rescheduled_to_date is None
        ):
            raise ValueError("rescheduled_to_date is required for RESCHEDULED")
        return self


class DeliveryReverse(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class PlannedSkipCreate(BaseModel):
    skip_date_from: date
    skip_date_to: date
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _ordered(self) -> PlannedSkipCreate:
        if self.skip_date_to < self.skip_date_from:
            raise ValueError("skip_date_to must not be before skip_date_from")
        return self


class PlannedSkipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    skip_date_from: date
    skip_date_to: date
    reason: str | None
    created_at: datetime


class HolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=200)


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    holiday_date: date
    name: str
    created_at: datetime
