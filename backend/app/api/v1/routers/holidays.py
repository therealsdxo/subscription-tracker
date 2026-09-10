"""Holiday calendar endpoints — read STAFF, write ADMIN (tech_doc.md §5.2, §6.7)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import SessionDep, require_admin, require_staff
from app.models.user import User
from app.schemas.delivery import HolidayCreate, HolidayOut
from app.services import holiday_service

router = APIRouter(prefix="/holidays", tags=["holidays"])

AdminUser = Annotated[User, Depends(require_admin)]


@router.get("", response_model=list[HolidayOut], dependencies=[Depends(require_staff)])
async def list_holidays(
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[HolidayOut]:
    rows = await holiday_service.list_holidays(session, start=start, end=end)
    return [HolidayOut.model_validate(r) for r in rows]


@router.post("", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
async def add_holiday(
    payload: HolidayCreate, session: SessionDep, actor: AdminUser
) -> HolidayOut:
    holiday = await holiday_service.add_holiday(
        session, payload.holiday_date, payload.name, actor_id=actor.id
    )
    return HolidayOut.model_validate(holiday)


@router.delete("/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_holiday(
    holiday_id: int, session: SessionDep, actor: AdminUser
) -> Response:
    await holiday_service.remove_holiday(session, holiday_id, actor_id=actor.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
