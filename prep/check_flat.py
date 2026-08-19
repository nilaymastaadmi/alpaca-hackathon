# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Read-only: confirm the practice account is flat and has no resting orders."""

import sys
from pathlib import Path

import requests

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
TRADE_API = "https://paper-api.alpaca.markets"

env = {}
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

h = {
    "APCA-API-KEY-ID": env["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": env["ALPACA_SECRET_KEY"],
}

pos = requests.get(f"{TRADE_API}/v2/positions", headers=h, timeout=20).json()
print(f"open positions: {len(pos)}")
for p in pos:
    print(f"  {p['symbol']}  qty={p['qty']}  mv={p.get('market_value')}  upl={p.get('unrealized_pl')}")

orders = requests.get(
    f"{TRADE_API}/v2/orders", headers=h, params={"status": "open", "limit": 50}, timeout=20
).json()
print(f"resting orders: {len(orders)}")
for o in orders:
    print(f"  {o['id'][:8]}  {o.get('order_class')}  {o['status']}  limit={o.get('limit_price')}")

acct = requests.get(f"{TRADE_API}/v2/account", headers=h, timeout=20).json()
print(f"\nequity      : {acct['equity']}")
print(f"cash        : {acct['cash']}")
print(f"last_equity : {acct['last_equity']}")
