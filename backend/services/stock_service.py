from backend.db import get_database
from datetime import datetime


class StockService:

    @staticmethod
    def get_collection():
        db = get_database()
        return db["stocks_master"]  # Collection stays the same

    @staticmethod
    async def upsert_stock(stock_data: dict):
        collection = StockService.get_collection()

        stock_data["updated_at"] = datetime.utcnow()

        result = await collection.update_one(
            {"symbol": stock_data["symbol"]},
            {"$set": stock_data},
            upsert=True
        )
        return result

    @staticmethod
    async def get_stocks(limit: int = 200):
        collection = StockService.get_collection()
        cursor = collection.find().limit(limit)
        return await cursor.to_list(length=limit)

    @staticmethod
    async def get_stock_by_symbol(symbol: str):
        collection = StockService.get_collection()
        return await collection.find_one({"symbol": symbol})
