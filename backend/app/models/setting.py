"""``settings`` — key/value operational configuration (tech_doc.md §3.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Setting(TimestampMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


# Default rows seeded by scripts/seed.py (tech_doc.md §3.3).
DEFAULT_SETTINGS: list[dict[str, Any]] = [
    {"key": "closed_weekday", "value": "TUESDAY",
     "description": "Weekly no-delivery day"},
    {"key": "expiry_days_threshold", "value": 7,
     "description": "'Expiring soon' if expected_end_date - today <= N"},
    {"key": "expiry_meals_threshold", "value": 5,
     "description": "'Expiring soon' if meals_remaining <= N"},
    {"key": "customer_code_prefix", "value": "CUST-", "description": None},
    {"key": "customer_code_width", "value": 6, "description": None},
    {"key": "package_code_prefix", "value": "PKG-", "description": None},
    {"key": "package_code_width", "value": 5, "description": None},
    {"key": "subscription_code_prefix", "value": "SUB-", "description": None},
    {"key": "subscription_code_width", "value": 6, "description": None},
]
