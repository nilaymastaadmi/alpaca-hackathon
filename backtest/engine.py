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
class StrategyParams:
    """
    Every knob, with defaults that exactly reproduce the committed H3 result.
    Changing a default here silently invalidates RESULT_H3.md, so do not.
    """
    max_concurrent: int = 1
    risk_per_position: float = RISK_PER_POSITION
    wing_pct: float = WING_PCT
    profit_target: float = PROFIT_TARGET
    exit_dte: int = EXIT_DTE
    structure: str = "condor"          # condor | put_spread | call_spread
    stop_loss_mult: float | None = None   # exit if buyback > credit * this
    one_per_expiry: bool = False       # stagger, a risk control at size
    # One decision per day. The engine runs on DAILY bars, so re-entering on the
    # same close that just closed a position uses one price for both sides of a
    # round trip, which flatters the result. Default False keeps the committed
    # H3 baseline reproducible; it is also the conservative choice.
    allow_same_day_reentry: bool = False


DEFAULT_PARAMS = StrategyParams()


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
    short_call: float | None
    long_call: float | None
    short_put: float | None
    long_put: float | None
    credit: float               # per contract, dollars per share
    wing: float
    contracts: int
    max_loss_per_contract: float

    @property
    def notional_risk(self) -> float:
        return self.max_loss_per_contract * 100.0 * self.contracts


_STRIKE_CACHE: dict = {}


def _find_strike_for_delta(S: float, dte: int, base_iv: float, skew: P.SkewModel,
                           target_delta: float, is_call: bool) -> float:
    """
    Scan $1 strikes and return the one whose model delta is closest to target.

    Memoised: the exploratory sweep re-runs the same (S, dte, iv) combinations
    across many parameter sets, and without this the scan dominates runtime.
    """
    key = (round(S, 1), dte, round(base_iv, 4), round(target_delta, 3), is_call)
    hit = _STRIKE_CACHE.get(key)
    if hit is not None:
        return hit
    T = dte / P.DAYS_PER_YEAR
    lo, hi = int(S * 0.80), int(S * 1.20)
    best_k, best_err = None, 1e9
    for K in range(lo, hi + 1):
        sigma = skew.iv(S, float(K), base_iv)
        d = P.bs_delta(S, float(K), T, sigma, is_call)
        err = abs(abs(d) - target_delta)
        if err < best_err:
            best_err, best_k = err, float(K)
    _STRIKE_CACHE[key] = best_k
    return best_k


def value_condor(c: Condor, S: float, dte: int, vix: float, vix3m: float,
                 skew: P.SkewModel) -> float:
    """
    Cost per contract to buy the structure back. Positive number.
    A None strike means that side of the structure is absent (vertical spreads).
    """
    if dte <= 0:
        v = 0.0
        if c.short_call is not None:
            v += max(S - c.short_call, 0.0) - max(S - c.long_call, 0.0)
        if c.short_put is not None:
            v += max(c.short_put - S, 0.0) - max(c.long_put - S, 0.0)
        return v
    T = dte / P.DAYS_PER_YEAR
    base = P.atm_iv(vix, vix3m, dte)
    v = 0.0
    if c.short_call is not None:
        v += P.bs_price(S, c.short_call, T, skew.iv(S, c.short_call, base), True)
        v -= P.bs_price(S, c.long_call, T, skew.iv(S, c.long_call, base), True)
    if c.short_put is not None:
        v += P.bs_price(S, c.short_put, T, skew.iv(S, c.short_put, base), False)
        v -= P.bs_price(S, c.long_put, T, skew.iv(S, c.long_put, base), False)
    return v


def build_condor(entry_date: pd.Timestamp, expiry: pd.Timestamp, S: float, dte: int,
                 vix: float, vix3m: float, skew: P.SkewModel, cfg: TrialConfig,
                 equity: float, credit_haircut: float = 0.0,
                 params: StrategyParams = DEFAULT_PARAMS) -> Condor | None:
    base = P.atm_iv(vix, vix3m, dte)
    wing = max(round(S * params.wing_pct), 1.0)
    T = dte / P.DAYS_PER_YEAR

    want_call = params.structure in ("condor", "call_spread")
    want_put = params.structure in ("condor", "put_spread")

    sc = lc = sp = lp = None
    credit = 0.0
    if want_call:
        sc = _find_strike_for_delta(S, dte, base, skew, cfg.short_delta, True)
        lc = sc + wing
        credit += P.bs_price(S, sc, T, skew.iv(S, sc, base), True)
        credit -= P.bs_price(S, lc, T, skew.iv(S, lc, base), True)
    if want_put:
        sp = _find_strike_for_delta(S, dte, base, skew, cfg.short_delta, False)
        lp = sp - wing
        credit += P.bs_price(S, sp, T, skew.iv(S, sp, base), False)
        credit -= P.bs_price(S, lp, T, skew.iv(S, lp, base), False)

    if want_call and want_put and sp >= sc:
        return None
    credit *= (1.0 - credit_haircut)
    if credit <= 0.01:
        return None

    # A condor can only lose on one side at a time, so max loss is one wing.
    max_loss = wing - credit
    if max_loss <= 0:
        return None
    contracts = int((equity * params.risk_per_position) // (max_loss * 100.0))
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
                 credit_haircut: float = 0.0,
                 params: StrategyParams = DEFAULT_PARAMS) -> dict:
    """
    Day loop over a panel indexed by date with columns:
      close, vix, vix3m, vrp_signal, contango

    Supports up to params.max_concurrent open positions. With the default
    max_concurrent=1 this reproduces the committed H3 result exactly.

    Refusals are a first-class output, not a side effect: section 9 prediction P6.
    """
    equity = STARTING_EQUITY
    open_pos: list[tuple[Condor, float]] = []   # (condor, entry_cost_paid)
    equity_curve, trades = [], []
    refusals = {"vrp": 0, "regime": 0, "no_expiry": 0, "unsized": 0}
    opportunities = 0
    at_capacity = 0   # kept OUT of refusals: being busy is not a refusal
    same_day_reentry = 0

    for day, row in panel.iterrows():
        S, vix, vix3m = row["close"], row["vix"], row["vix3m"]

        # 1. Manage every open position.
        still_open, unreal_total, cost_carried = [], 0.0, 0.0
        closed_today = False
        for pos, entry_cost in open_pos:
            dte = (pos.expiry - day).days
            buyback = value_condor(pos, S, dte, vix, vix3m, skew)
            unreal = (pos.credit - buyback) * 100.0 * pos.contracts
            hit_target = buyback <= pos.credit * (1.0 - params.profit_target)
            hit_stop = (params.stop_loss_mult is not None
                        and buyback >= pos.credit * params.stop_loss_mult)
            if hit_target or hit_stop or dte <= params.exit_dte:
                exit_cost = pos.credit * cost_pct * 100.0 * pos.contracts
                pnl = unreal - entry_cost - exit_cost
                equity += pnl
                trades.append({
                    "entry": pos.entry_date, "exit": day, "expiry": pos.expiry,
                    "credit": pos.credit, "buyback": buyback,
                    "contracts": pos.contracts, "pnl": pnl,
                    "max_loss": pos.notional_risk,
                    "r_multiple": pnl / pos.notional_risk if pos.notional_risk else np.nan,
                    "held_days": (day - pos.entry_date).days,
                    "exit_reason": ("target" if hit_target else
                                    "stop" if hit_stop else "dte"),
                })
                closed_today = True
            else:
                still_open.append((pos, entry_cost))
                unreal_total += unreal
                cost_carried += entry_cost
        open_pos = still_open

        # 2. Consider one new entry per day.
        if closed_today and not params.allow_same_day_reentry:
            same_day_reentry += 1   # counted, not taken
        elif len(open_pos) >= params.max_concurrent:
            at_capacity += 1
        else:
            opportunities += 1
            blocked = None
            if cfg.use_regime_gate and not row["contango"]:
                blocked = "regime"
            elif cfg.use_vrp_gate and not (row["vrp_signal"] >= threshold):
                blocked = "vrp"
            if blocked:
                refusals[blocked] += 1
            else:
                exp, dte = _pick_expiry(day, expiries, cfg)
                if params.one_per_expiry and exp is not None:
                    if any(p.expiry == exp for p, _ in open_pos):
                        exp = None
                if exp is None:
                    refusals["no_expiry"] += 1
                else:
                    c = build_condor(day, exp, S, dte, vix, vix3m, skew, cfg,
                                     equity, credit_haircut, params)
                    if c is None:
                        refusals["unsized"] += 1
                    else:
                        ec = c.credit * cost_pct * 100.0 * c.contracts
                        open_pos.append((c, ec))
                        cost_carried += ec

        equity_curve.append({"date": day, "equity": equity + unreal_total - cost_carried})

    eq = (pd.DataFrame(equity_curve).set_index("date")["equity"]
          if equity_curve else pd.Series(dtype=float))
    return {
        "equity": eq,
        "trades": pd.DataFrame(trades),
        "refusals": refusals,
        "opportunities": opportunities,
        "at_capacity": at_capacity,
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
