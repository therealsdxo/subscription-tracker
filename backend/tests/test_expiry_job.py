"""Tests for the daily subscription sweep (workers/expiry_job.py)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.workers.expiry_job import run_expiry_job
from tests.test_subscriptions import make_customer, make_package, sub_payload


async def test_job_expires_overdue_and_activates_due_pending(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    h = auth_headers(admin_user)
    pkg = await make_package(client, h)
    cid, aid = await make_customer(client, h)

    # An ACTIVE subscription that is already past its expected end date.
    overdue = (await client.post(
        "/api/v1/subscriptions",
        headers=h,
        json=sub_payload(
            cid, pkg, aid, start_date=(date.today() - timedelta(days=400)).isoformat()
        ),
    )).json()
    # Force it back to ACTIVE (create auto-expires a back-dated one).
    from app.models.enums import SubscriptionStatus
    from app.models.subscription import Subscription

    row = await db_session.get(Subscription, overdue["id"])
    assert row is not None
    row.status = SubscriptionStatus.ACTIVE
    row.actual_end_date = None
    await db_session.flush()

    # A PENDING subscription whose start date has arrived (queued behind the
    # ACTIVE one).
    pending = (await client.post(
        "/api/v1/subscriptions", headers=h, json=sub_payload(cid, pkg, aid)
    )).json()
    assert pending["status"] == "PENDING"

    result = await run_expiry_job(db_session)
    await db_session.flush()

    assert result == {"expired": 1, "activated": 1}
    assert (await client.get(
        f"/api/v1/subscriptions/{overdue['id']}", headers=h
    )).json()["status"] == "EXPIRED"
    assert (await client.get(
        f"/api/v1/subscriptions/{pending['id']}", headers=h
    )).json()["status"] == "ACTIVE"
