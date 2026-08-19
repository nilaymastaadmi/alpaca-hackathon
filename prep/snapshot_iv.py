# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py"]
# ///
"""
Daily IV/greeks snapshot logger for the Alpaca AI Trading Agents Hackathon prep.

Why this exists: Alpaca's option chain snapshot only exposes CURRENT implied
volatility, not a trailing history, but the locked strategy (Track 2 --
IV-rank-gated iron condors) needs IV rank, which requires a history to rank
against. Running this daily from 2026-08-19 through kickoff (2026-08-28)
builds ~9 days of real history before the build week even starts.

Runs against the PRACTICE account only (keys in .env). Never touches the
fresh submission account. Safe to re-run; each run just appends a new
dated snapshot to the log.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = Path(__file__).resolve().parent / "iv_history.jsonl"

# Liquid, options-friendly underlyings -- tight spreads, real open interest
# across strikes, good candidates for defined-risk premium selling.
UNIVERSE = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMD", "MSFT"]

# Classic iron-condor DTE window and a wide-enough strike band to capture
# both the short legs (near ATM-ish) and the long wings.
DTE_MIN, DTE_MAX = 21, 45
STRIKE_BAND = 0.15  # +/- 15% around spot


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        sys.exit(f"missing .env at {path}")
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def main() -> None:
    env = load_env(ENV_PATH)
    api_key = env.get("ALPACA_API_KEY")
    secret_key = env.get("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        sys.exit("ALPACA_API_KEY / ALPACA_SECRET_KEY missing from .env")

    stock_client = StockHistoricalDataClient(api_key, secret_key)
    option_client = OptionHistoricalDataClient(api_key, secret_key)

    today = date.today()
    exp_gte = today + timedelta(days=DTE_MIN)
    exp_lte = today + timedelta(days=DTE_MAX)

    rows = []
    errors = []

    for symbol in UNIVERSE:
        try:
            trade_req = StockLatestTradeRequest(symbol_or_symbols=symbol)
            latest = stock_client.get_stock_latest_trade(trade_req)[symbol]
            spot = float(latest.price)

            strike_lo = round(spot * (1 - STRIKE_BAND), 2)
            strike_hi = round(spot * (1 + STRIKE_BAND), 2)

            chain_req = OptionChainRequest(
                underlying_symbol=symbol,
                expiration_date_gte=exp_gte,
                expiration_date_lte=exp_lte,
                strike_price_gte=strike_lo,
                strike_price_lte=strike_hi,
            )
            chain = option_client.get_option_chain(chain_req)

            for occ_symbol, snap in chain.items():
                iv = getattr(snap, "implied_volatility", None)
                greeks = getattr(snap, "greeks", None)
                if iv is None and greeks is None:
                    continue
                rows.append(
                    {
                        "date": today.isoformat(),
                        "underlying": symbol,
                        "underlying_price": spot,
                        "occ_symbol": occ_symbol,
                        "implied_volatility": iv,
                        "delta": getattr(greeks, "delta", None) if greeks else None,
                        "gamma": getattr(greeks, "gamma", None) if greeks else None,
                        "theta": getattr(greeks, "theta", None) if greeks else None,
                        "vega": getattr(greeks, "vega", None) if greeks else None,
                    }
                )
        except Exception as exc:  # noqa: BLE001 -- log and keep going per symbol
            errors.append(f"{symbol}: {exc}")

    with LOG_PATH.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    stamp = datetime.now().isoformat(timespec="seconds")
    print(f"[{stamp}] logged {len(rows)} contract snapshots across {len(UNIVERSE)} underlyings")
    if errors:
        print(f"[{stamp}] {len(errors)} symbol errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
