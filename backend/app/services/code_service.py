"""Human-readable code generation (tech_doc.md §3.2).

Codes like ``CUST-000001`` / ``PKG-00001`` are drawn from a dedicated Postgres
sequence per entity, formatted with a prefix + zero-pad width taken from the
``settings`` table so they can be adjusted without a deploy.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting

Entity = Literal["customer", "package", "subscription"]

_SEQUENCES: dict[Entity, str] = {
    "customer": "customer_code_seq",
    "package": "package_code_seq",
    "subscription": "subscription_code_seq",
}
_DEFAULTS: dict[Entity, tuple[str, int]] = {
    "customer": ("CUST-", 6),
    "package": ("PKG-", 5),
    "subscription": ("SUB-", 6),
}


async def _format_config(session: AsyncSession, entity: Entity) -> tuple[str, int]:
    default_prefix, default_width = _DEFAULTS[entity]
    result = await session.execute(
        select(Setting.key, Setting.value).where(
            Setting.key.in_([f"{entity}_code_prefix", f"{entity}_code_width"])
        )
    )
    rows: dict[str, Any] = {row.key: row.value for row in result}
    prefix: str = rows.get(f"{entity}_code_prefix", default_prefix)
    width: int = rows.get(f"{entity}_code_width", default_width)
    return str(prefix), int(width)


async def next_code(session: AsyncSession, entity: Entity) -> str:
    prefix, width = await _format_config(session, entity)
    seq = _SEQUENCES[entity]
    value = (await session.execute(text(f"SELECT nextval('{seq}')"))).scalar_one()
    return f"{prefix}{int(value):0{width}d}"
