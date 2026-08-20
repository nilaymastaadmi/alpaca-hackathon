"""
Tests for the position ledger, exit rules, and broker reconciliation.

The failure this file exists to prevent: closing part of a condor and leaving
naked short options open. That is the worst outcome available to a short
premium agent, because a defined-risk position silently becomes an undefined
one, and the deployed sizing (5 concurrent at 3% each) assumes the wings are
there.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from positions import (  # noqa: E402
    ExitSignal, Ledger, OpenPosition, evaluate_exit, new_position, reconcile,
    value_from_quotes,
)

TODAY = date(2026, 8, 31)


def pos(**kw) -> OpenPosition:
    base = dict(
        id="pos-1", opened_at="2026-08-25T14:00:00+00:00", expiry="2026-09-11",
        contracts=6, credit=2.00, max_loss_per_contract=3.00,
        short_call="SPY260911C00784000", long_call="SPY260911C00789000",
        short_put="SPY260911P00752000", long_put="SPY260911P00747000",
    )
    base.update(kw)
    return OpenPosition(**base)


def q(bid, ask) -> dict:
    return {"bp": bid, "ap": ask}


FULL_QUOTES = {
    "SPY260911C00784000": q(1.00, 1.10),
    "SPY260911C00789000": q(0.40, 0.46),
    "SPY260911P00752000": q(1.20, 1.30),
    "SPY260911P00747000": q(0.55, 0.61),
}


# --- valuation ------------------------------------------------------------

def test_value_from_full_quotes():
    # call spread mid: 1.05 - 0.43 = 0.62 ; put spread mid: 1.25 - 0.58 = 0.67
    assert value_from_quotes(pos(), FULL_QUOTES) == pytest.approx(1.29)


def test_value_returns_none_when_a_leg_is_missing():
    """
    Three of four legs must NOT produce a number. A structure priced without a
    short leg looks cheaper than it is, and that error points toward holding a
    loser rather than closing it.
    """
    partial = dict(FULL_QUOTES)
    del partial["SPY260911P00752000"]
    assert value_from_quotes(pos(), partial) is None


def test_value_returns_none_on_a_zero_bid():
    broken = dict(FULL_QUOTES)
    broken["SPY260911C00789000"] = q(0.0, 0.46)
    assert value_from_quotes(pos(), broken) is None


def test_notional_risk_matches_contracts_and_wing():
    assert pos().notional_risk == pytest.approx(3.00 * 100 * 6)


# --- exit rules -----------------------------------------------------------

def test_holds_when_nothing_triggers():
    s = evaluate_exit(pos(), buyback=1.60, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=2.0)
    assert s.should_exit is False
    assert "holding" in s.reason


def test_exits_at_profit_target():
    # credit 2.00, buyback 1.00 -> 50% captured
    s = evaluate_exit(pos(), buyback=1.00, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=2.0)
    assert s.should_exit is True
    assert "max profit" in s.reason
    assert s.profit_frac == pytest.approx(0.50)


def test_exits_at_dte_even_while_losing():
    """Time-based exit must fire regardless of P&L. Gamma does not negotiate."""
    p = pos(expiry="2026-09-02")           # 2 DTE from TODAY
    s = evaluate_exit(p, buyback=3.50, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=None)
    assert s.should_exit is True
    assert "DTE" in s.reason


def test_stop_loss_fires_at_multiple_of_credit():
    s = evaluate_exit(pos(), buyback=4.00, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=2.0)
    assert s.should_exit is True
    assert "stop out" in s.reason


def test_stop_loss_disabled_lets_it_ride_to_the_wing():
    s = evaluate_exit(pos(), buyback=4.00, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=None)
    assert s.should_exit is False


def test_unquoted_position_near_expiry_still_closes():
    """An unquoted position about to expire must be closed on time, not held blind."""
    p = pos(expiry="2026-09-01")           # 1 DTE
    s = evaluate_exit(p, buyback=None, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=2.0)
    assert s.should_exit is True
    assert "unquoted" in s.reason


def test_unquoted_position_far_from_expiry_holds():
    s = evaluate_exit(pos(), buyback=None, today=TODAY, profit_target=0.50,
                      exit_dte=2, stop_loss_mult=2.0)
    assert s.should_exit is False


def test_unrealised_scales_with_contracts():
    s = evaluate_exit(pos(contracts=6), buyback=1.00, today=TODAY,
                      profit_target=0.50, exit_dte=2, stop_loss_mult=None)
    assert s.unrealised == pytest.approx((2.00 - 1.00) * 100 * 6)


# --- reconciliation, the dangerous case -----------------------------------

def test_reconcile_healthy_position():
    p = pos()
    healthy, issues = reconcile([p], set(p.legs))
    assert len(healthy) == 1 and issues == []


def test_reconcile_drops_a_fully_closed_position():
    p = pos()
    healthy, issues = reconcile([p], set())
    assert healthy == []
    assert issues[0]["severity"] == "info"


def test_reconcile_flags_a_partial_position_as_critical():
    """
    THE test. A condor missing its long call is a naked short call. It must be
    flagged CRITICAL and kept in the ledger, never silently dropped or repaired.
    """
    p = pos()
    present = set(p.legs) - {"SPY260911C00789000"}      # long wing gone
    healthy, issues = reconcile([p], present)
    assert len(issues) == 1
    assert issues[0]["severity"] == "CRITICAL"
    assert "naked short" in issues[0]["issue"]
    assert len(healthy) == 1, "a partial position must stay visible, not vanish"


def test_reconcile_handles_several_positions_independently():
    """
    Each position needs DISTINCT legs. Reusing one set of OCC symbols across
    three fixtures made all three reconcile as healthy, which is correct
    behaviour and a useless test.
    """
    a = pos(id="a", short_call="SPY260911C00784000", long_call="SPY260911C00789000",
            short_put="SPY260911P00752000", long_put="SPY260911P00747000")
    b = pos(id="b", short_call="SPY260918C00790000", long_call="SPY260918C00795000",
            short_put="SPY260918P00745000", long_put="SPY260918P00740000")
    c = pos(id="c", short_call="SPY260925C00800000", long_call="SPY260925C00805000",
            short_put="SPY260925P00735000", long_put="SPY260925P00730000")

    # a intact, b entirely gone, c missing its long call (the dangerous case)
    present = set(a.legs) | (set(c.legs) - {"SPY260925C00805000"})
    healthy, issues = reconcile([a, b, c], present)

    by_id = {i["position"]: i for i in issues}
    assert set(by_id) == {"b", "c"}
    assert by_id["b"]["severity"] == "info"
    assert by_id["c"]["severity"] == "CRITICAL"
    assert [p.id for p in healthy] == ["a", "c"]


# --- ledger persistence ---------------------------------------------------

@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "positions.json")


def test_ledger_roundtrip(ledger):
    ledger.add(pos(id="x"))
    ledger.add(pos(id="y"))
    loaded = ledger.load()
    assert [p.id for p in loaded] == ["x", "y"]
    assert loaded[0].contracts == 6


def test_ledger_remove(ledger):
    ledger.add(pos(id="x"))
    ledger.add(pos(id="y"))
    ledger.remove("x")
    assert [p.id for p in ledger.load()] == ["y"]


def test_ledger_update(ledger):
    ledger.add(pos(id="x", peak_profit_frac=0.0))
    p = ledger.load()[0]
    p.peak_profit_frac = 0.42
    ledger.update(p)
    assert ledger.load()[0].peak_profit_frac == pytest.approx(0.42)


def test_empty_ledger_reads_as_empty(ledger):
    assert ledger.load() == []


def test_new_position_from_plan_dict():
    plan = {
        "expiry": "2026-09-11", "max_loss_per_contract": 3.0,
        "short_call": "SPY260911C00784000", "long_call": "SPY260911C00789000",
        "short_put": "SPY260911P00752000", "long_put": "SPY260911P00747000",
    }
    p = new_position(plan, contracts=6, credit=2.0, entry_limit=-2.0, order_id="o1")
    assert p.contracts == 6
    assert len(p.legs) == 4
    assert p.id.startswith("pos-")
