# backend/etl/medium_term_score_etl.py
import asyncio
import os
import time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
from typing import List, Dict, Any

from backend.analysis.medium_term_scoring import compute_medium_term_score

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "stock_research_db")  # default to your DB
TECH_COLL = os.getenv("TECH_COLL", "technical_indicators")
MASTER_COLL = os.getenv("MASTER_COLL", "stocks_master")

BULK_CHUNK = int(os.getenv("BULK_CHUNK", "500"))
AGG_BATCH_SIZE = int(os.getenv("AGG_BATCH_SIZE", "1000"))

async def ensure_indexes(db):
    try:
        await db[TECH_COLL].create_index([("symbol", 1), ("date", -1)], background=True)
        await db[MASTER_COLL].create_index([("symbol", 1)], background=True)
    except Exception as e:
        print("Index creation error:", e)

async def fetch_latest_two_per_symbol(db) -> List[Dict[str, Any]]:
    pipeline = [
        {"$sort": {"symbol": 1, "date": -1}},
        {"$group": {"_id": "$symbol", "docs": {"$push": "$$ROOT"}}},
        {"$project": {"symbol": "$_id", "docs": {"$slice": ["$docs", 2]}}},
        {"$sort": {"symbol": 1}},
    ]
    cursor = db[TECH_COLL].aggregate(pipeline, allowDiskUse=True)
    out = []
    cnt = 0
    async for d in cursor:
        out.append(d)
        cnt += 1
        if cnt % AGG_BATCH_SIZE == 0:
            await asyncio.sleep(0)
    return out

def flatten_doc(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not raw:
        return {}
    flat = {}
    # indicators nested object -> top level
    inds = raw.get("indicators") or {}
    if isinstance(inds, dict):
        flat.update(inds)
    # copy some root-level fields too
    if "symbol" in raw:
        flat["symbol"] = raw["symbol"]
    if "date" in raw:
        flat["indicator_date"] = raw["date"]
    return flat

async def compute_and_write(db):
    t0 = time.time()
    print("Ensuring indexes...")
    await ensure_indexes(db)

    print("Aggregating latest two docs per symbol (this is a single pass)...")
    records = await fetch_latest_two_per_symbol(db)
    print(f"Fetched {len(records)} symbols' latest docs in {time.time() - t0:.2f}s")

    writes: List[UpdateOne] = []
    updated = 0
    run_timestamp = datetime.utcnow().isoformat()

    for rec in records:
        symbol = rec.get("symbol")
        docs = rec.get("docs", [])
        raw_latest = docs[0] if len(docs) > 0 else None
        raw_prev = docs[1] if len(docs) > 1 else None

        latest = flatten_doc(raw_latest)
        previous = flatten_doc(raw_prev) if raw_prev else None

        if not latest:
            continue

        score_obj = compute_medium_term_score(latest, previous)

        update = {
            "$set": {
                "analysis.medium_term.score": score_obj["score"],
                "analysis.medium_term.components": score_obj["components"],
                "analysis.medium_term.indicator_date": latest.get("indicator_date"),
                "analysis.medium_term.last_run_at": run_timestamp,
                "analysis.medium_term.meta": {"source": TECH_COLL}
            }
        }

        writes.append(UpdateOne({"symbol": symbol}, update, upsert=True))
        updated += 1

        if len(writes) >= BULK_CHUNK:
            try:
                res = await db[MASTER_COLL].bulk_write(writes, ordered=False)
                print(f"Bulk chunk wrote: matched={res.matched_count}, modified={res.modified_count}, upserted={len(res.upserted_ids)}")
            except Exception as e:
                print("Bulk write error:", e)
            writes = []

    if writes:
        try:
            res = await db[MASTER_COLL].bulk_write(writes, ordered=False)
            print(f"Final bulk write executed: matched={res.matched_count}, modified={res.modified_count}, upserted={len(res.upserted_ids)}")
        except Exception as e:
            print("Final bulk write error:", e)

    print(f"Completed scoring+write for {updated} symbols in {time.time() - t0:.2f}s")

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    await compute_and_write(db)
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
