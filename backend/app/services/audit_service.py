"""Write helper for the audit log (tech_doc.md §3.3).

Audited at minimum: package modifications, subscription extensions/cancellations,
meal adjustments, delivery reversals, payments, refunds, customer
deletion/deactivation, and user management.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None,
    actor_id: int | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        before=before,
        after=after,
        log_metadata=metadata,
        ip_address=ip_address,
    )
    session.add(entry)
    await session.flush()
    return entry
