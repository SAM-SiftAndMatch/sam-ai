from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.chunk import (
    ChunkContextResponse,
    ChunkListResponse,
    ChunkResponse,
    ChunkSearchItem,
    ChunkSearchRequest,
    ChunkSearchResponse,
    ChunkStatsResponse,
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
    "/context",
    response_model=ChunkContextResponse,
    summary="Get 2-tier context for brief generation",
    description="Retrieve universal chunks alongside category-specific chunks for brief generation wizard.",
)
async def get_brief_context(
    category: str | None = Query(
        default=None,
        description="Target category (e.g. 'website_ban_hang', 'crm', 'app_dat_lich')",
    ),
    service: ChunkService = Depends(get_chunk_service),
) -> ChunkContextResponse:
    universal, cat_specific = await service.get_brief_context(category=category)
    return ChunkContextResponse(
        universal=[
            ChunkResponse(
                id=c.id,
                text=c.text,
                embedding=c.embedding,
                metadata=c.metadata,
            )
            for c in universal
        ],
        category_specific=[
            ChunkResponse(
                id=c.id,
                text=c.text,
                embedding=c.embedding,
                metadata=c.metadata,
            )
            for c in cat_specific
        ],
    )


@router.post(
    "/search",
    response_model=ChunkSearchResponse,
    summary="Semantic vector search",
    description="Search chunks using Ollama bge-m3 dense vector embeddings and MongoDB Atlas Vector Search.",
)
async def semantic_search(
    body: ChunkSearchRequest,
    service: ChunkService = Depends(get_chunk_service),
) -> ChunkSearchResponse:
    universal_items: list[ChunkResponse] = []
    if body.include_universal:
        raw_universal = await service.get_universal_chunks()
        universal_items = [
            ChunkResponse(
                id=c.id,
                text=c.text,
                embedding=c.embedding,
                metadata=c.metadata,
            )
            for c in raw_universal
        ]

    search_results = await service.semantic_search(
        query_text=body.query,
        category=body.category,
        limit=body.limit,
    )
    relevant_items = [
        ChunkSearchItem(
            id=item["id"],
            text=item["text"],
            metadata=item["metadata"],
            score=item.get("score"),
        )
        for item in search_results
    ]

    return ChunkSearchResponse(
        query=body.query,
        universal=universal_items,
        relevant_chunks=relevant_items,
        total_relevant=len(relevant_items),
    )


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
