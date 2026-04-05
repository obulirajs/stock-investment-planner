# backend/etl/price_etl_sync.py - Synchronous version for testing
import requests
from pymongo import MongoClient, UpdateOne
from backend.config import MARKETSTACK_KEY, MARKETSTACK_BASE, MONGO_URL, DB_NAME

def get_db():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return client[DB_NAME]

def fetch_eod_sync(symbol):
    """Fetch EOD data synchronously from Marketstack API"""
    url = f"{MARKETSTACK_BASE}/eod"
    params = {
        "access_key": MARKETSTACK_KEY,
        "symbols": symbol + ".XNSE",
        "limit": 1000
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"API Error for {symbol}: {resp.status_code} - {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"Fetch error for {symbol}: {e}")
        return None

def save_price_data(symbol):
    """Fetch and save price data for a single symbol"""
    try:
        data = fetch_eod_sync(symbol)
        if not data or "data" not in data:
            print(f"✗ {symbol}: No data received")
            return False
        
        operations = []
        for row in data["data"]:
            doc = {
                "symbol": symbol,
                "date": row.get("date"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
                "adj_close": row.get("adj_close") or row.get("adjusted_close")
            }
            operations.append(
                UpdateOne(
                    {"symbol": symbol, "date": row.get("date")},
                    {"$set": doc},
                    upsert=True
                )
            )
        
        if operations:
            db = get_db()
            result = db["daily_price_data"].bulk_write(operations, ordered=False)
            count = len(result.upserted_ids) + result.modified_count
            print(f"✓ {symbol}: {count} records updated")
            return True
        else:
            print(f"✗ {symbol}: No operations to write")
            return False
            
    except Exception as e:
        print(f"✗ {symbol}: {type(e).__name__}: {str(e)[:100]}")
        return False

if __name__ == "__main__":
    import sys
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["TCS", "INFY", "RELIANCE"]
    
    print(f"Fetching price data for {len(symbols)} symbols...\n")
    success = sum(1 for s in symbols if save_price_data(s))
    print(f"\nCompleted: {success}/{len(symbols)} successful")
