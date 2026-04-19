# backend/etl/price_etl.py
import asyncio
import concurrent.futures
import time

import aiohttp
from pymongo import MongoClient, UpdateOne

from backend.api_clients.marketstack_client import fetch_eod
from backend.config import MONGO_URL, DB_NAME
from backend.etl.adapters.marketstack_adapter import MarketStackAdapter

CONCURRENCY = 4
DEFAULT_PROVIDER = "marketstack"
BATCH_SIZE = 500
FETCH_LIMIT = 300


def get_database_sync():
    """Get synchronous MongoDB connection"""
    client = MongoClient(MONGO_URL, connect=False)
    return client[DB_NAME]


def get_price_adapter(provider: str = DEFAULT_PROVIDER):
    if provider == "marketstack":
        return MarketStackAdapter()
    raise ValueError("Unsupported provider")


def is_valid(doc):
    return (
        doc.get("symbol") is not None and
        doc.get("date") is not None and
        doc.get("close") is not None
    )


async def fetch_and_save_eod_for_symbol(session, symbol):
    """Fetch data and return it (write will be done separately)"""
    try:
        adapter = get_price_adapter()
        print(f"[INFO] Fetching {symbol} with limit={FETCH_LIMIT}")
        resp = await fetch_eod(session, symbol + ".XNSE", limit=FETCH_LIMIT, offset=0)
        if not resp or "data" not in resp:
            return False, symbol, None

        operations = []
        for r in resp["data"]:
            doc = adapter.transform(r, symbol)
            if not is_valid(doc):
                continue

            operations.append(
                UpdateOne(
                    {"symbol": doc["symbol"], "date": doc["date"]},
                    {"$set": doc},
                    upsert=True,
                )
            )

        return True, symbol, operations

    except Exception as e:
        return False, f"{symbol}:{type(e).__name__}:{str(e)[:50]}", None


async def fetch_with_retry(session, symbol, retries=2):
    for attempt in range(retries):
        result = await fetch_and_save_eod_for_symbol(session, symbol)
        success = isinstance(result, tuple) and result[0]
        if success:
            return result
    return False, f"{symbol}:retry_failed", None


def write_to_database(db, symbol, operations):
    """Write operations to database synchronously"""
    if not operations:
        return True, f"{symbol}:no_ops"

    coll = db["daily_price_data"]
    start = time.time()
    num_records_written = 0

    print(f"[INFO] Writing {symbol}: total {len(operations)} records")

    for i in range(0, len(operations), BATCH_SIZE):
        batch = operations[i:i+BATCH_SIZE]
        print(f"[INFO] Writing {symbol}: batch {i//BATCH_SIZE + 1} ({len(batch)} records)")
        try:
            coll.bulk_write(batch, ordered=False)
            num_records_written += len(batch)
        except Exception as e:
            return False, f"{symbol}:db_error:{str(e)[:50]}"

    if time.time() - start > 10:
        print(f"[WARN] Slow DB write for {symbol}")

    return True, f"{symbol}:{num_records_written}"


async def run_price_etl(symbols: list):
    start = time.time()
    db = get_database_sync()
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        sem = asyncio.Semaphore(CONCURRENCY)

        async def worker(smb):
            async with sem:
                return await fetch_with_retry(session, smb)

        tasks = [worker(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        success = 0
        failed = []

        print(f"[INFO] Fetched {len(results)} symbols, writing to database...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            write_inputs = []
            for result in results:
                if not (isinstance(result, tuple) and len(result) == 3):
                    failed.append(str(result))
                    print(f"[ERROR] Error: {result}")
                    continue

                success_fetch, symbol, operations = result
                if success_fetch and operations:
                    print(f"[INFO] Submitting DB write for {symbol}")
                    write_inputs.append((success_fetch, symbol, operations))
                elif success_fetch:
                    print(f"[SKIPPED] {symbol}: no valid operations")
                else:
                    failed.append(symbol)
                    print(f"[ERROR] {symbol}: fetch failed")

            futures = [
                executor.submit(write_to_database, db, symbol, operations)
                for (success_fetch, symbol, operations) in write_inputs
                if success_fetch and operations
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    write_ok, write_msg = future.result(timeout=30)
                except Exception as e:
                    write_ok = False
                    write_msg = f"DB write thread failed: {e}"
                    print(f"[ERROR] {write_msg}")

                print("[INFO] DB write completed")

                if write_ok:
                    success += 1
                    print(f"[INFO] {write_msg}")
                else:
                    failed.append(write_msg)
                    print(f"[ERROR] {write_msg}")

        print("[INFO] All DB write threads completed")

        print(f"\n[INFO] Prices ETL done. success={success} failed={len(failed)}")
        if failed:
            print("[ERROR] Failed items:")
            for f in failed:
                print(f"  - {f}")
        print(f"\n[INFO] Time taken: {round(time.time() - start, 2)} sec")
        return results


if __name__ == "__main__":
    import sys

    syms = sys.argv[1:] if len(sys.argv) > 1 else ["TCS", "INFY", "RELIANCE"]
    asyncio.run(run_price_etl(syms))
