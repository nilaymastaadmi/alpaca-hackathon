# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "requests"]
# ///
"""
READ-ONLY. How much history can we actually get? The backtest design depends
entirely on the answer, so settle it before writing the pre-registration.

Checks:
  1. How far back do Alpaca SPY daily bars go (realized-vol input)?
  2. Do historical option bars exist, and from when (would allow real-quote backtest)?
  3. Is CBOE's free VIX / VIX3M daily history reachable (implied-vol input, and
     the term-structure regime gate)? Alpaca index data 404s, so this is the
     fallback source.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

env = {}
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

KEY, SEC = env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"]

print("=== 1. SPY daily bar history depth ===")
sc = StockHistoricalDataClient(KEY, SEC)
for start in ("2010-01-01", "2016-01-01", "2020-01-01"):
    try:
        bars = sc.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols="SPY",
                timeframe=TimeFrame.Day,
                start=datetime.fromisoformat(start),
                end=datetime.fromisoformat("2026-08-01"),
            )
        ).data.get("SPY", [])
        if bars:
            print(f"  from {start}: {len(bars):>5} bars, first={bars[0].timestamp.date()}")
        else:
            print(f"  from {start}: 0 bars")
    except Exception as exc:
        print(f"  from {start}: ERROR {str(exc)[:160]}")

print("\n=== 2. Historical OPTION bars ===")
oc = OptionHistoricalDataClient(KEY, SEC)
# A contract that existed in the past; probe a few vintages.
for sym, start, end in (
    ("SPY240book", "2024-01-02", "2024-02-01"),  # deliberately bogus, shows error shape
    ("SPY250117C00600000", "2024-06-01", "2024-12-31"),
    ("SPY260320C00600000", "2026-01-02", "2026-03-01"),
):
    try:
        bars = oc.get_option_bars(
            OptionBarsRequest(
                symbol_or_symbols=sym,
                timeframe=TimeFrame.Day,
                start=datetime.fromisoformat(start),
                end=datetime.fromisoformat(end),
            )
        ).data.get(sym, [])
        if bars:
            print(f"  {sym}: {len(bars)} bars, {bars[0].timestamp.date()} -> {bars[-1].timestamp.date()}")
        else:
            print(f"  {sym}: 0 bars in {start}..{end}")
    except Exception as exc:
        print(f"  {sym}: ERROR {str(exc)[:160]}")

print("\n=== 3. CBOE VIX / VIX3M daily history (free, primary source) ===")
for name, url in (
    ("VIX", "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"),
    ("VIX3M", "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv"),
):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            lines = r.text.strip().splitlines()
            print(f"  {name:6}: HTTP 200, {len(lines)} rows")
            print(f"           header: {lines[0]}")
            print(f"           first : {lines[1]}")
            print(f"           last  : {lines[-1]}")
        else:
            print(f"  {name:6}: HTTP {r.status_code}")
    except Exception as exc:
        print(f"  {name:6}: ERROR {str(exc)[:160]}")
