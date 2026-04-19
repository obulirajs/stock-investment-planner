import pytest
from backend.analysis.medium_term_scoring import compute_medium_term_score


def test_medium_term_score_basic():
    """Test basic functionality with valid inputs"""
    latest = {
        "close": 100,
        "sma50": 95,
        "sma200": 90,
        "momentum_20": 5,
        "52w_high": 120,
        "52w_low": 80
    }

    previous = {
        "sma200": 88
    }

    result = compute_medium_term_score(latest, previous, symbol="TCS")

    # Check structure
    assert result is not None
    assert "score" in result
    assert "score_int" in result
    assert "action" in result
    assert "components" in result
    assert "explanation" in result
    assert "computed_at" in result
    assert "symbol" in result

    # Check score range
    assert 0 <= result["score"] <= 100
    assert 0 <= result["score_int"] <= 100

    # Check action is valid
    assert result["action"] in ["BUY", "WATCH", "AVOID"]
    
    # Check components exist and are in range
    comp = result["components"]
    assert all(0 <= v <= 100 for v in comp.values())
    
    # Check explanation is non-empty
    assert len(result["explanation"]) > 0
    
    # Check timestamp format
    assert result["computed_at"].endswith("Z")


def test_medium_term_score_no_previous_data():
    """Test when previous data is missing (should default to 0.5 for slope)"""
    latest = {
        "close": 100,
        "sma50": 95,
        "sma200": 90,
        "momentum_20": 5,
        "52w_high": 120,
        "52w_low": 80
    }

    result = compute_medium_term_score(latest)
    
    assert result["score"] is not None
    assert 0 <= result["score"] <= 100
    assert result["action"] in ["BUY", "WATCH", "AVOID"]


def test_momentum_normalization():
    """Test momentum clamping [-20, +20]"""
    latest_bullish = {
        "close": 100,
        "sma50": 100,
        "sma200": 100,
        "momentum_20": 25,  # > 20, should clamp to 20 → score 100
        "52w_high": 100,
        "52w_low": 100
    }
    
    result_bullish = compute_medium_term_score(latest_bullish)
    assert result_bullish["components"]["momentum"] == 100.0
    
    latest_bearish = {
        "close": 100,
        "sma50": 100,
        "sma200": 100,
        "momentum_20": -25,  # < -20, should clamp to -20 → score 0
        "52w_high": 100,
        "52w_low": 100
    }
    
    result_bearish = compute_medium_term_score(latest_bearish)
    assert result_bearish["components"]["momentum"] == 0.0


def test_trend_slope_normalization():
    """Test trend slope percentage conversion and clamping [-5, +5]"""
    latest = {
        "close": 100,
        "sma50": 100,
        "sma200": 100,
        "momentum_20": 0,
        "52w_high": 100,
        "52w_low": 100
    }
    
    previous_rising = {
        "sma200": 95  # (100-95)/95 * 100 = 5.26%, clamps to 5% → score 100
    }
    
    result_rising = compute_medium_term_score(latest, previous_rising)
    assert result_rising["components"]["trend_slope"] == 100.0


def test_action_thresholds():
    """Test deterministic action thresholds"""
    # BUY threshold (≥ 65)
    latest_buy = {
        "close": 110, "sma50": 100, "sma200": 95,
        "momentum_20": 15, "52w_high": 120, "52w_low": 80
    }
    result_buy = compute_medium_term_score(latest_buy)
    assert result_buy["action"] == "BUY"
    assert result_buy["score_int"] >= 65
    
    # AVOID threshold (< 45)
    latest_avoid = {
        "close": 80, "sma50": 90, "sma200": 100,
        "momentum_20": -15, "52w_high": 120, "52w_low": 80
    }
    result_avoid = compute_medium_term_score(latest_avoid)
    assert result_avoid["action"] == "AVOID"
    assert result_avoid["score_int"] < 45


def test_missing_fields_default_neutral():
    """Test that missing fields default to neutral (0.5)"""
    latest = {}  # All fields missing
    result = compute_medium_term_score(latest)
    
    # With all neutral (0.5), final score should be 50
    assert result["score"] == 50.0
    assert result["score_int"] == 50
    assert result["action"] == "WATCH"  # 45-64 range