"""
Option pricing for H3.

Historical per-strike implied vol is not available for the development window
(2016 to 2022), so option prices there must be MODELLED. Pre-registration
section 6 fixes the model and, more importantly, fixes the gate that decides
whether the model is good enough to report H3 at all.

Three pieces:
  1. Black-Scholes, standard.
  2. An ATM term structure built from VIX (30 day) and VIX3M (93 day), so a
     7 to 14 day option is not priced with a 30 day vol.
  3. A skew multiplier in log-moneyness, calibrated from real collected chain
     snapshots. Equity index options have a steep put skew; pricing a condor
     with flat vol would systematically misprice the exact wings we sell.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DAYS_PER_YEAR = 365.0
RATE = 0.04
DIVIDEND_YIELD = 0.012

# VIX is the square root of a 30 day VARIANCE SWAP rate, computed by integrating
# option prices across all strikes weighted by 1/K^2. That integral is inflated
# by the put skew, so VIX sits structurally ABOVE the at-the-money implied vol of
# the same tenor. Treating VIX as ATM IV overstates vol and overprices everything.
#
# Measured by inverting Black-Scholes on 3,513 real near-ATM SPY option bars
# (backtest/diagnose_gate.py): market ATM IV / VIX = 0.853 median, sd 0.106, and
# stable across tenor (0.850 / 0.848 / 0.856) and year (0.864 / 0.846 / 0.842).
#
# The constant below is fitted on 2024 ONLY so that validation on 2025 to 2026 is
# genuinely out of sample for this correction. Do not refit it on the full sample.
VIX_ATM_RATIO = 0.8638
VIX_ATM_RATIO_FIT_YEAR = 2024


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(S: float, K: float, T: float, sigma: float, is_call: bool,
             r: float = RATE, q: float = DIVIDEND_YIELD) -> float:
    """Black-Scholes price. T in years, sigma as a decimal (0.15 = 15%)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = (S - K) if is_call else (K - S)
        return max(intrinsic, 0.0)
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    if is_call:
        return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)


def bs_delta(S: float, K: float, T: float, sigma: float, is_call: bool,
             r: float = RATE, q: float = DIVIDEND_YIELD) -> float:
    if T <= 0 or sigma <= 0:
        if is_call:
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrt_t)
    if is_call:
        return math.exp(-q * T) * _norm_cdf(d1)
    return -math.exp(-q * T) * _norm_cdf(-d1)


def implied_vol(price: float, S: float, K: float, T: float, is_call: bool,
                r: float = RATE, q: float = DIVIDEND_YIELD) -> float:
    """
    Invert Black-Scholes for sigma by bisection. Returns nan if the price is
    outside the no-arbitrage bounds, which happens with stale or crossed quotes.
    """
    if T <= 0 or price <= 0:
        return float("nan")
    intrinsic = max((S * math.exp(-q * T) - K * math.exp(-r * T)) if is_call
                    else (K * math.exp(-r * T) - S * math.exp(-q * T)), 0.0)
    if price < intrinsic - 1e-6:
        return float("nan")
    lo, hi = 1e-4, 5.0
    if bs_price(S, K, T, hi, is_call, r, q) < price:
        return float("nan")
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, mid, is_call, r, q) < price:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def atm_iv(vix: float, vix3m: float, dte: float,
           ratio: float = VIX_ATM_RATIO) -> float:
    """
    ATM implied vol for a given tenor, as a decimal.

    Interpolates TOTAL VARIANCE linearly in time between the 30 day (VIX) and
    93 day (VIX3M) points, which is the standard construction, then converts
    back to a vol. Extrapolates flat in variance-per-day below 30 days rather
    than letting a linear fit go negative.

    `ratio` converts the variance-swap level that VIX reports into an ATM level.
    See VIX_ATM_RATIO above. Pass ratio=1.0 to disable the correction, which is
    what the first (failed) validation run effectively did.
    """
    dte = max(float(dte), 1.0)
    vix = vix * ratio
    vix3m = vix3m * ratio
    t30, t93 = 30.0, 93.0
    var30 = (vix / 100.0) ** 2 * (t30 / DAYS_PER_YEAR)
    var93 = (vix3m / 100.0) ** 2 * (t93 / DAYS_PER_YEAR)

    if dte <= t30:
        # Flat variance rate below the VIX tenor.
        var = var30 * (dte / t30)
    elif dte >= t93:
        var = var93 * (dte / t93)
    else:
        w = (dte - t30) / (t93 - t30)
        var = var30 + w * (var93 - var30)

    years = dte / DAYS_PER_YEAR
    return math.sqrt(max(var, 1e-12) / years)


@dataclass
class SkewModel:
    """
    IV multiplier as a quadratic in log-moneyness k = ln(K/S).

        iv(K) = atm_iv * (1 + b*k + c*k^2)

    Calibrated on real chain snapshots and normalised so the multiplier is 1.0
    at the money. Clamped to keep the model from producing absurd vols far out
    in the tails where the fit has no support.
    """

    b: float
    c: float
    k_min: float
    k_max: float
    n_points: int
    tenor_label: str

    def multiplier(self, k: float) -> float:
        k_clamped = min(max(k, self.k_min), self.k_max)
        m = 1.0 + self.b * k_clamped + self.c * k_clamped * k_clamped
        return float(min(max(m, 0.35), 3.0))

    def iv(self, S: float, K: float, base_atm_iv: float) -> float:
        return base_atm_iv * self.multiplier(math.log(K / S))

    def describe(self) -> str:
        return (
            f"skew[{self.tenor_label}]: iv/atm = 1 {self.b:+.4f}k {self.c:+.4f}k^2  "
            f"(n={self.n_points}, k in [{self.k_min:+.4f}, {self.k_max:+.4f}])"
        )


def fit_skew(log_moneyness, ivs, tenor_label: str = "") -> SkewModel:
    """
    Least-squares fit of iv/atm against k and k^2.

    ATM iv is taken as the fitted value at k = 0 rather than the nearest
    contract, so a single odd quote near the money cannot rescale the whole
    surface.
    """
    k = np.asarray(log_moneyness, dtype=float)
    v = np.asarray(ivs, dtype=float)
    ok = np.isfinite(k) & np.isfinite(v) & (v > 0)
    k, v = k[ok], v[ok]
    if len(k) < 20:
        raise ValueError(f"not enough points to fit skew: {len(k)}")

    # Quadratic in k, then normalise so the intercept is 1.0.
    coeffs = np.polyfit(k, v, 2)  # c2*k^2 + c1*k + c0
    c2, c1, c0 = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])
    if c0 <= 0:
        raise ValueError("fitted ATM iv is non-positive, refusing to build a skew model")

    return SkewModel(
        b=c1 / c0,
        c=c2 / c0,
        k_min=float(np.percentile(k, 1)),
        k_max=float(np.percentile(k, 99)),
        n_points=int(len(k)),
        tenor_label=tenor_label or "unspecified",
    )


def parse_occ(symbol: str) -> tuple[str, str, bool, float]:
    """
    Split an OCC symbol into (root, yymmdd, is_call, strike).

    Format: ROOT + YYMMDD + C|P + strike * 1000, zero padded to 8.
    """
    i = 0
    while i < len(symbol) and symbol[i].isalpha():
        i += 1
    root, body = symbol[:i], symbol[i:]
    return root, body[:6], body[6] == "C", int(body[7:]) / 1000.0
