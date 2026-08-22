# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
What does the DEPLOYED config (D1: 5 concurrent, 3% risk, threshold=1.0,
both gates, 7-14 DTE) actually imply for a 4.5 trading-day window?

DEPLOYMENT_DECISIONS.md D1 currently states "+$700 to +$1,000 expected" and
"10 to 15 trades" without a derivation. An independent audit flagged this as
not reconciling with trade-count math and proposed a much wider, centered-near-
zero range instead. Re-deriving here rather than copying either the original
guess or the audit's number on faith: run the exact deployed config across the
full DEVELOPMENT window (never the sealed holdout), then slice the resulting
trade list into every possible ~4.5 trading-day window and look at the actual
empirical distribution of P&L, rather than asserting a point estimate.

Development window only. Holdout stays sealed.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import data as D
import engine as E
from run_h3 import build_panel, load_skew

DEPLOYED_THRESHOLD = 1.0  # matches agent/config.py Config.vrp_threshold

def main():
    series = D.load_all()
    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    skew = load_skew()

    cfg = E.TrialConfig("deployed", use_vrp_gate=True, use_regime_gate=True,
                        short_delta=0.16, dte_target=10, dte_min=7, dte_max=14)
    params = E.StrategyParams(max_concurrent=5, risk_per_position=0.03,
                              stop_loss_mult=2.0, one_per_expiry=True)

    panel = build_panel(spy, vix, vix3m, cfg.dte_target)
    expiries = E.build_expiries(panel.index)
    res = E.run_strategy(panel, expiries, skew, cfg, DEPLOYED_THRESHOLD, params=params)
    trades = res["trades"]
    years = (panel.index.max() - panel.index.min()).days / 365.25

    print(f"development window: {years:.2f} years, threshold={DEPLOYED_THRESHOLD}")
    print(f"total trades: {len(trades)}  ({len(trades)/years:.1f}/year)")
    print(f"total pnl over full window: ${trades['pnl'].sum():,.2f}")
    print(f"win rate: {(trades['pnl']>0).mean()*100:.1f}%")
    print(f"median trade pnl: ${trades['pnl'].median():,.2f}")
    print(f"mean trade pnl: ${trades['pnl'].mean():,.2f}")
    print(f"worst trade: ${trades['pnl'].min():,.2f}   best trade: ${trades['pnl'].max():,.2f}")

    # Slice into every ~4.5 trading-day (5 session) rolling window by ENTRY date,
    # summing pnl of trades entered within it (a trade may close later; this
    # measures capital PUT AT RISK within the window, which is what a judge's
    # 4.5 day snapshot would actually see initiated).
    trades = trades.copy()
    trades["entry"] = pd.to_datetime(trades["entry"])
    trading_days = panel.index.sort_values()
    window_pnls = []
    for i in range(len(trading_days) - 4):
        start, end = trading_days[i], trading_days[i + 4]  # 5 sessions inclusive = ~4.5 gap
        mask = (trades["entry"] >= start) & (trades["entry"] <= end)
        window_pnls.append(trades.loc[mask, "pnl"].sum())
    window_pnls = np.array(window_pnls)

    print(f"\nempirical distribution over {len(window_pnls)} overlapping "
          f"5-session windows (entry-date based):")
    for p in (5, 10, 25, 50, 75, 90, 95):
        print(f"  p{p:02d}: ${np.percentile(window_pnls, p):>10,.2f}")
    print(f"  mean: ${window_pnls.mean():>10,.2f}")
    print(f"  min : ${window_pnls.min():>10,.2f}")
    print(f"  max : ${window_pnls.max():>10,.2f}")
    print(f"  fraction of windows with >=1 trade entered: "
          f"{(window_pnls != 0).mean()*100:.1f}%")

    # Breach probability: fraction of windows where cumulative loss from
    # trades entered in it alone would have hit the -15% (D1 worst case) or
    # -10% (gate 2) threshold on $100k starting equity.
    breach_10 = (window_pnls <= -10_000).mean()
    breach_15 = (window_pnls <= -15_000).mean()
    print(f"\n  windows with >= $10,000 loss (10% of equity): {breach_10*100:.1f}%")
    print(f"  windows with >= $15,000 loss (15% of equity): {breach_15*100:.1f}%")

if __name__ == "__main__":
    main()
