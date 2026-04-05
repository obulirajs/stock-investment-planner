# backend/test_scripts/test_indicators.py
"""
Run simple test:
python -m backend.test_scripts.test_indicators
"""

import asyncio
from backend.etl.indicators_etl import run_indicators_etl

# sample small set for quick test
SAMPLE_SYMBOLS = ["TCS", "INFY", "RELIANCE"]

async def run():
    await run_indicators_etl(symbols=SAMPLE_SYMBOLS)

if __name__ == "__main__":
    asyncio.run(run())
