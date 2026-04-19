from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from backend.api.routes.common import success_response, validate_symbol
from backend.services.stock_service import get_medium_score, get_medium_scores, get_short_score

router = APIRouter(prefix="/score", tags=["scores"])


@router.get("/medium/{symbol}")
async def medium_score(symbol: str):
    symbol = validate_symbol(symbol)
    result = await run_in_threadpool(get_medium_score, symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return success_response(result)


@router.get("/short/{symbol}")
async def short_score(symbol: str):
    symbol = validate_symbol(symbol)
    result = await run_in_threadpool(get_short_score, symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return success_response(result)


@router.get("/medium")
async def batch_medium_score(symbols: str = Query(..., description="Comma-separated symbols, e.g. TCS,INFY")):
    parsed_symbols = [validate_symbol(symbol) for symbol in symbols.split(",") if symbol.strip()]
    if not parsed_symbols:
        raise HTTPException(status_code=400, detail="symbols query param must be comma-separated")

    result = await run_in_threadpool(get_medium_scores, parsed_symbols)
    return success_response(result)
