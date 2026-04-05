# Feature: API Layer

## 1. Objective

Expose REST APIs for accessing stock data, analysis results, and triggering ETL pipelines.

---

## 2. Responsibilities

* Handle HTTP requests
* Validate input
* Call service layer
* Return structured responses
* Trigger ETL jobs (optional)

---

## 3. Framework

* FastAPI
* Async endpoints

---

## 4. API Categories

### 4.1 Health Check

**GET /**
Returns API status

---

### 4.2 Stock APIs

#### Get Stock Overview

**GET /stocks/{symbol}**

Returns:

* Latest price
* Analysis (short, medium, long)
* Indicators

---

#### Get Price History

**GET /stocks/{symbol}/prices**

Query params:

* start_date
* end_date

---

#### Get Indicators

**GET /stocks/{symbol}/indicators**

---

#### Get Analysis

**GET /stocks/{symbol}/analysis**

---

### 4.3 ETL APIs

#### Run Price ETL

**POST /etl/price**

Body:

```json id="g9pyg9"
["TCS", "INFY"]
```

---

#### Run Indicators ETL

**POST /etl/indicators**

---

#### Run Scoring ETL

**POST /etl/scoring**

---

## 5. Request Validation

* Validate symbol format
* Validate date ranges
* Reject invalid inputs

---

## 6. Response Format

Standard response:

```json id="89vmlf"
{
  "status": "success",
  "data": {...},
  "error": null
}
```

Error response:

```json id="2w5q4n"
{
  "status": "error",
  "data": null,
  "error": "message"
}
```

---

## 7. Error Handling

* 400 → Bad request
* 404 → Not found
* 500 → Internal error

---

## 8. Dependencies

* Stock Service Layer
* ETL modules
* Database layer

---

## 9. Performance Considerations

* Async endpoints
* Avoid blocking operations
* Use background tasks for ETL

---

## 10. Security (Future)

* API authentication (JWT)
* Rate limiting
* Input sanitization

---

## 11. Documentation

* Swagger UI (`/docs`)
* OpenAPI specification

---

## 12. Future Enhancements

* GraphQL support
* WebSocket streaming (live prices)
* Batch APIs
* API versioning (`/v1`, `/v2`)
