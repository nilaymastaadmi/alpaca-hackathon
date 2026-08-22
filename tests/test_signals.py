"""
Tests for signals.py, focused on what changed to fix gate 7's tenor mismatch.

Not a full signals.py test suite: atm_iv_at, parse_chain and realised_vol
predate this fix and were previously only exercised through live runs. This
file covers short_strike_iv (new) and compute()'s wiring of it, since that is
what was actually changed and what a regression here would silently break.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from signals import Contract, compute, short_strike_iv  # noqa: E402

TODAY = date(2026, 8, 31)


def c(strike, is_call, delta, iv, expiry_offset=11) -> Contract:
    return Contract(
        occ=f"SPY{'C' if is_call else 'P'}{strike}",
        strike=strike, is_call=is_call,
        expiry=TODAY + timedelta(days=expiry_offset),
        iv=iv, delta=delta, bid=1.0, ask=1.1,
    )


# --- short_strike_iv: selection -------------------------------------------

def test_selects_nearest_delta_call_and_put_and_averages_iv():
    contracts = [
        c(780, True, 0.16, 0.12),     # exact match, call
        c(790, True, 0.05, 0.09),     # wrong delta, should be ignored
        c(750, False, -0.16, 0.14),   # exact match, put
        c(730, False, -0.05, 0.11),
    ]
    iv, dte = short_strike_iv(contracts, TODAY, target_dte=11,
                              short_delta=0.16, dte_min=7, dte_max=14)
    assert iv == pytest.approx((0.12 + 0.14) / 2 * 100.0)
    assert dte == 11


def test_picks_the_closest_delta_when_no_exact_match():
    contracts = [
        c(780, True, 0.20, 0.10),   # |0.20-0.16| = 0.04
        c(785, True, 0.10, 0.20),   # |0.10-0.16| = 0.06, farther
        c(750, False, -0.16, 0.13),
    ]
    iv, _ = short_strike_iv(contracts, TODAY, target_dte=11,
                            short_delta=0.16, dte_min=7, dte_max=14)
    # call side should have picked the 0.20-delta contract (iv 0.10)
    assert iv == pytest.approx((0.10 + 0.13) / 2 * 100.0)


def test_picks_expiry_nearest_target_when_several_are_in_range():
    contracts = [
        c(780, True, 0.16, 0.10, expiry_offset=8),
        c(750, False, -0.16, 0.10, expiry_offset=8),
        c(780, True, 0.16, 0.30, expiry_offset=13),  # farther from target=11
        c(750, False, -0.16, 0.30, expiry_offset=13),
    ]
    iv, dte = short_strike_iv(contracts, TODAY, target_dte=9,
                              short_delta=0.16, dte_min=7, dte_max=14)
    assert dte == 8
    assert iv == pytest.approx(10.0)


def test_prefers_more_depth_when_two_expiries_are_equidistant():
    near_target = 10  # both offsets 9 and 11 are equidistant from 10
    contracts = [
        c(780, True, 0.16, 0.10, expiry_offset=9),
        c(750, False, -0.16, 0.10, expiry_offset=9),
        c(780, True, 0.16, 0.50, expiry_offset=11),
        c(781, True, 0.15, 0.50, expiry_offset=11),
        c(750, False, -0.16, 0.50, expiry_offset=11),
        c(749, False, -0.17, 0.50, expiry_offset=11),
    ]
    iv, dte = short_strike_iv(contracts, TODAY, target_dte=near_target,
                              short_delta=0.16, dte_min=7, dte_max=14)
    assert dte == 11, "the expiry with more quoted depth should win a tie"


# --- short_strike_iv: refusal conditions -----------------------------------

def test_raises_when_nothing_is_in_the_dte_window():
    contracts = [c(780, True, 0.16, 0.10, expiry_offset=30)]
    with pytest.raises(ValueError):
        short_strike_iv(contracts, TODAY, target_dte=11, short_delta=0.16,
                        dte_min=7, dte_max=14)


def test_raises_when_only_one_side_is_quoted():
    """A short strangle needs both a call and a put; one side alone must fail."""
    contracts = [c(780, True, 0.16, 0.10)]
    with pytest.raises(ValueError):
        short_strike_iv(contracts, TODAY, target_dte=11, short_delta=0.16,
                        dte_min=7, dte_max=14)


def test_ignores_contracts_with_no_iv_or_no_delta():
    contracts = [
        Contract("x", 780, True, TODAY + timedelta(days=11), iv=None,
                delta=0.16, bid=1, ask=1.1),
        Contract("y", 750, False, TODAY + timedelta(days=11), iv=0.13,
                delta=None, bid=1, ask=1.1),
    ]
    with pytest.raises(ValueError):
        short_strike_iv(contracts, TODAY, target_dte=11, short_delta=0.16,
                        dte_min=7, dte_max=14)


# --- compute(): backward compatible without short_* params -----------------

def test_compute_without_short_params_leaves_short_fields_none():
    """Existing callers (none currently, but the backtest style) must not break."""
    contracts = [
        c(770, True, 0.50, 0.13, expiry_offset=30),
        c(770, False, -0.50, 0.13, expiry_offset=30),
    ]
    closes = [770.0 + i * 0.1 for i in range(25)]
    sig = compute(contracts, 770.0, closes, TODAY)
    assert sig.short_strike_iv is None
    assert sig.short_strike_dte is None
    assert sig.short_strike_vrp is None


def test_compute_with_short_params_populates_the_new_fields():
    contracts = [
        c(770, True, 0.50, 0.13, expiry_offset=30),
        c(770, False, -0.50, 0.13, expiry_offset=30),
        c(780, True, 0.16, 0.10, expiry_offset=11),
        c(750, False, -0.16, 0.14, expiry_offset=11),
    ]
    closes = [770.0 + (i % 3) * 0.1 for i in range(25)]
    sig = compute(contracts, 770.0, closes, TODAY,
                  short_delta=0.16, short_target_dte=11,
                  short_dte_min=7, short_dte_max=14)
    assert sig.short_strike_iv == pytest.approx((0.10 + 0.14) / 2 * 100.0)
    assert sig.short_strike_dte == 11
    assert sig.short_strike_vrp == pytest.approx(sig.short_strike_iv - sig.trailing_rv)


def test_compute_leaves_short_iv_none_when_traded_tenor_has_no_quotes():
    """
    The refuse-rather-than-fallback behaviour starts here: if the short tenor
    genuinely has nothing quoted, short_strike_iv stays None all the way
    through to gate 7, which then refuses instead of guessing.
    """
    contracts = [c(770, True, 0.50, 0.13, expiry_offset=30),
                c(770, False, -0.50, 0.13, expiry_offset=30)]
    closes = [770.0 + (i % 3) * 0.1 for i in range(25)]
    sig = compute(contracts, 770.0, closes, TODAY,
                  short_delta=0.16, short_target_dte=11,
                  short_dte_min=7, short_dte_max=14)
    assert sig.short_strike_iv is None


# --- the atm_vrp / short_strike_vrp split is real, not cosmetic -----------

def test_atm_vrp_and_short_strike_vrp_can_disagree():
    """
    This is the whole point of the fix: the two numbers are allowed to differ,
    and gate 7 must be reading the short-strike one, not the ATM one.
    """
    contracts = [
        c(770, True, 0.50, 0.20, expiry_offset=30),   # rich ATM-far IV
        c(770, False, -0.50, 0.20, expiry_offset=30),
        c(780, True, 0.16, 0.09, expiry_offset=11),    # cheap short-strike IV
        c(750, False, -0.16, 0.09, expiry_offset=11),
    ]
    closes = [770.0 + (i % 3) * 0.1 for i in range(25)]
    sig = compute(contracts, 770.0, closes, TODAY,
                  short_delta=0.16, short_target_dte=11,
                  short_dte_min=7, short_dte_max=14)
    assert sig.atm_vrp != pytest.approx(sig.short_strike_vrp, abs=0.5)


# --- far-tenor fallback: fails closed, not silently mislabelled -----------

def test_missing_far_tenor_falls_back_to_flat_ratio_and_fails_closed():
    """
    Documents the behaviour explicitly rather than leaving it to be
    rediscovered: when the far tenor has no quotes, atm_far is set equal to
    atm_near, making the ratio exactly 1.0. Since contango is `ratio < 1.0`,
    that reads as NOT contango (i.e. gate 6 blocks), which is the safe
    direction, not a bug, even though an earlier comment claimed the opposite.
    """
    contracts = [c(770, True, 0.50, 0.13, expiry_offset=30),   # near tenor only
                c(770, False, -0.50, 0.13, expiry_offset=30)]  # nothing near 90d
    closes = [770.0 + (i % 3) * 0.1 for i in range(25)]
    sig = compute(contracts, 770.0, closes, TODAY)   # no far-tenor quotes at all
    assert sig.term_ratio == pytest.approx(1.0)
    assert sig.contango is False
