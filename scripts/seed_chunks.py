#!/usr/bin/env python3
"""CLI script to seed chunks from a JSONL file into MongoDB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pymongo import ASCENDING, MongoClient
from pymongo.server_api import ServerApi

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.models.chunk import ChunkDocument  # noqa: E402


def seed_chunks(
    file_path: str,
    mongo_uri: str | None = None,
    db_name: str | None = None,
    drop_first: bool = False,
) -> dict[str, int]:
    target_path = Path(file_path)
    if not target_path.is_file():
        print(f"Error: File not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    uri = mongo_uri or settings.get_mongo_uri()
    database_name = db_name or settings.MONGO_DB_NAME

    # Mask password for display
    masked_uri = uri
    if "@" in uri and "://" in uri:
        proto, rest = uri.split("://", 1)
        _, host = rest.split("@", 1)
        masked_uri = f"{proto}://***:***@{host}"

    print(f"Connecting to MongoDB at: {masked_uri} (Database: '{database_name}')")

    server_api = ServerApi("1")
    client: MongoClient = MongoClient(uri, server_api=server_api)
    db = client[database_name]
    collection = db["chunks"]

    if drop_first:
        print("Flag --drop-first detected. Dropping collection 'chunks'...")
        collection.drop()

    inserted = 0
    updated = 0
    total = 0

    print(f"Processing JSONL file: {target_path} ...")
    with target_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            try:
                raw_data = json.loads(line_str)
                chunk = ChunkDocument.model_validate(raw_data)
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
                total += 1
            except Exception as e:
                print(
                    f"Warning: Failed to process line {line_num}: {e}", file=sys.stderr
                )

    print("Creating indexes on collection 'chunks'...")
    collection.create_index([("metadata.always_include", ASCENDING)])
    collection.create_index([("metadata.category", ASCENDING)])
    collection.create_index([("metadata.dimension", ASCENDING)])
    collection.create_index([("metadata.source_file", ASCENDING)])

    print("\n--- Seeding Complete ---")
    print(f"Total processed: {total}")
    print(f"Inserted:        {inserted}")
    print(f"Updated:         {updated}")
    print(
        "Indexes created: metadata.always_include, metadata.category, metadata.dimension, metadata.source_file"
    )

    client.close()
    return {"total": total, "inserted": inserted, "updated": updated}


def main():
    parser = argparse.ArgumentParser(description="Seed chunks into MongoDB from JSONL")
    parser.add_argument(
        "--file",
        "-f",
        default="data/kb-chunks.jsonl",
        help="Path to JSONL chunks file (default: data/kb-chunks.jsonl)",
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
    parser.add_argument(
        "--drop-first",
        action="store_true",
        help="Drop 'chunks' collection before seeding",
    )

    args = parser.parse_args()
    seed_chunks(
        file_path=args.file,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        drop_first=args.drop_first,
    )


if __name__ == "__main__":
    main()
