"""CSV import endpoints (tech_doc.md §10.7). ADMIN only."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.deps import CurrentUser, SessionDep, require_admin
from app.schemas.imports import ImportReport
from app.services import import_service

router = APIRouter(
    prefix="/imports",
    tags=["imports"],
    dependencies=[Depends(require_admin)],
)


@router.post("/customers", response_model=ImportReport)
async def import_customers(
    session: SessionDep,
    actor: CurrentUser,
    file: Annotated[UploadFile, File()],
    mode: Annotated[Literal["validate", "commit"], Query()] = "validate",
) -> ImportReport:
    content = await file.read()
    return await import_service.import_customers(
        session, content, commit=(mode == "commit"), actor_id=actor.id
    )
