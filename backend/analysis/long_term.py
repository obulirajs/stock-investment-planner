# backend/analysis/long_term.py
import math
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.db import get_database
import statistics

# Weights for final score (tunable)
WEIGHTS = {
    "growth": 0.30,
    "quality": 0.25,
    "balance": 0.15,
    "valuation": 0.15,
    "stability": 0.15
}

# Helpers to map raw values to 0-100 scores.
def _map_cagr_to_score(cagr_percent: Optional[float]) -> int:
    if cagr_percent is None:
        return 40  # neutral-ish
    # piecewise linear mapping
    if cagr_percent >= 30:
        return 100
    if cagr_percent >= 20:
        return int(80 + (cagr_percent - 20) * 2)  # 20->80, 30->100
    if cagr_percent >= 10:
        return int(50 + (cagr_percent - 10) * 3)  # 10->50, 20->80
    if cagr_percent >= 0:
        return int(10 + (cagr_percent - 0) * 4)   # 0->10, 10->50
    # negative growth
    if cagr_percent >= -20:
        return int(max(0, 10 + cagr_percent))    # -20->-10 => clamp
    return 0

def _map_roe_roce_to_score(roe: Optional[float], roce: Optional[float]) -> int:
    # Normalize against reasonable caps (e.g., 0..30% typical)
    def single(x):
        if x is None:
            return 50
        if x >= 30:
            return 100
        if x <= 0:
            return 10
        return int((x / 30.0) * 100)
    roe_s = single(roe)
    roce_s = single(roce)
    # weight ROE more (60%) and ROCE (40%)
    return int(round(0.6 * roe_s + 0.4 * roce_s))

def _map_de_to_score(de_ratio: Optional[float]) -> int:
    if de_ratio is None:
        return 60
    # lower D/E is better
    if de_ratio <= 0:
        return 100
    if de_ratio <= 0.5:
        return int(80 + (0.5 - de_ratio) * 40)  # 0.5->80, 0->100
    if de_ratio <= 1.5:
        return int(max(0, 50 + (1.5 - de_ratio) * 30))  # 1.5->50, 0.5->80
    if de_ratio <= 3:
        return int(max(0, 20 + (3 - de_ratio) * 10))
    return 5

def _map_pe_vs_sector(pe: Optional[float], sector_median_pe: Optional[float]) -> int:
    if pe is None:
        return 50
    if sector_median_pe is None or sector_median_pe <= 0:
        # fallback to absolute PE scale (0..50 -> good, >50 -> poor)
        if pe <= 10:
            return 90
        if pe <= 20:
            return 70
        if pe <= 40:
            return 40
        return 10
    rel = pe / sector_median_pe
    # rel < 0.7 => very attractive, rel > 1.5 => expensive
    if rel <= 0.7:
        return 90
    if rel <= 1.0:
        return int(70 + (1.0 - rel) * 66)  # 0.7->90, 1.0->70
    if rel <= 1.5:
        return int(70 - (rel - 1.0) * 40)  # 1.0->70, 1.5->50
    return int(max(5, 50 - (rel - 1.5) * 60))

def _marketcap_bucket_score(market_cap: Optional[float]) -> int:
    """
    market_cap in absolute rupees. Favor large caps moderately for stability.
    Use approximate buckets:
      Large: > 20,000 Cr (2e11) -> score 90
      Mid  : 5,000 - 20,000 Cr -> score 70
      Small: 500 - 5,000 Cr -> score 60
      Micro: <500 Cr -> score 40 (higher reward for multibagger but less stability)
    """
    if market_cap is None:
        return 60
    # market_cap may be raw rupees (int); if it seems very large (like 1e12), treat accordingly
    mc = float(market_cap)
    # convert if the value looks like it's already in crores (some sources vary) - we assume rupees
    if mc >= 1e12:  # > 10k crore maybe
        return 95
    if mc >= 2e11:  # 20,000 Cr = 2e11
        return 90
    if mc >= 5e10:  # 5,000 Cr
        return 75
    if mc >= 5e9:   # 500 Cr
        return 60
    return 40

async def _compute_sector_median_pe_for_stock(stock_doc: Dict[str, Any]) -> Optional[float]:
    """
    Compute the median PE for the stock's sector from stocks_master.
    If sector missing or insufficient data, return None.
    """
    db = get_database()
    sector = stock_doc.get("sector") or (stock_doc.get("metadata") or {}).get("sector")
    if not sector:
        return None
    coll = db["stocks_master"]
    cursor = coll.find({"sector": sector}, {"metadata.pe": 1})
    pes: List[float] = []
    async for doc in cursor:
        md = doc.get("metadata") or {}
        pe = md.get("pe")
        try:
            if pe is not None:
                pes.append(float(pe))
        except Exception:
            continue
    if not pes:
        return None
    try:
        return float(statistics.median(pes))
    except Exception:
        return None

async def compute_long_term_score(stock_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entrypoint. Accepts a stocks_master document and returns:
    {
      "score": int,
      "components": {growth:.., quality:.., balance:.., valuation:.., stability:..},
      "meta": {...},
      "last_updated": ISO timestamp
    }
    """
    # Extract fields safely
    md = stock_doc.get("metadata", {}) if stock_doc else {}
    # Prefer explicit CAGR fields if stored; else compute using available fields.
    revenue_cagr_5 = md.get("revenue_cagr_5")  # expected as percent (e.g., 15.5)
    pat_cagr_5 = md.get("pat_cagr_5")
    # If not present, try other proxies
    growth_cagr = None
    if revenue_cagr_5 is not None:
        growth_cagr = revenue_cagr_5
    elif pat_cagr_5 is not None:
        growth_cagr = pat_cagr_5
    else:
        # fallback: maybe metadata stores 'eps_cagr_5'
        growth_cagr = md.get("eps_cagr_5") or md.get("eps_cagr_3")

    roe = md.get("roe")
    roce = md.get("roce")
    de = md.get("de_ratio") or md.get("de")
    pe = md.get("pe")
    market_cap = stock_doc.get("market_cap") or md.get("market_cap")

    # compute sector median pe
    sector_median_pe = await _compute_sector_median_pe_for_stock(stock_doc)

    # component scores
    growth_score = _map_cagr_to_score(_safe_to_float(growth_cagr))
    quality_score = _map_roe_roce_to_score(_safe_to_float(roe), _safe_to_float(roce))
    balance_score = _map_de_to_score(_safe_to_float(de))
    valuation_score = _map_pe_vs_sector(_safe_to_float(pe), sector_median_pe)
    stability_score = _marketcap_bucket_score(_safe_to_float(market_cap))

    # weighted final
    final = (
        WEIGHTS["growth"] * growth_score +
        WEIGHTS["quality"] * quality_score +
        WEIGHTS["balance"] * balance_score +
        WEIGHTS["valuation"] * valuation_score +
        WEIGHTS["stability"] * stability_score
    )
    final_int = int(round(final))

    meta = {
        "used_fields": {
            "growth_cagr": growth_cagr,
            "roe": roe,
            "roce": roce,
            "de": de,
            "pe": pe,
            "sector_median_pe": sector_median_pe,
            "market_cap": market_cap
        },
        "component_values": {
            "growth_score": growth_score,
            "quality_score": quality_score,
            "balance_score": balance_score,
            "valuation_score": valuation_score,
            "stability_score": stability_score
        }
    }

    return {
        "score": max(0, min(100, final_int)),
        "components": {
            "growth": growth_score,
            "quality": quality_score,
            "balance_sheet": balance_score,
            "valuation": valuation_score,
            "stability": stability_score
        },
        "meta": meta,
        "last_updated": datetime.utcnow().isoformat()
    }

def _safe_to_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            return float(x.replace(",", "").strip())
        return float(x)
    except Exception:
        return None
