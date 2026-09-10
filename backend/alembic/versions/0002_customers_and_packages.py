"""Customers & packages

Revision ID: 0002_customers_and_packages
Revises: 0001_foundation
Create Date: 2026-09-10

Milestone 2 (tech_doc.md §16): packages, customers, customer_addresses, plus the
per-entity code sequences (tech_doc.md §3.2).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_customers_and_packages"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

package_status = postgresql.ENUM(
    "ACTIVE", "INACTIVE", name="package_status", create_type=False
)
dietary_pref = postgresql.ENUM(
    "VEGETARIAN",
    "NON_VEGETARIAN",
    "EGGETARIAN",
    "VEGAN",
    "JAIN",
    "OTHER",
    name="dietary_pref",
    create_type=False,
)


def upgrade() -> None:
    package_status.create(op.get_bind(), checkfirst=True)
    dietary_pref.create(op.get_bind(), checkfirst=True)

    op.execute("CREATE SEQUENCE IF NOT EXISTS customer_code_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS package_code_seq START 1")

    # --- packages --------------------------------------------------------
    op.create_table(
        "packages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("package_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("number_of_meals", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "tax_amount", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("final_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status", package_status, server_default=sa.text("'ACTIVE'"), nullable=False
        ),
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
            ["created_by"], ["users.id"],
            name="fk_packages_created_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_packages_updated_by_users", ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "number_of_meals BETWEEN 1 AND 500", name="ck_packages_meals_in_range"
        ),
        sa.CheckConstraint(
            "validity_days BETWEEN 1 AND 730", name="ck_packages_validity_in_range"
        ),
        sa.CheckConstraint("base_price >= 0", name="ck_packages_base_price_non_negative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_packages_tax_amount_non_negative"),
        sa.CheckConstraint(
            "final_price >= 0", name="ck_packages_final_price_non_negative"
        ),
    )
    op.create_unique_constraint("uq_packages_package_code", "packages", ["package_code"])
    op.create_index(
        "ix_packages_package_code", "packages", ["package_code"], unique=True
    )

    # --- customers ------------------------------------------------------
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("default_dietary_preference", dietary_pref, nullable=True),
        sa.Column("dietary_notes", sa.String(length=1000), nullable=True),
        sa.Column("allergies", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_by", sa.Integer(), nullable=True),
        sa.Column("deactivation_reason", sa.String(length=500), nullable=True),
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
            ["deactivated_by"], ["users.id"],
            name="fk_customers_deactivated_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_customers_created_by_users", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"],
            name="fk_customers_updated_by_users", ondelete="SET NULL",
        ),
    )
    op.create_unique_constraint(
        "uq_customers_customer_code", "customers", ["customer_code"]
    )
    op.create_unique_constraint("uq_customers_phone", "customers", ["phone"])
    op.create_unique_constraint("uq_customers_email", "customers", ["email"])
    op.create_index(
        "ix_customers_customer_code", "customers", ["customer_code"], unique=True
    )
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=True)
    op.create_index("ix_customers_is_active", "customers", ["is_active"])

    # --- customer_addresses -------------------------------------------
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("address_line", sa.String(length=500), nullable=False),
        sa.Column("area", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("pincode", sa.String(length=16), nullable=False),
        sa.Column("landmark", sa.String(length=200), nullable=True),
        sa.Column("delivery_notes", sa.String(length=1000), nullable=True),
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
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
            name="fk_customer_addresses_customer_id_customers", ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"]
    )
    # At most one primary address per customer.
    op.create_index(
        "uq_customer_addresses_one_primary",
        "customer_addresses",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    op.drop_table("customer_addresses")
    op.drop_index("ix_customers_is_active", table_name="customers")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_customer_code", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_packages_package_code", table_name="packages")
    op.drop_table("packages")
    op.execute("DROP SEQUENCE IF EXISTS package_code_seq")
    op.execute("DROP SEQUENCE IF EXISTS customer_code_seq")
    dietary_pref.drop(op.get_bind(), checkfirst=True)
    package_status.drop(op.get_bind(), checkfirst=True)
