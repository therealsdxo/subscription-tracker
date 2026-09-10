"""Typed reads of the ``settings`` key/value table (tech_doc.md §3.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting

_INT_DEFAULTS: dict[str, int] = {
    "expiry_days_threshold": 7,
    "expiry_meals_threshold": 5,
}


async def get_int(session: AsyncSession, key: str) -> int:
    value: Any = (
        await session.execute(select(Setting.value).where(Setting.key == key))
    ).scalar_one_or_none()
    if value is None:
        return _INT_DEFAULTS[key]
    return int(value)


async def expiry_thresholds(session: AsyncSession) -> tuple[int, int]:
    """(days_before_expiry, meals_remaining) — see ``expiring`` filter."""
    return (
        await get_int(session, "expiry_days_threshold"),
        await get_int(session, "expiry_meals_threshold"),
    )
