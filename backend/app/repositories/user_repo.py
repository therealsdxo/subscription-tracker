"""Query helpers for the ``users`` table."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_users(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[User], int]:
    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    rows = (
        await session.execute(
            select(User).order_by(User.id).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def add(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.flush()
    return user
