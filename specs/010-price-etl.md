# Feature: Price ETL Pipeline

## 1. Objective

Fetch and store historical daily stock price data (OHLCV) for all symbols using an external market data API.

---

## 2. Data Source

* External API: Marketstack
* Function: `fetch_eod(session, symbol, limit, offset)`

---

## 3. Input

* List of stock symbols (e.g., TCS, INFY)
* Symbols are mapped to exchange format:
  symbol + ".XNSE"

---

## 4. Processing Flow

1. For each symbol:

   * Call Marketstack API (`fetch_eod`)
   * Retrieve up to 1000 historical records
2. Transform API response into internal schema
3. Upsert each record into MongoDB

---

## 5. Output Schema

```json
{
  "symbol": "TCS",
  "date": "2026-03-30",
  "open": 3450,
  "high": 3550,
  "low": 3400,
  "close": 3500,
  "volume": 1200000,
  "adj_close": 3490
}
```

---

## 6. Data Storage

Collection:

* `daily_price_data`

Primary key:

* `symbol + date` (upsert)

---

## 7. Execution Model

* Async processing using `asyncio`
* HTTP client: `aiohttp`
* Concurrency controlled via semaphore (default: 4)

---

## 8. Error Handling

* API failure → mark symbol as failed
* Exception handling per symbol
* Continue processing other symbols

---

## 9. Logging

* Success/failure per symbol
* Summary:
  success count, failure count

---

## 10. Current Limitations

* No incremental loading (always fetches full dataset)
* Inefficient DB writes (one update per record)
* No retry logic for API failures
* No validation of API response

---

## 11. Performance Considerations

* Limited concurrency (4 parallel calls)
* Sequential DB writes inside loop (suboptimal)

---

## 12. Execution

```bash
python price_etl.py TCS INFY RELIANCE
```

---

## 13. Future Enhancements

* Incremental load (fetch only new dates)
* Bulk upsert instead of per-record update
* Retry mechanism with exponential backoff
* Data validation layer
* Support multiple exchanges/providers
* Config-driven concurrency

## 14. Refactoring Plan

### Phase 1: Performance Optimization

* Replace per-record `update_one` with `bulk_write`

### Phase 2: Incremental Loading

* Fetch only data after latest stored date
* Reduce API calls and DB writes

### Phase 3: Reliability Improvements

* Add retry mechanism for API failures
* Add structured logging

### Phase 4: Data Validation

* Validate OHLC values before storing
* Skip corrupted records
