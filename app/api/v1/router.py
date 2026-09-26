from fastapi import APIRouter

from app.api.v1.endpoints import brief, chunks, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks"])
api_v1_router.include_router(brief.router, prefix="/brief", tags=["Brief Wizard"])
