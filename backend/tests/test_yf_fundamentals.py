# backend/test_scripts/test_yf_fundamentals.py

import asyncio

import pytest
from backend.etl.yf_fundamentals_etl import symbol_to_yf, extract_financial_metrics
import yfinance as yf

@pytest.mark.asyncio
async def test():
    sym = "TCS"
    yf_sym = symbol_to_yf(sym)
    print("Testing TCS ->", yf_sym)

    ticker = yf.Ticker(yf_sym)
    metrics = extract_financial_metrics(ticker)

    print("\nExtracted fundamentals:")
    for k,v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    asyncio.run(test())
