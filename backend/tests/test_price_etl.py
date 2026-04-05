import pytest
import asyncio

from backend.etl.price_etl import run_price_etl, get_database_sync


@pytest.mark.asyncio
async def test_price_etl_end_to_end():
    symbol = "TCS"

    # Run ETL
    result = await run_price_etl([symbol])

    # Validate execution
    assert result is not None
    assert len(result) == 1

    # Check DB
    db = get_database_sync()
    coll = db["daily_price_data"]

    doc = coll.find_one({"symbol": symbol})

    assert doc is not None

    # Validate schema
    assert "open" in doc
    assert "high" in doc
    assert "low" in doc
    assert "close" in doc
    assert "volume" in doc


@pytest.mark.asyncio
async def test_price_etl_idempotent():
    symbol = "TCS"
    db = get_database_sync()
    coll = db["daily_price_data"]
    before = coll.count_documents({"symbol": symbol})
    await run_price_etl([symbol])
    after = coll.count_documents({"symbol": symbol})
    # No duplicates expected
    assert after == before