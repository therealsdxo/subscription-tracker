"""Customer + address endpoints (tech_doc.md §5.2, §8).

STAFF may create/update customers and manage addresses. Only ADMIN may
deactivate / reactivate a customer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import CurrentUser, SessionDep, require_admin, require_staff
from app.models.user import User
from app.schemas.common import DataWithWarnings, Page
from app.schemas.customer import (
    AddressCreate,
    AddressOut,
    AddressUpdate,
    CustomerCreate,
    CustomerDeactivate,
    CustomerDetail,
    CustomerOut,
    CustomerUpdate,
)
from app.schemas.subscription import CustomerSubscriptionSummary, SubscriptionOut
from app.services import customer_service, subscription_service

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(require_staff)],
)

AdminUser = Annotated[User, Depends(require_admin)]
CustomerResult = DataWithWarnings[CustomerOut]


@router.get("", response_model=Page[CustomerOut])
async def list_customers(
    session: SessionDep,
    q: Annotated[str | None, Query(description="name contains")] = None,
    phone: Annotated[str | None, Query()] = None,
    code: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[CustomerOut]:
    rows, total = await customer_service.search_customers(
        session,
        q=q,
        phone=phone,
        code=code,
        is_active=is_active,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[CustomerOut](
        items=[CustomerOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CustomerResult, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate, session: SessionDep, actor: CurrentUser
) -> CustomerResult:
    customer, warnings = await customer_service.create_customer(
        session, payload, actor_id=actor.id
    )
    return CustomerResult(data=CustomerOut.model_validate(customer), warnings=warnings)


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(customer_id: int, session: SessionDep) -> CustomerDetail:
    customer = await customer_service.get_customer(session, customer_id)
    current, past = await subscription_service.customer_summary(session, customer_id)
    detail = CustomerDetail.model_validate(customer)
    detail.subscriptions = CustomerSubscriptionSummary(
        current=SubscriptionOut.model_validate(current) if current else None,
        past_count=past,
    )
    return detail


@router.patch("/{customer_id}", response_model=CustomerResult)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    session: SessionDep,
    actor: CurrentUser,
) -> CustomerResult:
    customer, warnings = await customer_service.update_customer(
        session, customer_id, payload, actor_id=actor.id
    )
    return CustomerResult(data=CustomerOut.model_validate(customer), warnings=warnings)


@router.post("/{customer_id}/deactivate", response_model=CustomerOut)
async def deactivate_customer(
    customer_id: int,
    payload: CustomerDeactivate,
    session: SessionDep,
    actor: AdminUser,
) -> CustomerOut:
    customer = await customer_service.deactivate_customer(
        session, customer_id, payload.reason, actor_id=actor.id
    )
    return CustomerOut.model_validate(customer)


@router.post("/{customer_id}/reactivate", response_model=CustomerOut)
async def reactivate_customer(
    customer_id: int, session: SessionDep, actor: AdminUser
) -> CustomerOut:
    customer = await customer_service.reactivate_customer(
        session, customer_id, actor_id=actor.id
    )
    return CustomerOut.model_validate(customer)


# --- addresses ------------------------------------------------------------


@router.get("/{customer_id}/addresses", response_model=list[AddressOut])
async def list_addresses(customer_id: int, session: SessionDep) -> list[AddressOut]:
    customer = await customer_service.get_customer(session, customer_id)
    return [AddressOut.model_validate(a) for a in customer.addresses]


@router.post(
    "/{customer_id}/addresses",
    response_model=AddressOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    customer_id: int,
    payload: AddressCreate,
    session: SessionDep,
    actor: CurrentUser,
) -> AddressOut:
    address = await customer_service.add_address(
        session, customer_id, payload, actor_id=actor.id
    )
    return AddressOut.model_validate(address)


@router.patch("/{customer_id}/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    customer_id: int,
    address_id: int,
    payload: AddressUpdate,
    session: SessionDep,
    actor: CurrentUser,
) -> AddressOut:
    address = await customer_service.update_address(
        session, customer_id, address_id, payload, actor_id=actor.id
    )
    return AddressOut.model_validate(address)


@router.delete(
    "/{customer_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_address(
    customer_id: int,
    address_id: int,
    session: SessionDep,
    actor: CurrentUser,
) -> Response:
    await customer_service.remove_address(
        session, customer_id, address_id, actor_id=actor.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
