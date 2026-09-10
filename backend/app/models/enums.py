"""Enum types used by the foundational models.

Domain enums (subscription/delivery/payment status, dietary preference, …) are
added in later phases alongside their tables.
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
