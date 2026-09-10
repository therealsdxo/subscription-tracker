"""Shared response schemas: error envelope, pagination (tech_doc.md §8)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class Warning(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
    warnings: list[Warning] = Field(default_factory=list)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class DataWithWarnings(BaseModel, Generic[T]):
    """Success envelope for mutations that may surface non-blocking warnings
    (e.g. a possible-duplicate customer). ``tech_doc.md`` §8."""

    data: T
    warnings: list[Warning] = Field(default_factory=list)


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str


class ReadinessStatus(BaseModel):
    status: str
    checks: dict[str, str]
