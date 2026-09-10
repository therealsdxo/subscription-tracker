"""Postgres sequences backing the human-readable entity codes (tech_doc.md §3.2).

Bound to the metadata so ``create_all`` / ``drop_all`` manage them in tests;
the Alembic migrations create them explicitly for real databases.
"""

from __future__ import annotations

from sqlalchemy import Sequence

from app.models.base import Base

customer_code_seq = Sequence("customer_code_seq", start=1, metadata=Base.metadata)
package_code_seq = Sequence("package_code_seq", start=1, metadata=Base.metadata)
subscription_code_seq = Sequence(
    "subscription_code_seq", start=1, metadata=Base.metadata
)
