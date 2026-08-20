"""
Tests for the VIX tail hedge.

The thing being protected against is the one scenario that can sink the whole
submission: five correlated short-volatility positions hitting max loss together
for -15%. So the tests care most about the hedge REFUSING to act on data it
should not trust. A hedge bought off a bad forward estimate is not a hedge, it
is a second unmanaged position, and it would be discovered at exactly the wrong
moment.
"""

from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from hedge import (  # noqa: E402
    HedgePlan, VixQuote, build_hedge, hedge_order, parse_vix_chain,
    recover_forward,
)

TODAY = date(2026, 8, 20)
EXPIRY = date(2026, 9, 16)
T = (EXPIRY - TODAY).days / 365.0


def synth_chain(forward: float, strikes=None, expiry=EXPIRY,
                spread: float = 0.04) -> list[VixQuote]:
    """
    Build a chain that satisfies put-call parity exactly at `forward`, so any
    error the parity code makes shows up as a deviation from a known truth.
    """
    strikes = strikes or [12, 14, 15, 16, 17, 18, 19, 20, 22, 24, 26, 30]
    disc = math.exp(-0.04 * T)
    out = []
    for k in strikes:
        # Intrinsic-on-forward plus a small symmetric time value keeps C - P
        # exactly equal to disc * (F - K), which is the parity relation.
        tv = 0.60
        call = max(forward - k, 0) * disc + tv
        put = call - disc * (forward - k)
        for is_call, px in ((True, call), (False, put)):
            if px <= 0.02:
                continue
            out.append(VixQuote(
                occ=f"VIX{expiry.strftime('%y%m%d')}"
                    f"{'C' if is_call else 'P'}{int(k * 1000):08d}",
                strike=float(k), is_call=is_call, expiry=expiry,
                bid=round(px - spread / 2, 2), ask=round(px + spread / 2, 2)))
    return out


# --- parity recovery ------------------------------------------------------

def test_recovers_a_known_forward():
    fwd, disp = recover_forward(synth_chain(17.63), EXPIRY, TODAY)
    assert fwd == pytest.approx(17.63, abs=0.15)
    assert disp < 0.5


@pytest.mark.parametrize("true_fwd", [12.0, 15.5, 17.63, 22.0, 30.0])
def test_recovers_across_levels(true_fwd):
    fwd, _ = recover_forward(synth_chain(true_fwd), EXPIRY, TODAY)
    assert fwd == pytest.approx(true_fwd, abs=0.35)


def test_refuses_when_too_few_two_sided_strikes():
    thin = synth_chain(17.63, strikes=[16, 17])
    with pytest.raises(ValueError, match="not enough"):
        recover_forward(thin, EXPIRY, TODAY)


def test_ignores_strikes_missing_a_side():
    """Calls without matching puts carry no parity information."""
    chain = synth_chain(17.63)
    chain = [q for q in chain if q.is_call or q.strike <= 20]
    fwd, _ = recover_forward(chain, EXPIRY, TODAY)
    assert fwd == pytest.approx(17.63, abs=0.35)


def test_median_resists_one_corrupted_strike():
    """A single bad wing quote must not move the estimate."""
    chain = synth_chain(17.63)
    for q in chain:
        if q.strike == 30 and q.is_call:
            q.bid, q.ask = 40.0, 45.0        # nonsense
    fwd, _ = recover_forward(chain, EXPIRY, TODAY)
    assert fwd == pytest.approx(17.63, abs=0.6)


# --- hedge construction ---------------------------------------------------

def test_builds_a_plan_and_respects_the_budget():
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    assert plan is not None
    assert plan.cost <= plan.budget
    assert plan.budget == pytest.approx(1000.0)
    assert plan.contracts >= 1


def test_strike_sits_above_the_forward():
    """A tail hedge is out of the money by construction."""
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    assert plan.strike > plan.forward
    assert plan.moneyness > 1.0


def test_moneyness_tracks_the_target():
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY,
                       target_moneyness=1.35)
    assert plan.moneyness == pytest.approx(1.35, abs=0.20)


def test_budget_scales_with_equity():
    small = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    big = build_hedge(synth_chain(17.63), equity=400_000.0, today=TODAY)
    assert big.contracts > small.contracts


# --- refusing to act on untrustworthy data --------------------------------

def test_refuses_when_parity_estimates_disagree():
    """
    Dispersion is a confidence measure. If strikes disagree about the forward,
    the hedge must decline rather than pick one and hope.
    """
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY,
                       max_dispersion=0.0001)
    assert plan is None


def test_refuses_when_spreads_are_too_wide():
    wide = synth_chain(17.63, spread=3.0)
    plan = build_hedge(wide, equity=100_000.0, today=TODAY, max_spread_pct=0.10)
    assert plan is None


def test_refuses_when_budget_cannot_buy_one_contract():
    plan = build_hedge(synth_chain(17.63), equity=1_000.0, today=TODAY,
                       budget_pct=0.01)
    assert plan is None


def test_refuses_when_no_expiry_is_in_the_dte_window():
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY,
                       dte_min=90, dte_max=120)
    assert plan is None


def test_empty_chain_returns_none():
    assert build_hedge([], equity=100_000.0, today=TODAY) is None


# --- payoff sanity --------------------------------------------------------

def test_hedge_covers_the_worst_case_short_book_loss():
    """
    The book risks 15% of 100k, so 15,000. A VIX spike to 40 must produce
    materially more than that, or the hedge is decorative.
    """
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    payoff = max(40.0 - plan.strike, 0.0) * plan.contracts * 100.0
    assert payoff > 15_000.0, f"payoff {payoff} does not cover a 15% book loss"


def test_hedge_cost_is_a_small_fraction_of_equity():
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    assert plan.cost / 100_000.0 <= 0.02, "sizing above the 2% consensus ceiling"


# --- order shape ----------------------------------------------------------

def test_order_is_a_single_leg_buy_to_open():
    plan = build_hedge(synth_chain(17.63), equity=100_000.0, today=TODAY)
    o = hedge_order(plan)
    assert o["side"] == "buy"
    assert o["position_intent"] == "buy_to_open"
    assert o["type"] == "limit"
    assert o["qty"] == str(plan.contracts)


# --- parsing --------------------------------------------------------------

def test_parse_handles_the_data_snapshots_envelope():
    payload = {"data": {"snapshots": {
        "VIX260916C00024000": {"latestQuote": {"bp": 0.55, "ap": 0.59}},
        "VIX260916P00016000": {"latestQuote": {"bp": 0.40, "ap": 0.44}},
    }}}
    qs = parse_vix_chain(payload)
    assert len(qs) == 2
    call = next(q for q in qs if q.is_call)
    assert call.strike == 24.0
    assert call.mid == pytest.approx(0.57)


def test_parse_drops_contracts_without_a_two_sided_quote():
    payload = {"data": {"snapshots": {
        "VIX260916C00024000": {"latestQuote": {"bp": 0, "ap": 0.59}},
        "VIX260916C00026000": {"latestQuote": {}},
    }}}
    assert parse_vix_chain(payload) == []
