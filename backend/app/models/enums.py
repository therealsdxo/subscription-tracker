"""Enum types shared by the ORM models.

Domain enums for subscriptions / deliveries / payments are added in later phases
alongside their tables.
"""

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
