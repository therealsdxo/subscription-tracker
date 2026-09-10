"""User management endpoint tests (ADMIN only)."""

from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def test_admin_creates_user_and_writes_audit(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "email": "newstaff@example.com",
            "full_name": "New Staff",
            "password": "anothersecret123",
            "role": "STAFF",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "newstaff@example.com"

    audit = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "USER_CREATED")
        )
    ).scalars().all()
    assert len(audit) == 1


async def test_duplicate_email_conflicts(
    client: AsyncClient,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "email": "admin@example.com",
            "full_name": "Dupe",
            "password": "anothersecret123",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_list_users_paginated(
    client: AsyncClient,
    admin_user: User,
    staff_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    resp = await client.get("/api/v1/users", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert body["page"] == 1


async def test_admin_cannot_deactivate_self(
    client: AsyncClient,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    resp = await client.post(
        f"/api/v1/users/{admin_user.id}/deactivate",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 409


async def test_short_password_rejected(
    client: AsyncClient,
    admin_user: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers(admin_user),
        json={
            "email": "x@example.com",
            "full_name": "X",
            "password": "short",
            "role": "STAFF",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
