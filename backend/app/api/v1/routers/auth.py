"""Auth endpoints: login, refresh, me, logout (tech_doc.md §5, §8)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.core.deps import CurrentUser, SessionDep
from app.core.ratelimit import login_limiter
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Sliding-window limits for POST /auth/login (tech_doc.md §5.1).
_IP_LIMIT, _IP_WINDOW = 10, 300
_ACCOUNT_LIMIT, _ACCOUNT_WINDOW = 8, 300


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest, request: Request, session: SessionDep
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    account = payload.email.lower()
    login_limiter.check(f"ip:{ip}", limit=_IP_LIMIT, window_seconds=_IP_WINDOW)
    login_limiter.check(
        f"acct:{account}", limit=_ACCOUNT_LIMIT, window_seconds=_ACCOUNT_WINDOW
    )
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
