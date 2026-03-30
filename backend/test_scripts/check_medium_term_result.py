import asyncio
from backend.db import get_database

async def check():
    db = get_database()
    doc = await db["stocks_master"].find_one(
        {"symbol": "TCS"},
        {"analysis.medium_term": 1}
    )
    print(doc)

if __name__ == "__main__":
    asyncio.run(check())
