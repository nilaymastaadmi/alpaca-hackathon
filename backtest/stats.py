"""
Statistics for R1, including the multiple-testing arithmetic that sets the bars.

The formulas here are the ones the pre-registration commits to. They are
implemented once, in code, so the bars cannot drift between what was registered
and what is reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sharpe_se(sharpe: float, years: float) -> float:
    """
    Standard error of an annualised Sharpe: sqrt((1 + SR^2 / 2) / T), T in
    CALENDAR YEARS.

    There is deliberately no frequency term. Sampling more finely improves the
    volatility estimate, not the drift estimate. propdesk R2 corrected exactly
    this mistake, and the consequence is a hard floor on how short a window can
    resolve any Sharpe at all.
    """
    return math.sqrt((1.0 + (sharpe ** 2) / 2.0) / years)


def expected_max_null(n_trials: int) -> float:
    """
    Expected maximum of n independent standard normal draws, approximated as
    sqrt(2 ln n). This is what turns a trial count into a higher bar.
    """
    if n_trials < 2:
        return 0.0
    return math.sqrt(2.0 * math.log(n_trials))


def development_bar(n_trials: int, years: float, assumed_sharpe: float = 0.5) -> float:
    """Pre-registration section 8 development bar."""
    return expected_max_null(n_trials) * sharpe_se(assumed_sharpe, years)


def holdout_bar(years: float, assumed_sharpe: float = 0.5, z: float = 1.645) -> float:
    """Pre-registration section 8 holdout bar, single shot, one-sided 5%."""
    return z * sharpe_se(assumed_sharpe, years)


@dataclass
class Summary:
    n: int
    mean: float
    std: float
    t_stat: float
    p_one_sided: float

    def describe(self, unit: str = "") -> str:
        return (
            f"n={self.n}, mean={self.mean:+.2f}{unit}, sd={self.std:.2f}, "
            f"t={self.t_stat:+.2f}, one-sided p={self.p_one_sided:.4f}"
        )


def _normal_sf(z: float) -> float:
    """Survival function of the standard normal, no scipy dependency."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def summarise(x: pd.Series) -> Summary:
    """
    Mean, t statistic and one-sided p for a series.

    NOTE on the t statistic: overlapping forward windows make consecutive
    observations strongly autocorrelated, so the naive t is inflated. This is
    reported alongside a Newey-West corrected version wherever it matters, and
    the naive figure must never be quoted alone.
    """
    x = x.dropna()
    n = len(x)
    mean = float(x.mean())
    std = float(x.std(ddof=1))
    t = mean / (std / math.sqrt(n)) if n > 1 and std > 0 else float("nan")
    return Summary(n=n, mean=mean, std=std, t_stat=t, p_one_sided=_normal_sf(t))


def newey_west_t(x: pd.Series, lags: int) -> float:
    """
    t statistic with a Newey-West HAC correction.

    Required here because H1 uses 21-day FORWARD realised vol sampled daily, so
    each observation shares 20 of its 21 days with its neighbour. Ignoring that
    would overstate significance by roughly sqrt(21). Reporting the naive t on
    overlapping data is the exact error that makes vol-premium studies look
    stronger than they are.
    """
    x = x.dropna().to_numpy()
    n = len(x)
    if n < 2:
        return float("nan")
    mean = x.mean()
    e = x - mean
    gamma0 = float(e @ e) / n
    var = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1.0)
        cov = float(e[lag:] @ e[:-lag]) / n
        var += 2.0 * w * cov
    if var <= 0:
        return float("nan")
    se = math.sqrt(var / n)
    return mean / se


def annualised_sharpe(daily_returns: pd.Series) -> float:
    r = daily_returns.dropna()
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_drawdown(equity: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a negative fraction."""
    eq = equity.dropna()
    if eq.empty:
        return float("nan")
    peak = eq.cummax()
    return float((eq / peak - 1.0).min())


def profit_factor(pnl: pd.Series) -> float:
    wins = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    return float(wins / losses) if losses > 0 else float("inf")
