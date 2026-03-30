# backend/etl/stock_master_etl.py
import asyncio
import aiohttp
from math import ceil
from backend.api_clients.marketstack_client import fetch_symbols_list
from backend.api_clients.screener_client import fetch_screener_profile
from backend.merger import merge_marketstack_screener
from backend.db import get_database

CONCURRENCY = 4

async def run_stock_master_etl(batch_size: int = 200, batch_index: int = 0, fundamentals_mode: str = "on_demand"):
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # fetch all tickers via pagination
        tickers = []
        offset = 0
        page_limit = 100
        while True:
            resp = await fetch_symbols_list(session, exchange="XNSE", limit=page_limit, offset=offset)
            if not resp or "data" not in resp:
                break
            data = resp["data"]
            if not data:
                break
            tickers.extend(data)
            if len(data) < page_limit:
                break
            offset += page_limit

        # get unique base symbols (no .XNSE)
        symbols = []
        for t in tickers:
            sym = t.get("symbol") or t.get("ticker")
            if sym:
                base = sym.split(".")[0] if "." in sym else sym
                if base not in symbols:
                    symbols.append(base)

        total = len(symbols)
        num_batches = ceil(total / batch_size)
        if batch_index >= num_batches:
            print("batch index out of range")
            return

        start = batch_index * batch_size
        end = min(start + batch_size, total)
        batch_syms = symbols[start:end]
        print(f"Processing batch {batch_index+1}/{num_batches} symbols {start}..{end-1}")

        db = get_database()
        sem = asyncio.Semaphore(CONCURRENCY)

        async def process_symbol(sym):
            async with sem:
                try:
                    # find ms_item for the symbol (if present)
                    ms_item = next((x for x in tickers if (x.get("symbol","").split(".")[0] == sym)), {"symbol": f"{sym}.XNSE", "name": sym})
                    screener_data = {}
                    if fundamentals_mode in ("on_demand", "full"):
                        # fetch screener (sync call) - it's okay because it's intended to be light on demand
                        screener_data = fetch_screener_profile(sym, mode="fast") or {}
                    doc = merge_marketstack_screener(ms_item or {}, screener_data)
                    coll = db["stocks_master"]
                    await coll.update_one({"symbol": doc["symbol"]}, {"$set": doc}, upsert=True)
                    return (sym, True, None)
                except Exception as e:
                    return (sym, False, str(e))

        tasks = [process_symbol(s) for s in batch_syms]
        results = await asyncio.gather(*tasks)
        succeeded = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]
        print(f"Done. success={len(succeeded)} failed={len(failed)}")
        if failed:
            print("Failed sample:", failed[:10])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--batch-index", type=int, default=0)
    parser.add_argument("--fundamentals-mode", choices=["none","on_demand","full"], default="on_demand")
    args = parser.parse_args()
    asyncio.run(run_stock_master_etl(batch_size=args.batch_size, batch_index=args.batch_index, fundamentals_mode=args.fundamentals_mode))
