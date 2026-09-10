"""Delivery endpoints (tech_doc.md §5.2, §6, §8). All STAFF."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, SessionDep, require_staff
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, TimeSlot
from app.models.subscription import Subscription
from app.schemas.common import Page
from app.schemas.delivery import (
    DeliveryListRow,
    DeliveryOut,
    DeliveryReverse,
    DeliveryUpdate,
    GenerateRequest,
    GenerateResult,
)
from app.services import delivery_service

router = APIRouter(
    prefix="/deliveries",
    tags=["deliveries"],
    dependencies=[Depends(require_staff)],
)


def _row(delivery: Delivery, sub: Subscription, customer: Customer) -> DeliveryListRow:
    addr = sub.snapshot_delivery_address or {}
    base = DeliveryOut.model_validate(delivery).model_dump()
    return DeliveryListRow(
        **base,
        subscription_code=sub.subscription_code,
        customer_name=customer.name,
        customer_code=customer.customer_code,
        area=addr.get("area"),
        address_line=addr.get("address_line"),
    )


@router.get("", response_model=Page[DeliveryListRow])
async def list_deliveries(
    session: SessionDep,
    date_: Annotated[date, Query(alias="date")],
    status_filter: Annotated[DeliveryStatus | None, Query(alias="status")] = None,
    area: Annotated[str | None, Query()] = None,
    time_slot: Annotated[TimeSlot | None, Query()] = None,
    subscription_id: Annotated[int | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[DeliveryListRow]:
    rows, total = await delivery_service.list_for_date(
        session,
        on_date=date_,
        status=status_filter,
        area=area,
        time_slot=time_slot,
        subscription_id=subscription_id,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[DeliveryListRow](
        items=[_row(d, s, c) for d, s, c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_deliveries(
    payload: GenerateRequest, session: SessionDep, actor: CurrentUser
) -> GenerateResult:
    result = await delivery_service.generate(
        session, payload.date, actor_id=actor.id
    )
    return GenerateResult.model_validate(result)


@router.patch("/{delivery_id}", response_model=DeliveryOut)
async def update_delivery(
    delivery_id: int,
    payload: DeliveryUpdate,
    session: SessionDep,
    actor: CurrentUser,
) -> DeliveryOut:
    delivery = await delivery_service.set_status(
        session,
        delivery_id,
        new_status=payload.status,
        time_slot=payload.time_slot,
        notes=payload.notes,
        rescheduled_to_date=payload.rescheduled_to_date,
        time_slot_note=payload.time_slot_note,
        actor_id=actor.id,
    )
    return DeliveryOut.model_validate(delivery)


@router.post("/{delivery_id}/reverse", response_model=DeliveryOut)
async def reverse_delivery(
    delivery_id: int,
    payload: DeliveryReverse,
    session: SessionDep,
    actor: CurrentUser,
) -> DeliveryOut:
    delivery = await delivery_service.reverse(
        session, delivery_id, payload.reason, actor_id=actor.id
    )
    return DeliveryOut.model_validate(delivery)
