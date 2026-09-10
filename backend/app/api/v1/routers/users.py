"""User management endpoints — ADMIN only (tech_doc.md §5.2, §8)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessionDep, require_admin
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin)],
)

AdminUser = Annotated[User, Depends(require_admin)]


@router.get("", response_model=Page[UserOut])
async def list_users(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[UserOut]:
    rows, total = await user_service.list_users(
        session, limit=page_size, offset=(page - 1) * page_size
    )
    return Page[UserOut](
        items=[UserOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, session: SessionDep, actor: AdminUser
) -> UserOut:
    user = await user_service.create_user(session, payload, actor_id=actor.id)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, session: SessionDep) -> UserOut:
    return UserOut.model_validate(await user_service.get_user(session, user_id))


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, payload: UserUpdate, session: SessionDep, actor: AdminUser
) -> UserOut:
    user = await user_service.update_user(session, user_id, payload, actor_id=actor.id)
    return UserOut.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: int, session: SessionDep, actor: AdminUser
) -> UserOut:
    user = await user_service.deactivate_user(session, user_id, actor_id=actor.id)
    return UserOut.model_validate(user)
