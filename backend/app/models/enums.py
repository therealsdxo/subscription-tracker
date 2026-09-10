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


class DeliveryFrequency(str, enum.Enum):
    DAILY = "DAILY"
    SPECIFIC_WEEKDAYS = "SPECIFIC_WEEKDAYS"
    CUSTOM = "CUSTOM"


class TimeSlot(str, enum.Enum):
    MORNING = "MORNING"
    LUNCH = "LUNCH"
    EVENING = "EVENING"
    CUSTOM = "CUSTOM"


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
