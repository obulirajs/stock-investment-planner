# backend/analysis/short_term_scoring.py
"""
Balanced short-term scoring & human-friendly recommendation generator.

Usage:
    from backend.analysis.short_term_scoring import score_short_term_for_symbol
    result = await score_short_term_for_symbol("TCS", user_budget=50000)

Result schema (dict):
{
  "symbol": "TCS",
  "score": 78,                     # 0-100
  "action": "BUY"|"WATCH"|"AVOID",
  "confidence": 0.78,              # 0-1
  "price": 1520.0,                 # last close used as reference
  "buy_range": [low, high],        # recommended buy price window
  "target_price": 1580.0,
  "stop_loss": 1495.0,
  "suggested_qty": 15,             # based on user_budget
  "hold_period_days": 7,           # rough guidance
  "components": {...},             # numeric sub-scores
  "explanation": "human friendly text..."
}
"""
from datetime import datetime, timedelta
import math
from typing import Optional, Dict, Any

from backend.db import get_database
import asyncio

# Tunable thresholds and weights (balanced strategy)
WEIGHTS = {
    "rsi": 0.20,
    "momentum": 0.25,
    "trend": 0.20,
    "macd": 0.20,
    "volatility": 0.15  # negative contribution (higher atr -> penalty)
}

# Action thresholds (score)
ACTION_THRESHOLDS = {
    "BUY": 65,
    "WATCH": 45,
    "AVOID": 0
}

# Defaults
DEFAULT_HOLD_DAYS = 10
MIN_QTY = 1

# Helper: read latest indicator snapshot for a symbol
async def _get_latest_indicators(symbol: str) -> Optional[Dict[str, Any]]:
    db = get_database()
    coll = db["technical_indicators"]
    # fetch most recent indicators doc
    doc = await coll.find_one({"symbol": symbol}, sort=[("date", -1)])
    if not doc:
        return None
    return doc.get("indicators", {}), doc.get("date")

# small safe conversions
def _safe_float(x, default=None):
    try:
        return float(x) if x is not None else default
    except Exception:
        return default

def _score_rsi(rsi: Optional[float]) -> float:
    # Balanced: ideal range ~40-60. Score drops if extreme.
    if rsi is None:
        return 0.5
    if 40 <= rsi <= 60:
        return 1.0
    # 60-80 -> moderate positive but risk rising
    if rsi < 40:
        # lower than 30 can be oversold -> small boost
        return max(0.2, (40 + rsi) / 80)  # maps -ve -> 0.25..1
    if rsi > 60:
        # reduce as it approaches overbought
        return max(0.0, 1.0 - (rsi - 60) / 40.0)
    return 0.5

def _score_momentum(mom: Optional[float]) -> float:
    # momentum_20 is percent change over 20d: positive is good
    if mom is None:
        return 0.5
    # scale: -20%..+20% => 0..1
    val = max(-20, min(20, mom))
    return (val + 20) / 40.0

def _score_trend(close: float, sma20: Optional[float]) -> float:
    if sma20 is None:
        return 0.5
    # price above sma20 -> positive
    diff = (close - sma20) / sma20
    # map -10%..+10% to 0..1
    val = max(-0.10, min(0.10, diff))
    return (val + 0.10) / 0.20

def _score_macd(macd_hist: Optional[float]) -> float:
    if macd_hist is None:
        return 0.5
    # positive hist (increasing momentum) -> higher score
    # scale by typical values; clamp to -3..+3
    val = max(-3.0, min(3.0, macd_hist))
    return (val + 3.0) / 6.0

def _volatility_penalty(atr: Optional[float], close: Optional[float]) -> float:
    if atr is None or close is None or close == 0:
        return 1.0
    ratio = atr / close
    # high ratio -> lower factor. Typical ratio 0.01-0.05
    # map ratio 0..0.1 -> 1..0.3
    val = max(0.0, min(0.1, ratio))
    score = 1.0 - (val / 0.1) * 0.7  # 0 ->1.0 ; 0.1 -> 0.3
    return score

def _interpret_action(score: float) -> str:
    if score >= ACTION_THRESHOLDS["BUY"]:
        return "BUY"
    if score >= ACTION_THRESHOLDS["WATCH"]:
        return "WATCH"
    return "AVOID"

def _compute_stop_target(close: float, atr: Optional[float]) -> (float, float):
    # Suggest stop = close - k * ATR ; target = close + m * ATR
    # Balanced: stop = 1.6 * ATR ; target = 3.0 * ATR
    if atr is None or atr == 0:
        # fallback: use percent
        stop = close * 0.97  # 3% stop
        target = close * 1.03
        return round(stop, 2), round(target, 2)
    stop = close - 1.6 * atr
    target = close + 3.0 * atr
    return round(max(0.01, stop), 2), round(target, 2)

def _suggest_quantity(budget: float, price: float) -> int:
    if not budget or budget <= 0 or not price or price <= 0:
        return MIN_QTY
    qty = int(budget // price)
    return max(MIN_QTY, qty)

def _build_explanation(symbol: str, action: str, score: float, components: dict,
                       buy_range: tuple, stop: float, target: float, qty: int, hold_days: int) -> str:
    # Create a simple, friendly narrative for end users.
    score_pct = int(round(score))
    explanation = []
    explanation.append(f"Recommendation for {symbol}: {action} (score: {score_pct}/100).")
    explanation.append(f"Why: Short-term momentum is {'positive' if components['momentum']>=0.6 else 'weak or neutral'}, "
                       f"the price is {'above' if components['trend']>=0.55 else 'around or below'} the 20-day trend, "
                       f"and MACD confirms the current direction." )
    explanation.append(f"Suggested buy range: ₹{buy_range[0]:.2f} — ₹{buy_range[1]:.2f}.")
    explanation.append(f"Stop-loss: ₹{stop:.2f}. Target: ₹{target:.2f}.")
    explanation.append(f"Suggested quantity (based on your budget): {qty} shares.")
    explanation.append(f"Hold: approx {hold_days} days (typical short-term window).")
    explanation.append("Simple guidance: buy in the suggested range, place the stop-loss, and exit at or near the target. "
                       "If price falls below the stop-loss, exit to limit downside.")
    return " ".join(explanation)

async def score_short_term_for_symbol(symbol: str, user_budget: Optional[float] = None) -> Dict[str, Any]:
    """
    Compute a balanced short-term score + recommendation for `symbol`.
    user_budget: amount in INR to compute suggested quantity (if None, suggested_qty uses MIN_QTY).
    """
    indicators_and_date = await _get_latest_indicators(symbol)
    if not indicators_and_date:
        # lack of indicators -> return neutral response
        return {
            "symbol": symbol,
            "score": 50,
            "action": "WATCH",
            "confidence": 0.4,
            "price": None,
            "buy_range": [None, None],
            "target_price": None,
            "stop_loss": None,
            "suggested_qty": MIN_QTY,
            "hold_period_days": DEFAULT_HOLD_DAYS,
            "components": {},
            "explanation": f"No recent price/indicator data available for {symbol}."
        }

    indicators, ts = indicators_and_date
    # extract fields carefully
    close = _safe_float(indicators.get("close"))
    rsi = _safe_float(indicators.get("rsi14"))
    mom = _safe_float(indicators.get("momentum_20"))
    sma20 = _safe_float(indicators.get("sma20"))
    macd_hist = _safe_float(indicators.get("macd_hist"))
    atr = _safe_float(indicators.get("atr14"))
    bb_upper = _safe_float(indicators.get("bb_upper"))
    bb_lower = _safe_float(indicators.get("bb_lower"))

    # component scores (0..1)
    rsi_s = _score_rsi(rsi)
    mom_s = _score_momentum(mom)
    trend_s = _score_trend(close, sma20)
    macd_s = _score_macd(macd_hist)
    vol_factor = _volatility_penalty(atr, close)

    # combine weighted (note volatility is multiplicative)
    weighted = (
        WEIGHTS["rsi"] * rsi_s +
        WEIGHTS["momentum"] * mom_s +
        WEIGHTS["trend"] * trend_s +
        WEIGHTS["macd"] * macd_s
    )
    raw_score = weighted * vol_factor
    score_100 = int(round(max(0, min(100, raw_score * 100))))

    # Decide action
    action = _interpret_action(score_100)
    confidence = max(0.05, min(1.0, raw_score))  # 0..1

    # Price planning
    # Buy range: (close - 0.5*ATR) .. (close + 0.5*ATR) to allow buying on small dips or slight rallies
    if atr and close:
        buy_low = max(0.01, close - 0.5 * atr)
        buy_high = close + 0.5 * atr
    else:
        buy_low = close * 0.995 if close else None
        buy_high = close * 1.005 if close else None

    stop_loss, target = _compute_stop_target(close if close else 0.0, atr)

    # Suggest quantity based on budget
    suggested_qty = _suggest_quantity(user_budget, close) if user_budget and close else MIN_QTY

    components = {
        "rsi": round(rsi_s * 100, 1) if rsi_s is not None else None,
        "momentum": round(mom_s * 100, 1) if mom_s is not None else None,
        "trend": round(trend_s * 100, 1),
        "macd": round(macd_s * 100, 1),
        "volatility_factor": round(vol_factor * 100, 1)
    }

    explanation = _build_explanation(symbol, action, score_100, components, (buy_low, buy_high), stop_loss, target, suggested_qty, DEFAULT_HOLD_DAYS)

    return {
        "symbol": symbol,
        "score": score_100,
        "action": action,
        "confidence": round(confidence, 2),
        "price": round(close, 2) if close else None,
        "buy_range": (round(buy_low, 2) if buy_low else None, round(buy_high, 2) if buy_high else None),
        "target_price": target,
        "stop_loss": stop_loss,
        "suggested_qty": suggested_qty,
        "hold_period_days": DEFAULT_HOLD_DAYS,
        "components": components,
        "explanation": explanation,
        "computed_at": datetime.utcnow().isoformat()
    }
