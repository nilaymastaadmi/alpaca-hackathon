"""
Tests for _manage_hedge, the orchestration around agent/hedge.py.

hedge.py's own 23 tests already cover the parity math and strike selection.
This file is about the surrounding control flow: when the hedge gets bought,
when it is deliberately left alone, and that every path is logged, none of
which hedge.py's own unit tests can see since they never touch agent.py.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

import agent as A  # noqa: E402
from config import Config  # noqa: E402
from hedge import HedgePlan  # noqa: E402

TODAY = date(2026, 9, 2)


class FakeLog:
    def __init__(self):
        self.entries = []

    def append(self, rec):
        self.entries.append(rec)
        return "leaf"


class FakeBroker:
    def __init__(self, vix_chain_result=None, vix_chain_error=None,
                place_hedge_result=None):
        self.vix_chain_result = vix_chain_result or []
        self.vix_chain_error = vix_chain_error
        self.place_hedge_result = place_hedge_result or {"filled": True}
        self.vix_chain_calls = 0
        self.place_hedge_calls: list[tuple] = []

    def vix_chain(self, dte_lo, dte_hi):
        self.vix_chain_calls += 1
        if self.vix_chain_error:
            raise self.vix_chain_error
        return self.vix_chain_result

    def place_hedge(self, plan, dry_run=False):
        self.place_hedge_calls.append((plan, dry_run))
        return self.place_hedge_result


def a_plan() -> HedgePlan:
    return HedgePlan(
        contract="VIX260916C00024000", strike=24.0,
        expiry=date(2026, 9, 16), dte=14, forward=17.66, moneyness=1.359,
        price=1.20, contracts=8, cost=960.0, budget=1000.0,
        forward_dispersion=0.05,
    )


def call(broker, cfg=None, equity=100_000.0, market_open=True,
         broker_positions=None, dry_run=False, log=None):
    return A._manage_hedge(broker, cfg or Config(), equity, TODAY, market_open,
                           broker_positions or [], dry_run, log or FakeLog())


# --- when nothing should happen at all ------------------------------------

def test_disabled_skips_everything():
    broker = FakeBroker()
    res = call(broker, cfg=Config(hedge_enabled=False))
    assert res["action"] == "disabled"
    assert broker.vix_chain_calls == 0


def test_market_closed_skips_everything():
    broker = FakeBroker()
    res = call(broker, market_open=False)
    assert res["action"] == "skip"
    assert broker.vix_chain_calls == 0


def test_already_held_does_not_refetch_or_rebuy():
    broker = FakeBroker()
    positions = [{"symbol": "VIX260916C00024000", "qty": "8"}]
    res = call(broker, broker_positions=positions)
    assert res["action"] == "held"
    assert broker.vix_chain_calls == 0
    assert broker.place_hedge_calls == []


def test_held_check_does_not_false_positive_on_the_underlying_book():
    """SPY condor legs must not be mistaken for an existing VIX hedge."""
    broker = FakeBroker()
    positions = [{"symbol": "SPY260911C00784000"}, {"symbol": "SPY260911P00752000"}]
    res = call(broker, broker_positions=positions)
    assert res["action"] != "held"
    assert broker.vix_chain_calls == 1


# --- data problems are reported, not swallowed -----------------------------

def test_chain_fetch_failure_is_reported():
    broker = FakeBroker(vix_chain_error=ConnectionError("feed down"))
    log = FakeLog()
    res = call(broker, log=log)
    assert res["action"] == "error"
    assert "feed down" in res["reason"]
    assert log.entries and log.entries[0]["action"] == "hedge:error"


def test_no_candidate_is_reported_not_silently_dropped(monkeypatch):
    """
    build_hedge returning None means no strike cleared the spread, dispersion
    or budget checks. That is a real, loggable outcome, not a no-op.
    """
    monkeypatch.setattr(A, "build_hedge", lambda *a, **k: None)
    broker = FakeBroker(vix_chain_result=["not empty, content does not matter here"])
    log = FakeLog()
    res = call(broker, log=log)
    assert res["action"] == "no_candidate"
    assert log.entries[0]["action"] == "hedge:no_candidate"
    assert broker.place_hedge_calls == []


# --- a real candidate gets bought, dry run does not send ------------------

def test_dry_run_calls_place_hedge_with_dry_run_true(monkeypatch):
    monkeypatch.setattr(A, "build_hedge", lambda *a, **k: a_plan())
    broker = FakeBroker(place_hedge_result={"filled": False, "dry_run": True})
    res = call(broker, dry_run=True)
    assert res["action"] == "would_buy"
    assert broker.place_hedge_calls[0][1] is True   # dry_run flag reached the broker


def test_live_fill_is_reported_as_bought(monkeypatch):
    monkeypatch.setattr(A, "build_hedge", lambda *a, **k: a_plan())
    broker = FakeBroker(place_hedge_result={"filled": True, "filled_qty": 8})
    log = FakeLog()
    res = call(broker, log=log)
    assert res["action"] == "bought"
    assert res["plan"]["contract"] == "VIX260916C00024000"
    assert log.entries[0]["action"] == "hedge:bought"


def test_unfilled_resting_order_is_reported_distinctly(monkeypatch):
    """
    An unfilled hedge buy is a day order resting harmlessly, per broker.py's
    own reasoning: no short exposure the way an unfilled short leg would carry.
    It must still be visible in the artifact trail as its own outcome.
    """
    monkeypatch.setattr(A, "build_hedge", lambda *a, **k: a_plan())
    broker = FakeBroker(place_hedge_result={"filled": False, "resting": True})
    res = call(broker)
    assert res["action"] == "resting_unfilled"


# --- the config rename actually reaches build_hedge ------------------------

def test_config_moneyness_field_reaches_build_hedge(monkeypatch):
    """
    Regression guard for the hedge_target_delta -> hedge_target_moneyness
    rename. If the wrong kwarg name were passed, this would TypeError rather
    than silently misbehave, which is exactly why the check is worth having.
    """
    captured = {}

    def fake_build_hedge(quotes, equity, today, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(A, "build_hedge", fake_build_hedge)
    cfg = Config(hedge_target_moneyness=1.4)
    call(FakeBroker(), cfg=cfg)
    assert captured["target_moneyness"] == 1.4
