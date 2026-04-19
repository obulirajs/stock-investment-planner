# 002 - Short-Term Scoring Specification

## 1. Objective

The short-term scoring model evaluates **entry and exit timing** for stocks based on recent price momentum and reversal signals.

Unlike medium-term scoring (trend-focused), this model emphasizes:

* Momentum shifts
* Overbought / oversold conditions
* Short-term price positioning

---

## 2. Inputs

The scoring function expects the following fields from the `technical_indicators` collection:

* `rsi14`
* `macd_hist`
* `momentum20`
* `sma20`
* `close`

Optional (for slope calculation):

* Previous period `macd_hist`

---

## 3. Output Schema

The function must return:

```json
{
  "score": 0-100,
  "components": {
    "rsi": number,
    "macd": number,
    "momentum": number,
    "price_vs_sma20": number
  }
}
```

---

## 4. Scoring Components

All components must be normalized to a range of **0 to 1** before applying weights.

---

### 4.1 RSI Score (Reversal Signal)

Purpose:

* Detect overbought / oversold conditions

Logic:

* RSI ≤ 30 → Strong bullish → score = 1.0
* RSI ≥ 70 → Bearish → score = 0.0
* Between 30–70 → Linear interpolation

Notes:

* If RSI is missing → default score = 0.5

---

### 4.2 MACD Histogram Score (Momentum Shift)

Purpose:

* Detect change in momentum direction

Inputs:

* `macd_hist` (latest)
* `macd_hist` (previous)

Logic:

* If current > 0 → bullish bias
* If current > previous → strengthening momentum
* Combine both direction and slope

Normalization:

* Strong positive and increasing → score close to 1
* Strong negative and decreasing → score close to 0
* Neutral / missing → 0.5

---

### 4.3 Momentum Score

Purpose:

* Capture short-term strength

Input:

* `momentum20` (percentage)

Logic:

* Map range:

  * -10% → 0
  * +10% → 1
* Clamp outside range

Notes:

* Missing → default 0.5

---

### 4.4 Price vs SMA20 Score

Purpose:

* Identify short-term trend bias

Logic:

* (close - sma20) / sma20

Normalization:

* -5% → 0
* +5% → 1
* Linear scaling in between

Notes:

* Missing values → 0.5

---

## 5. Weights

| Component      | Weight |
| -------------- | ------ |
| RSI            | 0.30   |
| MACD           | 0.25   |
| Momentum       | 0.25   |
| Price vs SMA20 | 0.20   |

Final score:

```
score = weighted sum * 100
```

---

## 6. Action Rules

| Score Range | Action |
| ----------- | ------ |
| ≥ 70        | BUY    |
| ≤ 30        | SELL   |
| 30–70       | HOLD   |

---

## 7. Edge Cases & Safety

* Missing inputs → default component score = 0.5
* Division by zero → safe fallback (0.5)
* No previous MACD → slope treated as neutral
* All outputs must be bounded within [0, 100]

---

## 8. Design Principles

* Simple and explainable scoring
* No overfitting to historical data
* Independent components (no hidden coupling)
* Deterministic outputs (no randomness)

---

## 9. Future Enhancements (Not in current scope)

* Volume spike integration
* Intraday signals
* Volatility-adjusted scoring
* Signal smoothing / noise reduction
