from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.chunk import (
    ChunkListResponse,
    ChunkResponse,
    ChunkStatsResponse,
    SeedResponse,
)
from app.services.chunk_service import ChunkService

router = APIRouter()


def get_chunk_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ChunkService:
    """Dependency to instantiate ChunkService with active Mongo database."""
    return ChunkService(db)


@router.get(
    "",
    response_model=ChunkListResponse,
    summary="List chunks",
    description="Retrieve paginated chunks with optional category, dimension, and source_file filters.",
)
async def list_chunks(
    category: str | None = Query(default=None, description="Filter by category"),
    dimension: str | None = Query(default=None, description="Filter by dimension"),
    source_file: str | None = Query(default=None, description="Filter by source_file"),
    skip: int = Query(default=0, ge=0, description="Offset items"),
    limit: int = Query(default=50, ge=1, le=100, description="Limit items per page"),
    service: ChunkService = Depends(get_chunk_service),
) -> ChunkListResponse:
    total, items = await service.get_chunks(
        category=category,
        dimension=dimension,
        source_file=source_file,
        skip=skip,
        limit=limit,
    )
    chunk_responses = [
        ChunkResponse(
            id=item.id,
            text=item.text,
            embedding=item.embedding,
            metadata=item.metadata,
        )
        for item in items
    ]
    return ChunkListResponse(total=total, chunks=chunk_responses)


@router.get(
    "/universal",
    response_model=list[ChunkResponse],
    summary="Get universal chunks",
    description="Retrieve all chunks marked with always_include=True to be injected into AI context.",
)
async def get_universal_chunks(
    service: ChunkService = Depends(get_chunk_service),
) -> list[ChunkResponse]:
    items = await service.get_universal_chunks()
    return [
        ChunkResponse(
            id=item.id,
            text=item.text,
            embedding=item.embedding,
            metadata=item.metadata,
        )
        for item in items
    ]


@router.get(
    "/stats",
    response_model=ChunkStatsResponse,
    summary="Get chunk statistics",
    description="Get chunk aggregation metrics grouped by category, dimension, and source_file.",
)
async def get_stats(
    service: ChunkService = Depends(get_chunk_service),
) -> ChunkStatsResponse:
    return await service.get_stats()


@router.get(
    "/{chunk_id}",
    response_model=ChunkResponse,
    summary="Get chunk by ID",
    description="Retrieve a single chunk by its unique stable ID.",
)
async def get_chunk_by_id(
    chunk_id: str,
    service: ChunkService = Depends(get_chunk_service),
) -> ChunkResponse:
    item = await service.get_chunk_by_id(chunk_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk with id '{chunk_id}' not found.",
        )
    return ChunkResponse(
        id=item.id,
        text=item.text,
        embedding=item.embedding,
        metadata=item.metadata,
    )


@router.post(
    "/seed",
    response_model=SeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed chunks from JSONL",
    description="Load and upsert chunk records from a JSONL file into MongoDB.",
)
async def seed_chunks(
    file_path: str = Query(
        default="data/kb-chunks.jsonl",
        description="Path to JSONL file on server",
    ),
    drop_first: bool = Query(
        default=False,
        description="Drop existing collection before seeding",
    ),
    service: ChunkService = Depends(get_chunk_service),
) -> SeedResponse:
    try:
        result = await service.seed_from_jsonl(
            file_path=file_path, drop_first=drop_first
        )
        return SeedResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed chunks: {e}",
        ) from e
