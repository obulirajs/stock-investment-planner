from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import MONGO_URL, DB_NAME

# MONGO_URL = "mongodb://localhost:27017"
# DB_NAME = "stock_research_db"   # Updated as per your requirement

_client = None


def get_database():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
    return _client[DB_NAME]
