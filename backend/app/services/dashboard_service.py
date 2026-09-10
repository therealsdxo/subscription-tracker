"""Dashboard summary (tech_doc.md §9.4). Aggregate queries only — no row loops."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import Delivery
from app.models.enums import (
    TERMINAL_DELIVERY_STATUSES,
    TERMINAL_SUBSCRIPTION_STATUSES,
    DeliveryStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment, Refund
from app.models.subscription import Subscription
from app.schemas.dashboard import DashboardSummary
from app.services import settings_service
from app.services.subscription_service import business_today

_ZERO = Decimal("0")
_ACTIVE_LIKE = (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED)
_PLANNED = tuple(s for s in DeliveryStatus if s not in TERMINAL_DELIVERY_STATUSES) + (
    DeliveryStatus.DELIVERED,
)


async def summary(session: AsyncSession) -> DashboardSummary:
    today = business_today()
    days_t, meals_t = await settings_service.expiry_thresholds(session)

    active = (
        await session.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
    ).scalar_one()

    todays_meals = (
        await session.execute(
            select(func.coalesce(func.sum(Delivery.meal_quantity), 0)).where(
                Delivery.delivery_date == today,
                Delivery.status.in_(_PLANNED),
            )
        )
    ).scalar_one()

    delivered_today = (
        await session.execute(
            select(func.count())
            .select_from(Delivery)
            .where(
                Delivery.delivery_date == today,
                Delivery.status == DeliveryStatus.DELIVERED,
            )
        )
    ).scalar_one()

    expiring_soon = (
        await session.execute(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.status.in_(_ACTIVE_LIKE),
                (Subscription.expected_end_date <= today + timedelta(days=days_t))
                | (Subscription.meals_remaining <= meals_t),
            )
        )
    ).scalar_one()

    paid = (
        select(func.coalesce(func.sum(Payment.amount), _ZERO))
        .where(Payment.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    refunded = (
        select(func.coalesce(func.sum(Refund.amount), _ZERO))
        .where(Refund.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    dues = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(
                        func.greatest(
                            Subscription.snapshot_final_price - (paid - refunded), _ZERO
                        )
                    ),
                    _ZERO,
                )
            ).where(Subscription.status.notin_(TERMINAL_SUBSCRIPTION_STATUSES))
        )
    ).scalar_one()

    return DashboardSummary(
        active_subscriptions=int(active),
        todays_meals_planned=int(todays_meals),
        delivered_today=int(delivered_today),
        expiring_soon=int(expiring_soon),
        outstanding_dues_total=Decimal(dues).quantize(Decimal("0.01")),
    )
