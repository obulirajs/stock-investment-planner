# backend/api_clients/marketstack_client.py
import aiohttp
import urllib.parse
from typing import Optional, Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt
from backend.config import MARKETSTACK_KEY, MARKETSTACK_BASE

HEADERS = {"Accept": "application/json"}

def _build_url(path: str, params: dict):
    params = params.copy()
    params["access_key"] = MARKETSTACK_KEY
    qs = urllib.parse.urlencode(params)
    base = MARKETSTACK_BASE.rstrip("/")
    return f"{base}/{path.lstrip('/')}?{qs}"

@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
async def fetch_symbols_list(session: aiohttp.ClientSession, exchange: str = "XNSE", limit: int = 100, offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Fetch tickers list from Marketstack v1 tickers endpoint.
    """
    url = _build_url("tickers", {"exchange": exchange, "limit": limit, "offset": offset})
    async with session.get(url, headers=HEADERS, timeout=30) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Marketstack tickers fetch failed: {resp.status} - {text[:300]}")
        return await resp.json()

@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
async def fetch_eod(session: aiohttp.ClientSession, symbol: str, limit: int = 1000, offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Fetch EOD data for a symbol (Marketstack v1 endpoint: eod)
    Example symbol: TCS.XNSE
    """
    url = _build_url("eod", {"symbols": symbol, "limit": limit, "offset": offset})
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Marketstack EOD fetch failed: {resp.status} - {text[:300]}")
        return await resp.json()
