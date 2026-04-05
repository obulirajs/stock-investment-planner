# Feature: Indicators ETL Pipeline (Optimized)

## 1. Objective

Compute technical indicators for all stocks using multiprocessing and store them in the `technical_indicators` collection for downstream analytics and scoring. Supports incremental updates to avoid redundant recomputation.

---

## 2. Inputs

### Data Sources:

* Daily price data (OHLC + volume) from `daily_price_data` collection
* Stock symbols from `stocks_master` collection
* Last computed indicator date for incremental processing

---

## 3. Indicators Computed

### Moving Averages:
* SMA10, SMA20, SMA50, SMA100, SMA200
* EMA20, EMA50

### Momentum & Trend:
* RSI14 (Relative Strength Index, 14-period)
* MACD (12, 26, 9): MACD line, Signal line, Histogram
* ADX14 (Average Directional Index, 14-period)
* Momentum20, Momentum100 (percentage change)

### Volatility:
* ATR14 (Average True Range, 14-period)
* Bollinger Bands (20-period, 2 std): Upper, Mid, Lower
* Volatility20 (20-day annualized standard deviation)

### Volume & Price:
* OBV (On-Balance Volume)
* 52-week High (252-period rolling max)
* 52-week Low (252-period rolling min)

### Price Data:
* Close price
* Volume

**Total: 28 indicators + 2 price fields = 30 output fields**

---

## 4. Processing Flow

### Phase 1: Initialization
1. Fetch list of all symbols from `stocks_master`
2. Determine pool size (min of CPU count or 8, for safe laptop operation)

### Phase 2: Batch Processing
1. Retrieve symbols in batches of 32
2. For each batch, submit to multiprocessing pool:
   * Check if incremental mode enabled
   * Fetch last indicator computation date for symbol
   * Retrieve last 300 days of price data (lookback window)
   * Validate minimum 30 data points available
   * Compute all technical indicators
   * Filter new rows only (if incremental)
   * Bulk upsert to database
3. Report progress after each batch

### Phase 3: Completion
Track success/failure counts and display summary

---

## 5. Output Schema

```json
{
  "symbol": "TCS",
  "date": "2026-04-05T00:00:00Z",
  "indicators": {
    "sma10": 3245.67,
    "sma20": 3238.45,
    "sma50": 3225.89,
    "sma100": 3210.23,
    "sma200": 3195.56,
    "ema20": 3244.32,
    "ema50": 3232.15,
    "rsi14": 65.42,
    "macd": 15.78,
    "macd_signal": 14.23,
    "macd_hist": 1.55,
    "atr14": 28.45,
    "momentum20": 3.45,
    "momentum100": 7.82,
    "bb_upper": 3285.92,
    "bb_mid": 3238.45,
    "bb_lower": 3190.98,
    "adx14": 42.56,
    "volatility_20": 0.185,
    "obv": 5234567890.0,
    "52w_high": 3425.67,
    "52w_low": 2950.12,
    "close": 3245.67,
    "volume": 4523000.0
  }
}

```

---

## 6. Data Storage

### Collection:
* `technical_indicators`

### Indexes:
* Compound index: `{symbol, date}`
* Ensures efficient queries by symbol and date range

### Update Strategy:
* Upsert operation (insert if not exists, update if exists)
* Bulk writes for performance (ordered=false for speed)
* Handles BulkWriteError gracefully

---

## 7. Configuration Parameters

```python
MONGO_URI = "mongodb://localhost:27017"  # default
DB_NAME = "stock_research_db"            # default
POOL_SIZE = min(cpu_count(), 8)          # parallel workers
BATCH_SYMBOLS = 32                       # symbols per batch
LOOKBACK_DAYS = 300                      # rolling window for indicators
MIN_DATA_POINTS = 30                     # minimum rows to compute
```

---

## 8. Performance Design

### Parallelization:
* Multiprocessing Pool with up to 8 workers (CPU-safe)
* Batch processing: 32 symbols per batch
* Ordered=false bulk writes for faster database operations

### Incremental Updates:
* Check last computed date for each symbol
* Only fetch data since last computation (minus lookback)
* Filter and upsert only new rows
* Significantly reduces recomputation

### Lookback Strategy:
* Fixed 300-day lookback window
* Ensures rolling indicators have sufficient historical context
* Recalculates from last computed date to ensure accuracy

---

## 9. Error Handling

### Data Validation:
* Skip symbols with <30 data points
* Skip symbols with missing price data
* Handle NaN values in indicator calculations

### Failure Handling:
* Per-symbol try-catch wrapper
* Bulk write errors logged per symbol
* Failures don't block other symbols
* Continue processing remaining symbols

### Return Status:
* Success: `(symbol, True, "{n} rows")`
* Skip: `(symbol, True, "Not enough data")`
* Update: `(symbol, True, "No new rows")`
* Error: `(symbol, False, "{error message}")`

---

## 10. Dependencies

* `pandas`: Data manipulation and indicator calculations
* `numpy`: Numerical operations
* `pymongo`: MongoDB operations
* `multiprocessing`: Parallel processing
* Price ETL (`price_etl.py`): Populates `daily_price_data`
* Stock Master ETL (`stock_master_etl.py`): Populates `stocks_master`

---

## 11. Edge Cases & Handling

| Scenario | Handling |
|----------|----------|
| Insufficient data (<30 rows) | Skip symbol, return status |
| Missing OHLC values | Filtered out before calculations |
| Data gaps in price history | Rolling calculations still work (min_periods=1) |
| First run (no previous indicators) | Fetch full LOOKBACK_DAYS |
| Incremental with no new data | Skip upsert, report "No new rows" |
| Bulk write errors | Log error details, skip batch, continue |
| CPU > 8 cores | Limit pool to 8 for system stability |

---

## 12. Execution

### Run with incremental updates (recommended):
```bash
python -m backend.etl.indicators_etl_optimized
```

### Or directly:
```bash
cd /path/to/projects
python backend/etl/indicators_etl_optimized.py
```

### Output:
```
Running indicators ETL for 500 symbols (incremental=True)
Progress: 32/500 (ok=30, failed=2)
Progress: 64/500 (ok=61, failed=3)
...
Completed.
```

---

## 13. Monitoring & Debugging

### Progress Tracking:
* Batch-level progress printed to console
* Success/failure counts updated per batch
* Easy visibility into problematic symbols

### Troubleshooting:
* Check MongoDB connection: Verify `MONGO_URI` accessible
* Missing data: Ensure `daily_price_data` is populated from price ETL
* Slow performance: Monitor CPU usage, adjust `POOL_SIZE` if needed
* Memory issues: Adjust `BATCH_SYMBOLS` if processing large datasets

---

## 14. Future Enhancements

* Add distributed computing (Spark, Dask) for very large datasets
* Cache indicator results to avoid redundant calculations
* Real-time streaming indicator updates
* Additional indicators: Ichimoku Cloud, VWAP, Keltner Channels
* Indicator parameter optimization based on historical performance
* Export indicators to separate time-series database for faster queries
