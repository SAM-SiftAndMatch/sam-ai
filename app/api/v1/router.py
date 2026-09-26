from fastapi import APIRouter

from app.api.v1.endpoints import chunks, health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks"])
