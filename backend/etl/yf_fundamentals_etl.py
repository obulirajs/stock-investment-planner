# backend/etl/yf_fundamentals_etl.py

import yfinance as yf
from backend.db import get_database
from datetime import datetime
import asyncio

BATCH_SIZE = 50   # avoids rate-limit
SLEEP_TIME = 1.0  # 1 second per batch


def symbol_to_yf(symbol: str) -> str:
    """
    Convert NSE symbol to yfinance format.
    Example: TCS -> TCS.NS
    """
    return f"{symbol}.NS"


def extract_financial_metrics(yf_ticker) -> dict:
    """
    Extracts core financial metrics needed for our analysis.
    Returns a dictionary, even if some fields are missing.
    """

    info = yf_ticker.info or {}

    # Some fields may not exist; default to None
    return {
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE") or info.get("forwardPE"),
        "pb": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "eps": info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),

        # Growth proxies
        "revenue_cagr_5": info.get("revenueGrowth"),  # some stocks provide this
        "pat_cagr_5": info.get("earningsGrowth"),

        # Extra metrics (optional)
        "beta": info.get("beta"),
        "currency": info.get("currency")
    }


async def run_yf_fundamentals_etl(batch_size: int = BATCH_SIZE):
    """
    Fetches and updates key fundamentals for all stocks in stocks_master.
    Uses batching to avoid rate limits.
    """

    db = get_database()
    coll = db["stocks_master"]

    # Fetch all symbols
    cursor = coll.find({}, {"symbol": 1})
    symbols = [doc["symbol"] for doc in await cursor.to_list(length=5000)]

    print(f"Total symbols: {len(symbols)}")
    batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

    for idx, batch in enumerate(batches):
        print(f"\nProcessing batch {idx+1}/{len(batches)}")

        for sym in batch:
            yf_sym = symbol_to_yf(sym)

            try:
                ticker = yf.Ticker(yf_sym)
                metrics = extract_financial_metrics(ticker)

                # Store inside metadata.*
                await coll.update_one(
                    {"symbol": sym},
                    {"$set": {f"metadata.{k}": v for k, v in metrics.items()}},
                    upsert=False
                )

                print(f"Updated fundamentals for {sym} ({yf_sym})")

            except Exception as e:
                print(f"Failed for {sym}: {e}")

        # Sleep between batches
        await asyncio.sleep(SLEEP_TIME)

    print("\n🎉 yfinance fundamentals ETL completed!")


if __name__ == "__main__":
    asyncio.run(run_yf_fundamentals_etl())
