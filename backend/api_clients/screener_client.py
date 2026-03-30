# backend/api_clients/screener_client.py
import requests
from bs4 import BeautifulSoup
import time, random
from typing import Dict, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_screener_profile(symbol: str, mode: str = "fast") -> Optional[Dict]:
    """
    Scrape Screener.in company page for fundamentals.
    Call this on-demand (per-stock) to avoid blocks.
    symbol: e.g., "TCS" (no suffix).
    Returns a dict with keys found (pe, pb, sector, industry, market_cap, summary).
    """
    url = f"https://www.screener.in/company/{symbol}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        out = {}

        # company-profile block
        prof = soup.find("div", {"class": "company-profile"})
        if prof:
            for li in prof.find_all("li"):
                key_tag = li.find("span", {"class": "key"})
                val_tag = li.find("span", {"class": "value"})
                if key_tag and val_tag:
                    k = key_tag.get_text(strip=True).lower()
                    v = val_tag.get_text(strip=True)
                    if "industry" in k:
                        out["industry"] = v
                    if "sector" in k:
                        out["sector"] = v
                    if "market cap" in k:
                        out["market_cap"] = _parse_market_cap(v)

        # snapshot ratios table
        snap = soup.find("table", {"class": "snapshot"})
        if snap:
            for r in snap.find_all("tr"):
                tds = r.find_all("td")
                if len(tds) >= 2:
                    k = tds[0].get_text(strip=True).lower()
                    v = tds[1].get_text(strip=True)
                    if "p/e" in k and not out.get("pe"):
                        out["pe"] = _parse_number(v)
                    if "p/b" in k and not out.get("pb"):
                        out["pb"] = _parse_number(v)

        if mode == "full":
            about = soup.find("div", {"id": "company-profile"})
            if about:
                out["summary"] = about.get_text(" ", strip=True)[:4000]

        # polite delay
        time.sleep(0.6 + random.random() * 0.6)
        return out
    except Exception:
        return None

def _parse_market_cap(text: str):
    if not text:
        return None
    t = text.replace("₹", "").replace(",", "").strip().lower()
    try:
        if "cr" in t:
            num = float("".join(ch for ch in t if (ch.isdigit() or ch == ".")))
            return int(num * 1e7)
        if "bn" in t or "b" in t:
            num = float("".join(ch for ch in t if (ch.isdigit() or ch == ".")))
            return int(num * 1e9)
        return int("".join(ch for ch in t if (ch.isdigit() or ch == ".")))
    except Exception:
        return None

def _parse_number(text: str):
    if not text:
        return None
    try:
        t = text.split()[0].replace(",", "")
        return float(t)
    except Exception:
        return None
