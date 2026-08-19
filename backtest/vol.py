"""
Volatility measurement for R1.

Everything here is in ANNUALISED VOLATILITY POINTS to match VIX's own units
(VIX 15.84 means 15.84%). Mixing decimal and percent units is the most common
silent bug in vol work, so the convention is stated once and enforced by the
function names: anything returning vol returns percent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


def realised_vol_forward(close: pd.Series, horizon: int = 21) -> pd.Series:
    """
    Annualised realised vol over the NEXT `horizon` trading days, in percent.

    Indexed at day t, using returns from t+1 through t+horizon. This is the
    quantity VIX at day t is a forecast of, so aligning them is what makes the
    VRP subtraction meaningful.
    """
    r = log_returns(close)
    # shift(-1) so the window starts the day AFTER t
    fwd = r.shift(-1).rolling(horizon).std().shift(-(horizon - 1))
    return fwd * np.sqrt(TRADING_DAYS) * 100.0


def realised_vol_trailing(close: pd.Series, window: int) -> pd.Series:
    """Annualised trailing realised vol in percent, for HAR components."""
    r = log_returns(close)
    return r.rolling(window).std() * np.sqrt(TRADING_DAYS) * 100.0


def har_components(close: pd.Series) -> pd.DataFrame:
    """
    HAR-RV inputs (Corsi 2009): daily, weekly, monthly realised vol.

    Used as the realised-vol FORECAST in the live agent. H1 in the
    pre-registration deliberately uses VIX minus SUBSEQUENT realised vol
    instead, because that needs no model and so cannot be blamed on one.
    """
    return pd.DataFrame(
        {
            "rv_d": realised_vol_trailing(close, 1),
            "rv_w": realised_vol_trailing(close, 5),
            "rv_m": realised_vol_trailing(close, 22),
        }
    )


def vrp(vix_close: pd.Series, spy_close: pd.Series, horizon: int = 21) -> pd.DataFrame:
    """
    Volatility risk premium, in vol points: VIX(t) minus realised vol over
    (t, t+horizon]. Positive means implied exceeded what actually happened,
    which is the premium a seller collects.
    """
    rv_fwd = realised_vol_forward(spy_close, horizon)
    df = pd.DataFrame({"vix": vix_close, "rv_fwd": rv_fwd}).dropna()
    df["vrp"] = df["vix"] - df["rv_fwd"]
    return df


def term_structure(vix: pd.Series, vix3m: pd.Series) -> pd.DataFrame:
    """
    VIX / VIX3M ratio. Below 1.0 is contango (calm, tailwind for short premium);
    at or above 1.0 is backwardation (stress, stand down).
    """
    df = pd.DataFrame({"vix": vix, "vix3m": vix3m}).dropna()
    df["ratio"] = df["vix"] / df["vix3m"]
    df["contango"] = df["ratio"] < 1.0
    return df
