from __future__ import annotations

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.brief import (
    BriefGenerateRequest,
    BriefGenerateResponse,
    DiscoveryRequest,
    DiscoveryResponse,
)
from app.services.brief_service import BriefService

router = APIRouter()


def get_brief_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> BriefService:
    """Dependency injection for BriefService."""
    return BriefService(db)


@router.post(
    "/discovery",
    response_model=DiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Project Idea Discovery",
    description="Analyze user idea, identify domain category, and return structured interactive questions.",
)
async def discover_project_idea(
    body: DiscoveryRequest,
    service: BriefService = Depends(get_brief_service),
) -> DiscoveryResponse:
    """Analyze idea and return discovery questions with multiple-choice options."""
    return await service.discover(body)


@router.post(
    "/generate",
    response_model=BriefGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Comprehensive Brief & Estimation",
    description="Synthesize user answers and knowledge chunks into professional brief with timeline and budget.",
)
async def generate_project_brief(
    body: BriefGenerateRequest,
    service: BriefService = Depends(get_brief_service),
) -> BriefGenerateResponse:
    """Synthesize final brief, timeline phases, and cost projections."""
    return await service.generate(body)
