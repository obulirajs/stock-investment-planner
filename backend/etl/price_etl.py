# backend/etl/price_etl.py
import asyncio
import aiohttp
from backend.api_clients.marketstack_client import fetch_eod
from backend.db import get_database

CONCURRENCY = 4

async def fetch_and_save_eod_for_symbol(session, symbol, db):
    try:
        resp = await fetch_eod(session, symbol + ".XNSE", limit=1000, offset=0)
        if not resp or "data" not in resp:
            return False, symbol
        docs = []
        for r in resp["data"]:
            doc = {
                "symbol": symbol,
                "date": r.get("date"),
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "close": r.get("close"),
                "volume": r.get("volume"),
                "adj_close": r.get("adj_close") if "adj_close" in r else r.get("adjusted_close")
            }
            docs.append(doc)
        if docs:
            coll = db["daily_price_data"]
            for doc in docs:
                await coll.update_one({"symbol": doc["symbol"], "date": doc["date"]}, {"$set": doc}, upsert=True)
        return True, symbol
    except Exception as e:
        return False, f"{symbol}:{e}"

async def run_price_etl(symbols: list):
    db = get_database()
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        sem = asyncio.Semaphore(CONCURRENCY)
        async def worker(smb):
            async with sem:
                return await fetch_and_save_eod_for_symbol(session, smb, db)
        tasks = [worker(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        success = [r for r in results if r[0]]
        failed = [r for r in results if not r[0]]
        print(f"Prices ETL done. success={len(success)} failed={len(failed)}")
        return results

if __name__ == "__main__":
    import sys
    syms = sys.argv[1:] if len(sys.argv) > 1 else ["TCS", "INFY", "RELIANCE"]
    asyncio.run(run_price_etl(syms))
