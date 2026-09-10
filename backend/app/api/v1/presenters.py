"""Response presenters that enrich ORM objects with derived views."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.schemas.payment import PaymentSummary
from app.schemas.subscription import SubscriptionDetail, SubscriptionOut
from app.services import payment_service

_PAYMENT_FIELDS = (
    "payment_status",
    "total_paid",
    "net_paid",
    "outstanding_amount",
    "suggested_refund",
)


def _merge(model: SubscriptionOut, summary: PaymentSummary) -> None:
    data = summary.model_dump()
    for field in _PAYMENT_FIELDS:
        setattr(model, field, data[field])


async def subscription_detail(
    session: AsyncSession, sub: Subscription
) -> SubscriptionDetail:
    out = SubscriptionDetail.model_validate(sub)
    _merge(out, await payment_service.summary(session, sub))
    return out


async def subscription_out(
    session: AsyncSession, sub: Subscription
) -> SubscriptionOut:
    out = SubscriptionOut.model_validate(sub)
    _merge(out, await payment_service.summary(session, sub))
    return out


async def subscription_out_list(
    session: AsyncSession, subs: Sequence[Subscription]
) -> list[SubscriptionOut]:
    summaries = await payment_service.summaries_for(session, subs)
    result: list[SubscriptionOut] = []
    for sub in subs:
        out = SubscriptionOut.model_validate(sub)
        _merge(out, summaries[sub.id])
        result.append(out)
    return result
