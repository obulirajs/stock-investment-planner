# backend/etl/stock_master/fetch_symbols.py
import os
import sys
import argparse
import asyncio
import aiohttp
from datetime import datetime
from math import ceil

# ensure backend package importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from backend.services.stock_service import StockService
from backend.etl.stock_master.nse_fetcher import fetch_nifty500
from backend.etl.stock_master.fmp_fetcher import fetch_fmp_profile
from backend.etl.stock_master.merger import merge

# Tunables
CONCURRENCY = 8           # parallel FMP requests (safe)
DELAY_PER_REQ = 0.2       # polite delay between task completions
TIMEOUT_SECONDS = 60      # per request timeout

async def process_symbol(semaphore, session, item):
    async with semaphore:
        symbol = item.get("symbol")
        try:
            fmp_profile = await fetch_fmp_profile(session, symbol)
            merged = merge(item, fmp_profile or {})
            await StockService.upsert_stock(merged)
            return (symbol, True, None)
        except Exception as e:
            return (symbol, False, str(e))

async def run(batch_size: int = 250, batch_index: int = 0):
    print(f"\nStarting FMP-backed stock master ETL — {datetime.utcnow().isoformat()}")
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        # 1. fetch NSE list
        nse_list = await fetch_nifty500(session)
        if not nse_list:
            print("No NSE data returned; aborting")
            return

        # filter valid
        valid = [x for x in nse_list if x.get("symbol") and "NIFTY" not in x.get("symbol")]
        total = len(valid)
        print(f"NSE returned {len(nse_list)} entries, valid stocks: {total}")

        # compute batches
        num_batches = ceil(total / batch_size)
        if batch_index >= num_batches:
            print(f"batch_index {batch_index} out of range (num_batches={num_batches}); abort.")
            return

        start = batch_index * batch_size
        end = min(start + batch_size, total)
        batch = valid[start:end]
        print(f"Running batch {batch_index+1}/{num_batches}: symbols {start}..{end-1} (count {len(batch)})")

        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [process_symbol(semaphore, session, item) for item in batch]

        results = []
        for coro in asyncio.as_completed(tasks):
            res = await coro
            results.append(res)
            # polite delay
            await asyncio.sleep(DELAY_PER_REQ)

        succeeded = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]
        print(f"\nBatch completed. Success: {len(succeeded)}; Failed: {len(failed)}")
        if failed:
            print("Failed sample:", failed[:10])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=250, help="How many symbols to fetch per run")
    parser.add_argument("--batch-index", type=int, default=0, help="Which batch index to run (0-based)")
    args = parser.parse_args()

    asyncio.run(run(batch_size=args.batch_size, batch_index=args.batch_index))
