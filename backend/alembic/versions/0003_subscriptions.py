"""Subscriptions

Revision ID: 0003_subscriptions
Revises: 0002_customers_and_packages
Create Date: 2026-09-10

Milestone 3 (tech_doc.md §16): subscriptions, subscription_events,
meal_adjustments, and the subscription code sequence.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_subscriptions"
down_revision: str | None = "0002_customers_and_packages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

subscription_status = postgresql.ENUM(
    "PENDING", "ACTIVE", "PAUSED", "COMPLETED", "EXPIRED", "CANCELLED",
    name="subscription_status", create_type=False,
)
delivery_frequency = postgresql.ENUM(
    "DAILY", "SPECIFIC_WEEKDAYS", "CUSTOM",
    name="delivery_frequency", create_type=False,
)
time_slot = postgresql.ENUM(
    "MORNING", "LUNCH", "EVENING", "CUSTOM", name="time_slot", create_type=False,
)
event_type = postgresql.ENUM(
    "CREATED", "ACTIVATED", "PAUSED", "RESUMED", "EXTENDED", "COMPLETED",
    "EXPIRED", "CANCELLED", "RENEWED",
    name="subscription_event_type", create_type=False,
)
dietary_pref = postgresql.ENUM(
    "VEGETARIAN", "NON_VEGETARIAN", "EGGETARIAN", "VEGAN", "JAIN", "OTHER",
    name="dietary_pref", create_type=False,
)


def upgrade() -> None:
    for enum in (subscription_status, delivery_frequency, time_slot, event_type):
        enum.create(op.get_bind(), checkfirst=True)
    op.execute("CREATE SEQUENCE IF NOT EXISTS subscription_code_seq START 1")

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_code", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("package_id", sa.BigInteger(), nullable=False),
        sa.Column("subscription_number", sa.Integer(), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("original_end_date", sa.Date(), nullable=False),
        sa.Column("expected_end_date", sa.Date(), nullable=False),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("snapshot_package_name", sa.String(length=200), nullable=False),
        sa.Column("snapshot_package_description", sa.String(length=1000), nullable=True),
        sa.Column("snapshot_number_of_meals", sa.Integer(), nullable=False),
        sa.Column("snapshot_validity_days", sa.Integer(), nullable=False),
        sa.Column("snapshot_base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("snapshot_tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("snapshot_final_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("meals_allocated", sa.Integer(), nullable=False),
        sa.Column(
            "meals_consumed", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "meals_adjustment", sa.Integer(), server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "meals_remaining",
            sa.Integer(),
            sa.Computed(
                "meals_allocated + meals_adjustment - meals_consumed", persisted=True
            ),
            nullable=False,
        ),
        sa.Column("delivery_frequency", delivery_frequency, nullable=False),
        sa.Column("delivery_weekdays", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column(
            "custom_schedule", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "meals_per_delivery", sa.Integer(), server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("delivery_time_slot", time_slot, nullable=False),
        sa.Column("delivery_time_slot_note", sa.String(length=200), nullable=True),
        sa.Column("delivery_address_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "snapshot_delivery_address",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("snapshot_dietary_preference", dietary_pref, nullable=True),
        sa.Column("subscription_notes", sa.String(length=2000), nullable=True),
        sa.Column("previous_subscription_id", sa.BigInteger(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"],
            name="fk_subscriptions_customer_id_customers", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"], ["packages.id"],
            name="fk_subscriptions_package_id_packages", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_address_id"], ["customer_addresses.id"],
            name="fk_subscriptions_delivery_address_id_customer_addresses",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["previous_subscription_id"], ["subscriptions.id"],
            name="fk_subscriptions_previous_subscription_id_subscriptions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by"], ["users.id"],
            name="fk_subscriptions_cancelled_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_subscriptions_created_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_subscriptions_updated_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "meals_per_delivery >= 1", name="ck_subscriptions_meals_per_delivery_positive"
        ),
        sa.CheckConstraint(
            "snapshot_number_of_meals >= 1",
            name="ck_subscriptions_snapshot_meals_positive",
        ),
        sa.CheckConstraint(
            "meals_consumed >= 0", name="ck_subscriptions_meals_consumed_non_negative"
        ),
    )
    op.create_unique_constraint(
        "uq_subscriptions_subscription_code", "subscriptions", ["subscription_code"]
    )
    op.create_index(
        "ix_subscriptions_subscription_code",
        "subscriptions",
        ["subscription_code"],
        unique=True,
    )
    op.create_index(
        "ix_subscriptions_status_expected_end_date",
        "subscriptions",
        ["status", "expected_end_date"],
    )
    op.create_index(
        "ix_subscriptions_customer_id_status",
        "subscriptions",
        ["customer_id", "status"],
    )
    op.create_index(
        "uq_subscriptions_one_active_per_customer",
        "subscriptions",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "subscription_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("pause_start", sa.Date(), nullable=True),
        sa.Column("pause_end", sa.Date(), nullable=True),
        sa.Column("paused_days", sa.Integer(), nullable=True),
        sa.Column("old_expected_end_date", sa.Date(), nullable=True),
        sa.Column("new_expected_end_date", sa.Date(), nullable=True),
        sa.Column("performed_by", sa.Integer(), nullable=True),
        sa.Column(
            "performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_subscription_events_subscription_id_subscriptions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["users.id"],
            name="fk_subscription_events_performed_by_users", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_subscription_events_subscription_id",
        "subscription_events",
        ["subscription_id"],
    )

    op.create_table(
        "meal_adjustments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("performed_by", sa.Integer(), nullable=True),
        sa.Column(
            "performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_meal_adjustments_subscription_id_subscriptions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["users.id"],
            name="fk_meal_adjustments_performed_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_meal_adjustments_quantity_non_zero"),
    )
    op.create_index(
        "ix_meal_adjustments_subscription_id", "meal_adjustments", ["subscription_id"]
    )


def downgrade() -> None:
    op.drop_table("meal_adjustments")
    op.drop_table("subscription_events")
    op.drop_index(
        "uq_subscriptions_one_active_per_customer", table_name="subscriptions"
    )
    op.drop_index("ix_subscriptions_customer_id_status", table_name="subscriptions")
    op.drop_index(
        "ix_subscriptions_status_expected_end_date", table_name="subscriptions"
    )
    op.drop_index("ix_subscriptions_subscription_code", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.execute("DROP SEQUENCE IF EXISTS subscription_code_seq")
    for enum in (event_type, time_slot, delivery_frequency, subscription_status):
        enum.drop(op.get_bind(), checkfirst=True)
