from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.chunk import ChunkDocument
from app.schemas.chunk import ChunkStatsResponse

logger = logging.getLogger("sam_ai.chunks")


class ChunkService:
    """Service handling CRUD, filtering, aggregation, and seeding for chunks."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["chunks"]

    async def get_universal_chunks(self) -> list[ChunkDocument]:
        """Retrieve all universal chunks (metadata.always_include=True)."""
        cursor = self.collection.find({"metadata.always_include": True})
        return [ChunkDocument.model_validate(doc) async for doc in cursor]

    async def get_category_chunks(self, category: str) -> list[ChunkDocument]:
        """Retrieve all category-specific chunks for a particular domain."""
        query = {
            "metadata.scope": "category_specific",
            "metadata.category": category,
        }
        cursor = self.collection.find(query)
        return [ChunkDocument.model_validate(doc) async for doc in cursor]

    async def get_brief_context(
        self, category: str | None = None
    ) -> tuple[list[ChunkDocument], list[ChunkDocument]]:
        """Retrieve 2-tier context for brief generation: Universal + Category."""
        universal_chunks = await self.get_universal_chunks()
        category_chunks: list[ChunkDocument] = []
        if category:
            category_chunks = await self.get_category_chunks(category)
        return universal_chunks, category_chunks

    async def semantic_search(
        self,
        query_text: str,
        category: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Perform semantic vector search using MongoDB Atlas $vectorSearch,

        with automatic in-memory cosine similarity fallback.
        """
        from app.core.config import settings
        from app.services.embedding_service import embedding_service

        query_vector = await embedding_service.get_embedding(query_text)

        # 1. Try native Atlas $vectorSearch
        vector_search_stage: dict[str, Any] = {
            "index": settings.VECTOR_INDEX_NAME,
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": max(limit * 10, 50),
            "limit": limit,
        }
        if category:
            vector_search_stage["filter"] = {"metadata.category": category}

        pipeline = [
            {"$vectorSearch": vector_search_stage},
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            cursor = self.collection.aggregate(pipeline)
            results = []
            async for doc in cursor:
                results.append(
                    {
                        "id": str(doc["_id"]),
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "score": round(float(doc.get("score", 0.0)), 4),
                    }
                )
            if results:
                return results
        except Exception as exc:
            # Fallback to in-memory cosine similarity if Atlas Index is not configured yet
            logger.warning(
                "Atlas vector search unavailable or unindexed, falling back to in-memory cosine similarity: %s",
                exc,
            )

        # 2. In-memory Cosine Similarity fallback
        import math

        def _cosine(v1: list[float], v2: list[float]) -> float:
            dot = sum(a * b for a, b in zip(v1, v2, strict=True))
            norm_a = math.sqrt(sum(a * a for a in v1))
            norm_b = math.sqrt(sum(b * b for b in v2))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

        query: dict[str, Any] = {"embedding": {"$ne": None}}
        if category:
            query["metadata.category"] = category

        candidates = []
        async for doc in self.collection.find(query):
            doc_emb = doc.get("embedding")
            if doc_emb and len(doc_emb) == len(query_vector):
                score = _cosine(query_vector, doc_emb)
                candidates.append((score, doc))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:limit]

        return [
            {
                "id": str(doc["_id"]),
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": round(score, 4),
            }
            for score, doc in top_candidates
        ]

    async def get_chunks(
        self,
        category: str | None = None,
        dimension: str | None = None,
        source_file: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[ChunkDocument]]:
        """Retrieve paginated chunks matching query filters."""
        query: dict[str, Any] = {}
        if category is not None:
            query["metadata.category"] = category
        if dimension is not None:
            query["metadata.dimension"] = dimension
        if source_file is not None:
            query["metadata.source_file"] = source_file

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).skip(skip).limit(limit)
        items = [ChunkDocument.model_validate(doc) async for doc in cursor]
        return total, items

    async def get_chunk_by_id(self, chunk_id: str) -> ChunkDocument | None:
        """Retrieve a single chunk by its unique stable ID."""
        doc = await self.collection.find_one({"_id": chunk_id})
        if not doc:
            return None
        return ChunkDocument.model_validate(doc)

    async def get_stats(self) -> ChunkStatsResponse:
        """Aggregate chunks statistics by category, dimension, and source_file."""
        total_chunks = await self.collection.count_documents({})
        universal_count = await self.collection.count_documents(
            {"metadata.always_include": True}
        )

        async def _aggregate_field(field_path: str) -> dict[str, int]:
            pipeline = [
                {"$group": {"_id": f"${field_path}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            result: dict[str, int] = {}
            async for doc in self.collection.aggregate(pipeline):
                key = str(doc["_id"]) if doc["_id"] is not None else "null"
                result[key] = doc["count"]
            return result

        by_category = await _aggregate_field("metadata.category")
        by_dimension = await _aggregate_field("metadata.dimension")
        by_source_file = await _aggregate_field("metadata.source_file")

        return ChunkStatsResponse(
            total_chunks=total_chunks,
            universal_count=universal_count,
            by_category=by_category,
            by_dimension=by_dimension,
            by_source_file=by_source_file,
        )

    async def seed_from_jsonl(
        self,
        file_path: str = "data/kb-chunks.jsonl",
        drop_first: bool = False,
    ) -> dict[str, Any]:
        """Read JSONL file and upsert chunk records into MongoDB with indexes."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"JSONL file not found at: {file_path}")

        if drop_first:
            await self.collection.delete_many({})

        inserted = 0
        updated = 0
        total = 0

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                raw_data = json.loads(line_str)
                # Map 'id' to '_id' for ChunkDocument validation
                chunk = ChunkDocument.model_validate(raw_data)
                doc = chunk.model_dump(by_alias=True)

                res = await self.collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": doc},
                    upsert=True,
                )
                if res.upserted_id is not None:
                    inserted += 1
                else:
                    updated += 1
                total += 1

        # Create indexes
        await self.collection.create_index("metadata.always_include")
        await self.collection.create_index("metadata.category")
        await self.collection.create_index("metadata.dimension")
        await self.collection.create_index("metadata.source_file")

        return {
            "inserted": inserted,
            "updated": updated,
            "total": total,
            "message": f"Successfully processed {total} chunks ({inserted} inserted, {updated} updated).",
        }
