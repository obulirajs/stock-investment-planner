# Feature: Stock Service Layer

## 1. Objective

Provide a unified service layer to retrieve stock data, analysis results, and insights for API and UI consumption.

---

## 2. Responsibilities

* Fetch stock data from database
* Aggregate analysis results (short-term, medium-term, long-term)
* Provide structured responses for API layer
* Abstract database access from API

---

## 3. Inputs

* Stock symbol (e.g., TCS)
* Optional filters (date, timeframe)

---

## 4. Data Sources

* `stocks_master`
* `technical_indicators`
* `daily_price_data`

---

## 5. Core Functions

### 5.1 Get Stock Overview

Returns:

* Basic stock info
* Latest price
* Latest analysis scores

---

### 5.2 Get Analysis Data

Returns:

* Short-term score
* Medium-term score
* Long-term score

---

### 5.3 Get Price History

Returns:

* Historical OHLC data
* Date range support

---

### 5.4 Get Indicators

Returns:

* SMA50, SMA200
* Momentum
* 52-week high/low

---

## 6. Output Example

```json id="zsbx9f"
{
  "symbol": "TCS",
  "price": {
    "close": 3500,
    "date": "2026-03-30"
  },
  "analysis": {
    "short_term": {...},
    "medium_term": {...},
    "long_term": {...}
  },
  "indicators": {
    "sma50": 3400,
    "sma200": 3200
  }
}
```

---

## 7. Design Principles

* Separation of concerns (no business logic in API layer)
* Reusable service methods
* Async DB access

---

## 8. Dependencies

* MongoDB
* Analysis modules:

  * medium_term_scoring
  * short_term_scoring
  * long_term_scoring

---

## 9. Error Handling

* Missing stock → return 404-like response
* Missing data → return partial response
* DB failure → propagate error

---

## 10. Performance Considerations

* Minimize DB calls (aggregate queries)
* Use indexing on symbol/date
* Cache frequently accessed data (future)

---

## 11. Future Enhancements

* Add portfolio-level aggregation
* Add caching layer (Redis)
* Add pagination for historical data
* Add filtering and sorting options
