"""
Tests for the execution layer, focused on the double-open guard.

The failure this exists to prevent: `sell_to_open` is always valid on Alpaca's
side, so nothing there rejects a genuine duplicate order the way a closing
order would. Four ways a naive ladder produces one anyway: the MCP call raises
AFTER Alpaca already accepted the order, so no order_id is ever recorded to
cancel; polling for a fill hits an exception and discards a real order_id; a
parent-quantity partial fill times out the poll instead of resolving; or the
watchdog kills the process mid-ladder. A FakeMCP drives each of these directly,
since the live fill test can only ever show the happy path.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from broker import Broker, CondorPlan  # noqa: E402
from config import Config  # noqa: E402
from signals import Contract  # noqa: E402

EXP = date.today() + timedelta(days=11)


def contract(occ: str, strike: float, is_call: bool, bid: float, ask: float) -> Contract:
    return Contract(occ, strike, is_call, EXP, iv=0.15, delta=0.16 if is_call else -0.16,
                    bid=bid, ask=ask)


def make_plan() -> CondorPlan:
    sc = contract("SPY260911C00784000", 784, True, 1.16, 1.18)
    lc = contract("SPY260911C00793000", 793, True, 0.23, 0.28)
    sp = contract("SPY260911P00752000", 752, False, 1.63, 1.68)
    lp = contract("SPY260911P00747000", 747, False, 0.52, 0.53)
    credit_mid = sc.mid + sp.mid - lc.mid - lp.mid
    credit_crossing = (sc.bid + sp.bid) - (lc.ask + lp.ask)
    return CondorPlan(sc, lc, sp, lp, credit_mid, credit_crossing, 9.0, EXP,
                      (EXP - date.today()).days)


class FakeMCP:
    """
    Drives `call(tool, args)` from a per-tool script: a list of either canned
    return values or exceptions to raise, consumed in order. A tool called more
    times than scripted repeats its last entry, so tests only need to script
    the transitions that matter.
    """

    def __init__(self, script: dict[str, list]):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls: list[tuple[str, dict]] = []

    def call(self, tool: str, args: dict | None = None) -> dict:
        self.calls.append((tool, dict(args or {})))
        q = self.script.get(tool)
        if not q:
            return {"data": {}}
        item = q.pop(0) if len(q) > 1 else q[0]
        if isinstance(item, Exception):
            raise item
        return item

    def count(self, tool: str) -> int:
        return sum(1 for t, _ in self.calls if t == tool)


def empty_orders() -> dict:
    return {"data": {"result": []}}


def filled_order(oid="o1", qty="6", price="-2.03", status="filled") -> dict:
    return {"data": {"id": oid, "status": status, "filled_qty": qty,
                     "filled_avg_price": price}}


def resting_order_for(plan: CondorPlan, oid="existing-1") -> dict:
    return {"data": {"result": [{
        "id": oid, "status": "new",
        "legs": [{"symbol": plan.short_call.occ}, {"symbol": plan.long_call.occ},
                 {"symbol": plan.short_put.occ}, {"symbol": plan.long_put.occ}],
    }]}}


# --- happy path -------------------------------------------------------------

def test_happy_path_fills_on_first_rung():
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [empty_orders()],
        "place_option_order": [{"data": {"id": "o1"}}],
        "get_order_by_id": [filled_order()],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["filled"] is True
    assert res["filled_qty"] == 6
    assert res["rung"] == 1
    assert mcp.count("place_option_order") == 1


def test_guard_runs_even_on_a_clean_first_rung():
    """The check must happen every time, not only after something goes wrong."""
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [empty_orders()],
        "place_option_order": [{"data": {"id": "o1"}}],
        "get_order_by_id": [filled_order()],
    })
    Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert mcp.count("get_orders") >= 1


# --- THE core test: exception after acceptance must not double-open --------

def test_exception_after_acceptance_does_not_double_open():
    """
    Rung 1's send raises client-side (network blip) even though Alpaca actually
    accepted the order. The naive ladder would blindly send rung 2. The guard
    must instead find the order resting via get_orders and wait on it, never
    sending a second order for the same legs.
    """
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [empty_orders(), resting_order_for(plan)],
        "place_option_order": [ConnectionError("timed out, unknown outcome")],
        "get_order_by_id": [filled_order(oid="existing-1")],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)

    assert res["filled"] is True
    assert res["order"]["id"] == "existing-1"
    # THE assertion. Only one send attempt total, ever, across the whole call.
    assert mcp.count("place_option_order") == 1


def test_watchdog_style_leftover_order_is_found_and_waited_on():
    """
    Simulates the next cycle after a kill left an order resting from a
    previous, now-dead ladder call. The very first check, before rung 1 is
    ever sent, must find it.
    """
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [resting_order_for(plan, oid="leftover-1")],
        "get_order_by_id": [filled_order(oid="leftover-1")],
        "place_option_order": [{"data": {"id": "should-never-be-used"}}],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["filled"] is True
    assert res["order"]["id"] == "leftover-1"
    assert mcp.count("place_option_order") == 0, (
        "a resting order was already there; nothing new should have been sent")


# --- cannot confirm safety -> abort, never guess ----------------------------

def test_get_orders_failure_aborts_rather_than_sends():
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [ConnectionError("network down")],
        "place_option_order": [{"data": {"id": "should-never-be-used"}}],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["filled"] is False
    assert res["aborted_unsafe"] is True
    assert mcp.count("place_option_order") == 0


def test_unexpected_response_shape_is_treated_as_unconfirmed():
    """A shape that does not parse as a list must not be read as 'no orders'."""
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [{"data": {"unexpected": "shape"}}],
        "place_option_order": [{"data": {"id": "should-never-be-used"}}],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["aborted_unsafe"] is True
    assert mcp.count("place_option_order") == 0


# --- partial fills -----------------------------------------------------------

def test_partial_fill_cancels_remainder_and_stops():
    plan = make_plan()
    mcp = FakeMCP({
        "get_orders": [empty_orders()],
        "place_option_order": [{"data": {"id": "o1"}}],
        "get_order_by_id": [filled_order(oid="o1", qty="3", status="partially_filled")],
        "cancel_order_by_id": [{"data": {}}],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)

    assert res["filled"] is True
    assert res["partial"] is True
    assert res["filled_qty"] == 3
    assert mcp.count("cancel_order_by_id") == 1, "the unfilled remainder must be cancelled"
    assert mcp.count("place_option_order") == 1, (
        "must not send a further rung on top of a partial fill")


# --- an order resting on DIFFERENT legs must not block or match ------------

def test_resting_order_on_different_legs_does_not_block():
    plan = make_plan()
    other_order = {"data": {"result": [{
        "id": "unrelated", "status": "new",
        "legs": [{"symbol": "QQQ260911C00500000"}],
    }]}}
    mcp = FakeMCP({
        "get_orders": [other_order],
        "place_option_order": [{"data": {"id": "o1"}}],
        "get_order_by_id": [filled_order(oid="o1")],
    })
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["filled"] is True
    assert res["order"]["id"] == "o1"
    assert mcp.count("place_option_order") == 1


# --- a resting order that never fills gets cancelled, then a fresh one sent -

def test_resting_order_that_terminates_unfilled_is_cancelled_then_fresh_rung_sent():
    plan = make_plan()
    mcp = FakeMCP({
        # First check finds a leftover; second check (after cancelling it) is clear.
        "get_orders": [resting_order_for(plan, oid="stale-1"), empty_orders()],
        "get_order_by_id": [{"data": {"id": "stale-1", "status": "canceled"}}],
        "cancel_order_by_id": [{"data": {}}],
        "place_option_order": [{"data": {"id": "fresh-1"}}],
    })
    # After the fresh send, its own fill check must report filled.
    mcp.script["get_order_by_id"] = [
        {"data": {"id": "stale-1", "status": "canceled"}},
        filled_order(oid="fresh-1"),
    ]
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True)
    assert res["filled"] is True
    assert res["order"]["id"] == "fresh-1"
    assert mcp.count("place_option_order") == 1


# --- dry run never touches the order book -----------------------------------

def test_dry_run_never_calls_get_orders_or_sends_anything():
    plan = make_plan()
    mcp = FakeMCP({})
    res = Broker(mcp, Config()).place_laddered(plan, 6, opening=True, dry_run=True)
    assert res["filled"] is False
    assert res["dry_run"] is True
    assert mcp.count("get_orders") == 0
    assert mcp.count("place_option_order") == 0
    assert len(res["attempts"]) == Config().price_ladder_rungs


# --- ladder exhaustion, no resting order left behind ------------------------

def test_ladder_exhausts_cleanly_when_nothing_ever_fills():
    """
    Every rung's poll returns a non-terminal status ("new"), so _await_fill's
    real wall-clock timeout runs for real on each one. rung_wait_seconds is
    overridden to keep this test fast; it is real sleeping, not mocked time,
    so the override must stay well above zero to still exercise the loop.
    """
    plan = make_plan()
    cfg = Config(rung_wait_seconds=0.3)
    n = cfg.price_ladder_rungs
    mcp = FakeMCP({
        "get_orders": [empty_orders()] * n,
        "place_option_order": [{"data": {"id": f"o{i}"}} for i in range(1, n + 1)],
        "get_order_by_id": [{"data": {"id": "x", "status": "new"}}],
        "cancel_order_by_id": [{"data": {}}],
    })
    res = Broker(mcp, cfg).place_laddered(plan, 6, opening=True)
    assert res["filled"] is False
    assert mcp.count("place_option_order") == n
    assert mcp.count("cancel_order_by_id") == n, (
        "every unfilled rung must be cancelled before the next is sent")
