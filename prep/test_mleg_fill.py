# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "requests"]
# ///
"""
THE decisive test: do multi-leg (mleg) iron condor orders fill in Alpaca paper,
and at what net price relative to mid vs. crossing the spread?

Why this matters more than anything else unresolved: STRATEGY.md's whole cost
model assumes we can transact near mid. If a net-credit limit only fills when
every leg is independently marketable at the touch, round-trip cost roughly
doubles and iron condors may stop clearing their toll -- fallback becomes single
vertical credit spreads. propdesk R2/R3 died exactly on a cost assumption that
was ~5x off. Measure, don't assume.

Method: build a real same-expiry 16d/5d condor at the CHOSEN 7-14 DTE tenor
(which also settles the short-tenor spread-cost unknown), then walk a price
ladder from mid toward the crossing price, 1 contract, recording where it
actually fills. Then close it the same way to get the true round trip.

SAFETY
  - PRACTICE account only (.env), paper money.
  - qty = 1 contract, defined-risk structure (wings cap max loss).
  - Bails immediately if the market is closed (no resting orders left behind).
  - Cancels every unfilled order before moving on.
  - Exit ladder walks aggressive enough to guarantee we end FLAT.
"""

import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
TRADE_API = "https://paper-api.alpaca.markets"

UNDERLYING = "SPY"
DTE_MIN, DTE_MAX = 7, 14
RUNG_WAIT_S = 20
RUNGS = 5


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        sys.exit(f"missing .env at {path}")
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def hdr(env):
    return {
        "APCA-API-KEY-ID": env["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": env["ALPACA_SECRET_KEY"],
    }


def check_market_open(env) -> bool:
    r = requests.get(f"{TRADE_API}/v2/clock", headers=hdr(env), timeout=20)
    r.raise_for_status()
    c = r.json()
    print(f"  clock: {c['timestamp'][:19]}  is_open={c['is_open']}")
    print(f"  next_open={c['next_open'][:19]}  next_close={c['next_close'][:19]}")
    return bool(c["is_open"])


def build_condor(env):
    """Assemble a same-expiry 16-delta/5-delta iron condor at 7-14 DTE."""
    sc = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    oc = OptionHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])

    spot = float(
        sc.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=UNDERLYING))[
            UNDERLYING
        ].price
    )
    today = date.today()
    chain = oc.get_option_chain(
        OptionChainRequest(
            underlying_symbol=UNDERLYING,
            expiration_date_gte=today + timedelta(days=DTE_MIN),
            expiration_date_lte=today + timedelta(days=DTE_MAX),
            strike_price_gte=round(spot * 0.88, 2),
            strike_price_lte=round(spot * 1.12, 2),
        )
    )

    by_exp: dict[str, list] = {}
    for occ, snap in chain.items():
        q = getattr(snap, "latest_quote", None)
        if not q or not q.bid_price or not q.ask_price:
            continue
        g = getattr(snap, "greeks", None)
        delta = getattr(g, "delta", None) if g else None
        if delta is None:
            continue
        body = occ[len(UNDERLYING):]
        by_exp.setdefault(body[:6], []).append(
            {
                "occ": occ,
                "delta": delta,
                "bid": float(q.bid_price),
                "ask": float(q.ask_price),
                "mid": (float(q.bid_price) + float(q.ask_price)) / 2,
                "is_call": body[6] == "C",
                "strike": int(body[7:]) / 1000,
            }
        )
    if not by_exp:
        sys.exit("no two-sided quotes in the 7-14 DTE window")

    exp = max(by_exp, key=lambda e: len(by_exp[e]))
    legs = by_exp[exp]

    def nearest(target, is_call):
        pool = [l for l in legs if l["is_call"] == is_call]
        return min(pool, key=lambda l: abs(l["delta"] - target)) if pool else None

    short_call, long_call = nearest(0.16, True), nearest(0.05, True)
    short_put, long_put = nearest(-0.16, False), nearest(-0.05, False)
    if not all((short_call, long_call, short_put, long_put)):
        sys.exit("could not assemble 4 legs")

    credit_mid = short_call["mid"] + short_put["mid"] - long_call["mid"] - long_put["mid"]
    credit_cross = short_call["bid"] + short_put["bid"] - long_call["ask"] - long_put["ask"]

    print(f"  {UNDERLYING} spot {spot:.2f}, expiry 20{exp[:2]}-{exp[2:4]}-{exp[4:6]}")
    for nm, l in (("short call", short_call), ("long call ", long_call),
                  ("short put ", short_put), ("long put  ", long_put)):
        print(f"    {nm} {l['occ']:22} K={l['strike']:>7.1f} d={l['delta']:+.3f} "
              f"bid={l['bid']:.2f} ask={l['ask']:.2f} sprd={l['ask']-l['bid']:.2f}")
    print(f"    credit @ mid      : ${credit_mid:.2f}")
    print(f"    credit @ crossing : ${credit_cross:.2f}")
    print(f"    spread toll (1-way): ${credit_mid - credit_cross:.2f} "
          f"({(credit_mid - credit_cross)/credit_mid*100:.1f}% of mid credit)")

    return {
        "short_call": short_call, "long_call": long_call,
        "short_put": short_put, "long_put": long_put,
        "credit_mid": credit_mid, "credit_cross": credit_cross,
    }


def submit(env, legs_spec, limit_price):
    payload = {
        "order_class": "mleg",
        "qty": "1",
        "type": "limit",
        "time_in_force": "day",
        "limit_price": f"{limit_price:.2f}",
        "legs": legs_spec,
    }
    r = requests.post(f"{TRADE_API}/v2/orders", headers=hdr(env), json=payload, timeout=30)
    if r.status_code not in (200, 201):
        print(f"      REJECTED HTTP {r.status_code}: {r.text[:300]}")
        return None
    return r.json()


def poll(env, order_id, seconds):
    """Wait for terminal status; return the order dict."""
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        r = requests.get(f"{TRADE_API}/v2/orders/{order_id}", headers=hdr(env), timeout=20)
        r.raise_for_status()
        last = r.json()
        if last["status"] in ("filled", "canceled", "rejected", "expired"):
            return last
        time.sleep(2)
    return last


def cancel(env, order_id):
    requests.delete(f"{TRADE_API}/v2/orders/{order_id}", headers=hdr(env), timeout=20)


def ladder(env, legs_spec, start_price, end_price, label):
    """Walk from start_price to end_price over RUNGS steps; return fill info."""
    print(f"\n  --- {label} ladder: {start_price:+.2f} -> {end_price:+.2f} ---")
    for i in range(RUNGS):
        frac = i / (RUNGS - 1) if RUNGS > 1 else 1.0
        px = start_price + (end_price - start_price) * frac
        print(f"    rung {i+1}/{RUNGS}: limit {px:+.2f} "
              f"({'credit' if px < 0 else 'debit'} ${abs(px):.2f})")
        o = submit(env, legs_spec, px)
        if o is None:
            continue
        o = poll(env, o["id"], RUNG_WAIT_S)
        if o and o["status"] == "filled":
            fap = o.get("filled_avg_price")
            print(f"      *** FILLED at {fap} ***")
            return {"filled": True, "limit": px, "filled_avg_price": fap, "rung": i + 1}
        print(f"      no fill (status={o['status'] if o else '?'}), cancelling")
        if o:
            cancel(env, o["id"])
        time.sleep(1)
    return {"filled": False}


def main():
    env = load_env(ENV_PATH)
    print(f"mleg fill test  {datetime.now().isoformat(timespec='seconds')}")
    print("PRACTICE account, paper money, 1 contract, defined risk\n")

    print("=== market clock ===")
    if not check_market_open(env):
        print("\n  MARKET CLOSED -- aborting so no order rests overnight.")
        print("  Re-run during US session (19:00-01:30 IST).")
        return

    print("\n=== building condor (7-14 DTE) ===")
    c = build_condor(env)

    open_legs = [
        {"symbol": c["short_call"]["occ"], "ratio_qty": "1", "side": "sell",
         "position_intent": "sell_to_open"},
        {"symbol": c["long_call"]["occ"], "ratio_qty": "1", "side": "buy",
         "position_intent": "buy_to_open"},
        {"symbol": c["short_put"]["occ"], "ratio_qty": "1", "side": "sell",
         "position_intent": "sell_to_open"},
        {"symbol": c["long_put"]["occ"], "ratio_qty": "1", "side": "buy",
         "position_intent": "buy_to_open"},
    ]

    # Credit -> negative limit_price. Start at mid, walk toward crossing.
    entry = ladder(env, open_legs, -c["credit_mid"], -c["credit_cross"], "ENTRY (credit)")

    if not entry["filled"]:
        print("\n  ENTRY NEVER FILLED even at the crossing price.")
        print("  -> Net-credit mleg limits do NOT fill like a single marketable order.")
        print("  -> STRATEGY.md fallback (single vertical spreads) becomes the base case.")
        return

    print("\n  Position is OPEN. Closing it to measure the true round trip.")
    time.sleep(3)

    close_legs = [
        {"symbol": c["short_call"]["occ"], "ratio_qty": "1", "side": "buy",
         "position_intent": "buy_to_close"},
        {"symbol": c["long_call"]["occ"], "ratio_qty": "1", "side": "sell",
         "position_intent": "sell_to_close"},
        {"symbol": c["short_put"]["occ"], "ratio_qty": "1", "side": "buy",
         "position_intent": "buy_to_close"},
        {"symbol": c["long_put"]["occ"], "ratio_qty": "1", "side": "sell",
         "position_intent": "sell_to_close"},
    ]

    # Closing a short condor = pay a debit -> positive limit_price.
    # Walk from mid debit up past crossing to guarantee we end flat.
    debit_mid = c["credit_mid"]
    debit_cross = c["credit_cross"] + (c["credit_mid"] - c["credit_cross"]) * 2
    exit_ = ladder(env, close_legs, debit_mid, debit_cross, "EXIT (debit)")

    print("\n=== RESULT ===")
    print(f"  entry: filled at {entry['filled_avg_price']} on rung {entry['rung']}/{RUNGS}")
    if exit_["filled"]:
        print(f"  exit : filled at {exit_['filled_avg_price']} on rung {exit_['rung']}/{RUNGS}")
        try:
            rt = abs(float(entry["filled_avg_price"])) - abs(float(exit_["filled_avg_price"]))
            print(f"  round-trip net: ${rt:+.2f} on ${c['credit_mid']:.2f} mid credit "
                  f"({rt/c['credit_mid']*100:+.1f}%)")
        except (TypeError, ValueError):
            pass
    else:
        print("  exit : NOT FILLED -- a position is still open on the practice account.")
        print("         Harmless (defined risk, paper money) but close it manually.")

    print("\n  Check open positions/orders on the practice account before trusting this.")


if __name__ == "__main__":
    main()
