"""Customer + address management (tech_doc.md §3.3, §4.1 BR-1…BR-3).

Customers are never hard-deleted — ``BL-04`` is overridden by Q0.2. Deletion is
always a soft ``is_active = false`` and history is retained.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.customer import Customer, CustomerAddress
from app.repositories import customer_repo
from app.schemas.common import Warning
from app.schemas.customer import (
    AddressCreate,
    AddressUpdate,
    CustomerCreate,
    CustomerUpdate,
)
from app.services import audit_service, code_service


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def _normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-().]", "", phone.strip())
    return cleaned


async def _duplicate_warnings(
    session: AsyncSession, name: str, *, exclude_id: int | None = None
) -> list[Warning]:
    match = await customer_repo.find_active_by_normalized_name(
        session, _normalize_name(name), exclude_id=exclude_id
    )
    if match is None:
        return []
    return [
        Warning(
            code="POSSIBLE_DUPLICATE",
            message=(
                f"An active customer with a matching name already exists "
                f"({match.customer_code})."
            ),
        )
    ]


async def _check_unique_contact(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
    exclude_id: int | None = None,
) -> None:
    if phone is not None:
        existing = await customer_repo.get_by_phone(session, phone)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(
                "A customer with this phone number already exists",
                code="PHONE_TAKEN",
            )
    if email is not None:
        existing = await customer_repo.get_by_email(session, email)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(
                "A customer with this email already exists", code="EMAIL_TAKEN"
            )


async def get_customer(session: AsyncSession, customer_id: int) -> Customer:
    customer = await customer_repo.get_with_addresses(session, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    return customer


async def search_customers(
    session: AsyncSession,
    *,
    q: str | None,
    phone: str | None,
    code: str | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[Customer], int]:
    return await customer_repo.search(
        session,
        q=q,
        phone=phone,
        code=code,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


async def create_customer(
    session: AsyncSession, payload: CustomerCreate, *, actor_id: int | None
) -> tuple[Customer, list[Warning]]:
    phone = _normalize_phone(payload.phone)
    email = payload.email.lower() if payload.email else None
    await _check_unique_contact(session, phone=phone, email=email)
    warnings = await _duplicate_warnings(session, payload.name)

    customer = Customer(
        customer_code=await code_service.next_code(session, "customer"),
        name=payload.name.strip(),
        phone=phone,
        email=email,
        default_dietary_preference=payload.default_dietary_preference,
        dietary_notes=payload.dietary_notes,
        allergies=payload.allergies,
        notes=payload.notes,
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    primary_index = next(
        (i for i, a in enumerate(payload.addresses) if a.is_primary), 0
    )
    for i, addr in enumerate(payload.addresses):
        customer.addresses.append(_build_address(addr, is_primary=(i == primary_index)))

    session.add(customer)
    try:
        await session.flush()
    except IntegrityError as exc:  # pragma: no cover - race fallback
        raise ConflictError(
            "A customer with this phone or email already exists",
            code="CONTACT_TAKEN",
        ) from exc

    await audit_service.record(
        session,
        action="CUSTOMER_CREATED",
        entity_type="customer",
        entity_id=customer.id,
        actor_id=actor_id,
        after={"customer_code": customer.customer_code, "name": customer.name},
    )
    return customer, warnings


async def update_customer(
    session: AsyncSession,
    customer_id: int,
    payload: CustomerUpdate,
    *,
    actor_id: int | None,
) -> tuple[Customer, list[Warning]]:
    customer = await get_customer(session, customer_id)
    data = payload.model_dump(exclude_unset=True)
    before = {"name": customer.name, "phone": customer.phone, "email": customer.email}

    new_phone = _normalize_phone(data["phone"]) if data.get("phone") else None
    new_email = data["email"].lower() if data.get("email") else None
    await _check_unique_contact(
        session, phone=new_phone, email=new_email, exclude_id=customer.id
    )

    if data.get("name") is not None:
        customer.name = data["name"].strip()
    if new_phone is not None:
        customer.phone = new_phone
    if "email" in data:
        customer.email = data["email"].lower() if data["email"] else None
    if "default_dietary_preference" in data:
        customer.default_dietary_preference = data["default_dietary_preference"]
    if "dietary_notes" in data:
        customer.dietary_notes = data["dietary_notes"]
    if "allergies" in data:
        customer.allergies = data["allergies"]
    if "notes" in data:
        customer.notes = data["notes"]
    customer.updated_by = actor_id
    await session.flush()

    warnings = (
        await _duplicate_warnings(session, customer.name, exclude_id=customer.id)
        if data.get("name") is not None
        else []
    )
    await audit_service.record(
        session,
        action="CUSTOMER_UPDATED",
        entity_type="customer",
        entity_id=customer.id,
        actor_id=actor_id,
        before=before,
        after={
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
        },
    )
    return customer, warnings


async def deactivate_customer(
    session: AsyncSession, customer_id: int, reason: str, *, actor_id: int | None
) -> Customer:
    customer = await get_customer(session, customer_id)
    if not customer.is_active:
        raise ConflictError("Customer is already deactivated")
    customer.is_active = False
    customer.deactivated_at = datetime.now(UTC)
    customer.deactivated_by = actor_id
    customer.deactivation_reason = reason
    customer.updated_by = actor_id
    await session.flush()
    await audit_service.record(
        session,
        action="CUSTOMER_DEACTIVATED",
        entity_type="customer",
        entity_id=customer.id,
        actor_id=actor_id,
        metadata={"reason": reason},
    )
    return customer


async def reactivate_customer(
    session: AsyncSession, customer_id: int, *, actor_id: int | None
) -> Customer:
    customer = await get_customer(session, customer_id)
    if customer.is_active:
        raise ConflictError("Customer is already active")
    customer.is_active = True
    customer.deactivated_at = None
    customer.deactivated_by = None
    customer.deactivation_reason = None
    customer.updated_by = actor_id
    await session.flush()
    await audit_service.record(
        session,
        action="CUSTOMER_REACTIVATED",
        entity_type="customer",
        entity_id=customer.id,
        actor_id=actor_id,
    )
    return customer


# --- addresses -------------------------------------------------------------


def _build_address(payload: AddressCreate, *, is_primary: bool) -> CustomerAddress:
    return CustomerAddress(
        label=payload.label,
        address_line=payload.address_line.strip(),
        area=payload.area.strip(),
        city=payload.city.strip(),
        pincode=payload.pincode.strip(),
        landmark=payload.landmark,
        delivery_notes=payload.delivery_notes,
        is_primary=is_primary,
        is_active=True,
    )


async def _demote_primaries(
    customer: Customer, *, except_id: int | None = None
) -> None:
    """Clear ``is_primary`` on the customer's addresses (ORM-tracked).

    The caller must ``flush()`` this before setting a new primary so the partial
    unique index is never transiently violated.
    """
    for addr in customer.addresses:
        if addr.is_primary and addr.id != except_id:
            addr.is_primary = False


async def add_address(
    session: AsyncSession,
    customer_id: int,
    payload: AddressCreate,
    *,
    actor_id: int | None,
) -> CustomerAddress:
    customer = await get_customer(session, customer_id)
    active = [a for a in customer.addresses if a.is_active]
    make_primary = payload.is_primary or not active

    if make_primary:
        await _demote_primaries(customer)
        await session.flush()

    address = _build_address(payload, is_primary=make_primary)
    customer.addresses.append(address)
    await session.flush()

    await audit_service.record(
        session,
        action="CUSTOMER_ADDRESS_ADDED",
        entity_type="customer",
        entity_id=customer.id,
        actor_id=actor_id,
        metadata={"address_id": address.id},
    )
    return address


async def update_address(
    session: AsyncSession,
    customer_id: int,
    address_id: int,
    payload: AddressUpdate,
    *,
    actor_id: int | None,
) -> CustomerAddress:
    customer = await get_customer(session, customer_id)
    address = next((a for a in customer.addresses if a.id == address_id), None)
    if address is None or not address.is_active:
        raise NotFoundError("Address not found")
    data = payload.model_dump(exclude_unset=True)

    for field in (
        "label",
        "address_line",
        "area",
        "city",
        "pincode",
        "landmark",
        "delivery_notes",
    ):
        if field in data:
            setattr(address, field, data[field])

    if data.get("is_primary") is True and not address.is_primary:
        await _demote_primaries(customer, except_id=address.id)
        await session.flush()
        address.is_primary = True
    elif data.get("is_primary") is False and address.is_primary:
        raise ConflictError(
            "Set another address as primary instead of unsetting this one",
            code="PRIMARY_REQUIRED",
        )

    await session.flush()
    await audit_service.record(
        session,
        action="CUSTOMER_ADDRESS_UPDATED",
        entity_type="customer",
        entity_id=customer_id,
        actor_id=actor_id,
        metadata={"address_id": address.id},
    )
    return address


async def remove_address(
    session: AsyncSession,
    customer_id: int,
    address_id: int,
    *,
    actor_id: int | None,
) -> None:
    customer = await get_customer(session, customer_id)
    address = next((a for a in customer.addresses if a.id == address_id), None)
    if address is None or not address.is_active:
        raise NotFoundError("Address not found")

    active = [a for a in customer.addresses if a.is_active]
    if len(active) <= 1:
        raise ConflictError(
            "A customer must have at least one active address",
            code="LAST_ADDRESS",
        )

    was_primary = address.is_primary
    address.is_active = False
    address.is_primary = False
    await session.flush()

    if was_primary:
        for candidate in customer.addresses:
            if candidate.is_active and candidate.id != address_id:
                candidate.is_primary = True
                break
        await session.flush()

    await audit_service.record(
        session,
        action="CUSTOMER_ADDRESS_REMOVED",
        entity_type="customer",
        entity_id=customer_id,
        actor_id=actor_id,
        metadata={"address_id": address_id},
    )
