"""Health endpoints (tech_doc.md §8, §11).

``/health``       — liveness; always 200 if the process is up.
``/health/ready`` — readiness; 503 if a dependency (the database) is unavailable.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.db import engine
from app.core.logging import get_logger
from app.schemas.common import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])
logger = get_logger("healthx.health")


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    settings = get_settings()
    return HealthStatus(
        status="ok",
        version=__version__,
        environment=settings.env,
    )


@router.get("/health/ready", response_model=ReadinessStatus)
async def readiness(response: Response) -> ReadinessStatus:
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report any failure as not-ready
        logger.warning("readiness_db_check_failed", error=str(exc))
        checks["database"] = "error"

    ok = all(v == "ok" for v in checks.values())
    response.status_code = (
        status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return ReadinessStatus(status="ok" if ok else "unavailable", checks=checks)
