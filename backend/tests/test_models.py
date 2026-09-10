"""Model-level invariants for the foundational tables."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User


async def test_timestamps_are_timezone_aware_utc(db_session: AsyncSession) -> None:
    user = User(
        email="tz@example.com",
        full_name="TZ",
        password_hash="x",
        role=UserRole.STAFF,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset() == timedelta(0)
    # Server clock and app clock should agree to within a few minutes.
    assert abs(user.created_at - datetime.now(UTC)) < timedelta(minutes=5)
