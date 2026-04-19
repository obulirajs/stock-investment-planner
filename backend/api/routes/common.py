from datetime import datetime
from typing import Optional

from fastapi import HTTPException


def success_response(data):
    return {"status": "success", "data": data, "error": None}


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip()
    if not symbol or symbol != symbol.upper() or not symbol.isalnum():
        raise HTTPException(status_code=400, detail="Symbol must be an uppercase alphanumeric string")
    return symbol


def parse_date(value: Optional[str], field_name: str) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must use YYYY-MM-DD format") from exc
