import json
import os
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

# ==============================
# Configuration
# ==============================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "stock_research_db")

POOL_SIZE = min(cpu_count(), 8)     # safe default for laptops
BATCH_SYMBOLS = 32                  # symbols per pool batch
LOOKBACK_DAYS = 300                 # safe lookback for rolling indicators

# ==============================
# DB (SYNC) HELPER
# ==============================

def get_database_sync():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

# ==============================
# INDICATOR FUNCTIONS
# ==============================

def sma(s, window): return s.rolling(window, min_periods=1).mean()
def ema(s, span): return s.ewm(span=span, adjust=False).mean()

def rsi(s, period=14):
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(com=period - 1, adjust=False).mean()
    ma_down = down.ewm(com=period - 1, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)

def macd(s, short=12, long=26, signal=9):
    es = ema(s, short)
    el = ema(s, long)
    macd_line = es - el
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line

def atr(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()

def momentum_pct(s, window): return s.pct_change(window) * 100

def bollinger(s, window=20, num_std=2):
    mid = sma(s, window)
    std = s.rolling(window, min_periods=1).std().fillna(0)
    return mid + num_std * std, mid, mid - num_std * std

def volatility_std(s, window=20):
    return s.pct_change().rolling(window, min_periods=1).std() * np.sqrt(252)

def obv(close, volume):
    return (np.sign(close.diff()).fillna(0) * volume).cumsum().fillna(0)

def adx(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_high, prev_low, prev_close = high.shift(1), low.shift(1), close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    tr_s = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_s = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_s = minus_dm.ewm(alpha=1 / period, adjust=False).mean()
    dx = (abs((plus_s / tr_s) - (minus_s / tr_s)) /
          ((plus_s / tr_s) + (minus_s / tr_s))).fillna(0) * 100
    return dx.ewm(alpha=1 / period, adjust=False).mean().fillna(0)

# ==============================
# DB FETCH / WRITE
# ==============================

def get_all_symbols_sync() -> List[str]:
    db = get_database_sync()
    return [d["symbol"] for d in db["stocks_master"].find({}, {"symbol": 1})]

def get_last_indicator_date(symbol: str) -> Optional[datetime]:
    db = get_database_sync()
    doc = db["technical_indicators"].find({"symbol": symbol}).sort("date", -1).limit(1)
    res = list(doc)
    return res[0]["date"] if res else None

def fetch_price_df_sync(symbol: str, start: Optional[datetime]) -> pd.DataFrame:
    db = get_database_sync()
    query = {"symbol": symbol}
    if start:
        query["date"] = {"$gte": start}
    rows = list(db["daily_price_data"].find(query).sort("date", 1))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.set_index("date")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["open", "high", "low", "close", "volume"]]

def bulk_upsert(symbol: str, ind: pd.DataFrame):
    db = get_database_sync()
    ops = []
    for idx, row in ind.iterrows():
        indicators = {k: float(v) for k, v in row.items() if pd.notna(v)}
        ops.append(UpdateOne(
            {"symbol": symbol, "date": idx.to_pydatetime()},
            {"$set": {"symbol": symbol, "date": idx.to_pydatetime(), "indicators": indicators}},
            upsert=True
        ))
    if ops:
        try:
            db["technical_indicators"].bulk_write(ops, ordered=False)
        except BulkWriteError as e:
            print(f"[ERROR] Bulk write error for {symbol}: {e.details}")

# ==============================
# CORE COMPUTE (RUNS IN POOL)
# ==============================

def compute_symbol(args: Tuple[str, bool]):
    symbol, incremental = args
    try:
        last_date = get_last_indicator_date(symbol) if incremental else None
        start = last_date - pd.Timedelta(days=LOOKBACK_DAYS) if last_date else None
        df = fetch_price_df_sync(symbol, start)
        df = df.dropna(subset=["close"])

        if df.empty:
            return symbol, False, "No data"

        if len(df) < 30:
            return symbol, True, "Skipped: insufficient data"

        c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
        ind = pd.DataFrame(index=df.index)

        ind["sma10"] = sma(c, 10)
        ind["sma20"] = sma(c, 20)
        ind["sma50"] = sma(c, 50)
        ind["sma100"] = sma(c, 100)
        ind["sma200"] = sma(c, 200)
        ind["ema20"] = ema(c, 20)
        ind["ema50"] = ema(c, 50)
        ind["rsi14"] = rsi(c)
        macd_l, macd_s, macd_h = macd(c)
        ind["macd"] = macd_l
        ind["macd_signal"] = macd_s
        ind["macd_hist"] = macd_h
        ind["atr14"] = atr(df)
        ind["momentum20"] = momentum_pct(c, 20)
        ind["momentum100"] = momentum_pct(c, 100)
        bb_u, bb_m, bb_l = bollinger(c)
        ind["bb_upper"] = bb_u
        ind["bb_mid"] = bb_m
        ind["bb_lower"] = bb_l
        ind["52w_high"] = c.rolling(252, min_periods=1).max()
        ind["52w_low"] = c.rolling(252, min_periods=1).min()
        ind["volatility_20"] = volatility_std(c)
        ind["obv"] = obv(c, v)
        ind["adx14"] = adx(df)
        ind["close"] = c
        ind["volume"] = v

        if incremental and last_date:
            ind = ind[ind.index > pd.to_datetime(last_date, utc=True)]
            if ind.empty:
                return symbol, True, "No new rows"

        bulk_upsert(symbol, ind)
        return symbol, True, f"{len(ind)} rows"

    except Exception as e:
        return symbol, False, str(e)

# ==============================
# ORCHESTRATOR
# ==============================

def run_indicators_etl_sync(incremental: bool = True):
    start = time.time()
    symbols = get_all_symbols_sync()
    print(f"[INFO] Running indicators ETL for {len(symbols)} symbols (incremental={incremental})")

    args = [(s, incremental) for s in symbols]
    results = []

    with Pool(POOL_SIZE) as pool:
        for i in range(0, len(args), BATCH_SYMBOLS):
            chunk = args[i:i+BATCH_SYMBOLS]
            chunk_res = pool.map(compute_symbol, chunk)
            results.extend(chunk_res)
            success = []
            skipped = []
            failed = []
            for symbol, ok, msg in results:
                if ok and "Skipped" in msg:
                    skipped.append((symbol, msg))
                elif ok:
                    success.append(symbol)
                else:
                    failed.append((symbol, msg))
            print(
                f"[INFO] Progress: {len(results)}/{len(symbols)} "
                f"(success={len(success)}, skipped={len(skipped)}, failed={len(failed)})"
            )

    success = []
    skipped = []
    failed = []
    for symbol, ok, msg in results:
        if ok and "Skipped" in msg:
            skipped.append((symbol, msg))
        elif ok:
            success.append(symbol)
        else:
            failed.append((symbol, msg))

    with open("failed_symbols.json", "w") as f:
        json.dump(failed, f, indent=2)

    print("\nSummary:")
    print(f"Success: {len(success)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print(f"\n[INFO] Time taken: {round(time.time() - start, 2)} sec")
    print("\n[INFO] Completed.")
    return results

# ==============================
# ENTRY POINT
# ==============================

if __name__ == "__main__":
    run_indicators_etl_sync(incremental=True)
