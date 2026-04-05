# backend/etl/price_etl.py
import asyncio
import aiohttp
from backend.api_clients.marketstack_client import fetch_eod
from pymongo import MongoClient, UpdateOne
from backend.config import MONGO_URL, DB_NAME

CONCURRENCY = 4

def get_database_sync():
    """Get synchronous MongoDB connection"""
    client = MongoClient(MONGO_URL, connect=False)
    return client[DB_NAME]

async def fetch_and_save_eod_for_symbol(session, symbol):
    """Fetch data and return it (write will be done separately)"""
    try:
        resp = await fetch_eod(session, symbol + ".XNSE", limit=1000, offset=0)
        if not resp or "data" not in resp:
            return False, symbol, None

        # Prepare bulk operations
        operations = []
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

            operations.append(
                UpdateOne(
                    {"symbol": doc["symbol"], "date": doc["date"]},
                    {"$set": doc},
                    upsert=True
                )
            )

        return True, symbol, operations

    except Exception as e:
        return False, f"{symbol}:{type(e).__name__}:{str(e)[:50]}", None

def write_to_database(db, symbol, operations):
    """Write operations to database synchronously"""
    try:
        if operations:
            coll = db["daily_price_data"]
            result = coll.bulk_write(operations, ordered=False)
            return True, f"{symbol}:{result.upserted_ids.__len__() + result.modified_count}"
        return True, f"{symbol}:no_ops"
    except Exception as e:
        return False, f"{symbol}:{str(e)[:100]}"
    
async def run_price_etl(symbols: list):
    db = get_database_sync()
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        sem = asyncio.Semaphore(CONCURRENCY)
        
        async def worker(smb):
            async with sem:
                return await fetch_and_save_eod_for_symbol(session, smb)
        
        tasks = [worker(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Now write all data to database synchronously
        success = 0
        failed = []
        
        print(f"Fetched {len(results)} symbols, writing to database...")
        
        for idx, result in enumerate(results):
            if isinstance(result, tuple) and len(result) == 3:
                success_fetch, symbol, operations = result
                if success_fetch and operations:
                    write_ok, write_msg = write_to_database(db, symbol, operations)
                    if write_ok:
                        success += 1
                        print(f"✓ {symbol}")
                    else:
                        failed.append(write_msg)
                        print(f"✗ {symbol}: {write_msg}")
                elif not success_fetch:
                    failed.append(symbol)
                    print(f"✗ {symbol}: fetch failed")
            else:
                failed.append(str(result))
                print(f"✗ Error: {result}")
        
        print(f"\nPrices ETL done. success={success} failed={len(failed)}")
        if failed:
            print("Failed items:")
            for f in failed:
                print(f"  - {f}")
        return results

if __name__ == "__main__":
    import sys
    syms = sys.argv[1:] if len(sys.argv) > 1 else ["TCS", "INFY", "RELIANCE"]
    asyncio.run(run_price_etl(syms))
