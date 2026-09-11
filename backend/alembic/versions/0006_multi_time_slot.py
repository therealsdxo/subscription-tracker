"""Subscriptions: multiple delivery time slots

Revision ID: 0006_multi_time_slot
Revises: 0005_payments
Create Date: 2026-09-11

A subscription can now carry more than one delivery time slot (e.g. both
MORNING and EVENING), so the daily generator produces one delivery per slot
per due day for that subscription — the requested "multiple deliveries a day
for one customer" without relaxing the one-active-subscription-per-customer
rule.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_multi_time_slot"
down_revision: str | None = "0005_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_time_slot = postgresql.ENUM(
    "MORNING", "LUNCH", "EVENING", "CUSTOM", name="time_slot", create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("delivery_time_slots", postgresql.ARRAY(_time_slot), nullable=True),
    )
    op.execute(
        "UPDATE subscriptions SET delivery_time_slots = ARRAY[delivery_time_slot]"
    )
    op.alter_column("subscriptions", "delivery_time_slots", nullable=False)
    op.drop_column("subscriptions", "delivery_time_slot")


def downgrade() -> None:
    op.add_column(
        "subscriptions", sa.Column("delivery_time_slot", _time_slot, nullable=True)
    )
    op.execute(
        "UPDATE subscriptions SET delivery_time_slot = delivery_time_slots[1]"
    )
    op.alter_column("subscriptions", "delivery_time_slot", nullable=False)
    op.drop_column("subscriptions", "delivery_time_slots")
