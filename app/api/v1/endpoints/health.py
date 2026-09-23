from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.db.mongodb import ping_mongo
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    is_db_connected = await ping_mongo()
    return HealthResponse(
        status="healthy",
        database="connected" if is_db_connected else "disconnected",
        app_name=settings.APP_NAME,
        version="0.1.0",
        timestamp=datetime.now(UTC).isoformat(),
    )
