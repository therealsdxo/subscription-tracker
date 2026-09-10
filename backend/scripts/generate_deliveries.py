"""Generate the delivery list for a date.

    uv run python -m scripts.generate_deliveries            # tomorrow (IST)
    uv run python -m scripts.generate_deliveries 2026-09-15
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.logging import configure_logging, get_logger
from app.services.delivery_service import generate
from app.services.subscription_service import business_today

logger = get_logger("healthx.generate_deliveries")


async def main(target: date) -> None:
    configure_logging(get_settings().log_level)
    async with SessionFactory() as session:
        result = await generate(session, target, actor_id=None)
        await session.commit()
    logger.info("generate_deliveries_done", **result)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        day = date.fromisoformat(sys.argv[1])
    else:
        day = business_today() + timedelta(days=1)
    asyncio.run(main(day))
