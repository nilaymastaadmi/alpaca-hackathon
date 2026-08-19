# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
Why did the pricing gate fail at 26.78% with a +26.45% overprice bias?

Hypothesis: VIX is not ATM implied vol. VIX is the square root of a 30 day
variance swap rate, computed by integrating option prices across ALL strikes
weighted by 1/K^2. That integral is inflated by the put skew, so VIX sits
structurally ABOVE the at-the-money implied vol of the same tenor. Feeding VIX
in as if it were ATM IV overprices every option, and then the skew multiplier
compounds the error further out.

Test: invert Black-Scholes on real near-ATM SPY option bars to recover the
market's actual ATM IV, then compare against VIX on the same date. If the
hypothesis holds, the ratio ATM_IV / VIX should sit meaningfully below 1.0 and
be reasonably stable.

This changes nothing on its own. It decides whether the fix is principled (a
known property of VIX, correctable) or whether the whole modelled approach
should be abandoned for real option data.

Run:  uv run backtest/diagnose_gate.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import pricing as P  # noqa: E402
from calibrate_and_validate import build_validation_symbols, fetch_option_bars  # noqa: E402


def main() -> None:
    print("=" * 72)
    print("DIAGNOSTIC: is VIX being misused as ATM implied vol?")
    print("=" * 72)

    series = D.load_all()
    spy, vix, vix3m = series["SPY"], series["VIX"], series["VIX3M"]

    symbols = build_validation_symbols(spy)
    print(f"\nfetching bars for {len(symbols)} contracts")
    bars = fetch_option_bars(symbols)
    print(f"  {len(bars)} bars")

    spy_close, vix_close, vix3m_close = spy["close"], vix["close"], vix3m["close"]

    recs = []
    for row in bars.itertuples(index=False):
        d = row.date
        if d not in spy_close.index or d not in vix_close.index:
            continue
        _, yymmdd, is_call, strike = P.parse_occ(row.symbol)
        exp = datetime.strptime(yymmdd, "%y%m%d").date()
        dte = (exp - d.date()).days
        if dte < 5 or dte > 60 or row.close <= 0.10:
            continue
        S = float(spy_close.loc[d])
        mny = strike / S
        # Near the money only: that is where IV is well determined, because
        # vega is largest and the quote is most liquid.
        if not (0.98 <= mny <= 1.02):
            continue
        iv = P.implied_vol(row.close, S, strike, dte / P.DAYS_PER_YEAR, is_call)
        if not np.isfinite(iv) or iv <= 0.01 or iv > 2.0:
            continue
        recs.append({
            "date": d, "dte": dte, "moneyness": mny,
            "market_iv": iv * 100.0,
            "vix": float(vix_close.loc[d]),
            "vix3m": float(vix3m_close.loc[d]) if d in vix3m_close.index else np.nan,
            "model_atm_iv": P.atm_iv(float(vix_close.loc[d]),
                                     float(vix3m_close.loc[d]) if d in vix3m_close.index
                                     else float(vix_close.loc[d]), dte) * 100.0,
        })

    df = pd.DataFrame(recs).dropna()
    if df.empty:
        print("no near-ATM observations recovered")
        sys.exit(1)

    df["ratio_to_vix"] = df["market_iv"] / df["vix"]
    df["ratio_to_model"] = df["market_iv"] / df["model_atm_iv"]

    print(f"\nrecovered market ATM IV from {len(df)} near-ATM option bars")
    print(f"  market ATM IV  median {df['market_iv'].median():6.2f}")
    print(f"  VIX            median {df['vix'].median():6.2f}")
    print(f"  model ATM IV   median {df['model_atm_iv'].median():6.2f}")

    print(f"\n  ratio market_ATM_IV / VIX:")
    for q in (0.10, 0.25, 0.50, 0.75, 0.90):
        print(f"    p{int(q * 100):02d}  {df['ratio_to_vix'].quantile(q):.4f}")
    print(f"    mean {df['ratio_to_vix'].mean():.4f}   sd {df['ratio_to_vix'].std():.4f}")

    print(f"\n  ratio market_ATM_IV / model_ATM_IV (what the model actually used):")
    for q in (0.10, 0.25, 0.50, 0.75, 0.90):
        print(f"    p{int(q * 100):02d}  {df['ratio_to_model'].quantile(q):.4f}")

    print("\n  by DTE bucket (median ratio to VIX):")
    df["dte_bucket"] = pd.cut(df["dte"], [0, 14, 30, 60], labels=["5-14", "15-30", "31-60"])
    for b, g in df.groupby("dte_bucket", observed=True):
        print(f"    {str(b):>6}  n={len(g):>5}  ratio={g['ratio_to_vix'].median():.4f}")

    print("\n  by year (is the ratio stable over time?):")
    df["year"] = df["date"].dt.year
    for y, g in df.groupby("year"):
        print(f"    {y}  n={len(g):>5}  ratio={g['ratio_to_vix'].median():.4f}")

    med = df["ratio_to_vix"].median()
    sd = df["ratio_to_vix"].std()
    print("\n" + "-" * 72)
    if med < 0.95:
        print(f"  CONFIRMED. Market ATM IV runs at {med:.3f} of VIX "
              f"(sd {sd:.3f}).")
        print(f"  Using VIX directly as ATM IV overstates vol by "
              f"{(1 / med - 1) * 100:.1f}%, which explains a "
              f"+{(1 / med - 1) * 100:.0f}% price bias almost exactly.")
        print("  This is a known property of VIX, so the correction is principled,")
        print("  not a tune-until-it-passes adjustment.")
    else:
        print(f"  NOT CONFIRMED. Ratio is {med:.3f}, so VIX is not the main error.")
        print("  The overprice bias comes from somewhere else; do not 'fix' this.")
    print("-" * 72)


if __name__ == "__main__":
    main()
