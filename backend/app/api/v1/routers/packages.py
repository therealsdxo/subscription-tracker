"""Package endpoints — read: STAFF; write: ADMIN (tech_doc.md §5.2, §8)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import SessionDep, require_admin, require_staff
from app.models.enums import PackageStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.package import PackageCreate, PackageOut, PackageUpdate
from app.services import package_service

router = APIRouter(prefix="/packages", tags=["packages"])

AdminUser = Annotated[User, Depends(require_admin)]


@router.get("", response_model=Page[PackageOut], dependencies=[Depends(require_staff)])
async def list_packages(
    session: SessionDep,
    status_filter: Annotated[PackageStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[PackageOut]:
    rows, total = await package_service.list_packages(
        session, status=status_filter, limit=page_size, offset=(page - 1) * page_size
    )
    return Page[PackageOut](
        items=[PackageOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{package_id}",
    response_model=PackageOut,
    dependencies=[Depends(require_staff)],
)
async def get_package(package_id: int, session: SessionDep) -> PackageOut:
    return PackageOut.model_validate(
        await package_service.get_package(session, package_id)
    )


@router.post(
    "",
    response_model=PackageOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_package(
    payload: PackageCreate, session: SessionDep, actor: AdminUser
) -> PackageOut:
    pkg = await package_service.create_package(session, payload, actor_id=actor.id)
    return PackageOut.model_validate(pkg)


@router.patch("/{package_id}", response_model=PackageOut)
async def update_package(
    package_id: int, payload: PackageUpdate, session: SessionDep, actor: AdminUser
) -> PackageOut:
    pkg = await package_service.update_package(
        session, package_id, payload, actor_id=actor.id
    )
    return PackageOut.model_validate(pkg)


@router.post("/{package_id}/activate", response_model=PackageOut)
async def activate_package(
    package_id: int, session: SessionDep, actor: AdminUser
) -> PackageOut:
    pkg = await package_service.set_status(
        session, package_id, PackageStatus.ACTIVE, actor_id=actor.id
    )
    return PackageOut.model_validate(pkg)


@router.post("/{package_id}/deactivate", response_model=PackageOut)
async def deactivate_package(
    package_id: int, session: SessionDep, actor: AdminUser
) -> PackageOut:
    pkg = await package_service.set_status(
        session, package_id, PackageStatus.INACTIVE, actor_id=actor.id
    )
    return PackageOut.model_validate(pkg)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    package_id: int, session: SessionDep, actor: AdminUser
) -> Response:
    await package_service.delete_package(session, package_id, actor_id=actor.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
