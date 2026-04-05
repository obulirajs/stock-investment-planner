# backend/test_scripts/test_marketstack.py
import asyncio
from backend.api_clients.marketstack_client import fetch_symbols_list
import aiohttp
import pytest

@pytest.mark.asyncio
async def test():
    async with aiohttp.ClientSession() as s:
        try:
            resp = await fetch_symbols_list(s, exchange="XNSE", limit=5, offset=0)
            print("Marketstack tickers fetch OK. Keys:", list(resp.keys()) if resp else None)
            print("Sample data:", resp.get("data", [])[:5] if resp else None)
        except Exception as e:
            print("marketstack test failed:", e)

if __name__ == "__main__":
    asyncio.run(test())
