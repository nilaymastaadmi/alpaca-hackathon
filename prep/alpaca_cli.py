"""
Thin wrapper around Alpaca's official CLI, for READ-ONLY reporting.

Why this exists alongside the MCP client: the agent's every trading decision
goes through Alpaca's MCP server, and that stays true. The CLI is a second,
independent read path used only by reporting tools (the live-week results
page, the Friday flatten watch). Reading the account through a different
Alpaca surface than the one that wrote to it is a real check: if the ledger,
the MCP view and the CLI view ever disagreed, that is worth knowing before a
judge finds it.

Hard rule: nothing here places, cancels or modifies anything. The command
allowlist below is enforced, so a future edit cannot quietly turn this into
an execution path. Alpaca's own CLI README warns that its destructive
commands take no confirmation, which is exactly why this file refuses to
call them.

Credentials come from .env.live (gitignored) into the child process
environment only, and are never logged or printed.

    uv run python prep/alpaca_cli.py account get --quiet
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env.live"

# Where the binary usually lands. `alpaca` on PATH wins if present.
CANDIDATES = (
    Path(os.environ.get("ALPACA_CLI", "")) if os.environ.get("ALPACA_CLI") else None,
    Path.home() / ".local" / "bin" / "alpaca.exe",
    Path.home() / ".local" / "bin" / "alpaca",
)

# Read-only commands only. Anything not on this list is refused here, before
# it reaches the process.
ALLOWED = {
    ("account", "get"),
    ("account", "portfolio"),
    ("position", "list"),
    ("order", "list"),
    ("clock", "markets"),
    ("calendar", "market"),
    ("version",),
}


class CliUnavailable(RuntimeError):
    """The CLI is not installed, or has no credentials to use."""


def cli_path() -> Path:
    for c in CANDIDATES:
        if c and c.exists():
            return c
    from shutil import which
    found = which("alpaca")
    if found:
        return Path(found)
    raise CliUnavailable("alpaca CLI not found; install from "
                         "github.com/alpacahq/cli releases")


def _env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get("ALPACA_API_KEY") or not env.get("ALPACA_SECRET_KEY"):
        raise CliUnavailable("no Alpaca credentials for the CLI")
    # Belt and braces: the CLI treats env keys as paper unless this is set,
    # and it must never be set from here.
    env.pop("ALPACA_LIVE_TRADE", None)
    return env


def run(*args: str, timeout: int = 90) -> dict | list:
    """Run one allowlisted read-only command and return its parsed JSON."""
    # The command path is the leading words before the first flag. Filtering
    # every non-dash token instead would fold flag VALUES into the key
    # ("--period 1W" -> ... "1W"), which made the allowlist reject its own
    # commands the first time this ran.
    key: tuple[str, ...] = ()
    for a in args:
        if a.startswith("-"):
            break
        key += (a,)
    if key not in ALLOWED:
        raise ValueError(f"refusing to run non-allowlisted command: {' '.join(args)}")
    proc = subprocess.run([str(cli_path()), *args], capture_output=True,
                          text=True, env=_env(), timeout=timeout)
    if proc.returncode != 0:
        # stderr can echo a bad key back; truncate hard and never log it.
        raise CliUnavailable(f"alpaca {' '.join(args)} exited "
                             f"{proc.returncode}")
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out[:2000]}


def version() -> str:
    proc = subprocess.run([str(cli_path()), "version"], capture_output=True,
                          text=True, timeout=30)
    return proc.stdout.strip() or "unknown"


def snapshot() -> dict:
    """Account, positions and portfolio history, or a reason it is missing."""
    try:
        acct = run("account", "get", "--quiet")
        pos = run("position", "list")
        hist = run("account", "portfolio", "--period", "1W", "--timeframe", "1D")
        return {"ok": True, "cli_version": version(), "account": acct,
                "positions": pos, "portfolio_history": hist}
    except (CliUnavailable, subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(run(*sys.argv[1:]), indent=1)[:4000])
    else:
        snap = snapshot()
        if snap["ok"]:
            a = snap["account"]
            print(f"cli {snap['cli_version']}  account {a.get('account_number')}  "
                  f"equity {a.get('equity')}  positions {len(snap['positions'])}")
        else:
            print("CLI unavailable:", snap["reason"])
