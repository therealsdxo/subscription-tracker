"""Auth flow + RBAC guard tests."""

from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient

from app.models.user import User


async def test_login_returns_token_pair(client: AsyncClient, admin_user: User) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_rejects_bad_password(client: AsyncClient, admin_user: User) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_me_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(staff_user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "staff@example.com"
    assert body["role"] == "STAFF"


async def test_refresh_issues_new_pair(client: AsyncClient, admin_user: User) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "supersecret123"},
    )
    refresh_token = login.json()["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(
    client: AsyncClient, admin_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    access = auth_headers(admin_user)["Authorization"].removeprefix("Bearer ")
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


async def test_staff_cannot_access_user_admin(
    client: AsyncClient, staff_user: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    resp = await client.get("/api/v1/users", headers=auth_headers(staff_user))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
