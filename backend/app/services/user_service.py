"""User management (ADMIN only at the API layer)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserUpdate
from app.services import audit_service


async def create_user(
    session: AsyncSession, payload: UserCreate, *, actor_id: int | None
) -> User:
    if await user_repo.get_by_email(session, payload.email):
        raise ConflictError("A user with this email already exists", code="EMAIL_TAKEN")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    try:
        await user_repo.add(session, user)
    except IntegrityError as exc:  # pragma: no cover - race fallback
        raise ConflictError("A user with this email already exists", code="EMAIL_TAKEN") from exc

    await audit_service.record(
        session,
        action="USER_CREATED",
        entity_type="user",
        entity_id=user.id,
        actor_id=actor_id,
        after={"email": user.email, "role": user.role.value},
    )
    return user


async def list_users(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[User], int]:
    return await user_repo.list_users(session, limit=limit, offset=offset)


async def get_user(session: AsyncSession, user_id: int) -> User:
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


async def update_user(
    session: AsyncSession, user_id: int, payload: UserUpdate, *, actor_id: int | None
) -> User:
    user = await get_user(session, user_id)
    before = {"full_name": user.full_name, "role": user.role.value}

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    await session.flush()

    await audit_service.record(
        session,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        actor_id=actor_id,
        before=before,
        after={"full_name": user.full_name, "role": user.role.value},
    )
    return user


async def deactivate_user(
    session: AsyncSession, user_id: int, *, actor_id: int | None
) -> User:
    user = await get_user(session, user_id)
    if user.id == actor_id:
        raise ConflictError("You cannot deactivate your own account")
    user.is_active = False
    await session.flush()
    await audit_service.record(
        session,
        action="USER_DEACTIVATED",
        entity_type="user",
        entity_id=user.id,
        actor_id=actor_id,
    )
    return user
