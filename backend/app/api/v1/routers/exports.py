"""CSV export endpoints (tech_doc.md §9.3). All STAFF."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import SessionDep, require_staff
from app.services import export_service

router = APIRouter(
    prefix="/exports",
    tags=["exports"],
    dependencies=[Depends(require_staff)],
)


async def _csv(body: AsyncIterator[str], filename: str) -> Response:
    content = "".join([chunk async for chunk in body])
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/customers.csv")
async def customers_csv(session: SessionDep) -> Response:
    return await _csv(export_service.customers_csv(session), "customers.csv")


@router.get("/subscriptions.csv")
async def subscriptions_csv(session: SessionDep) -> Response:
    return await _csv(export_service.subscriptions_csv(session), "subscriptions.csv")


@router.get("/payments.csv")
async def payments_csv(session: SessionDep) -> Response:
    return await _csv(export_service.payments_csv(session), "payments.csv")


@router.get("/deliveries.csv")
async def deliveries_csv(
    session: SessionDep,
    date_: Annotated[date | None, Query(alias="date")] = None,
) -> Response:
    name = f"deliveries-{date_.isoformat()}.csv" if date_ else "deliveries.csv"
    return await _csv(export_service.deliveries_csv(session, date_), name)
