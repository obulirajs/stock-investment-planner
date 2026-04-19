# backend/analysis/medium_term_scoring.py
# Pure scoring logic for medium-term (0-100). No DB access here.
from typing import Optional, Dict, Any
from math import isfinite
from datetime import datetime, timezone

# Weights (simple, explainable)
WEIGHTS = {
    "trend_health": 0.25,    # close vs sma50
    "long_trend": 0.25,      # sma50 vs sma200
    "trend_slope": 0.20,     # delta sma200
    "momentum": 0.20,        # momentum value (roc or momentum_20)
    "week52_strength": 0.10  # close position in 52-week range
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

def score_trend_health(latest: Dict[str, Any]) -> float:
    # close vs sma50: if close is above sma50 by 15% => 1.0, below -15% => 0.0
    close = _safe_get(latest, "close")
    sma50 = _safe_get(latest, "sma50")
    if close is None or sma50 is None or sma50 == 0:
        return 0.5
    diff = (close - sma50) / sma50
    return _norm_clip(diff, -0.15, 0.15)

def score_long_trend(latest: Dict[str, Any]) -> float:
    # sma50 vs sma200: 20% range
    sma50 = _safe_get(latest, "sma50")
    sma200 = _safe_get(latest, "sma200")
    if sma50 is None or sma200 is None or sma200 == 0:
        return 0.5
    diff = (sma50 - sma200) / sma200
    return _norm_clip(diff, -0.20, 0.20)

def score_trend_slope(latest: Dict[str, Any], prev: Optional[Dict[str, Any]]) -> float:
    # slope of sma200: if increasing fast -> 1.0; decreasing fast -> 0.0
    s_today = _safe_get(latest, "sma200")
    s_prev = _safe_get(prev, "sma200")
    if s_today is None or s_prev is None:
        return 0.5
    slope_pct = ((s_today - s_prev) / (s_prev + 1e-9)) * 100  # Convert to % per spec
    # spec range: [-5%, +5%]
    return _norm_clip(slope_pct, -5.0, 5.0)

def score_momentum(latest: Dict[str, Any]) -> float:
    # use roc63 if present, else roc21 else momentum_20 (input already in %)
    roc63 = _safe_get(latest, "roc63")
    roc21 = _safe_get(latest, "roc21")
    mom = _safe_get(latest, "momentum_20") or _safe_get(latest, "momentum100")
    val = roc63 if roc63 is not None else (roc21 if roc21 is not None else mom)
    if val is None:
        return 0.5
    # spec range: [-20%, +20%] (input already in %)
    return _norm_clip(val, -20.0, 20.0)

def score_52week(latest: Dict[str, Any]) -> float:
    # position in 52-week range: 0..1
    high = _safe_get(latest, "52w_high") or _safe_get(latest, "52_week_high") or _safe_get(latest, "52wHigh")
    low = _safe_get(latest, "52w_low") or _safe_get(latest, "52_week_low") or _safe_get(latest, "52wLow")
    close = _safe_get(latest, "close")
    if high is None or low is None or close is None or high == low:
        return 0.5
    pos = (close - low) / (high - low)
    return max(0.0, min(1.0, pos))

def _get_action(score_int: int) -> str:
    """Determine action based on integer score (deterministic thresholds)"""
    if score_int >= 65:
        return "BUY"
    elif score_int >= 45:
        return "WATCH"
    else:
        return "AVOID"

def _generate_explanation(components: Dict[str, float], score: float, action: str) -> str:
    """Generate human-readable explanation based on components"""
    trend_h = components["trend_health"]
    long_t = components["long_trend"]
    slope = components["trend_slope"]
    mom = components["momentum"]
    week52 = components["week52_strength"]
    
    explanation = f"Score: {score:.0f} ({action}). "
    
    # Trend health
    if trend_h >= 80:
        explanation += "Close significantly above SMA50 (strong short-term). "
    elif trend_h >= 60:
        explanation += "Close above SMA50 (uptrend). "
    elif trend_h <= 20:
        explanation += "Close below SMA50 (downtrend). "
    else:
        explanation += "Close near SMA50 (neutral short-term). "
    
    # Long trend
    if long_t >= 80:
        explanation += "SMA50 well above SMA200 (strong intermediate uptrend). "
    elif long_t >= 60:
        explanation += "SMA50 above SMA200 (uptrend). "
    elif long_t <= 20:
        explanation += "SMA50 below SMA200 (downtrend). "
    
    # Momentum
    if mom >= 70:
        explanation += f"Strong positive momentum. "
    elif mom <= 30:
        explanation += f"Weak or negative momentum. "
    
    # 52-week positioning
    if week52 >= 80:
        explanation += "Trading near 52-week highs (bullish)."
    elif week52 <= 20:
        explanation += "Trading near 52-week lows (bearish)."
    
    return explanation

def compute_medium_term_score(latest: Dict[str, Any], previous: Optional[Dict[str, Any]] = None, symbol: str = "") -> Dict[str, Any]:
    """
    Compute medium-term investment score (0-100) with action recommendation.
    
    Args:
        latest: flattened indicators dict (close, sma50, sma200, roc21/63, momentum_20, 52w_high, 52w_low)
        previous: flattened indicators dict (for prev sma200, required for trend_slope)
        symbol: stock symbol (optional, for output)
    
    Returns: {
        score: float (0-100, 2 decimals),
        score_int: int (0-100, for thresholds),
        action: str (BUY, WATCH, AVOID),
        components: dict of component scores [0, 100],
        explanation: str (human-readable),
        computed_at: str (ISO 8601 UTC timestamp),
        symbol: str (if provided)
    }
    """
    # components in 0..1
    c_trend_health = score_trend_health(latest)
    c_long_trend = score_long_trend(latest)
    c_trend_slope = score_trend_slope(latest, previous)
    c_momentum = score_momentum(latest)
    c_week52 = score_52week(latest)

    comp_map = {
        "trend_health": round(c_trend_health * 100, 1),
        "long_trend": round(c_long_trend * 100, 1),
        "trend_slope": round(c_trend_slope * 100, 1),
        "momentum": round(c_momentum * 100, 1),
        "week52_strength": round(c_week52 * 100, 1),
    }

    final = (
        WEIGHTS["trend_health"] * c_trend_health
        + WEIGHTS["long_trend"] * c_long_trend
        + WEIGHTS["trend_slope"] * c_trend_slope
        + WEIGHTS["momentum"] * c_momentum
        + WEIGHTS["week52_strength"] * c_week52
    )

    score_0_100 = round(max(0.0, min(100.0, final * 100)), 2)
    score_int = int(score_0_100)  # Floor for deterministic thresholds
    action = _get_action(score_int)
    explanation = _generate_explanation(comp_map, score_0_100, action)

    result = {
        "score": score_0_100,
        "score_int": score_int,
        "action": action,
        "components": comp_map,
        "explanation": explanation,
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    
    if symbol:
        result["symbol"] = symbol
    
    return result
