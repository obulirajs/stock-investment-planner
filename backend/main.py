from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os

app = FastAPI()

# ----------------------------
# CORS configuration
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# MongoDB connection
# ----------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "stock_research_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]


@app.get("/")
def root():
    return {"message": "FastAPI backend running!"}


# ----------------------------
# Helper functions
# ----------------------------
def get_advice(score: float) -> str:
    if score >= 70:
        return "Buy"
    if score >= 50:
        return "Watch"
    return "Avoid"


def get_explanation(score: float) -> str:
    if score >= 70:
        return "Strong trend and momentum. Stock is trading near its recent highs."
    if score >= 50:
        return "Stable trend with moderate momentum. Can be accumulated on dips."
    if score >= 30:
        return "Weak momentum and sideways movement. Risk is relatively higher."
    return "Poor trend and momentum. Better to avoid for now."


# ----------------------------
# API endpoint
# ----------------------------
@app.get("/api/medium-term")
def get_medium_term_scores(minScore: float = 0,limit: int = 100):
    cursor = (
        db["stocks_master"]
        .find(
            {"analysis.medium_term.score": {"$exists": True, "$gte": minScore}},
            {
                "_id": 0,
                "symbol": 1,
                "analysis.medium_term.score": 1,
            },
        )
        .sort("analysis.medium_term.score", -1)
        .limit(limit)
    )

    results = []
    for doc in cursor:
        score = round(doc["analysis"]["medium_term"]["score"], 2)
        results.append(
            {
                "symbol": doc["symbol"],
                "score": score,
                "advice": get_advice(score),
                "explanation": get_explanation(score),
            }
        )

    return results
