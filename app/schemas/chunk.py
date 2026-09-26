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


class ChunkSearchItem(BaseModel):
    """Chunk result with similarity score."""

    id: str = Field(..., description="Stable hash ID")
    text: str = Field(..., description="Chunk text")
    metadata: ChunkMetadata
    score: float | None = Field(
        default=None, description="Vector similarity score (0.0 to 1.0)"
    )


class ChunkSearchRequest(BaseModel):
    """Request model for semantic vector search."""

    query: str = Field(..., min_length=2, description="User search query")
    category: str | None = Field(default=None, description="Optional category filter")
    limit: int = Field(
        default=3, ge=1, le=20, description="Max relevant category chunks to return"
    )
    include_universal: bool = Field(
        default=True,
        description="Whether to include universal chunks in response",
    )


class ChunkSearchResponse(BaseModel):
    """Hybrid response: Universal chunks + Relevant category chunks from vector search."""

    query: str = Field(..., description="Original search query")
    universal: list[ChunkResponse] = Field(
        default_factory=list,
        description="Universal chunks to be hard-injected into prompt",
    )
    relevant_chunks: list[ChunkSearchItem] = Field(
        default_factory=list,
        description="Top-K category chunks retrieved via vector similarity search",
    )
    total_relevant: int = Field(..., description="Count of relevant chunks returned")
