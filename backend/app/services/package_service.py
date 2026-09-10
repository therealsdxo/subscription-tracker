"""Package management (tech_doc.md §4.2 BR-4…BR-7).

Editing a package never touches existing subscriptions — critical values are
snapshotted at subscription creation (BR-5), implemented in Milestone 3.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import PackageStatus
from app.models.package import Package
from app.repositories import package_repo, subscription_repo
from app.schemas.package import PackageCreate, PackageUpdate
from app.services import audit_service, code_service


async def is_package_referenced(session: AsyncSession, package_id: int) -> bool:
    """Whether any subscription has ever used this package (BR-6)."""
    return await subscription_repo.package_in_use(session, package_id)


def _summary(pkg: Package) -> dict[str, object]:
    return {
        "package_code": pkg.package_code,
        "name": pkg.name,
        "number_of_meals": pkg.number_of_meals,
        "validity_days": pkg.validity_days,
        "base_price": str(pkg.base_price),
        "tax_amount": str(pkg.tax_amount),
        "final_price": str(pkg.final_price),
        "status": pkg.status.value,
    }


async def get_package(session: AsyncSession, package_id: int) -> Package:
    pkg = await package_repo.get_by_id(session, package_id)
    if pkg is None:
        raise NotFoundError("Package not found")
    return pkg


async def list_packages(
    session: AsyncSession,
    *,
    status: PackageStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[Package], int]:
    return await package_repo.list_packages(
        session, status=status, limit=limit, offset=offset
    )


async def create_package(
    session: AsyncSession, payload: PackageCreate, *, actor_id: int | None
) -> Package:
    tax = payload.tax_amount
    pkg = Package(
        package_code=await code_service.next_code(session, "package"),
        name=payload.name.strip(),
        description=payload.description,
        number_of_meals=payload.number_of_meals,
        validity_days=payload.validity_days,
        base_price=payload.base_price,
        tax_amount=tax,
        final_price=payload.base_price + tax,
        status=PackageStatus.ACTIVE,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(pkg)
    await session.flush()
    await audit_service.record(
        session,
        action="PACKAGE_CREATED",
        entity_type="package",
        entity_id=pkg.id,
        actor_id=actor_id,
        after=_summary(pkg),
    )
    return pkg


async def update_package(
    session: AsyncSession,
    package_id: int,
    payload: PackageUpdate,
    *,
    actor_id: int | None,
) -> Package:
    pkg = await get_package(session, package_id)
    before = _summary(pkg)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        pkg.name = data["name"].strip()
    if "description" in data:
        pkg.description = data["description"]
    if data.get("number_of_meals") is not None:
        pkg.number_of_meals = data["number_of_meals"]
    if data.get("validity_days") is not None:
        pkg.validity_days = data["validity_days"]
    if data.get("base_price") is not None:
        pkg.base_price = data["base_price"]
    if data.get("tax_amount") is not None:
        pkg.tax_amount = data["tax_amount"]
    pkg.final_price = _as_decimal(pkg.base_price) + _as_decimal(pkg.tax_amount)
    pkg.updated_by = actor_id
    await session.flush()

    await audit_service.record(
        session,
        action="PACKAGE_UPDATED",
        entity_type="package",
        entity_id=pkg.id,
        actor_id=actor_id,
        before=before,
        after=_summary(pkg),
    )
    return pkg


async def set_status(
    session: AsyncSession,
    package_id: int,
    status: PackageStatus,
    *,
    actor_id: int | None,
) -> Package:
    pkg = await get_package(session, package_id)
    if pkg.status == status:
        return pkg
    pkg.status = status
    pkg.updated_by = actor_id
    await session.flush()
    await audit_service.record(
        session,
        action="PACKAGE_ACTIVATED" if status == PackageStatus.ACTIVE
        else "PACKAGE_DEACTIVATED",
        entity_type="package",
        entity_id=pkg.id,
        actor_id=actor_id,
        after={"status": pkg.status.value},
    )
    return pkg


async def delete_package(
    session: AsyncSession, package_id: int, *, actor_id: int | None
) -> None:
    pkg = await get_package(session, package_id)
    if await is_package_referenced(session, package_id):
        raise ConflictError(
            "This package has been used by a subscription and can only be "
            "deactivated, not deleted",
            code="PACKAGE_IN_USE",
        )
    summary = _summary(pkg)
    try:
        await session.delete(pkg)
        await session.flush()
    except IntegrityError as exc:  # pragma: no cover - defensive
        raise ConflictError(
            "This package is referenced and cannot be deleted",
            code="PACKAGE_IN_USE",
        ) from exc
    await audit_service.record(
        session,
        action="PACKAGE_DELETED",
        entity_type="package",
        entity_id=package_id,
        actor_id=actor_id,
        before=summary,
    )


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
