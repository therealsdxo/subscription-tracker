"""Query helpers for the ``packages`` table."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PackageStatus
from app.models.package import Package


async def get_by_id(session: AsyncSession, package_id: int) -> Package | None:
    return await session.get(Package, package_id)


async def list_packages(
    session: AsyncSession,
    *,
    status: PackageStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[Package], int]:
    where = () if status is None else (Package.status == status,)
    total = (
        await session.execute(
            select(func.count()).select_from(Package).where(*where)
        )
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(Package)
                .where(*where)
                .order_by(Package.id)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total


async def add(session: AsyncSession, package: Package) -> Package:
    session.add(package)
    await session.flush()
    return package
