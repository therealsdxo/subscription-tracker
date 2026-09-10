"""Code generator tests (tech_doc.md §3.2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.services import code_service


async def test_sequential_zero_padded_with_default_config(
    db_session: AsyncSession,
) -> None:
    first = await code_service.next_code(db_session, "customer")
    second = await code_service.next_code(db_session, "customer")
    assert first == "CUST-000001"
    assert second == "CUST-000002"


async def test_package_uses_own_sequence_and_width(db_session: AsyncSession) -> None:
    code = await code_service.next_code(db_session, "package")
    assert code == "PKG-00001"


async def test_prefix_and_width_come_from_settings(db_session: AsyncSession) -> None:
    db_session.add(Setting(key="customer_code_prefix", value="MEMBER-"))
    db_session.add(Setting(key="customer_code_width", value=4))
    await db_session.flush()
    code = await code_service.next_code(db_session, "customer")
    assert code.startswith("MEMBER-")
    assert code == "MEMBER-0001"
