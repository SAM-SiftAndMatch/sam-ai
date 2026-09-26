#!/usr/bin/env python3
"""Batch generates embeddings for chunks using Ollama (bge-m3) and syncs to MongoDB and JSONL."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402


async def embed_and_sync_chunks(
    file_path: str = "data/kb-chunks.jsonl",
    batch_size: int = 10,
    sync_mongo: bool = True,
) -> dict[str, int]:
    target_path = Path(file_path)
    if not target_path.is_file():
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    print("--- 🚀 Starting Batch Embedding with Ollama ---")
    print(f"Ollama URL:    {settings.OLLAMA_BASE_URL}")
    print(
        f"Model:         {settings.EMBEDDING_MODEL} ({settings.EMBEDDING_DIMENSIONS} dims)"
    )
    print(f"Target File:   {target_path}")

    # Load JSONL records
    records = []
    with target_path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))

    total_chunks = len(records)
    print(f"Total chunks loaded: {total_chunks}")

    embed_service = EmbeddingService(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )

    # Collect texts
    texts = [r["text"] for r in records]

    start_time = time.time()
    print(f"Generating embeddings in batches of {batch_size}...")
    embeddings = await embed_service.get_embeddings_batch(texts, batch_size=batch_size)
    elapsed = time.time() - start_time
    print(
        f"✅ Generated {len(embeddings)} embeddings in {elapsed:.2f}s ({len(embeddings) / elapsed:.1f} chunks/sec)"
    )

    # Attach embeddings to records
    for i, vec in enumerate(embeddings):
        records[i]["embedding"] = vec

    # Write back to JSONL
    print(f"Writing updated chunks with embeddings to {target_path} ...")
    with target_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("✅ JSONL file updated successfully.")

    # Sync to MongoDB
    mongo_updated = 0
    if sync_mongo:
        mongo_uri = settings.get_mongo_uri()
        db_name = settings.MONGO_DB_NAME
        masked_uri = mongo_uri
        if "@" in mongo_uri and "://" in mongo_uri:
            proto, rest = mongo_uri.split("://", 1)
            _, host = rest.split("@", 1)
            masked_uri = f"{proto}://***:***@{host}"

        print(
            f"\nSyncing embeddings to MongoDB Atlas: {masked_uri} (DB: '{db_name}') ..."
        )
        server_api = ServerApi("1")
        client: MongoClient = MongoClient(mongo_uri, server_api=server_api)
        db = client[db_name]
        collection = db["chunks"]

        for r in records:
            res = collection.update_one(
                {"_id": r["id"]},
                {
                    "$set": {
                        "embedding": r["embedding"],
                        "metadata": r["metadata"],
                        "text": r["text"],
                    }
                },
                upsert=True,
            )
            if res.matched_count or res.upserted_id:
                mongo_updated += 1

        client.close()
        print(f"✅ MongoDB sync complete! {mongo_updated} documents updated.")

    return {
        "total": total_chunks,
        "embedded": len(embeddings),
        "mongo_synced": mongo_updated,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for chunks using Ollama"
    )
    parser.add_argument(
        "--file",
        "-f",
        default="data/kb-chunks.jsonl",
        help="Path to JSONL file (default: data/kb-chunks.jsonl)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=10,
        help="Batch size for embedding requests (default: 10)",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip syncing to MongoDB (only update JSONL)",
    )

    args = parser.parse_args()
    asyncio.run(
        embed_and_sync_chunks(
            file_path=args.file,
            batch_size=args.batch_size,
            sync_mongo=not args.no_mongo,
        )
    )


if __name__ == "__main__":
    main()
