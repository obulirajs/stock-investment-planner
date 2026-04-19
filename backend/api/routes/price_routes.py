from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from backend.api.routes.common import parse_date, success_response, validate_symbol
from backend.services.stock_service import get_price_history

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{symbol}")
async def price_history(
    symbol: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    symbol = validate_symbol(symbol)
    start = parse_date(start_date, "start_date")
    end = parse_date(end_date, "end_date")

    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    result = await run_in_threadpool(get_price_history, symbol, start, end)
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return success_response(result)
