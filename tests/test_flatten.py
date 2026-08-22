"""
Tests for the drawdown-breaker flatten logic.

Gate 2's own message says "HALT and flatten" when it fires. Before this, the
breaker stopped new entries but nothing ever closed the positions already open,
so the message overpromised what the system did. These tests exist to prove
`_flatten_all` closes what gate 2 says it closes, including when things go
wrong: quotes unavailable, one position refusing to close, an empty book.

A fake Broker (duck-typed, no real MCP) and a real Ledger pointed at tmp_path
are used, matching the pattern in test_broker.py.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from agent import _flatten_all  # noqa: E402
from positions import Ledger, OpenPosition  # noqa: E402

TODAY = date(2026, 9, 2)


def pos(**kw) -> OpenPosition:
    base = dict(
        id="pos-1", opened_at="2026-08-25T14:00:00+00:00", expiry="2026-09-11",
        contracts=6, credit=2.00, max_loss_per_contract=3.00,
        short_call="SPY260911C00784000", long_call="SPY260911C00789000",
        short_put="SPY260911P00752000", long_put="SPY260911P00747000",
    )
    base.update(kw)
    return OpenPosition(**base)


class FakeLog:
    def __init__(self):
        self.entries = []

    def append(self, rec):
        self.entries.append(rec)
        return "leaf"


class FakeBroker:
    """
    Scripts quotes() and close_position() independently of the MCP transport
    tested in test_broker.py. This file is about the FLATTEN POLICY: which
    positions get closed, in what order, with what fallback, and what happens
    to the ledger, not about the wire protocol underneath close_position.
    """

    def __init__(self, quotes_result=None, quotes_error=None,
                close_results: dict[str, dict] | None = None):
        self.quotes_result = quotes_result or {}
        self.quotes_error = quotes_error
        self.close_results = close_results or {}
        self.close_calls: list[tuple[str, float, int]] = []

    def quotes(self, symbols):
        if self.quotes_error:
            raise self.quotes_error
        return self.quotes_result

    def close_position(self, position, buyback, contracts, dry_run=False):
        self.close_calls.append((position.id, buyback, contracts))
        return self.close_results.get(position.id, {"filled": True})


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "positions.json")


# --- basic shape -------------------------------------------------------

def test_empty_book_flattens_nothing(ledger):
    broker = FakeBroker()
    results = _flatten_all(broker, ledger, [], TODAY, dry_run=False, log=FakeLog())
    assert results == []
    assert broker.close_calls == []


def test_dry_run_never_calls_close_position(ledger):
    p = pos()
    ledger.add(p)
    broker = FakeBroker()
    log = FakeLog()
    results = _flatten_all(broker, ledger, [p], TODAY, dry_run=True, log=log)
    assert results[0]["action"] == "would_flatten"
    assert broker.close_calls == []
    assert ledger.load() == [p], "dry run must not touch the ledger"


# --- the actual promise: everything held gets closed --------------------

def test_all_positions_close_and_leave_the_ledger(ledger):
    a, b = pos(id="a"), pos(id="b")
    ledger.add(a)
    ledger.add(b)
    broker = FakeBroker(close_results={"a": {"filled": True}, "b": {"filled": True}})
    results = _flatten_all(broker, ledger, [a, b], TODAY, dry_run=False, log=FakeLog())

    assert {r["position"] for r in results} == {"a", "b"}
    assert all(r["action"] == "closed" for r in results)
    assert ledger.load() == [], "everything closed must leave nothing in the ledger"
    assert len(broker.close_calls) == 2


def test_every_position_gets_attempted_even_after_an_earlier_one(ledger):
    """One position closing must not stop the loop from reaching the rest."""
    positions = [pos(id=f"p{i}") for i in range(4)]
    for p in positions:
        ledger.add(p)
    broker = FakeBroker()
    _flatten_all(broker, ledger, positions, TODAY, dry_run=False, log=FakeLog())
    assert len(broker.close_calls) == 4


# --- a failed close must not be lost --------------------------------------

def test_a_position_that_fails_to_close_stays_in_the_ledger(ledger):
    """
    THE test. If close_position reports not filled, that position must remain
    in the ledger so the next cycle (drawdown will still be true) retries it,
    rather than being silently dropped.
    """
    a, b = pos(id="a"), pos(id="b")
    ledger.add(a)
    ledger.add(b)
    broker = FakeBroker(close_results={
        "a": {"filled": True}, "b": {"filled": False, "aborted_unsafe": True},
    })
    results = _flatten_all(broker, ledger, [a, b], TODAY, dry_run=False, log=FakeLog())

    by_id = {r["position"]: r for r in results}
    assert by_id["a"]["action"] == "closed"
    assert by_id["b"]["action"] == "close_failed"

    remaining_ids = {p.id for p in ledger.load()}
    assert remaining_ids == {"b"}, "the failed close must survive in the ledger"


# --- emergency behaviour: quotes failing must not cancel the flatten ------

def test_quote_failure_does_not_abort_the_flatten(ledger):
    """
    Deliberately different from _manage_exits, which gives up entirely if
    quotes cannot be fetched, because holding is the safe default there. Here
    the breaker firing means doing nothing IS the unsafe option, so every
    position still gets a real close attempt, falling back to its own entry
    credit as the ladder seed.
    """
    p = pos(credit=2.00)
    ledger.add(p)
    broker = FakeBroker(quotes_error=ConnectionError("market data down"))
    results = _flatten_all(broker, ledger, [p], TODAY, dry_run=False, log=FakeLog())

    assert len(broker.close_calls) == 1, "a close must still be attempted"
    _, buyback_used, contracts_used = broker.close_calls[0]
    assert buyback_used == pytest.approx(2.00), "falls back to the position's own credit"
    assert results[0]["action"] == "closed"
    assert "quote_warning" in results[0]


def test_quote_failure_is_recorded_but_does_not_block_other_positions(ledger):
    a, b = pos(id="a"), pos(id="b")
    ledger.add(a)
    ledger.add(b)
    broker = FakeBroker(quotes_error=TimeoutError("slow feed"))
    results = _flatten_all(broker, ledger, [a, b], TODAY, dry_run=False, log=FakeLog())
    assert len(broker.close_calls) == 2
    assert all("quote_warning" in r for r in results)


# --- every attempt is logged, closed or not -------------------------------

def test_every_flatten_attempt_is_logged_even_on_failure(ledger):
    p = pos()
    ledger.add(p)
    broker = FakeBroker(close_results={p.id: {"filled": False}})
    log = FakeLog()
    _flatten_all(broker, ledger, [p], TODAY, dry_run=False, log=log)
    assert len(log.entries) == 1
    assert log.entries[0]["action"] == "flatten:close_failed"


def test_logged_records_carry_the_reason(ledger):
    """A judge reading the artifact must see WHY a position was force-closed."""
    p = pos()
    ledger.add(p)
    broker = FakeBroker()
    log = FakeLog()
    _flatten_all(broker, ledger, [p], TODAY, dry_run=True, log=log)
    assert "drawdown breaker" in log.entries[0]["flatten"]["reason"].lower()
