# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "tzdata"]
# ///
"""
Supervisor for the live week. Runs agent cycles on an interval and survives the
failure that is most likely to cost us the whole window.

## The failure this exists for

US market hours are 19:00 to 01:30 IST, so the agent runs unattended overnight
for five straight nights. `propdesk` documented what happens when the laptop
sleeps mid-request, with numbers:

  "Sleeping the laptop hangs in-flight HTTP permanently. Threads block inside
   the client's own session, which socket.setdefaulttimeout does not reach.
   Observed twice, 11.5h and 4.8h of a live process producing nothing."

A hung agent does not crash. It sits there looking alive while the trading
window passes, and you find out the next morning. That is the single most likely
way the live week produces zero trades, and no amount of strategy work protects
against it.

## How it survives that

Every cycle runs in a SEPARATE SUBPROCESS with a hard timeout. A timeout is
enforced by the OS killing the child, so it works even when the child is blocked
inside a socket that no Python-level timeout can reach. That is the whole point:
an in-process timer cannot rescue a thread stuck in a syscall, but killing the
process can.

propdesk's other lesson applies too: "pkill reported success while leaving
wrapper loops alive that respawned workers. Always verify a kill rather than
trusting its exit code." So kills are verified, not assumed.

Run:
  uv run agent/watchdog.py --dry-run            supervise, place nothing
  uv run agent/watchdog.py --publish            live, publish artifacts each cycle
  uv run agent/watchdog.py --interval 300       cycle every 5 minutes
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

AGENT = Path(__file__).resolve().parent / "agent.py"
REPO = Path(__file__).resolve().parent.parent
HEARTBEAT = REPO / "artifacts" / "watchdog.json"

DEFAULT_INTERVAL = 300          # 5 minutes between cycles
DEFAULT_TIMEOUT = 240           # a cycle taking over 4 minutes is hung
MAX_CONSECUTIVE_FAILURES = 5


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_heartbeat(state: dict) -> None:
    """
    A file the operator (or the dashboard) can look at to see the supervisor is
    alive. A supervisor with no external evidence of life has the same problem
    as the agent it supervises.
    """
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    HEARTBEAT.write_text(json.dumps(state, indent=2), encoding="utf-8")


def kill_verified(proc: subprocess.Popen, grace: float = 10.0) -> str:
    """
    Terminate, then kill, then CONFIRM the process is gone.

    propdesk lost most of a day to a kill that reported success while workers
    stayed alive. Returning the verified outcome rather than assuming it is the
    entire lesson.
    """
    if proc.poll() is not None:
        return "already_exited"
    try:
        proc.terminate()
        proc.wait(timeout=grace)
        return "terminated"
    except subprocess.TimeoutExpired:
        pass
    try:
        proc.kill()
        proc.wait(timeout=grace)
        return "killed"
    except subprocess.TimeoutExpired:
        return "UNKILLABLE"          # surfaced loudly; do not pretend otherwise


def run_cycle(dry_run: bool, publish: bool, timeout: int,
             env_file: str | None = None) -> dict:
    """One agent cycle in its own process, with an OS-enforced timeout."""
    cmd = [
        "uv", "run", "--with", "requests", "--with", "tzdata",
        "python", str(AGENT), "--once",
    ]
    if dry_run:
        cmd.append("--dry-run")
    if publish:
        cmd.append("--publish")
    if env_file:
        cmd += ["--env-file", env_file]

    started = time.time()
    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace",
                            creationflags=creation)
    try:
        out, _ = proc.communicate(timeout=timeout)
        elapsed = time.time() - started
        return {
            "ok": proc.returncode == 0,
            "outcome": "completed" if proc.returncode == 0 else "nonzero_exit",
            "returncode": proc.returncode,
            "elapsed_s": round(elapsed, 1),
            "tail": (out or "").strip().splitlines()[-25:],
        }
    except subprocess.TimeoutExpired:
        # THE case this file exists for. The child is wedged, very likely inside
        # a socket that no in-process timeout can reach. Only the OS can help.
        disposition = kill_verified(proc)
        try:
            out, _ = proc.communicate(timeout=5)
        except Exception:                        # noqa: BLE001
            out = ""
        return {
            "ok": False,
            "outcome": "TIMEOUT_KILLED",
            "kill_disposition": disposition,
            "elapsed_s": round(time.time() - started, 1),
            "timeout_s": timeout,
            "tail": (out or "").strip().splitlines()[-25:],
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                    help="seconds between cycle starts")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="kill a cycle that exceeds this many seconds")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true",
                    help="commit and push artifacts each cycle")
    ap.add_argument("--env-file", type=str, default=None,
                    help="passed through to each agent.py cycle. Defaults to "
                         ".env (practice account); the live submission "
                         "account's credentials belong in .env.live.")
    ap.add_argument("--max-cycles", type=int, default=0,
                    help="stop after N cycles; 0 means run until stopped")
    args = ap.parse_args()

    if args.timeout >= args.interval:
        # Otherwise a hung cycle is still being killed when the next should start,
        # and cycles pile up on top of each other.
        print(f"timeout ({args.timeout}s) must be less than interval "
              f"({args.interval}s)", file=sys.stderr)
        sys.exit(2)

    print(f"watchdog up {now()}")
    print(f"  interval {args.interval}s, cycle timeout {args.timeout}s, "
          f"dry_run={args.dry_run}, publish={args.publish}")
    print(f"  heartbeat -> {HEARTBEAT}")

    stats = {"cycles": 0, "completed": 0, "timeouts": 0, "failures": 0}
    consecutive = 0
    stop = False

    def handle_signal(signum, _frame):
        nonlocal stop
        print(f"\nsignal {signum} received, finishing current cycle then stopping")
        stop = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except (ValueError, OSError):
            pass

    while not stop:
        cycle_started = time.time()
        stats["cycles"] += 1
        res = run_cycle(args.dry_run, args.publish, args.timeout, args.env_file)

        if res["outcome"] == "completed":
            stats["completed"] += 1
            consecutive = 0
        elif res["outcome"] == "TIMEOUT_KILLED":
            stats["timeouts"] += 1
            consecutive += 1
        else:
            stats["failures"] += 1
            consecutive += 1

        line = (f"[{now()}] cycle {stats['cycles']}: {res['outcome']} "
                f"in {res['elapsed_s']}s")
        if res["outcome"] != "completed":
            line += f"  (consecutive failures: {consecutive})"
        print(line)
        for t in res.get("tail", [])[-4:]:
            print(f"    | {t}")

        write_heartbeat({
            "alive": True, "stats": stats, "consecutive_failures": consecutive,
            "last_cycle": res,
            "config": {"interval_s": args.interval, "timeout_s": args.timeout,
                       "dry_run": args.dry_run, "publish": args.publish},
        })

        if consecutive >= MAX_CONSECUTIVE_FAILURES:
            # Keep supervising rather than exiting. Exiting on a transient
            # network outage would turn a recoverable problem into a dead night.
            print(f"  WARNING: {consecutive} consecutive failures. Still "
                  f"supervising, but something is wrong. Check the tail above.")

        if args.max_cycles and stats["cycles"] >= args.max_cycles:
            break

        sleep_for = max(args.interval - (time.time() - cycle_started), 1.0)
        # Sleep in short slices so a stop signal is honoured promptly rather
        # than after a full interval.
        deadline = time.time() + sleep_for
        while time.time() < deadline and not stop:
            time.sleep(min(2.0, deadline - time.time()))

    write_heartbeat({"alive": False, "stats": stats, "stopped_at": now()})
    print(f"\nwatchdog stopped. {json.dumps(stats)}")


if __name__ == "__main__":
    main()
