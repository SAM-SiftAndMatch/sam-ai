from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router
from app.core.config import settings

api_router = APIRouter()

# Mount API v1
api_router.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Also expose health check at top level (/health) for backward compatibility & healthcheck probes
api_router.include_router(health.router)
