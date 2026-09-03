"""
Friday flatten watch: an independent witness to the deadline close.

The agent flattens the book in the 90 minutes before the 11:00 ET submission
deadline, and writes its own artifacts while doing it. Those artifacts are
written by the same process that places the orders. This watcher is the
second pair of eyes: it polls the broker through Alpaca's CLI, a different
surface from the MCP path the agent trades on, and records what the account
actually shows, minute by minute, whatever the agent believes.

It never places or cancels anything. It cannot: every call goes through
prep/alpaca_cli.py, whose allowlist contains only read commands.

    uv run python prep/flatten_watch.py                  # until 11:05 ET
    uv run python prep/flatten_watch.py --minutes 30     # or a fixed span
    uv run python prep/flatten_watch.py --interval 30

Output: prep/flatten_watch.log (gitignored, local evidence for the writeup
and the video) plus a line per poll on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "prep" / "flatten_watch.log"
sys.path.insert(0, str(ROOT / "prep"))

import alpaca_cli  # noqa: E402

ET = timezone(timedelta(hours=-4))          # ET in September, no DST change
DEADLINE = datetime(2026, 9, 4, 11, 0, tzinfo=ET)


def log(msg: str) -> None:
    line = f"{datetime.now(ET).isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def poll() -> str:
    try:
        acct = alpaca_cli.run("account", "get", "--quiet")
        pos = alpaca_cli.run("position", "list")
        orders = alpaca_cli.run("order", "list", "--status", "open")
    except Exception as exc:                              # noqa: BLE001
        return f"READ FAILED {type(exc).__name__}: {str(exc)[:120]}"
    legs = len(pos or [])
    unreal = sum(float(p.get("unrealized_pl") or 0) for p in (pos or []))
    n_open_orders = len(orders or []) if isinstance(orders, list) else 0
    return (f"equity {float(acct.get('equity', 0)):,.2f}  legs {legs}  "
            f"unrealised {unreal:+,.2f}  resting orders {n_open_orders}"
            + ("  FLAT" if legs == 0 else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="seconds between polls")
    ap.add_argument("--minutes", type=int, default=0,
                    help="run this long; default is until 5 minutes past the deadline")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    if args.once:
        log(poll())
        return 0

    end = (datetime.now(ET) + timedelta(minutes=args.minutes)) if args.minutes \
        else (DEADLINE + timedelta(minutes=5))
    log(f"flatten watch up, polling every {args.interval}s until "
        f"{end.isoformat(timespec='minutes')} ET (deadline "
        f"{DEADLINE.isoformat(timespec='minutes')} ET). Read-only.")

    was_flat = False
    while datetime.now(ET) < end:
        line = poll()
        log(line)
        if "FLAT" in line and not was_flat:
            log("book is flat: every position closed, P&L is realised from here")
            was_flat = True
        time.sleep(max(args.interval, 5))
    log("flatten watch done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
