#!/usr/bin/env python3
"""Standardizes and partitions chunks in data/kb-chunks.jsonl into the 2 exact JSON formats:

1. Universal Chunks (scope='universal', always_include=True, category=None)
2. Category-Specific Chunks (scope='category_specific', always_include=False, category='<category_name>')
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def classify_and_format_chunk(record: dict) -> dict:
    meta = record.get("metadata", {})
    bc = meta.get("breadcrumb", "")
    dimension = meta.get("dimension")

    # Detection of Universal Chunks
    is_universal = (
        "UNIVERSAL" in bc
        or "PHẦN A" in bc
        or "PHẦN 0" in bc
        or "PHẦN 5" in bc
        or "PHẦN 6" in bc
        or dimension == "routing_table"
        or meta.get("scope") == "universal"
    )

    if is_universal:
        scope = "universal"
        always_include = True
        category = None
    else:
        scope = "category_specific"
        always_include = False

        # Match category from breadcrumb / PRD prefixes
        if "Website bán hàng" in bc or "E-commerce" in bc or "PRD-EC" in bc:
            category = "website_ban_hang"
        elif "App đặt lịch" in bc or "Booking" in bc or "PRD-BOOK" in bc:
            category = "app_dat_lich"
        elif "CRM" in bc or "PRD-CRM" in bc:
            category = "crm"
        elif (
            "App đặt hàng" in bc or "Food" in bc or "Delivery" in bc or "PRD-MOB" in bc
        ):
            category = "app_giao_hang"
        elif "PRD-ERP" in bc:
            category = "erp_noi_bo"
        elif "PRD-HR" in bc:
            category = "hr_nhan_su"
        elif "PRD-INV" in bc:
            category = "quan_ly_kho"
        elif "PRD-EDU" in bc:
            category = "app_giao_duc"
        elif "PRD-MKT" in bc:
            category = "marketing_tool"
        elif "PRD-FIN" in bc:
            category = "app_tai_chinh"
        elif "PRD-AI" in bc:
            category = "ai_assistant"
        elif "PRD-DASH" in bc:
            category = "bi_dashboard"
        elif "PRD-WF" in bc:
            category = "workflow_automation"
        elif "PRD-EV" in bc:
            category = "event_booking"
        else:
            category = meta.get("category") or "other"

    # Normalize keywords to list[str]
    raw_kw = meta.get("keywords")
    if isinstance(raw_kw, str):
        keywords = [k.strip() for k in raw_kw.split(",") if k.strip()]
    elif isinstance(raw_kw, list):
        keywords = [str(k).strip() for k in raw_kw if str(k).strip()]
    else:
        keywords = []

    return {
        "id": record["id"],
        "text": record["text"],
        "embedding": record.get("embedding"),
        "metadata": {
            "source_file": meta.get("source_file", ""),
            "category": category,
            "dimension": dimension,
            "scope": scope,
            "always_include": always_include,
            "keywords": keywords,
            "title": meta.get("title", ""),
            "breadcrumb": bc,
            "updated_at": meta.get("updated_at", "2026-09-25"),
        },
    }


def reformat_file(file_path: str = "data/kb-chunks.jsonl"):
    path = Path(file_path)
    if not path.is_file():
        print(f"Error: File not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Reading and reformatting '{path}' ...")
    formatted_records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            raw_record = json.loads(line_str)
            formatted = classify_and_format_chunk(raw_record)
            formatted_records.append(formatted)

    # Save formatted records back
    with path.open("w", encoding="utf-8") as f:
        for item in formatted_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    universal_count = sum(
        1 for r in formatted_records if r["metadata"]["scope"] == "universal"
    )
    category_count = sum(
        1 for r in formatted_records if r["metadata"]["scope"] == "category_specific"
    )
    categories = sorted(
        {
            r["metadata"]["category"]
            for r in formatted_records
            if r["metadata"]["category"]
        }
    )

    print(f"✅ Successfully formatted {len(formatted_records)} chunks in '{path}':")
    print(
        f"   - Universal chunks:         {universal_count} (always_include=True, category=null)"
    )
    print(f"   - Category-specific chunks: {category_count} (always_include=False)")
    print(f"   - Categories ({len(categories)}): {', '.join(categories)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reformat JSONL chunks into 2 standardized formats"
    )
    parser.add_argument(
        "--file", "-f", default="data/kb-chunks.jsonl", help="Target JSONL file"
    )
    args = parser.parse_args()
    reformat_file(args.file)
