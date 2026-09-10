"""Payments

Revision ID: 0005_payments
Revises: 0004_deliveries
Create Date: 2026-09-10

Milestone 5 (tech_doc.md §16, §7): payments and refunds. Payment status /
outstanding amount are derived from these rows, never stored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_payments"
down_revision: str | None = "0004_deliveries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

payment_method = postgresql.ENUM(
    "CASH", "UPI", "CARD", "BANK_TRANSFER", "OTHER",
    name="payment_method", create_type=False,
)


def upgrade() -> None:
    payment_method.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("recorded_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_payments_subscription_id_subscriptions", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"], ["users.id"],
            name="fk_payments_recorded_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
    op.create_index(
        "ix_payments_subscription_id", "payments", ["subscription_id"]
    )

    op.create_table(
        "refunds",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscription_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("refund_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("recorded_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name="fk_refunds_subscription_id_subscriptions", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"], ["users.id"],
            name="fk_refunds_recorded_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
    )
    op.create_index("ix_refunds_subscription_id", "refunds", ["subscription_id"])


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_index("ix_payments_subscription_id", table_name="payments")
    op.drop_table("payments")
    payment_method.drop(op.get_bind(), checkfirst=True)
