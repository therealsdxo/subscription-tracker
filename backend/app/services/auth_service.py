"""Authentication: login, token refresh, current-user resolution."""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.repositories import user_repo
from app.schemas.auth import TokenPair

_INVALID_CREDENTIALS = "Invalid email or password"


async def authenticate(session: AsyncSession, email: str, password: str) -> TokenPair:
    user = await user_repo.get_by_email(session, email)
    if user is None or not user.is_active:
        # Still run a hash to keep timing roughly constant.
        verify_password(password, _DUMMY_HASH)
        raise AuthError(_INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash):
        raise AuthError(_INVALID_CREDENTIALS)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = datetime.now(UTC)
    await session.flush()
    return _issue_tokens(user)


async def refresh(session: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired refresh token") from exc

    user = await user_repo.get_by_id(session, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Account is no longer active")
    return _issue_tokens(user)


async def current_user(session: AsyncSession, access_token: str) -> User:
    try:
        payload = decode_token(access_token, expected_type="access")
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired access token") from exc

    user = await user_repo.get_by_id(session, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Account is no longer active")
    return user


def _issue_tokens(user: User) -> TokenPair:
    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


# A fixed valid Argon2 hash of a random string, used only to equalise timing on
# the "unknown user" path.
_DUMMY_HASH = hash_password("timing-equalisation-placeholder")
