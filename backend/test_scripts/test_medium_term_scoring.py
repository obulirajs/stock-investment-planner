import asyncio
from backend.analysis.medium_term_scoring import compute_medium_term_score
from pymongo import MongoClient
from backend.config import MONGO_URL, DB_NAME


def get_latest_two(symbol):
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
    if score >= 70:
        return "BUY"
    elif score <= 30:
        return "SELL"
    return "HOLD"


def run(symbols):
    for sym in symbols:
        latest, previous = get_latest_two(sym)

        if not latest:
            print(f"{sym}: No data")
            continue

        result = compute_medium_term_score(latest, previous)

        print("-" * 60)
        print("Symbol:", sym)
        print("Score:", result["score"])
        print("Action:", get_action(result["score"]))
        print("Components:", result["components"])
        print("-" * 60)


if __name__ == "__main__":
    run(["TCS", "INFY", "RELIANCE"])