# backend/test_scripts/test_short_term_scoring.py
"""
Quick local test:
    python -m backend.test_scripts.test_short_term_scoring
"""

import asyncio
from backend.analysis.short_term_scoring import score_short_term_for_symbol

SAMPLE = ["TCS", "INFY", "RELIANCE"]

async def run():
    budget = 50000  # example user budget; test with different values
    for s in SAMPLE:
        res = await score_short_term_for_symbol(s, user_budget=budget)
        print("-" * 60)
        print("Symbol:", s)
        print("Score:", res["score"], "Action:", res["action"], "Confidence:", res["confidence"])
        print("Price:", res["price"], "Buy range:", res["buy_range"])
        print("Stop:", res["stop_loss"], "Target:", res["target_price"])
        print("Qty:", res["suggested_qty"])
        print("Explanation:", res["explanation"][:400], "...")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(run())
