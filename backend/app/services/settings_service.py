"""Typed reads of the ``settings`` key/value table (tech_doc.md §3.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WEEKDAY_NAMES
from app.models.setting import Setting

_INT_DEFAULTS: dict[str, int] = {
    "expiry_days_threshold": 7,
    "expiry_meals_threshold": 5,
}
_STR_DEFAULTS: dict[str, str] = {
    "closed_weekday": "TUESDAY",
}


async def _get(session: AsyncSession, key: str) -> Any:
    return (
        await session.execute(select(Setting.value).where(Setting.key == key))
    ).scalar_one_or_none()


async def get_int(session: AsyncSession, key: str) -> int:
    value = await _get(session, key)
    if value is None:
        return _INT_DEFAULTS[key]
    return int(value)


async def get_str(session: AsyncSession, key: str) -> str:
    value = await _get(session, key)
    return str(value) if value is not None else _STR_DEFAULTS[key]


async def closed_weekday_index(session: AsyncSession) -> int:
    """``date.weekday()`` value (Mon=0 … Sun=6) of the weekly no-delivery day."""
    name = (await get_str(session, "closed_weekday")).upper()
    return WEEKDAY_NAMES.get(name, WEEKDAY_NAMES["TUESDAY"])


async def expiry_thresholds(session: AsyncSession) -> tuple[int, int]:
    """(days_before_expiry, meals_remaining) — see ``expiring`` filter."""
    return (
        await get_int(session, "expiry_days_threshold"),
        await get_int(session, "expiry_meals_threshold"),
    )
