import pytest
import asyncio

from backend.analysis.medium_term_scoring import compute_medium_term_score


def test_medium_term_score_basic():
    latest = {
        "close": 100,
        "sma50": 95,
        "sma200": 90,
        "roc21": 5,
        "52w_high": 120,
        "52w_low": 80
    }

    previous = {
        "sma200": 88
    }

    result = compute_medium_term_score(latest, previous)

    assert result is not None
    assert "score" in result
    assert "components" in result

    assert 0 <= result["score"] <= 100

#------------------------------------------------------------------------------

# @pytest.mark.asyncio
# async def test_medium_term_scoring_valid_symbol():
#     symbol = "TCS"
    
#     result = await score_medium_term_for_symbol(symbol)

#     # Basic structure checks
#     assert result is not None
#     assert "score" in result
#     assert "action" in result
#     assert "components" in result

#     # Score range validation
#     assert 0 <= result["score"] <= 100

#     # Action validation
#     assert result["action"] in ["BUY", "WATCH", "AVOID"]

#     # Components validation
#     components = result["components"]
#     assert isinstance(components, dict)
#     assert len(components) > 0

# @pytest.mark.asyncio
# async def test_medium_term_scoring_invalid_symbol():
#     symbol = "INVALID_SYMBOL"

#     result = await score_medium_term_for_symbol(symbol)

#     assert result is not None
#     assert result["score"] == 50
#     assert result["action"] == "WATCH"