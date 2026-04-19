# backend/analysis/short_term_scoring.py
# Pure scoring logic for short-term (0-100). No DB access here.
from typing import Optional, Dict, Any
from math import isfinite

# Weights (simple, explainable)
WEIGHTS = {
    "rsi": 0.30,
    "macd": 0.25,
    "momentum": 0.25,
    "price_vs_sma20": 0.20,
}

def _safe_get(d: Optional[Dict[str, Any]], key: str, default=None):
    if not d:
        return default
    v = d.get(key, default)
    try:
        return float(v) if v is not None else default
    except:
        return default

def _norm_clip(x, lo, hi):
    if x is None or not isfinite(x):
        return 0.5
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (x - lo) / (hi - lo)

def score_rsi(latest: Dict[str, Any]) -> float:
    # rsi14: <= 30 is bullish (1.0), >= 70 is bearish (0.0)
    rsi = _safe_get(latest, "rsi14")
    if rsi is None:
        return 0.5
    return 1.0 - _norm_clip(rsi, 30.0, 70.0)

def score_macd(latest: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> float:
    # combine histogram direction and slope; neutral on missing previous
    current = _safe_get(latest, "macd_hist")
    prev = _safe_get(previous, "macd_hist")
    if current is None:
        return 0.5

    # direction_score = _norm_clip(current, -1.0, 1.0)
    # slope_score = 0.5 if prev is None else _norm_clip(current - prev, -0.5, 0.5)
    # direction_score = _norm_clip(current, -3.0, 3.0)
    direction_score = _norm_clip(current, -5.0, 5.0)
    slope_score = 0.5 if prev is None else _norm_clip(current - prev, -1.0, 1.0)

    return max(0.0, min(1.0, (direction_score * 0.6) + (slope_score * 0.4)))

def score_momentum(latest: Dict[str, Any]) -> float:
    # momentum20 in %: -10% => 0.0, +10% => 1.0
    momentum = _safe_get(latest, "momentum20")
    if momentum is None:
        return 0.5 
    return _norm_clip(momentum, -8.0, 8.0)

def score_price_vs_sma20(latest: Dict[str, Any]) -> float:
    # close vs sma20: -5% => 0.0, +5% => 1.0
    close = _safe_get(latest, "close")
    sma20 = _safe_get(latest, "sma20")
    if close is None or sma20 is None or sma20 == 0:
        return 0.5
    diff = (close - sma20) / sma20
    return _norm_clip(diff, -0.04, 0.04)

def compute_short_term_score(latest: Dict[str, Any], previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Compute short-term timing score (0-100).

    Args:
        latest: flattened indicators dict (rsi14, macd_hist, momentum20, sma20, close)
        previous: flattened indicators dict (previous macd_hist, optional)

    Returns: {
        score: float (0-100, 2 decimals),
        components: dict of component scores [0, 1]
    }
    """
    c_rsi = score_rsi(latest)
    c_macd = score_macd(latest, previous)
    c_momentum = score_momentum(latest)
    c_price_vs_sma20 = score_price_vs_sma20(latest)

    final = (
        WEIGHTS["rsi"] * c_rsi
        + WEIGHTS["macd"] * c_macd
        + WEIGHTS["momentum"] * c_momentum
        + WEIGHTS["price_vs_sma20"] * c_price_vs_sma20
    )

    return {
        "score": round(max(0.0, min(100.0, final * 100)), 2),
        "components": {
            "rsi": round(c_rsi * 100, 2),
            "macd": round(c_macd * 100, 2),
            "momentum": round(c_momentum * 100, 2),
            "price_vs_sma20": round(c_price_vs_sma20 * 100, 2),
            # # "rsi": round(c_rsi, 4),
            # "rsi": round(c_rsi * 100, 2),
            # "macd": round(c_macd, 4),
            # "momentum": round(c_momentum, 4),
            # "price_vs_sma20": round(c_price_vs_sma20, 4),
        }
    }
