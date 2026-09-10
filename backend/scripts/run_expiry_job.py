"""Run the subscription expiry / activation sweep once.

    uv run python -m scripts.run_expiry_job
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.logging import configure_logging, get_logger
from app.workers.expiry_job import run_expiry_job

logger = get_logger("healthx.run_expiry_job")


async def main() -> None:
    configure_logging(get_settings().log_level)
    async with SessionFactory() as session:
        result = await run_expiry_job(session)
        await session.commit()
    logger.info("run_expiry_job_done", **result)


if __name__ == "__main__":
    asyncio.run(main())
