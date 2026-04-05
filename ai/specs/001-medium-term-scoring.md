# Feature: Medium Term Scoring (Production Specification)

## 1. Objective

Compute a deterministic medium-term investment score (0–100) for a stock to guide **buy/hold/avoid** decisions over a 1–3 month horizon. Score is derived from 5 technical components with explicit normalization and clamping to ensure reproducibility and edge-case determinism.

---

## 2. Data Sources & Input Specifications

### 2.1 Primary Source
- **Collection**: `technical_indicators` (MongoDB)
- **Access Pattern**: Single fetch per symbol per day
- **Temporal Requirement**: Current day + previous day data (for slope calculation)

### 2.2 Required Input Fields (with strict units)

| Field | Type | Unit | Required | Tolerance | 
|-------|------|------|----------|-----------|
| `close` | float | Currency (₹) | YES | > 0.0 |
| `sma50` | float | Currency (₹) | YES | > 0.0 |
| `sma200` | float | Currency (₹) | YES | > 0.0 |
| `sma200_prev` | float | Currency (₹) | YES* | > 0.0 |
| `momentum_20` | float | Percentage (%) | YES | -∞ to +∞ |
| `52w_high` | float | Currency (₹) | YES | > 0.0 |
| `52w_low` | float | Currency (₹) | YES | > 0.0 |

**Note**: `*sma200_prev` required for slope; if unavailable, default component to 0.5

### 2.3 Alternative Field Name Mappings
Normalize these variations to canonical names:
```
52w_high → 52_week_high → 52wHigh
52w_low → 52_week_low → 52wLow
momentum_20 → roc20 → roc21 → roc63 (fallback precedence)
```

---

## 3. Output Specification

### 3.1 Response Schema (JSON)
```json
{
  "symbol": "TCS",
  "score": 78.45,
  "score_int": 78,
  "action": "BUY",
  "components": {
    "trend_health": 72.5,
    "long_trend": 80.1,
    "trend_slope": 65.0,
    "momentum": 70.0,
    "week52_strength": 85.2
  },
  "explanation": "Strong uptrend: close above SMA50 (72.5%), SMA50 above SMA200 (80.1%), positive 3-day slope, momentum at 70%.",
  "computed_at": "2026-04-05T09:30:00Z",
  "version": "1.0"
}
```

### 3.2 Field Definitions
- `score`: Floating-point (0–100), rounded to 2 decimals
- `score_int`: Integer (0–100) for action thresholds
- `components`: Each value in range [0, 100], rounded to 1 decimal
- `computed_at`: ISO 8601 timestamp (UTC)

---

## 4. Component Scoring Formulas

All components normalize to [0, 1] internally, then scaled to [0, 100] for display.

---

### 4.1 Trend Health (Weight: 0.25)

**Measures**: Short-term price vs. 50-day moving average

**Mathematical Definition**:
```
raw_diff = (close - sma50) / sma50           [as decimal]
clamped = clamp(raw_diff, -0.15, +0.15)     [deadzone: [-15%, +15%]]
component = clamped / 0.15 / 2 + 0.5         [normalize to [0, 1]]
display = component * 100                     [scale to [0, 100]]
```

**Interpretation**:
- `component = 0.0`: Close is 15%+ below SMA50 (bearish)
- `component = 0.5`: Close ≈ SMA50 (neutral)
- `component = 1.0`: Close is 15%+ above SMA50 (bullish)

**Edge Case**:
- If `close` or `sma50` is None/invalid or `sma50 = 0` → `component = 0.5`

---

### 4.2 Long-Term Trend (Weight: 0.25)

**Measures**: Intermediate trend vs. long-term trend (SMA50 vs SMA200)

**Mathematical Definition**:
```
raw_diff = (sma50 - sma200) / sma200         [as decimal]
clamped = clamp(raw_diff, -0.20, +0.20)     [deadzone: [-20%, +20%]]
component = clamped / 0.20 / 2 + 0.5         [normalize to [0, 1]]
display = component * 100                     [scale to [0, 100]]
```

**Interpretation**:
- `component = 0.0`: SMA50 is 20%+ below SMA200 (downtrend)
- `component = 0.5`: SMA50 ≈ SMA200 (trend inflection)
- `component = 1.0`: SMA50 is 20%+ above SMA200 (uptrend)

**Edge Case**:
- If `sma50` or `sma200` is None/invalid or `sma200 = 0` → `component = 0.5`

---

### 4.3 Trend Slope (Weight: 0.20)

**Measures**: Direction and speed of long-term moving average (SMA200 momentum)

**Mathematical Definition**:
```
slope_pct = ((sma200_today - sma200_prev) / (sma200_prev + 1e-9)) * 100    [in %]
clamped = clamp(slope_pct, -5.0, +5.0)                                    [range: [-5%, +5%]]
component = clamped / 5.0 / 2 + 0.5                                       [normalize to [0, 1]]
display = component * 100                                                  [scale to [0, 100]]
```

**Interpretation**:
- `component = 0.0`: SMA200 falling 5%+ (strong downtrend)
- `component = 0.5`: SMA200 flat (no trend change)
- `component = 1.0`: SMA200 rising 5%+ (strong uptrend)

**Edge Cases**:
- If `sma200_today` or `sma200_prev` is None/invalid → `component = 0.5`
- If `sma200_prev = 0` → Use `1e-9` as denominator (prevents div-by-zero)

---

### 4.4 Momentum (Weight: 0.20)

**Measures**: Rate of change over ~20–60 days

**Input Priority** (try in order):
1. `roc63` (63-day rate of change) — primary
2. `roc21` (21-day rate of change) — fallback
3. `momentum_20` (20-day momentum) — last resort

**Mathematical Definition** (assuming input is already in %):
```
momentum_val = roc63 OR roc21 OR momentum_20   [in %, e.g., 15.3]
clamped = clamp(momentum_val, -20.0, +20.0)    [range: [-20%, +20%]]
component = clamped / 20.0 / 2 + 0.5           [normalize to [0, 1]]
display = component * 100                      [scale to [0, 100]]
```

**Interpretation**:
- `component = 0.0`: Price down 20%+ over period (strong negative momentum)
- `component = 0.5`: No momentum change (flat)
- `component = 1.0`: Price up 20%+ over period (strong positive momentum)

**Edge Cases**:
- If all momentum fields are None/invalid → `component = 0.5`
- Ensure input raw value is in % format; if in decimal (e.g., 0.15 for 15%), multiply by 100 first

---

### 4.5 52-Week Strength (Weight: 0.10)

**Measures**: Current price position within 52-week trading range

**Mathematical Definition**:
```
if (52w_high - 52w_low) == 0:
    component = 0.5                                    [symmetric range edge case]
else:
    position = (close - 52w_low) / (52w_high - 52w_low)    [as decimal]
    component = clamp(position, 0.0, 1.0)             [ensure [0, 1]]

display = component * 100                             [scale to [0, 100]]
```

**Interpretation**:
- `component = 0.0`: Close near 52-week low (bearish extremes)
- `component = 0.5`: Close near 52-week midpoint (neutral)
- `component = 1.0`: Close near 52-week high (bullish extremes)

**Edge Cases**:
- If `52w_high = 52w_low` (zero range) → `component = 0.5`
- If `close < 52w_low` or `close > 52w_high` (data integrity error) → Clamp and proceed
- If any field is None/invalid → `component = 0.5`

---

## 5. Composite Score Calculation

### 5.1 Weight Definition
Validates to: 0.25 + 0.25 + 0.20 + 0.20 + 0.10 = **1.0** ✓

```python
weights = {
    "trend_health": 0.25,
    "long_trend": 0.25,
    "trend_slope": 0.20,
    "momentum": 0.20,
    "week52_strength": 0.10
}
```

### 5.2 Final Score Formula
```
weighted_sum = (
    c_trend_health * 0.25 +
    c_long_trend * 0.25 +
    c_trend_slope * 0.20 +
    c_momentum * 0.20 +
    c_week52_strength * 0.10
)

score_raw = weighted_sum * 100                    [convert [0,1] to [0,100]]
score_clamped = clamp(score_raw, 0.0, 100.0)   [safety clamp]
score_final = round(score_clamped, 2)            [2 decimals]
score_int = int(floor(score_final))              [integer for thresholds]
```

### 5.3 Display Precision
- Components: 1 decimal place (e.g., 72.5)
- Final score: 2 decimal places (e.g., 78.45)
- Threshold use: Integer (e.g., 78)

---

## 6. Action Thresholds (Deterministic)

Computed using **integer score** for consistency:

```python
score_int = int(floor(final_score))

if score_int >= 65:
    action = "BUY"
elif score_int >= 45:
    action = "WATCH"
else:
    action = "AVOID"
```

| Score Int | Range    | Action | Confidence |
|-----------|----------|--------|------------|
| 65–100    | [65, 100]| BUY    | High       |
| 45–64     | [45, 64] | WATCH  | Medium     |
| 0–44      | [0, 44]  | AVOID  | Low        |

**Boundary Precision**:
- Score 64.99 → int(64) → WATCH ✓
- Score 65.00 → int(65) → BUY ✓
- Score 44.99 → int(44) → AVOID ✓
- Score 45.00 → int(45) → WATCH ✓

---

## 7. Deterministic Edge Case Handling

### 7.1 Missing/Invalid Data
| Scenario | Handling | Rationale |
|----------|----------|-----------|
| `close` is None | Use 0.5 for affected components | Neutral default |
| `sma50 = 0` | Use 0.5 for `trend_health` | Prevent division-by-zero |
| `sma200_prev` missing | Use 0.5 for `trend_slope` | Cannot compute slope |
| All components = 0.5 | Final score = 50.0 | Neutral overall |
| Negative price (corruption) | Proceed with math; flag in logs | Data integrity issue |
| `52w_high < 52w_low` | Clamp to valid; use 0.5 | Data error; fallback neutral |
| `close > 52w_high` | Clamp position to 1.0, proceed | Boundary condition; treat as high strength |

### 7.2 NaN/Infinite Handling
```python
if not isfinite(value):
    # Treat as None; default component to 0.5
    component = 0.5
```

### 7.3 Null Check Protocol
```python
def safe_get(data_dict, key, default=None):
    if data_dict is None:
        return default
    val = data_dict.get(key, default)
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default
```

---

## 8. Data Quality & Validation Rules

### 8.1 Pre-Scoring Validation
```
✓ All numeric fields must be float (no NaN, no infinity)
✓ All prices (close, sma*, 52w_*) must be > 0 in real data
✓ 52w_high >= 52w_low (logical constraint)
✓ 52w_low <= close <= 52w_high (expected; allow clamp if violated)
✓ sma200 <= sma50 (typical in downtrend, not enforced)
✓ Timestamp must be ISO 8601 UTC
```

### 8.2 Failure Modes
| Failure | Recovery |
|---------|----------|
| DB fetch timeout | Return cached result or score = NULL |
| All fields missing | score = 50, action = "WATCH" |
| Momentum field ambiguous | Try priority list; default 0.5 if all None |
| Historical sma200 unavailable | Set trend_slope = 0.5 (neutral) |

---

## 9. Dependencies & Data Contracts

### 9.1 Upstream Dependencies
- **Collection**: `technical_indicators` (MongoDB)
- **Required Indices**: `{symbol: 1, date: -1}` for fast lookups
- **Refresh Frequency**: Daily (one record per symbol per trading day)

### 9.2 Downstream Contracts
- **Consumer**: Risk/Portfolio Management system
- **Update Frequency**: Daily, post-market-close or intraday
- **Async Support**: All lookups designed for async/await pattern
- **Idempotency**: Same inputs → guaranteed same score (deterministic)

---

## 10. Explanation Text Generation

### 10.1 Template Rules
Generate human-readable rationale based on component values:

```
Trend Health (72.5%):
  if component >= 80: "Close significantly above SMA50 (strong short-term uptrend)"
  elif component >= 60: "Close above SMA50 (short-term uptrend)"
  elif component >= 40: "Close near SMA50 (neutral short-term trend)"
  else: "Close below SMA50 (short-term downtrend)"

Long Trend (80.1%):
  if component >= 80: "SMA50 well above SMA200 (strong intermediate uptrend)"
  elif component >= 60: "SMA50 above SMA200 (intermediate uptrend)"
  else: "SMA50 below SMA200 (downtrend or recovery phase)"

Trend Slope (65.0%):
  if component >= 75: "SMA200 rising sharply (accelerating uptrend)"
  elif component >= 60: "SMA200 rising (uptrend established)"
  else: "SMA200 flat or declining (trend weakness)"

Momentum (70.0%):
  if component >= 80: "Strong positive momentum ({val}%)"
  elif component >= 60: "Positive momentum ({val}%)"
  else: "Weak or negative momentum ({val}%)"

52-Week Strength (85.2%):
  if component >= 80: "Trading near 52-week highs (strong bullish sentiment)"
  elif component >= 60: "Trading in upper range (bullish bias)"
  else: "Trading in lower range or near lows (bearish sentiment)"
```

### 10.2 Composite Explanation Example
```
Score: 78 (BUY) | Reason: Strong uptrend: close above SMA50 
(72.5%), SMA50 above SMA200 (80.1%), positive 3-day slope 
(65%), momentum at 70%, trading near 52-week highs (85.2%).
```

---

## 11. Performance Requirements

### 11.1 Latency Targets
- **Component Calculation**: < 1 ms (pure compute)
- **DB Fetch (current + prev)**: < 50 ms
- **End-to-End**: < 100 ms per symbol (single async call)
- **Batch (100 symbols)**: < 500 ms (concurrent)

### 11.2 Computation Complexity
- **Time**: O(1) — fixed 5 components, no loops
- **Space**: O(1) — no dynamic allocations
- **DB I/O**: 2 queries per symbol (current, prev SMA200)

---

## 12. Version Control & Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-05 | Initial production release; deterministic edge cases; explicit normalization formulas |

---

## 13. Future Enhancements (Road Map)

- [ ] Add RSI (Relative Strength Index) component (weight: 0.15, adjust others)
- [ ] Add Volatility (ATR) component for risk assessment
- [ ] Add Drawdown-from-highs component
- [ ] Support intraday scoring (minute-level data)
- [ ] Add sector/market regime filters
- [ ] Machine-learning calibration of weights based on realized returns
* Replace static weights with ML model
* Multi-timeframe scoring

## Mathematical Definitions (STRICT)

### Momentum

- Input: momentum_20 (percentage)
- Example: 15 means +15%

Normalization:

score = clip(momentum_20, -20, +20)
normalized = (score + 20) / 40

---

### Trend Slope (SMA200)

- slope_pct = ((sma200_today - sma200_prev) / sma200_prev) * 100

Normalization:

score = clip(slope_pct, -5, +5)
normalized = (score + 5) / 10

## Units & Conventions

- All percentage values are in percentage points (e.g., 15 = 15%)
- No metric should use fractional representation (0.15)
- All normalization must operate on percentage units

## Output Contract

Scoring module returns:

{
  "score": float (0-100),
  "components": {component_name: float (0-100)}
}

Service layer must enrich with:
- action
- explanation
- computed_at
- symbol