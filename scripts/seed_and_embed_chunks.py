#!/usr/bin/env python3
"""All-in-one CLI pipeline: Generates embeddings with Ollama (bge-m3),
updates JSONL, seeds MongoDB Atlas, and creates all required indexes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import certifi
from pymongo import ASCENDING, MongoClient
from pymongo.server_api import ServerApi

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.models.chunk import ChunkDocument  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402


async def run_seed_and_embed(
    file_path: str = "data/kb-chunks.jsonl",
    batch_size: int = 10,
    drop_first: bool = False,
    force_reembed: bool = False,
    mongo_uri: str | None = None,
    db_name: str | None = None,
) -> dict[str, int]:
    target_path = Path(file_path)
    if not target_path.is_file():
        print(f"❌ Error: File not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    print("==================================================")
    print("🚀 ALL-IN-ONE PIPELINE: SEED CHUNKS + EMBEDDING")
    print("==================================================")
    print(f"Target File:       {target_path}")
    print(f"Ollama Server:     {settings.OLLAMA_BASE_URL}")
    print(
        f"Embedding Model:   {settings.EMBEDDING_MODEL} ({settings.EMBEDDING_DIMENSIONS} dims)"
    )

    # 1. Load JSONL records
    records: list[dict] = []
    with target_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                records.append(record)
            except json.JSONDecodeError as exc:
                print(
                    f"⚠️ Warning: Skipping malformed JSON at line {line_num}: {exc}",
                    file=sys.stderr,
                )

    total_chunks = len(records)
    print(f"Total Chunks:      {total_chunks}")
    print("--------------------------------------------------")

    # 2. Check and generate embeddings
    indices_to_embed: list[int] = []
    for idx, r in enumerate(records):
        emb = r.get("embedding")
        if force_reembed or not emb or len(emb) != settings.EMBEDDING_DIMENSIONS:
            indices_to_embed.append(idx)

    new_embedded_count = 0
    if indices_to_embed:
        print(
            f"🔄 Generating embeddings for {len(indices_to_embed)} chunks in batches of {batch_size}..."
        )
        embed_service = EmbeddingService(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

        texts_to_embed = [records[i]["text"] for i in indices_to_embed]
        start_time = time.time()
        generated_vectors = await embed_service.get_embeddings_batch(
            texts_to_embed, batch_size=batch_size
        )
        elapsed = time.time() - start_time

        for idx, vec in zip(indices_to_embed, generated_vectors, strict=True):
            records[idx]["embedding"] = vec

        new_embedded_count = len(generated_vectors)
        rate = new_embedded_count / elapsed if elapsed > 0 else 0
        print(
            f"✅ Generated {new_embedded_count} vector embeddings in {elapsed:.2f}s ({rate:.1f} chunks/sec)."
        )

        # Update JSONL file on disk with embeddings
        print(f"💾 Saving updated records with embeddings to {target_path} ...")
        with target_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("✅ JSONL file synchronized successfully.")
    else:
        print(
            "⚡ All chunks already contain valid embeddings. Skipping embedding generation."
        )

    print("--------------------------------------------------")

    # 3. Seed into MongoDB Atlas
    uri = mongo_uri or settings.get_mongo_uri()
    database_name = db_name or settings.MONGO_DB_NAME

    masked_uri = uri
    if "@" in uri and "://" in uri:
        proto, rest = uri.split("://", 1)
        _, host = rest.split("@", 1)
        masked_uri = f"{proto}://***:***@{host}"

    print(
        f"📦 Connecting to MongoDB at: {masked_uri} (Database: '{database_name}') ..."
    )

    server_api = ServerApi("1")
    client: MongoClient = MongoClient(uri, server_api=server_api, tlsCAFile=certifi.where())
    db = client[database_name]
    collection = db["chunks"]

    if drop_first:
        print("⚠️ Flag --drop-first detected. Dropping existing 'chunks' collection...")
        collection.drop()

    inserted = 0
    updated = 0

    print("Seeding documents into collection 'chunks'...")
    for r in records:
        try:
            chunk = ChunkDocument.model_validate(r)
            doc = chunk.model_dump(by_alias=True)

            res = collection.update_one(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True,
            )
            if res.upserted_id is not None:
                inserted += 1
            else:
                updated += 1
        except Exception as exc:
            print(
                f"⚠️ Warning: Failed to upsert chunk ID {r.get('id')}: {exc}",
                file=sys.stderr,
            )

    # 4. Create indexes
    print("Creating MongoDB indexes on 'chunks' collection...")
    collection.create_index([("metadata.always_include", ASCENDING)])
    collection.create_index([("metadata.category", ASCENDING)])
    collection.create_index([("metadata.dimension", ASCENDING)])
    collection.create_index([("metadata.source_file", ASCENDING)])

    client.close()

    print("==================================================")
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print("==================================================")
    print(f"Total Chunks Processed:  {total_chunks}")
    print(f"New Embeddings Created:  {new_embedded_count}")
    print(f"MongoDB Inserted:        {inserted}")
    print(f"MongoDB Updated:         {updated}")
    print(
        "Indexes Created:         metadata.always_include, metadata.category, metadata.dimension, metadata.source_file"
    )
    print(
        f"Atlas Vector Search:     Ensure index '{settings.VECTOR_INDEX_NAME}' is active on MongoDB Atlas."
    )
    print("==================================================")

    return {
        "total": total_chunks,
        "new_embedded": new_embedded_count,
        "inserted": inserted,
        "updated": updated,
    }


def main():
    parser = argparse.ArgumentParser(
        description="All-in-one CLI: Generate embeddings + seed chunks into MongoDB Atlas"
    )
    parser.add_argument(
        "--file",
        "-f",
        default="data/kb-chunks.jsonl",
        help="Path to JSONL chunks file (default: data/kb-chunks.jsonl)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=10,
        help="Batch size for Ollama embeddings (default: 10)",
    )
    parser.add_argument(
        "--drop-first",
        action="store_true",
        help="Drop 'chunks' collection in MongoDB before seeding",
    )
    parser.add_argument(
        "--force-reembed",
        action="store_true",
        help="Regenerate embeddings for all chunks even if they already exist",
    )
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="MongoDB connection URI (defaults to .env settings)",
    )
    parser.add_argument(
        "--db-name",
        default=None,
        help="Target database name (defaults to .env settings)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_seed_and_embed(
            file_path=args.file,
            batch_size=args.batch_size,
            drop_first=args.drop_first,
            force_reembed=args.force_reembed,
            mongo_uri=args.mongo_uri,
            db_name=args.db_name,
        )
    )


if __name__ == "__main__":
    main()
