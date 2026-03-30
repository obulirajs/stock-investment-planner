# backend/test_scripts/test_medium_term_scoring.py
from backend.analysis.medium_term_scoring import compute_medium_term_score

# Minimal mock data
latest = {
    "close": 120.0,
    "sma50": 110.0,
    "sma200": 100.0,
    "roc21": 3.0,
    "roc63": 12.0,
    "momentum_20": 5.0,
    "52w_high": 140.0,
    "52w_low": 80.0
}
previous = {"sma200": 98.0}

if __name__ == "__main__":
    res = compute_medium_term_score(latest, previous)
    print("Score:", res["score"])
    print("Components:", res["components"])
