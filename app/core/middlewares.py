import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_ctx

logger = logging.getLogger("sam_ai.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request ID, measure response duration, and log access."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Get existing request ID or generate a new UUID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(request_id)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Request failed: %s %s (%.2fms)",
                request.method,
                request.url.path,
                process_time_ms,
            )
            raise
        finally:
            request_id_ctx.reset(token)

        process_time_ms = (time.perf_counter() - start_time) * 1000

        # Attach metadata headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"

        # Skip logging noisy favicon / docs static calls
        if request.url.path not in ("/favicon.ico", "/openapi.json"):
            logger.info(
                "%s %s - %d (%.2fms)",
                request.method,
                request.url.path,
                response.status_code,
                process_time_ms,
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to inject standard OWASP security headers into HTTP responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # OWASP recommended headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
