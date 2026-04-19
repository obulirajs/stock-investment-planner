from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from pymongo import MongoClient

from backend.analysis.medium_term_scoring import compute_medium_term_score
from backend.analysis.short_term_scoring import compute_short_term_score
from backend.config import DB_NAME, MONGO_URL
from backend.db import get_database


def _get_sync_database():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def derive_action(score: float) -> str:
    if score >= 70:
        return "BUY"
    if score >= 40:
        return "HOLD"
    return "AVOID"


def generate_short_term_explanation(components: dict) -> str:
    explanation = []

    if components.get("rsi", 0) > 70:
        explanation.append("RSI indicates overbought conditions.")
    elif components.get("rsi", 0) < 30:
        explanation.append("RSI indicates oversold conditions.")

    if components.get("macd", 0) > 50:
        explanation.append("MACD shows bullish momentum.")

    if components.get("momentum", 0) > 0:
        explanation.append("Positive short-term momentum.")

    if not explanation:
        explanation.append("Neutral short-term signals.")

    return " ".join(explanation)


def _standard_score_response(
    symbol: str,
    score_type: str,
    score: float,
    components: Dict[str, Any],
    action: str,
    explanation: str,
    computed_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "type": score_type,
        "score": score,
        "score_int": int(round(score)),
        "action": action,
        "components": components,
        "explanation": explanation,
        "computed_at": computed_at or datetime.utcnow().isoformat(),
    }


def get_latest_indicator(symbol: str) -> Optional[Dict[str, Any]]:
    db = _get_sync_database()
    doc = db["technical_indicators"].find_one(
        {"symbol": symbol},
        sort=[("date", -1)],
    )
    return _serialize(doc) if doc else None


def get_latest_two_indicators(symbol: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    db = _get_sync_database()
    docs = list(
        db["technical_indicators"]
        .find({"symbol": symbol})
        .sort("date", -1)
        .limit(2)
    )

    if not docs:
        return None, None

    latest = docs[0].get("indicators")
    previous = docs[1].get("indicators") if len(docs) > 1 else None
    return latest, previous


def get_medium_score(symbol: str) -> Optional[Dict[str, Any]]:
    latest, previous = get_latest_two_indicators(symbol)
    if not latest:
        return None

    result = compute_medium_term_score(latest, previous, symbol=symbol)
    score = result["score"]
    return _serialize(
        _standard_score_response(
            symbol=symbol,
            score_type="medium_term",
            score=score,
            components=result.get("components", {}),
            action=result.get("action") or derive_action(score),
            explanation=result.get("explanation", ""),
            computed_at=result.get("computed_at"),
        )
    )


def get_short_score(symbol: str) -> Optional[Dict[str, Any]]:
    latest, previous = get_latest_two_indicators(symbol)
    if not latest:
        return None

    result = compute_short_term_score(latest, previous)
    score = result["score"]
    components = result.get("components", {})
    return _serialize(
        _standard_score_response(
            symbol=symbol,
            score_type="short_term",
            score=score,
            components=components,
            action=derive_action(score),
            explanation=generate_short_term_explanation(components),
        )
    )


def get_medium_scores(symbols: List[str]) -> List[Dict[str, Any]]:
    results = []
    for symbol in symbols:
        score = get_medium_score(symbol)
        if score:
            results.append(score)
    return results


def get_price_history(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    db = _get_sync_database()
    query: Dict[str, Any] = {"symbol": symbol}
    date_filter: Dict[str, Any] = {}

    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["date"] = date_filter

    docs = list(
        db["daily_price_data"]
        .find(query)
        .sort("date", 1)
    )
    return _serialize(docs)


class StockService:

    @staticmethod
    def get_collection():
        db = get_database()
        return db["stocks_master"]  # Collection stays the same

    @staticmethod
    async def upsert_stock(stock_data: dict):
        collection = StockService.get_collection()

        stock_data["updated_at"] = datetime.utcnow()

        result = await collection.update_one(
            {"symbol": stock_data["symbol"]},
            {"$set": stock_data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_stocks(limit: int = 200):
        collection = StockService.get_collection()
        cursor = collection.find().limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def get_stock_by_symbol(symbol: str):
        collection = StockService.get_collection()
        return await collection.find_one({"symbol": symbol})
