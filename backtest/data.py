"""
Data loading for R1, with two guards the pre-registration requires.

Guard 1, the SEAL. The holdout window (2023-01-01 onward) cannot be loaded
without an explicit unseal call that writes an auditable record to disk. Section
10 of the pre-registration allows exactly one holdout shot, and only after a
development trial clears its bar. Enforcing that in code rather than in memory
is the point: a future session cannot quietly peek.

Guard 2, the STALE GATE. propdesk R1 reported a hypothesis as failed when the
underlying data was broken (one index quoted its open as exactly the prior close
on 99.0% of rows, making overnight return zero by construction). Any series
failing this check is declared UNUSABLE so the dependent hypothesis is reported
untestable rather than false.
"""

from __future__ import annotations

import io
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(__file__).resolve().parent / "cache"
SEAL_LOG = Path(__file__).resolve().parent / "HOLDOUT_SEAL.log"
ENV_PATH = PROJECT_ROOT / ".env"

# Fixed by pre-registration section 2. Do not edit these to fit a result.
DEV_START = "2016-01-04"
DEV_END = "2022-12-31"
HOLDOUT_START = "2023-01-01"
HOLDOUT_END = "2026-08-18"

CBOE_URLS = {
    "VIX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
    "VIX3M": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv",
}

STALE_THRESHOLD = 0.05  # >5% of rows with open == prior close means unusable


class HoldoutSealError(RuntimeError):
    """Raised when holdout data is requested without an explicit unseal."""


@dataclass
class StaleReport:
    series: str
    rows: int
    stale_rows: int

    @property
    def stale_fraction(self) -> float:
        return self.stale_rows / self.rows if self.rows else 0.0

    @property
    def usable(self) -> bool:
        return self.stale_fraction <= STALE_THRESHOLD

    def describe(self) -> str:
        verdict = "USABLE" if self.usable else "UNUSABLE"
        return (
            f"{self.series}: {self.stale_rows}/{self.rows} rows stale "
            f"({self.stale_fraction * 100:.1f}%), {verdict}"
        )


def _load_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        sys.exit(f"missing .env at {ENV_PATH}")
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.csv"


def fetch_spy(refresh: bool = False) -> pd.DataFrame:
    """SPY daily bars from Alpaca, cached. Full range; windowing happens later."""
    cache = _cache_path("spy_daily")
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["date"])
        return df.set_index("date").sort_index()

    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    env = _load_env()
    client = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    bars = client.get_stock_bars(
        StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=datetime(2016, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 8, 19, tzinfo=timezone.utc),
        )
    ).data.get("SPY", [])
    if not bars:
        sys.exit("Alpaca returned no SPY bars")

    df = pd.DataFrame(
        [
            {
                "date": b.timestamp.date(),
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume),
            }
            for b in bars
        ]
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df.to_csv(cache)
    return df


def fetch_cboe(series: str, refresh: bool = False) -> pd.DataFrame:
    """VIX or VIX3M daily OHLC from CBOE directly, the primary source."""
    cache = _cache_path(series.lower())
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["date"])
        return df.set_index("date").sort_index()

    r = requests.get(CBOE_URLS[series], timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
    df = df[["date", "open", "high", "low", "close"]].set_index("date").sort_index()
    df.to_csv(cache)
    return df


def stale_check(df: pd.DataFrame, name: str) -> StaleReport:
    """Pre-registration section 1: open == prior close on >5% of rows is unusable."""
    prior_close = df["close"].shift(1)
    stale = (df["open"] - prior_close).abs() < 1e-9
    stale = stale.iloc[1:]  # first row has no prior close
    return StaleReport(series=name, rows=int(stale.size), stale_rows=int(stale.sum()))


def unseal_holdout(reason: str) -> None:
    """
    Deliberately open the sealed holdout. Writes an append-only record.

    Pre-registration section 10 permits ONE holdout evaluation, only after a
    development trial clears the 0.76 bar. Calling this is a research event and
    is meant to leave a permanent mark.
    """
    SEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "unsealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": reason,
    }
    with SEAL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    os.environ["R1_HOLDOUT_UNSEALED"] = "1"


def holdout_is_sealed() -> bool:
    return os.environ.get("R1_HOLDOUT_UNSEALED") != "1"


def window(df: pd.DataFrame, which: str) -> pd.DataFrame:
    """
    Slice to 'dev' or 'holdout'. Requesting holdout while sealed raises.
    """
    if which == "dev":
        return df.loc[DEV_START:DEV_END]
    if which == "holdout":
        if holdout_is_sealed():
            raise HoldoutSealError(
                "Holdout is SEALED. Pre-registration section 10 allows one shot, "
                "only after a development trial clears Sharpe 0.76. "
                "Call unseal_holdout(reason=...) deliberately if that has happened."
            )
        return df.loc[HOLDOUT_START:HOLDOUT_END]
    raise ValueError(f"unknown window {which!r}, expected 'dev' or 'holdout'")


def load_all(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Load every series, run the stale gate, and report before any analysis."""
    out = {
        "SPY": fetch_spy(refresh=refresh),
        "VIX": fetch_cboe("VIX", refresh=refresh),
        "VIX3M": fetch_cboe("VIX3M", refresh=refresh),
    }
    print("data loaded:")
    for name, df in out.items():
        print(f"  {name:6} {len(df):>5} rows  {df.index.min().date()} to {df.index.max().date()}")
    print("\nstale gate (pre-registration section 1):")
    for name, df in out.items():
        rep = stale_check(df, name)
        print(f"  {rep.describe()}")
        if not rep.usable:
            print(f"  WARNING: {name} fails the stale gate. Any hypothesis "
                  f"depending on it must be reported UNTESTABLE, not false.")
    return out
