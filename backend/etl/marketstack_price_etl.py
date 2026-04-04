# backend/etl/marketstack_price_etl.py

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_fixed

from backend.db import get_database
from backend.config import MARKETSTACK_KEY


# MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")
MARKETSTACK_API_KEY = MARKETSTACK_KEY
BASE_URL = "http://api.marketstack.com/v1/eod"

CONCURRENCY = 10   # download 10 symbols in parallel


def to_ms_symbol(symbol: str) -> str:
    return f"{symbol}.XNSE"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def fetch_eod(session, ms_symbol, date_from, date_to):
    params = {
        "access_key": MARKETSTACK_API_KEY,
        "symbols": ms_symbol,
        "date_from": date_from,
        "date_to": date_to,
        "limit": 5000,
    }

    async with session.get(BASE_URL, params=params, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        data = await resp.json()
        return data.get("data", [])


async def store_price_rows(symbol, rows, coll):
    for r in rows:
        date_str = r.get("date")
        if not date_str:
            continue

        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            continue

        doc = {
            "symbol": symbol,
            "date": dt,
            "open": r.get("open"),
            "high": r.get("high"),
            "low": r.get("low"),
            "close": r.get("close"),
            "volume": r.get("volume"),
        }

        await coll.update_one(
            {"symbol": symbol, "date": dt},
            {"$set": doc},
            upsert=True
        )


async def process_symbol(session, sym, price_coll, master_coll, date_from_str, date_to_str, idx, total):
    # Skip if already updated
    doc = await master_coll.find_one({"symbol": sym}, {"last_price_update": 1})

    if doc and doc.get("last_price_update"):
        print(f"[{idx}/{total}] ⏭ Skipping {sym} (already updated)")
        return

    ms_symbol = to_ms_symbol(sym)
    print(f"[{idx}/{total}] ⬇ Fetching {sym} ({ms_symbol}) ...")

    try:
        rows = await fetch_eod(session, ms_symbol, date_from_str, date_to_str)

        if not rows:
            print(f"⚠ No data for {sym}")
            return

        await store_price_rows(sym, rows, price_coll)

        # Mark symbol as updated
        await master_coll.update_one(
            {"symbol": sym},
            {"$set": {"last_price_update": datetime.utcnow()}}
        )

        print(f"✔ Finished {sym} ({len(rows)} rows)")

    except Exception as e:
        print(f"❌ Failed for {sym}: {e}")


async def run_marketstack_price_etl():
    if not MARKETSTACK_API_KEY:
        print("❌ MARKETSTACK_API_KEY not set.")
        return

    db = get_database()
    price_coll = db["daily_price_data"]
    master_coll = db["stocks_master"]

    symbols = [doc["symbol"] async for doc in master_coll.find({}, {"symbol": 1})]
    total = len(symbols)

    date_to = datetime.utcnow()
    date_from = date_to - timedelta(days=5 * 365)

    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")

    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, sym in enumerate(symbols, start=1):

            task = asyncio.create_task(
                worker(sem, session, sym, price_coll, master_coll,
                       date_from_str, date_to_str, idx, total)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

    print("\n🎉 FAST Marketstack ETL completed successfully!")


async def worker(sem, session, sym, price_coll, master_coll,
                 date_from_str, date_to_str, idx, total):
    async with sem:
        await process_symbol(session, sym, price_coll, master_coll,
                             date_from_str, date_to_str, idx, total)



if __name__ == "__main__":
    asyncio.run(run_marketstack_price_etl())
