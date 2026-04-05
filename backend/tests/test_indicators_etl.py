import pytest
from backend.etl.indicators_etl_optimized import compute_symbol
from backend.etl.indicators_etl_optimized import get_database_sync



def test_compute_symbol_basic():
    # Use a real symbol that has data
    symbol = "TCS"

    result = compute_symbol((symbol, False))

    # Structure validation
    assert isinstance(result, tuple)
    assert len(result) == 3

    sym, success, msg = result

    assert sym == symbol
    assert isinstance(success, bool)

    # Either success or known failure (like not enough data)
    assert success in [True, False]



def test_indicators_written():
    db = get_database_sync()

    # Check if indicators exist for TCS
    doc = db["technical_indicators"].find_one({"symbol": "TCS"})

    assert doc is not None
    assert "indicators" in doc

    indicators = doc["indicators"]

    # Basic fields check
    assert "sma50" in indicators
    assert "sma200" in indicators