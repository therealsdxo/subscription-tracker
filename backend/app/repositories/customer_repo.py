"""Query helpers for ``customers`` and ``customer_addresses``."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer


async def get_by_id(session: AsyncSession, customer_id: int) -> Customer | None:
    return await session.get(Customer, customer_id)


async def get_with_addresses(
    session: AsyncSession, customer_id: int
) -> Customer | None:
    stmt = (
        select(Customer)
        .where(Customer.id == customer_id)
        .options(selectinload(Customer.addresses))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    stmt = select(Customer).where(Customer.phone == phone)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> Customer | None:
    stmt = select(Customer).where(func.lower(Customer.email) == email.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def find_active_by_normalized_name(
    session: AsyncSession, normalized_name: str, *, exclude_id: int | None = None
) -> Customer | None:
    stmt = select(Customer).where(
        Customer.is_active.is_(True),
        func.lower(func.btrim(Customer.name)) == normalized_name,
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    return (await session.execute(stmt)).scalars().first()


async def search(
    session: AsyncSession,
    *,
    q: str | None,
    phone: str | None,
    code: str | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[Customer], int]:
    # Filter shape: (q OR phone OR code) AND is_active
    search_group = []
    if q:
        search_group.append(Customer.name.ilike(f"%{q}%"))
    if phone:
        search_group.append(Customer.phone.ilike(f"%{phone}%"))
    if code:
        search_group.append(Customer.customer_code.ilike(f"%{code}%"))

    stmt = select(Customer)
    count_stmt = select(func.count()).select_from(Customer)
    if search_group:
        cond = or_(*search_group)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if is_active is not None:
        stmt = stmt.where(Customer.is_active.is_(is_active))
        count_stmt = count_stmt.where(Customer.is_active.is_(is_active))

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (
            await session.execute(
                stmt.order_by(Customer.id).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total
