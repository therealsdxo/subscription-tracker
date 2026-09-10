"""Auth endpoints: login, refresh, me, logout (tech_doc.md §5, §8)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: SessionDep) -> TokenPair:
    return await auth_service.authenticate(session, payload.email, payload.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: SessionDep) -> TokenPair:
    return await auth_service.refresh(session, payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(_: CurrentUser) -> Response:
    """Stateless logout.

    v1 uses short-lived access tokens; the client discards its tokens. A
    server-side refresh-token denylist is a documented v2 item (tech_doc.md §5.1).
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)
