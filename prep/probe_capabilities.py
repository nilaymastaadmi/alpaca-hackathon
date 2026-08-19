# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py"]
# ///
"""
READ-ONLY capability probe. Places no orders, changes no state.

Answers the four empirical unknowns the Track 2 plan depends on, so we find out
NOW rather than burning a build-week day on a wrong assumption:

  1. Is index data (SPX / VIX / VIX3M) actually available on this account?
     Alpaca's own index-options blog post said index market data was "coming in
     the coming months" -- if it is still missing, the VIX term-structure regime
     filter needs a fallback built from equity option chains instead.
  2. Are index option contracts (SPXW 0DTE, XSP) listed and tradeable?
     European-style + cash-settled removes early-assignment risk entirely.
  3. What does the market calendar actually say for the hackathon window?
     Confirms how many live trading days the agent really gets.
  4. THE BIG ONE: what does crossing the bid/ask on a 4-leg iron condor cost,
     as a percentage of the credit collected? propdesk R2/R3 died exactly here
     -- real gross edge, destroyed by transaction costs. Measure before building.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


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


def hdr(env):
    return {
        "APCA-API-KEY-ID": env["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": env["ALPACA_SECRET_KEY"],
    }


def probe_index_data(env):
    print("\n=== 1. INDEX DATA (SPX / VIX / VIX3M) ===")
    url = "https://data.alpaca.markets/v1beta1/indices/snapshots"
    for syms in ("SPX,VIX,VIX3M", "^SPX,^VIX", "I:SPX"):
        try:
            r = requests.get(url, headers=hdr(env), params={"symbols": syms}, timeout=20)
            print(f"  symbols={syms!r:20} -> HTTP {r.status_code}  {r.text[:220]}")
        except Exception as exc:
            print(f"  symbols={syms!r:20} -> ERROR {exc}")


def probe_index_contracts(env):
    print("\n=== 2. INDEX OPTION CONTRACTS (SPXW 0DTE / XSP) ===")
    url = "https://paper-api.alpaca.markets/v2/options/contracts"
    today = date.today()
    for root in ("SPXW", "SPX", "XSP", "VIX"):
        try:
            r = requests.get(
                url,
                headers=hdr(env),
                params={
                    "underlying_symbols": root,
                    "expiration_date_gte": today.isoformat(),
                    "expiration_date_lte": (today + timedelta(days=10)).isoformat(),
                    "limit": 3,
                },
                timeout=20,
            )
            if r.status_code == 200:
                contracts = r.json().get("option_contracts", [])
                print(f"  {root:6} -> HTTP 200, {len(contracts)} contract(s)")
                for c in contracts[:2]:
                    print(
                        f"           {c.get('symbol')}  exp={c.get('expiration_date')} "
                        f"strike={c.get('strike_price')} style={c.get('style')} "
                        f"tradable={c.get('tradable')}"
                    )
            else:
                print(f"  {root:6} -> HTTP {r.status_code}  {r.text[:180]}")
        except Exception as exc:
            print(f"  {root:6} -> ERROR {exc}")


def probe_calendar(env):
    print("\n=== 3. MARKET CALENDAR, HACKATHON WINDOW ===")
    url = "https://paper-api.alpaca.markets/v2/calendar"
    try:
        r = requests.get(
            url,
            headers=hdr(env),
            params={"start": "2026-08-28", "end": "2026-09-08"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}  {r.text[:200]}")
            return
        for d in r.json():
            print(f"  {d['date']}  open {d['open']}  close {d['close']}")
    except Exception as exc:
        print(f"  ERROR {exc}")


def probe_condor_cost(env):
    """The decisive test: credit collected vs cost of crossing 4 spreads."""
    print("\n=== 4. IRON CONDOR TRANSACTION COST (the propdesk test) ===")
    stock_client = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    option_client = OptionHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])

    for symbol in ("SPY", "QQQ"):
        try:
            spot = float(
                stock_client.get_stock_latest_trade(
                    StockLatestTradeRequest(symbol_or_symbols=symbol)
                )[symbol].price
            )
            today = date.today()
            chain = option_client.get_option_chain(
                OptionChainRequest(
                    underlying_symbol=symbol,
                    expiration_date_gte=today + timedelta(days=25),
                    expiration_date_lte=today + timedelta(days=45),
                    strike_price_gte=round(spot * 0.85, 2),
                    strike_price_lte=round(spot * 1.15, 2),
                )
            )

            # Collect quoted contracts with a usable two-sided market, keyed by
            # expiry -- a real iron condor is SAME-EXPIRY on all four legs.
            by_exp: dict[str, list] = {}
            for occ, snap in chain.items():
                q = getattr(snap, "latest_quote", None)
                if not q or not q.bid_price or not q.ask_price:
                    continue
                greeks = getattr(snap, "greeks", None)
                delta = getattr(greeks, "delta", None) if greeks else None
                if delta is None:
                    continue
                # OCC: ROOT + YYMMDD + C/P + strike(8)
                body = occ[len(symbol):]
                exp, cp = body[:6], body[6]
                by_exp.setdefault(exp, []).append(
                    {
                        "occ": occ,
                        "delta": delta,
                        "bid": float(q.bid_price),
                        "ask": float(q.ask_price),
                        "mid": (float(q.bid_price) + float(q.ask_price)) / 2,
                        "is_call": cp == "C",
                    }
                )

            if not by_exp:
                print(f"  {symbol}: no two-sided quotes returned (market likely closed)")
                continue

            # Use the expiry with the most quoted contracts -- the liquid one.
            exp = max(by_exp, key=lambda e: len(by_exp[e]))
            legs = by_exp[exp]
            print(f"  {symbol} (spot {spot:.2f}, single expiry 20{exp[:2]}-{exp[2:4]}-{exp[4:6]})")

            def nearest(target_delta, is_call):
                pool = [l for l in legs if l["is_call"] == is_call]
                if not pool:
                    return None
                return min(pool, key=lambda l: abs(l["delta"] - target_delta))

            # Classic ~16-delta short strikes, ~5-delta long wings.
            short_call = nearest(0.16, True)
            long_call = nearest(0.05, True)
            short_put = nearest(-0.16, False)
            long_put = nearest(-0.05, False)
            if not all((short_call, long_call, short_put, long_put)):
                print(f"  {symbol}: could not assemble 4 legs")
                continue

            # Credit at mid vs credit if we cross the spread on every leg.
            credit_mid = (
                short_call["mid"] + short_put["mid"] - long_call["mid"] - long_put["mid"]
            )
            credit_crossed = (
                short_call["bid"] + short_put["bid"] - long_call["ask"] - long_put["ask"]
            )
            spread_cost = credit_mid - credit_crossed
            pct = (spread_cost / credit_mid * 100) if credit_mid else float("nan")

            width_call = long_call["occ"], short_call["occ"]
            for name, leg in (
                ("short call", short_call),
                ("long call ", long_call),
                ("short put ", short_put),
                ("long put  ", long_put),
            ):
                width = leg["ask"] - leg["bid"]
                print(
                    f"    {name} {leg['occ']:22} d={leg['delta']:+.3f} "
                    f"bid={leg['bid']:.2f} ask={leg['ask']:.2f} spread={width:.2f}"
                )
            print(f"    credit @ mid            : ${credit_mid:.2f}")
            print(f"    credit @ crossing spread: ${credit_crossed:.2f}")
            print(f"    ONE-WAY spread cost     : ${spread_cost:.2f}  ({pct:.1f}% of mid credit)")
            print(f"    ROUND TRIP (in+out)     : ~{2 * pct:.1f}% of mid credit")
        except Exception as exc:
            print(f"  {symbol}: ERROR {exc}")


def main():
    env = load_env(ENV_PATH)
    print(f"probe run {datetime.now().isoformat(timespec='seconds')} -- READ ONLY, no orders")
    probe_index_data(env)
    probe_index_contracts(env)
    probe_calendar(env)
    probe_condor_cost(env)


if __name__ == "__main__":
    main()
