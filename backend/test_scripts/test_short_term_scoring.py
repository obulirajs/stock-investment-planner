# backend/test_scripts/test_short_term_scoring.py

from pymongo import MongoClient
from backend.analysis.short_term_scoring import compute_short_term_score
from backend.config import MONGO_URL, DB_NAME


def get_latest_two(symbol):
    """Fetch latest two technical indicator records for a symbol"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]

    docs = list(
        db["technical_indicators"]
        .find({"symbol": symbol})
        .sort("date", -1)
        .limit(2)
    )

    if len(docs) < 1:
        return None, None

    latest = docs[0]["indicators"]
    previous = docs[1]["indicators"] if len(docs) > 1 else None

    return latest, previous


def get_action(score):
    """Convert score to action"""
    if score >= 70:
        return "BUY"
    elif score <= 30:
        return "SELL"
    return "HOLD"


def run(symbols):
    """Run short-term scoring for symbols and display results"""
    for sym in symbols:
        latest, previous = get_latest_two(sym)

        if not latest:
            print(f"{sym}: No data")
            continue

        result = compute_short_term_score(latest, previous)

        print("-" * 60)
        print("Symbol:", sym)
        print("Score:", result["score"])
        print("Action:", get_action(result["score"]))
        print("Components:", result["components"])
        print("-" * 60)


if __name__ == "__main__":
    run(["TCS", "INFY", "RELIANCE"])
