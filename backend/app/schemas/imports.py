"""CSV import schemas (tech_doc.md §10.7)."""

from __future__ import annotations

from pydantic import BaseModel


class RowError(BaseModel):
    row: int
    field: str
    message: str


class ImportReport(BaseModel):
    total: int
    valid: int
    invalid: int
    committed: bool
    created_customers: int = 0
    created_subscriptions: int = 0
    errors: list[RowError] = []
