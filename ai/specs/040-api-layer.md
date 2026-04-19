# Feature: API Layer (Refined)

---

## 1. Objective

Expose REST APIs for retrieving stock scores, indicators, and price data using existing ETL and scoring modules.

Primary goal: Enable consumption of computed insights (NOT raw ETL orchestration).

---

## 2. Architecture

Follow clean separation:

API Layer -> Service Layer -> Data / Scoring Layer

* API Layer: FastAPI routes
* Service Layer: orchestrates DB + scoring calls
* Data Layer: MongoDB
* Analysis Layer: scoring modules

---

## 3. Framework

* FastAPI
* Async endpoints
* Uvicorn server

---

## 4. Core APIs (Phase 1)

Focus ONLY on read APIs first (NO ETL trigger APIs)

---

### 4.1 Health Check

**GET /**

Response:

```json
{
  "status": "ok"
}
```

---

### 4.2 Get Medium-Term Score

**GET /score/medium/{symbol}**

Uses:

* `backend.analysis.medium_term_scoring`
* `backend.test_scripts.test_medium_term_scoring` pattern

Response:

```json
{
  "status": "success",
  "data": {
    "symbol": "TCS",
    "score": 78.5,
    "action": "BUY",
    "components": {},
    "explanation": "..."
  }
}
```

---

### 4.3 Get Short-Term Score

**GET /score/short/{symbol}**

Uses:

* `backend.analysis.short_term_scoring`

Response:

```json
{
  "status": "success",
  "data": {
    "symbol": "TCS",
    "score": 65.2,
    "components": {}
  }
}
```

---

### 4.4 Batch Score API

**GET /score/medium**

Query:

```text
?symbols=TCS,INFY,RELIANCE
```

Response:

```json
{
  "status": "success",
  "data": [
    { "symbol": "TCS", "score": 78.5 },
    { "symbol": "INFY", "score": 72.1 }
  ]
}
```

---

### 4.5 Get Latest Indicators

**GET /indicators/{symbol}**

Returns latest document from:

`technical_indicators` collection

---

### 4.6 Get Price History

**GET /prices/{symbol}**

Query params:

* `start_date` (optional)
* `end_date` (optional)

Returns data from:

`daily_price_data` collection

---

## 5. Service Layer (IMPORTANT)

Create new module:

`backend/services/stock_service.py`

Responsibilities:

* Fetch latest indicators
* Fetch previous indicators (for scoring)
* Call scoring functions
* Format response

---

## 6. Async vs Sync Handling (CRITICAL)

Mongo (`pymongo`) is synchronous.

Therefore:

* API = async
* DB calls = sync (wrapped safely)

Use:

```python
from fastapi.concurrency import run_in_threadpool
```

Example:

```python
latest = await run_in_threadpool(get_latest_indicator, symbol)
```

---

## 7. Response Format

Standard:

```json
{
  "status": "success",
  "data": {},
  "error": null
}
```

Error:

```json
{
  "status": "error",
  "data": null,
  "error": "message"
}
```

---

## 8. Validation

* Symbol must be uppercase string
* `symbols` query param must be comma-separated
* Validate date format (`YYYY-MM-DD`)

---

## 9. Error Handling

* 400 -> Invalid input
* 404 -> Symbol not found
* 500 -> Internal error

---

## 10. Performance Considerations

* Use async endpoints
* Avoid blocking calls directly
* Use threadpool for DB + scoring

---

## 11. Out of Scope (Phase 1)

DO NOT implement now:

* ETL trigger APIs
* Authentication
* Rate limiting
* WebSockets

---

## 12. Future Enhancements

* Add long-term scoring
* Add caching (Redis)
* Add batch APIs for indicators
* Add portfolio-level scoring
* Add UI integration

---

## 13. Deliverables

* FastAPI app (`backend/api/main.py`)
* Routes module (`backend/api/routes/`)
* Service layer (`backend/services/`)
* Fully working endpoints for:
* `/score/medium/{symbol}`
* `/score/short/{symbol}`
* `/indicators/{symbol}`
* `/prices/{symbol}`
