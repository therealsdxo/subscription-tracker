"""Subscription request/response schemas (tech_doc.md §3.3, §4.3–§4.5, §8)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    DeliveryFrequency,
    DietaryPreference,
    SubscriptionEventType,
    SubscriptionStatus,
    TimeSlot,
)

Weekday = Annotated[int, Field(ge=1, le=7)]


class _DeliveryConfig(BaseModel):
    delivery_frequency: DeliveryFrequency
    delivery_weekdays: list[Weekday] | None = None
    custom_schedule: dict[str, Any] | None = None
    meals_per_delivery: int = Field(default=1, ge=1, le=10)
    delivery_time_slot: TimeSlot
    delivery_time_slot_note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _frequency_shape(self) -> _DeliveryConfig:
        if self.delivery_frequency is DeliveryFrequency.SPECIFIC_WEEKDAYS:
            if not self.delivery_weekdays:
                raise ValueError(
                    "delivery_weekdays is required for SPECIFIC_WEEKDAYS"
                )
            if len(set(self.delivery_weekdays)) != len(self.delivery_weekdays):
                raise ValueError("delivery_weekdays must not repeat")
        if (
            self.delivery_frequency is DeliveryFrequency.CUSTOM
            and not self.custom_schedule
        ):
            raise ValueError("custom_schedule is required for CUSTOM frequency")
        if self.delivery_time_slot is TimeSlot.CUSTOM and not self.delivery_time_slot_note:
            raise ValueError("delivery_time_slot_note is required for a CUSTOM slot")
        return self


class SubscriptionCreate(_DeliveryConfig):
    customer_id: int
    package_id: int
    start_date: date
    delivery_address_id: int
    dietary_preference_override: DietaryPreference | None = None
    subscription_notes: str | None = Field(default=None, max_length=2000)


class SubscriptionRenew(_DeliveryConfig):
    package_id: int
    start_date: date
    delivery_address_id: int
    dietary_preference_override: DietaryPreference | None = None
    subscription_notes: str | None = Field(default=None, max_length=2000)


class SubscriptionUpdate(BaseModel):
    subscription_notes: str | None = Field(default=None, max_length=2000)
    delivery_frequency: DeliveryFrequency | None = None
    delivery_weekdays: list[Weekday] | None = None
    custom_schedule: dict[str, Any] | None = None
    meals_per_delivery: int | None = Field(default=None, ge=1, le=10)
    delivery_time_slot: TimeSlot | None = None
    delivery_time_slot_note: str | None = Field(default=None, max_length=200)
    delivery_address_id: int | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> SubscriptionUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("no fields to update")
        return self


class PauseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ResumeRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ExtendRequest(BaseModel):
    days: int | None = Field(default=None, ge=1, le=365)
    new_end_date: date | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _exactly_one_target(self) -> ExtendRequest:
        if (self.days is None) == (self.new_end_date is None):
            raise ValueError("provide exactly one of days or new_end_date")
        return self


class CancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class MealAdjustmentRequest(BaseModel):
    quantity: int = Field(description="signed, non-zero")
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _non_zero(self) -> MealAdjustmentRequest:
        if self.quantity == 0:
            raise ValueError("quantity must not be zero")
        return self


class SubscriptionEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: SubscriptionEventType
    reason: str | None
    effective_date: date
    pause_start: date | None
    pause_end: date | None
    paused_days: int | None
    old_expected_end_date: date | None
    new_expected_end_date: date | None
    performed_by: int | None
    performed_at: datetime


class MealAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    reason: str
    performed_by: int | None
    performed_at: datetime


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_code: str
    customer_id: int
    package_id: int
    subscription_number: int
    status: SubscriptionStatus

    start_date: date
    original_end_date: date
    expected_end_date: date
    actual_end_date: date | None

    snapshot_package_name: str
    snapshot_package_description: str | None
    snapshot_number_of_meals: int
    snapshot_validity_days: int
    snapshot_base_price: Decimal
    snapshot_tax_amount: Decimal
    snapshot_final_price: Decimal

    meals_allocated: int
    meals_consumed: int
    meals_adjustment: int
    meals_remaining: int

    delivery_frequency: DeliveryFrequency
    delivery_weekdays: list[int] | None
    meals_per_delivery: int
    delivery_time_slot: TimeSlot
    delivery_time_slot_note: str | None
    delivery_address_id: int | None
    snapshot_dietary_preference: DietaryPreference | None
    subscription_notes: str | None
    previous_subscription_id: int | None

    created_at: datetime
    updated_at: datetime


class SubscriptionDetail(SubscriptionOut):
    custom_schedule: dict[str, Any] | None
    snapshot_delivery_address: dict[str, Any]
    events: list[SubscriptionEventOut] = Field(default_factory=list)


class CustomerSubscriptionSummary(BaseModel):
    current: SubscriptionOut | None = None
    past_count: int = 0
