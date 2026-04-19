from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend.api.routes.common import success_response, validate_symbol
from backend.services.stock_service import get_latest_indicator

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/{symbol}")
async def latest_indicators(symbol: str):
    symbol = validate_symbol(symbol)
    result = await run_in_threadpool(get_latest_indicator, symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return success_response(result)
