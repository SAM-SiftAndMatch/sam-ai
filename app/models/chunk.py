from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ChunkMetadata(BaseModel):
    """Metadata attached to each chunk for filtering and context."""

    source_file: str = Field(
        ...,
        description="Original markdown filename (e.g. 'kb-attribute-data-layer.md')",
    )
    category: str | None = Field(
        default=None,
        description="Product category for filtering (e.g. 'website_ban_hang', 'crm')",
    )
    dimension: str | None = Field(
        default=None,
        description="Aspect/dimension within a category (e.g. 'payment_shipping')",
    )
    scope: str = Field(
        default="category_specific",
        description="'universal' (applies to all categories) or 'category_specific'",
    )
    always_include: bool = Field(
        default=False,
        description="If true, this chunk is always injected into AI context regardless of query",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="List of keywords for this chunk",
    )
    title: str = Field(
        ...,
        description="Heading title of this chunk section",
    )
    breadcrumb: str = Field(
        ...,
        description="Full breadcrumb path (e.g. 'E-commerce > B1.2 — Thanh toán')",
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO date string of last update (e.g. '2026-09-25')",
    )

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: str | list[str] | None) -> list[str]:
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        if v is None:
            return []
        return v

    @field_validator("scope", mode="before")
    @classmethod
    def set_default_scope(cls, v: str | None) -> str:
        if not v:
            return "category_specific"
        return v


class ChunkDocument(BaseModel):
    """A single chunk document as stored in MongoDB.

    The `id` field maps to MongoDB's `_id` — a stable hash generated from
    `source_file + '::' + breadcrumb`.
    """

    id: str = Field(..., alias="_id", description="Stable hash ID")
    text: str = Field(
        ...,
        description="Chunk text with [Nguồn: ...] [breadcrumb] prefix for embedding",
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Vector embedding (1024-dim for Ollama bge-m3).",
    )
    metadata: ChunkMetadata

    model_config = {"populate_by_name": True}
