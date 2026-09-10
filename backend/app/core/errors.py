"""Application error types and the standard error envelope (tech_doc.md §8)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("healthx.errors")


class AppError(Exception):
    """Base class for expected, mapped application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: list[dict[str, Any]] | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHENTICATED"


class PermissionError(AppError):  # noqa: A001 - deliberate domain name
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"

    def __init__(self, message: str, *, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _envelope(
    code: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {"code": code, "message": message, "details": details or []},
        "warnings": warnings or [],
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers: dict[str, str] | None = None
        if isinstance(exc, RateLimitError):
            headers = {"Retry-After": str(exc.retry_after)}
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, details=exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"loc": list(err["loc"]), "message": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", details=details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
        )
