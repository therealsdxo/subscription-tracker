"""Test fixtures: a real Postgres test DB with per-test transaction rollback."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable

# Point the app at the test database *before* app modules read settings.
os.environ.setdefault(
    "HEALTHX_DATABASE_URL",
    "postgresql+psycopg://healthx:healthx@localhost:5433/healthx_test",
)
os.environ.setdefault("HEALTHX_JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("HEALTHX_ENV", "ci")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

# Sequences are non-transactional, so each test resets them for stable codes.
_CODE_SEQUENCES = ("customer_code_seq", "package_code_seq", "subscription_code_seq")

from app.core.config import get_settings  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        get_settings().async_database_url,
        connect_args={"options": "-c timezone=utc"},
    )
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
        # Drop any leftover Alembic marker so a prior `alembic` run against this
        # database can't confuse a later one (the suite builds schema from
        # metadata, not migrations).
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with _engine.begin() as setup:
        for seq in _CODE_SEQUENCES:
            await setup.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))

    conn = await _engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        full_name="Test Admin",
        password_hash=hash_password("supersecret123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    user = User(
        email="staff@example.com",
        full_name="Test Staff",
        password_hash=hash_password("supersecret123"),
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    from app.core.security import create_access_token

    def _make(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    return _make
