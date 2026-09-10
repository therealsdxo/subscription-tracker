"""Seed the first ADMIN user and default settings rows.

Idempotent — safe to run repeatedly. Run after ``alembic upgrade head``:

    uv run python -m scripts.seed
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.setting import DEFAULT_SETTINGS, Setting
from app.models.user import User

logger = get_logger("healthx.seed")


async def seed() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    async with SessionFactory() as session:
        # Default settings
        existing_keys = set(
            (await session.execute(select(Setting.key))).scalars().all()
        )
        added = 0
        for row in DEFAULT_SETTINGS:
            if row["key"] not in existing_keys:
                session.add(Setting(**row))
                added += 1

        # First ADMIN
        admin = (
            await session.execute(
                select(User).where(User.email == settings.seed_admin_email.lower())
            )
        ).scalar_one_or_none()
        if admin is None:
            session.add(
                User(
                    email=settings.seed_admin_email.lower(),
                    full_name=settings.seed_admin_name,
                    password_hash=hash_password(settings.seed_admin_password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            logger.info("seed_admin_created", email=settings.seed_admin_email)
        else:
            logger.info("seed_admin_exists", email=settings.seed_admin_email)

        await session.commit()
        logger.info("seed_complete", settings_added=added)


if __name__ == "__main__":
    asyncio.run(seed())
