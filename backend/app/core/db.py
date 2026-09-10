"""Database engine and session management (async SQLAlchemy 2.x)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    # Store and return timestamps in UTC regardless of server/host timezone
    # (tech_doc.md §14 — business dates are interpreted in Asia/Kolkata at the
    # application layer).
    connect_args={"options": "-c timezone=utc"},
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one transactional session per request.

    Commits on success, rolls back on any exception.
    """
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
