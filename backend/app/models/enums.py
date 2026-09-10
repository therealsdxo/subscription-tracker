"""Enum types shared by the ORM models."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"


class PackageStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DietaryPreference(str, enum.Enum):
    VEGETARIAN = "VEGETARIAN"
    NON_VEGETARIAN = "NON_VEGETARIAN"
    EGGETARIAN = "EGGETARIAN"
    VEGAN = "VEGAN"
    JAIN = "JAIN"
    OTHER = "OTHER"


class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


TERMINAL_SUBSCRIPTION_STATUSES = frozenset(
    {
        SubscriptionStatus.COMPLETED,
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.CANCELLED,
    }
)


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


class PaymentStatus(str, enum.Enum):
    """Derived from the payment/refund rows — never stored (BL-18, tech_doc §4.6)."""

    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class DeliveryFrequency(str, enum.Enum):
    DAILY = "DAILY"
    SPECIFIC_WEEKDAYS = "SPECIFIC_WEEKDAYS"
    CUSTOM = "CUSTOM"


class TimeSlot(str, enum.Enum):
    MORNING = "MORNING"
    LUNCH = "LUNCH"
    EVENING = "EVENING"
    CUSTOM = "CUSTOM"


class DeliveryStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    PREPARING = "PREPARING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"


# A delivery in one of these states is finished — only ``DELIVERED`` moved meals.
TERMINAL_DELIVERY_STATUSES = frozenset(
    {
        DeliveryStatus.DELIVERED,
        DeliveryStatus.SKIPPED,
        DeliveryStatus.CANCELLED,
        DeliveryStatus.FAILED,
        DeliveryStatus.RESCHEDULED,
    }
)
# Positive outcomes — blocked when the subscription is not ACTIVE (BR-29).
DELIVERY_PROGRESS_STATUSES = frozenset(
    {
        DeliveryStatus.PREPARING,
        DeliveryStatus.OUT_FOR_DELIVERY,
        DeliveryStatus.DELIVERED,
    }
)

WEEKDAY_NAMES: dict[str, int] = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


class SubscriptionEventType(str, enum.Enum):
    CREATED = "CREATED"
    ACTIVATED = "ACTIVATED"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    EXTENDED = "EXTENDED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    RENEWED = "RENEWED"
