# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""
READ-ONLY. Can this machine, on this connection, do anything resembling HFT
against Alpaca? Measure rather than assume.

HFT is a latency and queue-position business. The relevant questions are:
  1. What is the round trip to Alpaca's trading and data endpoints from here?
  2. How much does that vary (jitter matters more than the mean for HFT)?
  3. What do the rate limit headers actually permit?

If round trips are in the hundreds of milliseconds, every strategy whose edge
lives inside a second is unreachable, and no amount of clever code fixes it.
"""

import statistics
import sys
import time
from pathlib import Path

import requests

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

env = {}
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

H = {
    "APCA-API-KEY-ID": env["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": env["ALPACA_SECRET_KEY"],
}

ENDPOINTS = [
    ("trading  /v2/clock", "https://paper-api.alpaca.markets/v2/clock", {}),
    ("trading  /v2/account", "https://paper-api.alpaca.markets/v2/account", {}),
    ("data     stock quote", "https://data.alpaca.markets/v2/stocks/SPY/quotes/latest", {}),
    ("data     option snap",
     "https://data.alpaca.markets/v1beta1/options/snapshots/SPY",
     {"limit": "10"}),
]

N = 15
print(f"measuring {N} round trips per endpoint, sequential, warm connection\n")
session = requests.Session()

results = {}
for label, url, params in ENDPOINTS:
    times = []
    last_headers = {}
    for i in range(N):
        t0 = time.perf_counter()
        try:
            r = session.get(url, headers=H, params=params, timeout=30)
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code == 200:
                times.append(dt)
                last_headers = r.headers
        except Exception as exc:
            print(f"  {label}: ERROR {str(exc)[:80]}")
            break
        time.sleep(0.05)

    if not times:
        print(f"{label:24} no successful calls")
        continue

    results[label] = times
    print(f"{label:24} n={len(times):>3}  "
          f"min={min(times):7.1f}ms  median={statistics.median(times):7.1f}ms  "
          f"max={max(times):7.1f}ms  jitter(sd)={statistics.pstdev(times):6.1f}ms")

    for hk in ("X-Ratelimit-Limit", "X-Ratelimit-Remaining", "X-Ratelimit-Reset"):
        if hk in last_headers:
            print(f"{'':24}   {hk}: {last_headers[hk]}")

print("\n" + "=" * 72)
if results:
    all_med = statistics.median([statistics.median(v) for v in results.values()])
    print(f"typical round trip: {all_med:.0f} ms")
    print(f"\nFor scale:")
    print(f"  professional HFT colocation : 0.001 to 0.1 ms")
    print(f"  retail 'fast' algo trading  : 10 to 50 ms")
    print(f"  this machine                : {all_med:.0f} ms")
    print(f"\n  round trips available per second: {1000 / all_med:.1f}")
    print(f"  round trips in a 4.5 day window : "
          f"{(1000 / all_med) * 6.5 * 3600 * 4.5:,.0f} theoretical max")
    if all_med > 50:
        print(f"\n  VERDICT: {all_med:.0f} ms rules out any strategy whose edge lives")
        print(f"  inside a second. By the time an order arrives, the opportunity that")
        print(f"  triggered it is {all_med:.0f} ms old and has been taken by someone")
        print(f"  co-located. This is a physics problem, not a code problem.")
