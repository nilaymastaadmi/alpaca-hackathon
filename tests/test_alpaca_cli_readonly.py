"""
The CLI wrapper must stay a read path, permanently.

Alpaca's own CLI README warns that its destructive commands take no
confirmation: `position close-all` liquidates the portfolio, `order
cancel-all` cancels everything without listing it first. This project uses
the CLI only to READ the account back through a different surface than the
MCP path that trades on it. These tests are what stops a later edit from
quietly widening that.

No network and no credentials: every test here refuses before a process
would be started.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "prep"))

import alpaca_cli as C  # noqa: E402


DESTRUCTIVE = [
    ("order", "submit", "--symbol", "SPY", "--side", "buy"),
    ("order", "cancel-all"),
    ("order", "cancel"),
    ("position", "close-all"),
    ("position", "close"),
    ("locate", "create"),
    ("profile", "login"),
    ("account", "config", "update"),
]


@pytest.mark.parametrize("cmd", DESTRUCTIVE)
def test_every_destructive_command_is_refused(cmd):
    with pytest.raises(ValueError, match="non-allowlisted"):
        C.run(*cmd)


def test_allowlist_contains_only_read_verbs():
    """
    A read command names a thing or lists it. If a verb like submit, close,
    cancel, create, delete, update or login ever appears in the allowlist,
    this fails rather than waiting for it to be used.
    """
    banned = {"submit", "close", "close-all", "cancel", "cancel-all", "create",
              "delete", "update", "login", "replace", "exercise"}
    for entry in C.ALLOWED:
        assert not (set(entry) & banned), f"write verb in allowlist: {entry}"


def test_allowlist_is_small_and_explicit():
    assert C.ALLOWED == {
        ("account", "get"),
        ("account", "portfolio"),
        ("position", "list"),
        ("order", "list"),
        ("clock", "markets"),
        ("calendar", "market"),
        ("version",),
    }


def test_command_key_ignores_flag_values_not_just_flags(monkeypatch):
    """
    Regression, 2026-09-03: the key was built from every token that did not
    start with a dash, so `account portfolio --period 1W` keyed on
    ("account","portfolio","1W") and the allowlist rejected its own command.
    The key is the leading words before the first flag.

    Hermetic: the process is stubbed, so this asserts the guard's behaviour
    on any machine, with or without the CLI installed. An earlier version
    asserted a failure instead and passed only where no CLI existed.
    """
    calls = []

    class Done:
        returncode, stdout, stderr = 0, '{"equity": [1, 2]}', ""

    monkeypatch.setattr(C, "cli_path", lambda: Path("alpaca"))
    monkeypatch.setattr(C, "_env", lambda: {})
    monkeypatch.setattr(C.subprocess, "run",
                        lambda *a, **k: (calls.append(a[0]), Done())[1])

    out = C.run("account", "portfolio", "--period", "1W", "--timeframe", "1D")

    assert out == {"equity": [1, 2]}
    assert calls and calls[0][1:] == ["account", "portfolio", "--period", "1W",
                                      "--timeframe", "1D"]


def test_live_trade_flag_is_never_passed_through(monkeypatch):
    """The CLI treats env keys as paper unless ALPACA_LIVE_TRADE is set."""
    monkeypatch.setenv("ALPACA_API_KEY", "PKTEST")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")
    monkeypatch.setenv("ALPACA_LIVE_TRADE", "true")
    assert "ALPACA_LIVE_TRADE" not in C._env()


def test_missing_credentials_raise_unavailable_not_a_silent_pass(monkeypatch):
    monkeypatch.setattr(C, "ENV_FILE", Path("does-not-exist.env"))
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    with pytest.raises(C.CliUnavailable):
        C._env()


def test_snapshot_reports_failure_instead_of_raising(monkeypatch):
    """
    The results page calls this. A missing CLI must degrade the page, never
    break the generation of a report built from the sealed log.
    """
    def boom(*a, **k):
        raise C.CliUnavailable("no CLI here")
    monkeypatch.setattr(C, "run", boom)
    snap = C.snapshot()
    assert snap["ok"] is False
    assert "no CLI here" in snap["reason"]
