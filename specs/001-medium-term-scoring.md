# Feature: Medium Term Scoring

## 1. Objective

Compute a medium-term investment score (0–100) for a stock to guide decisions over a 1–3 month horizon.

---

## 2. Inputs

Data is sourced from `technical_indicators` collection.

Required fields:

* `close` (latest price)
* `sma50`
* `sma200`
* `momentum_20`
* `52w_high`
* `52w_low`

---

## 3. Output

```json
{
  "symbol": "TCS",
  "score": 78,
  "action": "BUY",
  "components": {
    "trend_health": 72.5,
    "long_trend": 80.1,
    "trend_slope": 65.0,
    "momentum": 70.0,
    "week52_strength": 85.2
  },
  "explanation": "text",
  "computed_at": "timestamp"
}
```

---

## 4. Scoring Components

### 4.1 Trend Health

* Formula: (close - sma50) / sma50
* Normalized to range [0,1]
* Clamped between [-0.15, +0.15]

---

### 4.2 Long-Term Trend

* Formula: (sma50 - sma200) / sma200
* Clamped between [-0.20, +0.20]

---

### 4.3 Trend Slope

* Based on change in SMA200 (current vs previous)
* Range normalized between [-5, +5]

---

### 4.4 Momentum

* Based on 20-day momentum
* Clamped between [-20, +20]

---

### 4.5 52-Week Strength

* Position of current price within 52-week range
* Formula:
  (close - low) / (high - low)

---

## 5. Weights

| Component        | Weight |
| ---------------- | ------ |
| Trend Health     | 0.25   |
| Long Trend       | 0.25   |
| Trend Slope      | 0.20   |
| Momentum         | 0.20   |
| 52-week Strength | 0.10   |

---

## 6. Final Score

* Weighted sum of all components
* Scaled to 0–100
* Rounded to integer

---

## 7. Action Thresholds

| Score | Action |
| ----- | ------ |
| ≥ 65  | BUY    |
| 45–64 | WATCH  |
| < 45  | AVOID  |

---

## 8. Edge Cases

* Missing data → default component score = 0.5
* Invalid ranges → fallback to neutral
* 52-week high == low → return 0.5

---

## 9. Dependencies

* MongoDB collection: `technical_indicators`
* Previous day SMA200 required for slope

---

## 10. Explanation Logic

Generate human-readable explanation:

* Trend vs SMA50
* Long-term trend direction
* Momentum strength
* 52-week positioning

---

## 11. Performance Considerations

* Single DB fetch per symbol
* One additional fetch for previous SMA200
* Designed for async execution

---

## 12. Future Enhancements

* Add RSI, volatility, drawdown
* Replace static weights with ML model
* Multi-timeframe scoring
