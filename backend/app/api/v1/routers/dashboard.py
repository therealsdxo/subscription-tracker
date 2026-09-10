"""Dashboard endpoint (tech_doc.md §9.4). STAFF."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import SessionDep, require_staff
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_staff)],
)


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(session: SessionDep) -> DashboardSummary:
    return await dashboard_service.summary(session)
