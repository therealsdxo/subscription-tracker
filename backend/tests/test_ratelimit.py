"""Login rate-limiting tests (tech_doc.md §5.1)."""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User


async def test_ip_limit_returns_429_with_retry_after(
    client: AsyncClient, admin_user: User
) -> None:
    # 10 attempts / IP allowed; the 11th is blocked regardless of correctness.
    for _ in range(10):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "supersecret123"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) >= 1


async def test_account_limit_is_independent_of_ip_cap(
    client: AsyncClient, admin_user: User
) -> None:
    # 8 attempts / account allowed; the 9th for that email is blocked even
    # though the IP cap (10) has not been hit.
    for _ in range(8):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "supersecret123"},
    )
    assert blocked.status_code == 429


async def test_good_login_within_window_still_works(
    client: AsyncClient, admin_user: User
) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "supersecret123"},
    )
    assert r.status_code == 200
