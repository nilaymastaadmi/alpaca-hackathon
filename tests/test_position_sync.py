"""
Regression tests for the 2026-08-31 live incident.

What happened: `Broker.positions()` looked for a "positions" key in a payload
the MCP server actually wraps as {"data": {"result": [...]}}, so it returned
[] for every response, populated or not. Each cycle then believed the account
was flat: reconcile() dropped the ledger entry as "closed elsewhere", the
capacity gate read 0/5, the stagger gate never saw the held expiry, and the
agent stacked four condors in 36 minutes where the design intended one. The
sealed artifact for seq 30 contains both the raw MCP response WITH the legs
and the reconcile drop that ignored them, which is how this was caught.

Two guards now exist and are pinned here:
  1. positions() parses the real wrapper, and RAISES on an unrecognised shape
     rather than defaulting to "flat".
  2. reconcile() checks the broker-to-ledger direction too: broker option legs
     on the traded underlying that no ledger position covers are CRITICAL,
     which gate 0 turns into a halt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from broker import Broker  # noqa: E402
from config import Config  # noqa: E402
from positions import OpenPosition, reconcile  # noqa: E402
from risk import RiskEngine  # noqa: E402


class StubMCP:
    def __init__(self, payload):
        self.payload = payload

    def call(self, tool, args=None):
        return self.payload


def leg_position(symbol: str, qty: str = "-7") -> dict:
    return {"symbol": symbol, "qty": qty, "asset_class": "us_option"}


LIVE_LEGS = [
    "SPY261002C00792000", "SPY261002C00797000",
    "SPY261002P00731000", "SPY261002P00726000",
    "SPY261002P00732000", "SPY261002P00727000",
]


def ledger_pos(pos_id="pos-d", legs=None) -> OpenPosition:
    legs = legs or LIVE_LEGS[:4]
    return OpenPosition(
        id=pos_id, opened_at="2026-08-31T14:21:40+00:00", expiry="2026-10-02",
        contracts=7, credit=1.09, max_loss_per_contract=3.835,
        short_call=legs[0], long_call=legs[1],
        short_put=legs[2], long_put=legs[3],
    )


# --- positions() parsing, THE regression ------------------------------------

def test_positions_parses_the_real_mcp_result_wrapper():
    """The exact shape the live server sends. This returning [] is what
    stacked four condors."""
    payload = {"data": {"result": [leg_position(s) for s in LIVE_LEGS]}}
    got = Broker(StubMCP(payload), Config()).positions()
    assert len(got) == 6
    assert {p["symbol"] for p in got} == set(LIVE_LEGS)


def test_positions_empty_result_is_genuinely_empty():
    got = Broker(StubMCP({"data": {"result": []}}), Config()).positions()
    assert got == []


def test_positions_accepts_a_bare_list_and_the_legacy_key():
    bare = {"data": [leg_position(LIVE_LEGS[0])]}
    assert len(Broker(StubMCP(bare), Config()).positions()) == 1
    legacy = {"data": {"positions": [leg_position(LIVE_LEGS[0])]}}
    assert len(Broker(StubMCP(legacy), Config()).positions()) == 1


def test_positions_raises_on_unrecognised_shape_instead_of_reading_flat():
    """{"text": ...} is what mcp_client returns when the server's JSON does
    not parse. Defaulting that to [] is the fail-open that armed the bug."""
    with pytest.raises(RuntimeError):
        Broker(StubMCP({"text": "server said something unparseable"}),
               Config()).positions()
    with pytest.raises(RuntimeError):
        Broker(StubMCP({"data": {"unexpected": 1}}), Config()).positions()


# --- reconcile's broker-to-ledger direction ---------------------------------

def test_reconcile_flags_uncovered_broker_legs_as_critical_orphans():
    """The live morning's end state: ledger knows one condor, broker holds
    four (six unique leg symbols). The two legs the ledger does not cover
    must surface as CRITICAL."""
    broker_symbols = set(LIVE_LEGS) | {"SPY", "VIX261021C00020000"}
    healthy, issues = reconcile([ledger_pos()], broker_symbols,
                                underlying="SPY")
    assert len(healthy) == 1
    orphan = [i for i in issues if i.get("orphan_legs")]
    assert len(orphan) == 1
    assert orphan[0]["severity"] == "CRITICAL"
    assert orphan[0]["orphan_legs"] == sorted(
        ["SPY261002P00732000", "SPY261002P00727000"])


def test_reconcile_orphan_check_ignores_stock_and_other_roots():
    """A bare SPY share position and the VIX hedge legs are not orphans; only
    option legs on the traded underlying count."""
    healthy, issues = reconcile(
        [ledger_pos()],
        set(LIVE_LEGS[:4]) | {"SPY", "VIX261021C00020000"},
        underlying="SPY")
    assert healthy and not issues


def test_reconcile_fully_covered_book_raises_no_orphans():
    a = ledger_pos("pos-a", LIVE_LEGS[:4])
    b = ledger_pos("pos-b", [LIVE_LEGS[0], LIVE_LEGS[1],
                             LIVE_LEGS[4], LIVE_LEGS[5]])
    healthy, issues = reconcile([a, b], set(LIVE_LEGS), underlying="SPY")
    assert len(healthy) == 2
    assert issues == []


def test_reconcile_without_underlying_keeps_the_old_contract():
    """Callers that never opted in (isolated comparison runs constructed on
    old call sites, external users of the function) see no new issue type."""
    _, issues = reconcile([], set(LIVE_LEGS))
    assert issues == []


# --- the gate stack turns orphans into a halt --------------------------------

def test_orphans_block_gate0_and_read_as_a_halt():
    _, issues = reconcile([], set(LIVE_LEGS), underlying="SPY")
    eng = RiskEngine(Config())
    g0 = eng.g0_position_integrity(issues)
    assert g0.passed is False
    assert RiskEngine.is_halt([g0]) is True, (
        "an unknown book is a broken assumption, not a market opinion; the "
        "agent must halt, not merely refuse this one entry")
