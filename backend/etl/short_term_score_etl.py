# backend/etl/short_term_score_etl.py
"""
ETL to compute short-term score for all symbols and persist into stocks_master.analysis.short_term
Usage:
    python -m backend.etl.short_term_score_etl --budget 50000
"""

import asyncio
import argparse
from backend.db import get_database
from backend.analysis.short_term_scoring import score_short_term_for_symbol

CONCURRENCY = 8

async def run_full_etl(user_budget: float = None):
    db = get_database()
    master = db["stocks_master"]

    symbols = [d["symbol"] async for d in master.find({}, {"symbol": 1})]
    sem = asyncio.Semaphore(CONCURRENCY)

    async def worker(sym):
        async with sem:
            try:
                result = await score_short_term_for_symbol(sym, user_budget)
                result["last_updated"] = result.get("computed_at")  # inject timestamp

                await master.update_one(
                    {"symbol": sym},
                    {"$set": {"analysis.short_term": result}},
                    upsert=False
                )

                print(f"✔ {sym}: score={result['score']}, action={result['action']}")
                return True

            except Exception as e:
                print(f"❌ {sym} error: {e}")
                return False


    tasks = [asyncio.create_task(worker(s)) for s in symbols]
    results = await asyncio.gather(*tasks)
    succeeded = sum(1 for r in results if r)
    failed = len(results) - succeeded
    print(f"\nDone. succeeded={succeeded}, failed={failed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=float, default=None, help="User budget in INR (used to suggest quantity)")
    args = parser.parse_args()
    asyncio.run(run_full_etl(user_budget=args.budget))
