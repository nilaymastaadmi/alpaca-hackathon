"""
H3 strategy engine: defined-risk short premium on SPY, walk-forward.

Design is fixed by research/PREREGISTRATION_R1.md sections 4, 5 and 7, plus
amendment A1. Nothing here may be tuned to improve a result; the only fitted
quantity is the VRP entry threshold, chosen inside in-sample windows only.

Position: iron condor, short strikes at the configured delta, wings 0.65% of
spot either side. Exit at 50% of max profit or at 2 DTE, whichever comes first.
Risk per position capped at 1.0% of equity, one position at a time.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import pricing as P

WING_PCT = 0.0065          # amendment A1.1
RISK_PER_POSITION = 0.01   # section 5
PROFIT_TARGET = 0.50       # section 4
EXIT_DTE = 2               # section 4
COST_PCT = 0.015           # section 7, measured
STARTING_EQUITY = 100_000.0

THRESHOLD_GRID = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]  # section 4, the only fit


@dataclass(frozen=True)
class TrialConfig:
    name: str
    use_vrp_gate: bool
    use_regime_gate: bool
    short_delta: float = 0.16
    dte_target: int = 10
    dte_min: int = 7
    dte_max: int = 14


TRIALS = [
    TrialConfig("T1 baseline", False, False),
    TrialConfig("T2 vrp gate", True, False),
    TrialConfig("T3 regime gate", False, True),
    TrialConfig("T4 both gates", True, True),
    TrialConfig("T5 both, 10 delta", True, True, short_delta=0.10),
    TrialConfig("T6 both, 21-45 DTE", True, True, dte_target=33, dte_min=21, dte_max=45),
]


@dataclass
class Condor:
    entry_date: pd.Timestamp
    expiry: pd.Timestamp
    short_call: float
    long_call: float
    short_put: float
    long_put: float
    credit: float               # per contract, dollars per share
    wing: float
    contracts: int
    max_loss_per_contract: float

    @property
    def notional_risk(self) -> float:
        return self.max_loss_per_contract * 100.0 * self.contracts


def _find_strike_for_delta(S: float, dte: int, base_iv: float, skew: P.SkewModel,
                           target_delta: float, is_call: bool) -> float:
    """Scan $1 strikes and return the one whose model delta is closest to target."""
    T = dte / P.DAYS_PER_YEAR
    lo, hi = int(S * 0.80), int(S * 1.20)
    best_k, best_err = None, 1e9
    for K in range(lo, hi + 1):
        sigma = skew.iv(S, float(K), base_iv)
        d = P.bs_delta(S, float(K), T, sigma, is_call)
        err = abs(abs(d) - target_delta)
        if err < best_err:
            best_err, best_k = err, float(K)
    return best_k


def value_condor(c: Condor, S: float, dte: int, vix: float, vix3m: float,
                 skew: P.SkewModel) -> float:
    """Cost per contract to buy the condor back. Positive number."""
    if dte <= 0:
        # Settle at intrinsic.
        sc = max(S - c.short_call, 0.0)
        lc = max(S - c.long_call, 0.0)
        sp = max(c.short_put - S, 0.0)
        lp = max(c.long_put - S, 0.0)
        return (sc - lc) + (sp - lp)
    T = dte / P.DAYS_PER_YEAR
    base = P.atm_iv(vix, vix3m, dte)
    v = 0.0
    v += P.bs_price(S, c.short_call, T, skew.iv(S, c.short_call, base), True)
    v -= P.bs_price(S, c.long_call, T, skew.iv(S, c.long_call, base), True)
    v += P.bs_price(S, c.short_put, T, skew.iv(S, c.short_put, base), False)
    v -= P.bs_price(S, c.long_put, T, skew.iv(S, c.long_put, base), False)
    return v


def build_condor(entry_date: pd.Timestamp, expiry: pd.Timestamp, S: float, dte: int,
                 vix: float, vix3m: float, skew: P.SkewModel, cfg: TrialConfig,
                 equity: float, credit_haircut: float = 0.0) -> Condor | None:
    base = P.atm_iv(vix, vix3m, dte)
    sc = _find_strike_for_delta(S, dte, base, skew, cfg.short_delta, True)
    sp = _find_strike_for_delta(S, dte, base, skew, cfg.short_delta, False)
    wing = max(round(S * WING_PCT), 1.0)
    lc, lp = sc + wing, sp - wing
    if sp >= sc:
        return None

    T = dte / P.DAYS_PER_YEAR
    credit = (
        P.bs_price(S, sc, T, skew.iv(S, sc, base), True)
        - P.bs_price(S, lc, T, skew.iv(S, lc, base), True)
        + P.bs_price(S, sp, T, skew.iv(S, sp, base), False)
        - P.bs_price(S, lp, T, skew.iv(S, lp, base), False)
    )
    credit *= (1.0 - credit_haircut)
    if credit <= 0.01:
        return None

    max_loss = wing - credit
    if max_loss <= 0:
        return None
    contracts = int((equity * RISK_PER_POSITION) // (max_loss * 100.0))
    if contracts < 1:
        return None

    return Condor(entry_date, expiry, sc, lc, sp, lp, credit, wing, contracts, max_loss)


def _pick_expiry(day: pd.Timestamp, expiries: np.ndarray, cfg: TrialConfig):
    """Nearest listed expiry inside the configured DTE band."""
    for exp in expiries:
        dte = (exp - day).days
        if cfg.dte_min <= dte <= cfg.dte_max:
            return exp, dte
    return None, None


def run_strategy(panel: pd.DataFrame, expiries: np.ndarray, skew: P.SkewModel,
                 cfg: TrialConfig, threshold: float,
                 cost_pct: float = COST_PCT,
                 credit_haircut: float = 0.0) -> dict:
    """
    Day loop over a panel indexed by date with columns:
      close, vix, vix3m, vrp_signal, contango

    Returns equity curve, trade list and the refusal count. Refusals are a
    first-class output, not a side effect: section 9 prediction P6.
    """
    equity = STARTING_EQUITY
    pos: Condor | None = None
    entry_cost_paid = 0.0
    equity_curve, trades = [], []
    refusals = {"vrp": 0, "regime": 0, "no_expiry": 0, "unsized": 0}
    opportunities = 0

    for day, row in panel.iterrows():
        S, vix, vix3m = row["close"], row["vix"], row["vix3m"]

        if pos is not None:
            dte = (pos.expiry - day).days
            buyback = value_condor(pos, S, dte, vix, vix3m, skew)
            unreal = (pos.credit - buyback) * 100.0 * pos.contracts
            should_exit = (buyback <= pos.credit * (1.0 - PROFIT_TARGET)) or (dte <= EXIT_DTE)
            if should_exit:
                exit_cost = pos.credit * cost_pct * 100.0 * pos.contracts
                pnl = unreal - entry_cost_paid - exit_cost
                equity += pnl
                trades.append({
                    "entry": pos.entry_date, "exit": day, "expiry": pos.expiry,
                    "credit": pos.credit, "buyback": buyback,
                    "contracts": pos.contracts, "pnl": pnl,
                    "max_loss": pos.notional_risk,
                    "r_multiple": pnl / pos.notional_risk if pos.notional_risk else np.nan,
                    "held_days": (day - pos.entry_date).days,
                })
                pos = None
                equity_curve.append({"date": day, "equity": equity})
                continue
            equity_curve.append({"date": day, "equity": equity + unreal - entry_cost_paid})
            continue

        # Flat: consider entering.
        opportunities += 1
        if cfg.use_regime_gate and not row["contango"]:
            refusals["regime"] += 1
            equity_curve.append({"date": day, "equity": equity})
            continue
        if cfg.use_vrp_gate and not (row["vrp_signal"] >= threshold):
            refusals["vrp"] += 1
            equity_curve.append({"date": day, "equity": equity})
            continue

        exp, dte = _pick_expiry(day, expiries, cfg)
        if exp is None:
            refusals["no_expiry"] += 1
            equity_curve.append({"date": day, "equity": equity})
            continue

        c = build_condor(day, exp, S, dte, vix, vix3m, skew, cfg, equity, credit_haircut)
        if c is None:
            refusals["unsized"] += 1
            equity_curve.append({"date": day, "equity": equity})
            continue

        pos = c
        entry_cost_paid = c.credit * cost_pct * 100.0 * c.contracts
        equity_curve.append({"date": day, "equity": equity - entry_cost_paid})

    eq = pd.DataFrame(equity_curve).set_index("date")["equity"] if equity_curve else pd.Series(dtype=float)
    return {
        "equity": eq,
        "trades": pd.DataFrame(trades),
        "refusals": refusals,
        "opportunities": opportunities,
        "final_equity": equity,
    }


def build_expiries(index: pd.DatetimeIndex) -> np.ndarray:
    """
    SPY lists Monday, Wednesday and Friday expiries in the modern era. Using
    every Friday only would understate how often a 7 to 14 DTE tenor is
    available; using all three is closer to reality for the recent sample and
    conservative for the early one.
    """
    days = pd.date_range(index.min(), index.max() + pd.Timedelta(days=60), freq="D")
    return np.array([d for d in days if d.weekday() in (0, 2, 4)])
