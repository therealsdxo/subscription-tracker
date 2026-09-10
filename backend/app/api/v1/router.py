"""Aggregate router for API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    auth,
    customers,
    deliveries,
    health,
    holidays,
    packages,
    subscriptions,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(packages.router)
api_router.include_router(customers.router)
api_router.include_router(subscriptions.router)
api_router.include_router(deliveries.router)
api_router.include_router(holidays.router)
