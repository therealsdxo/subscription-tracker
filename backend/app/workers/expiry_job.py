"""Daily subscription sweep (tech_doc.md §4.5 BR-24, §11).

- Activates PENDING subscriptions whose start date has arrived and whose customer
  has no ACTIVE subscription.
- Expires ACTIVE / PAUSED subscriptions past their expected end date.

Idempotent. Callable from ``scripts/run_expiry_job.py``; scheduling is infra (M6).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import SubscriptionEventType, SubscriptionStatus
from app.models.subscription import Subscription, SubscriptionEvent
from app.repositories import subscription_repo
from app.services import audit_service
from app.services.subscription_service import business_today

logger = get_logger("healthx.expiry_job")


def _event(
    session: AsyncSession,
    sub: Subscription,
    event_type: SubscriptionEventType,
    effective_date: date,
) -> None:
    session.add(
        SubscriptionEvent(
            subscription_id=sub.id,
            event_type=event_type,
            effective_date=effective_date,
            performed_by=None,
        )
    )


async def run_expiry_job(session: AsyncSession) -> dict[str, int]:
    today = business_today()
    activated = 0
    expired = 0

    for sub in await subscription_repo.overdue(session, on_date=today):
        sub.status = SubscriptionStatus.EXPIRED
        sub.actual_end_date = sub.expected_end_date
        _event(session, sub, SubscriptionEventType.EXPIRED, today)
        await session.flush()
        await audit_service.record(
            session,
            action="SUBSCRIPTION_EXPIRED",
            entity_type="subscription",
            entity_id=sub.id,
            actor_id=None,
            metadata={"via": "expiry_job"},
        )
        expired += 1

    seen: set[int] = set()
    for sub in await subscription_repo.due_for_activation(session, on_date=today):
        if sub.customer_id in seen:
            continue
        if await subscription_repo.get_active_for_customer(session, sub.customer_id):
            seen.add(sub.customer_id)
            continue
        sub.status = SubscriptionStatus.ACTIVE
        _event(session, sub, SubscriptionEventType.ACTIVATED, today)
        await session.flush()
        await audit_service.record(
            session,
            action="SUBSCRIPTION_ACTIVATED",
            entity_type="subscription",
            entity_id=sub.id,
            actor_id=None,
            metadata={"via": "expiry_job"},
        )
        seen.add(sub.customer_id)
        activated += 1

    logger.info("expiry_job_complete", expired=expired, activated=activated)
    return {"expired": expired, "activated": activated}
