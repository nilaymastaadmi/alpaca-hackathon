"""
Tests for the submission-deadline flatten trigger.

Found while deploying T6 (21-45 DTE, DEPLOYMENT_DECISIONS.md D3, 2026-08-30):
a T6 position opened during the live week will not reach natural expiry
before judging, so without this, its final P&L is whatever the tape shows at
an arbitrary instant rather than a realised result. Also found in the same
pass: config already had `event_derisk_fraction` for exactly this kind of
situation, and it was never wired to anything -- the same "the gate's own
message overpromises what the code does" bug the drawdown-breaker flatten
(test_flatten.py) already fixed once, in a different gate.

`_is_deadline_close` is deliberately a pure function of config and a
timestamp so the trigger window is testable without mocking a full cycle;
what happens once it fires reuses `_flatten_all`, already covered by
test_flatten.py.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from agent import _is_deadline_close  # noqa: E402
from config import Config  # noqa: E402

DEADLINE_CFG = Config(
    deadline_flatten_enabled=True,
    submission_deadline_et="2026-09-04T11:00:00",
    deadline_flatten_hours_before=1.5,
)


def test_well_before_deadline_does_not_trigger():
    close, hours = _is_deadline_close(DEADLINE_CFG, datetime(2026, 8, 31, 10, 0))
    assert close is False
    assert hours > 1.5


def test_inside_the_window_triggers():
    # 09:30 ET, 4 Sep: the real target moment (market open, 1.5h before 11:00 ET)
    close, hours = _is_deadline_close(DEADLINE_CFG, datetime(2026, 9, 4, 9, 30))
    assert close is True
    assert 0.0 <= hours <= 1.5


def test_right_at_the_window_boundary_triggers():
    """Boundary is inclusive: exactly 1.5h out must not slip through."""
    close, hours = _is_deadline_close(DEADLINE_CFG, datetime(2026, 9, 4, 9, 30, 0))
    assert close is True
    assert hours == 1.5


def test_right_at_the_deadline_itself_still_triggers():
    close, hours = _is_deadline_close(DEADLINE_CFG, datetime(2026, 9, 4, 11, 0, 0))
    assert close is True
    assert hours == 0.0


def test_after_the_deadline_has_passed_does_not_retrigger():
    """
    Once judging has happened, forcing more closes is pointless and could
    even be actively wrong (e.g. a manual position opened after submission
    for an unrelated reason should not be swept up by a stale check).
    """
    close, hours = _is_deadline_close(DEADLINE_CFG, datetime(2026, 9, 4, 12, 0))
    assert close is False
    assert hours < 0.0


def test_disabled_never_triggers_even_inside_the_window():
    cfg = replace(DEADLINE_CFG, deadline_flatten_enabled=False)
    close, hours = _is_deadline_close(cfg, datetime(2026, 9, 4, 9, 30))
    assert close is False
    assert hours == float("inf")


def test_default_config_has_the_flatten_enabled():
    """The deployed default must ship with this on, not opt-in and forgotten."""
    cfg = Config()
    assert cfg.deadline_flatten_enabled is True
    assert cfg.submission_deadline_et == "2026-09-04T11:00:00"
