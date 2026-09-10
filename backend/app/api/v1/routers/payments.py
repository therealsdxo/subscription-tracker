"""Payment lookup endpoints (tech_doc.md §8). All STAFF.

Payment/refund *creation* lives on the subscriptions router
(``POST /subscriptions/{id}/payments`` · ``/refunds``).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_staff
from app.models.enums import PaymentMethod
from app.schemas.common import Page
from app.schemas.payment import PaymentOut
from app.services import payment_service

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=Page[PaymentOut])
async def list_payments(
    session: SessionDep,
    subscription_id: Annotated[int | None, Query()] = None,
    customer_id: Annotated[int | None, Query()] = None,
    method: Annotated[PaymentMethod | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[PaymentOut]:
    rows, total = await payment_service.list_payments(
        session,
        subscription_id=subscription_id,
        customer_id=customer_id,
        method=method,
        date_from=date_from,
        date_to=date_to,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[PaymentOut](
        items=[PaymentOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(payment_id: int, session: SessionDep) -> PaymentOut:
    return PaymentOut.model_validate(
        await payment_service.get_payment(session, payment_id)
    )
