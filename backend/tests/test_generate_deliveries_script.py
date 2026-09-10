"""Test the scripts.generate_deliveries job (tech_doc.md §16)."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import Delivery
from app.models.user import User
from app.services.delivery_service import generate
from tests.test_subscriptions import make_customer, make_package, sub_payload


async def test_generate_for_explicit_date_creates_rows(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers,
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)
    await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(cid, pkg, aid, start_date="2026-09-01"),
    )

    # This is what scripts.generate_deliveries.main() does.
    result = await generate(db_session, date(2026, 9, 7), actor_id=None)
    await db_session.flush()

    assert result == {"date": "2026-09-07", "created": 1, "open_day": True}
    count = (
        await db_session.execute(select(func.count()).select_from(Delivery))
    ).scalar_one()
    assert count == 1
