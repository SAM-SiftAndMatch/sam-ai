from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.chunk import ChunkMetadata


class ChunkResponse(BaseModel):
    """API response model for a single chunk."""

    id: str = Field(..., description="Stable hash ID")
    text: str = Field(..., description="Chunk text")
    embedding: list[float] | None = Field(
        default=None,
        description="Vector embedding (optional for phase 1)",
    )
    metadata: ChunkMetadata

    model_config = {"populate_by_name": True}


class ChunkListResponse(BaseModel):
    """API response model for paginated list of chunks."""

    total: int = Field(..., description="Total matching chunks count")
    chunks: list[ChunkResponse] = Field(..., description="List of chunk items")


class ChunkStatsResponse(BaseModel):
    """API response model for chunk statistics."""

    total_chunks: int = Field(..., description="Total number of chunks in the database")
    universal_count: int = Field(
        ...,
        description="Number of chunks with always_include=True",
    )
    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Count of chunks grouped by category",
    )
    by_dimension: dict[str, int] = Field(
        default_factory=dict,
        description="Count of chunks grouped by dimension",
    )
    by_source_file: dict[str, int] = Field(
        default_factory=dict,
        description="Count of chunks grouped by source_file",
    )


class SeedResponse(BaseModel):
    """API response model for seed operation."""

    inserted: int = Field(..., description="Number of newly inserted documents")
    updated: int = Field(..., description="Number of updated documents")
    total: int = Field(..., description="Total documents processed from JSONL")
    message: str = Field(..., description="Status summary message")


class ChunkContextResponse(BaseModel):
    """2-tier context response separating universal and category-specific chunks."""

    universal: list[ChunkResponse] = Field(
        ...,
        description="Universal chunks to be hard-injected into AI context",
    )
    category_specific: list[ChunkResponse] = Field(
        ...,
        description="Category-specific chunks dynamically fetched based on client industry",
    )
