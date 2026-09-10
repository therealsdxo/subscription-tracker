"""Dashboard summary schema (tech_doc.md §9.4)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_subscriptions: int
    todays_meals_planned: int
    delivered_today: int
    expiring_soon: int
    outstanding_dues_total: Decimal
