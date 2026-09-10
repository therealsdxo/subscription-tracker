"""Subscription endpoints (tech_doc.md §5.2, §8).

STAFF: create, edit, pause/resume, renew. ADMIN: extend, cancel, meal adjustments.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import CurrentUser, SessionDep, require_admin, require_staff
from app.models.enums import SubscriptionStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.delivery import (
    DeliveryOut,
    PlannedSkipCreate,
    PlannedSkipOut,
)
from app.schemas.subscription import (
    CancelRequest,
    ExtendRequest,
    MealAdjustmentRequest,
    PauseRequest,
    ResumeRequest,
    SubscriptionCreate,
    SubscriptionDetail,
    SubscriptionEventOut,
    SubscriptionOut,
    SubscriptionRenew,
    SubscriptionUpdate,
)
from app.services import delivery_service, subscription_service

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(require_staff)],
)

AdminUser = Annotated[User, Depends(require_admin)]


@router.get("", response_model=Page[SubscriptionOut])
async def list_subscriptions(
    session: SessionDep,
    status_filter: Annotated[SubscriptionStatus | None, Query(alias="status")] = None,
    customer_id: Annotated[int | None, Query()] = None,
    expiring: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[SubscriptionOut]:
    rows, total = await subscription_service.list_subscriptions(
        session,
        status=status_filter,
        customer_id=customer_id,
        expiring=expiring,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[SubscriptionOut](
        items=[SubscriptionOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SubscriptionDetail, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreate, session: SessionDep, actor: CurrentUser
) -> SubscriptionDetail:
    sub = await subscription_service.create_subscription(
        session, payload, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.get("/{subscription_id}", response_model=SubscriptionDetail)
async def get_subscription(
    subscription_id: int, session: SessionDep, actor: CurrentUser
) -> SubscriptionDetail:
    sub = await subscription_service.get_subscription(
        session, subscription_id, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.patch("/{subscription_id}", response_model=SubscriptionDetail)
async def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    session: SessionDep,
    actor: CurrentUser,
) -> SubscriptionDetail:
    sub = await subscription_service.update_subscription(
        session, subscription_id, payload, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.get("/{subscription_id}/events", response_model=list[SubscriptionEventOut])
async def list_events(
    subscription_id: int, session: SessionDep
) -> list[SubscriptionEventOut]:
    events = await subscription_service.list_events(session, subscription_id)
    return [SubscriptionEventOut.model_validate(e) for e in events]


@router.post("/{subscription_id}/pause", response_model=SubscriptionDetail)
async def pause_subscription(
    subscription_id: int,
    payload: PauseRequest,
    session: SessionDep,
    actor: CurrentUser,
) -> SubscriptionDetail:
    sub = await subscription_service.pause_subscription(
        session, subscription_id, payload.reason, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.post("/{subscription_id}/resume", response_model=SubscriptionDetail)
async def resume_subscription(
    subscription_id: int,
    payload: ResumeRequest,
    session: SessionDep,
    actor: CurrentUser,
) -> SubscriptionDetail:
    del payload
    sub = await subscription_service.resume_subscription(
        session, subscription_id, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.post("/{subscription_id}/renew", response_model=SubscriptionDetail,
             status_code=status.HTTP_201_CREATED)
async def renew_subscription(
    subscription_id: int,
    payload: SubscriptionRenew,
    session: SessionDep,
    actor: CurrentUser,
) -> SubscriptionDetail:
    sub = await subscription_service.renew_subscription(
        session, subscription_id, payload, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.post("/{subscription_id}/extend", response_model=SubscriptionDetail)
async def extend_subscription(
    subscription_id: int,
    payload: ExtendRequest,
    session: SessionDep,
    actor: AdminUser,
) -> SubscriptionDetail:
    sub = await subscription_service.extend_subscription(
        session,
        subscription_id,
        days=payload.days,
        new_end_date=payload.new_end_date,
        reason=payload.reason,
        actor_id=actor.id,
    )
    return SubscriptionDetail.model_validate(sub)


@router.post("/{subscription_id}/cancel", response_model=SubscriptionDetail)
async def cancel_subscription(
    subscription_id: int,
    payload: CancelRequest,
    session: SessionDep,
    actor: AdminUser,
) -> SubscriptionDetail:
    sub = await subscription_service.cancel_subscription(
        session, subscription_id, payload.reason, actor_id=actor.id
    )
    return SubscriptionDetail.model_validate(sub)


@router.post("/{subscription_id}/meal-adjustments", response_model=SubscriptionDetail)
async def adjust_meals(
    subscription_id: int,
    payload: MealAdjustmentRequest,
    session: SessionDep,
    actor: AdminUser,
) -> SubscriptionDetail:
    sub = await subscription_service.adjust_meals(
        session,
        subscription_id,
        quantity=payload.quantity,
        reason=payload.reason,
        actor_id=actor.id,
    )
    return SubscriptionDetail.model_validate(sub)


# --- deliveries & planned skips (Milestone 4) ------------------------


@router.get(
    "/{subscription_id}/deliveries", response_model=list[DeliveryOut]
)
async def list_subscription_deliveries(
    subscription_id: int, session: SessionDep
) -> list[DeliveryOut]:
    rows = await delivery_service.for_subscription(session, subscription_id)
    return [DeliveryOut.model_validate(r) for r in rows]


@router.get(
    "/{subscription_id}/skips", response_model=list[PlannedSkipOut]
)
async def list_planned_skips(
    subscription_id: int, session: SessionDep
) -> list[PlannedSkipOut]:
    rows = await delivery_service.list_planned_skips(session, subscription_id)
    return [PlannedSkipOut.model_validate(r) for r in rows]


@router.post(
    "/{subscription_id}/skips",
    response_model=PlannedSkipOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_planned_skip(
    subscription_id: int,
    payload: PlannedSkipCreate,
    session: SessionDep,
    actor: CurrentUser,
) -> PlannedSkipOut:
    skip = await delivery_service.add_planned_skip(
        session,
        subscription_id,
        skip_from=payload.skip_date_from,
        skip_to=payload.skip_date_to,
        reason=payload.reason,
        actor_id=actor.id,
    )
    return PlannedSkipOut.model_validate(skip)


@router.delete(
    "/{subscription_id}/skips/{skip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_planned_skip(
    subscription_id: int,
    skip_id: int,
    session: SessionDep,
    actor: CurrentUser,
) -> Response:
    await delivery_service.remove_planned_skip(
        session, subscription_id, skip_id, actor_id=actor.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
