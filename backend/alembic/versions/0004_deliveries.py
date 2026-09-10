"""Deliveries

Revision ID: 0004_deliveries
Revises: 0003_subscriptions
Create Date: 2026-09-10

Milestone 4 (tech_doc.md §16, §6): deliveries, planned_skips, holidays.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_deliveries"
down_revision: str | None = "0003_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

delivery_status = postgresql.ENUM(
    "SCHEDULED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "SKIPPED",
    "CANCELLED", "FAILED", "RESCHEDULED",
    name="delivery_status", create_type=False,
)
time_slot = postgresql.ENUM(
    "MORNING", "LUNCH", "EVENING", "CUSTOM", name="time_slot", create_type=False,
)


def upgrade() -> None:
    delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("time_slot", time_slot, nullable=False),
        sa.Column(
            "status", delivery_status, server_default=sa.text("'SCHEDULED'"),
            nullable=False,
        ),
        sa.Column("meal_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "meals_deducted", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by", sa.Integer(), nullable=True),
        sa.Column(
            "reversed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("reversal_reason", sa.String(length=500), nullable=True),
        sa.Column("reversed_by", sa.Integer(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rescheduled_to_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_deliveries_subscription_id_subscriptions", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"],
            name="fk_deliveries_customer_id_customers", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"], ["users.id"],
            name="fk_deliveries_recorded_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reversed_by"], ["users.id"],
            name="fk_deliveries_reversed_by_users", ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "subscription_id", "delivery_date", "time_slot",
            name="uq_deliveries_one_per_slot_per_day",
        ),
        sa.CheckConstraint("meal_quantity >= 1", name="ck_deliveries_meal_quantity_positive"),
        sa.CheckConstraint(
            "meals_deducted >= 0", name="ck_deliveries_meals_deducted_non_negative"
        ),
    )
    op.create_index("ix_deliveries_subscription_id", "deliveries", ["subscription_id"])
    op.create_index(
        "ix_deliveries_delivery_date_status", "deliveries", ["delivery_date", "status"]
    )

    op.create_table(
        "planned_skips",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("skip_date_from", sa.Date(), nullable=False),
        sa.Column("skip_date_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_planned_skips_subscription_id_subscriptions", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_planned_skips_created_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "skip_date_to >= skip_date_from", name="ck_planned_skips_skip_range_ordered"
        ),
    )
    op.create_index(
        "ix_planned_skips_subscription_id", "planned_skips", ["subscription_id"]
    )

    op.create_table(
        "holidays",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_holidays_created_by_users", ondelete="SET NULL",
        ),
        sa.UniqueConstraint("holiday_date", name="uq_holidays_holiday_date"),
    )
    op.create_index(
        "ix_holidays_holiday_date", "holidays", ["holiday_date"], unique=True
    )


def downgrade() -> None:
    op.drop_table("holidays")
    op.drop_table("planned_skips")
    op.drop_index("ix_deliveries_delivery_date_status", table_name="deliveries")
    op.drop_index("ix_deliveries_subscription_id", table_name="deliveries")
    op.drop_table("deliveries")
    delivery_status.drop(op.get_bind(), checkfirst=True)
