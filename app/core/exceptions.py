import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger("sam_ai.errors")


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


def build_error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Format unified error response JSON."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_ctx.get(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    }
    if details:
        payload["error"]["details"] = details
    return payload


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("AppException [%s]: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(exc.code, exc.message, exc.details),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(code, str(exc.detail)),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_payload(
            code="VALIDATION_ERROR",
            message="Request body or query parameter validation failed",
            details=errors,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception occurred while processing request: %s", str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
        ),
    )


def register_exception_handlers(app: FastAPI):
    """Register all centralized exception handlers with FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
