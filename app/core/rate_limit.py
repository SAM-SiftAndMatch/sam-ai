from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.exceptions import build_error_payload

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.DEFAULT_RATE_LIMIT],
    enabled=settings.RATE_LIMIT_ENABLED,
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Format HTTP 429 response when rate limit is exceeded."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=build_error_payload(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded: {exc.detail}",
        ),
    )
