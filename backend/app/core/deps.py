"""Reusable FastAPI dependencies: DB session, current user, role guards."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AuthError, PermissionError
from app.models.enums import UserRole
from app.models.user import User
from app.services import auth_service

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError("Authentication required")
    return await auth_service.current_user(session, credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(
    *allowed: UserRole,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    async def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionError("You do not have permission to perform this action")
        return user

    return _guard


require_admin = require_role(UserRole.ADMIN)
require_staff = require_role(UserRole.ADMIN, UserRole.STAFF)
