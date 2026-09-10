"""Smoke tests for the health endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_liveness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "ci"
    assert "version" in body


async def test_request_id_header_present(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.headers.get("x-request-id")


async def test_readiness_reports_database_ok(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"]["database"] == "ok"
