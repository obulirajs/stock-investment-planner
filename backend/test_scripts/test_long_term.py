# backend/test_scripts/test_long_term.py
"""
Run from project root:
python -m backend.test_scripts.test_long_term

This script fetches a small sample from stocks_master and computes long-term scores.
"""

import asyncio
from backend.db import get_database
from backend.analysis.long_term import compute_long_term_score

SAMPLE_IMAGE = "/mnt/data/14ceada0-edc7-4f5a-af94-d30752de440b.png"  # optional, ignore if irrelevant

async def _run_test(limit=10):
    db = get_database()
    coll = db["stocks_master"]
    # fetch a sample of documents that have some metadata
    cursor = coll.find({}, limit=limit)
    docs = []
    async for d in cursor:
        docs.append(d)
    if not docs:
        print("No documents found in stocks_master. Please run stock_master_etl first.")
        return
    for d in docs:
        sym = d.get("symbol")
        print("="*60)
        print("Symbol:", sym, "| Name:", d.get("name"))
        result = await compute_long_term_score(d)
        print("Long-term score:", result["score"])
        print("Components:", result["components"])
        print("Meta used fields:", result["meta"]["used_fields"])
        print("Last updated:", result["last_updated"])
    print("\nSample image path (for UI/test):", SAMPLE_IMAGE)

if __name__ == "__main__":
    asyncio.run(_run_test(limit=10))
