# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
Attack the H3 result before believing it.

Three things in the H3 output look wrong, and each has an innocent and a fatal
explanation:

  1. Doubling transaction costs IMPROVED Sharpe (+1.728 vs +1.614). Costs cannot
     help. Innocent: higher costs change which threshold the in-sample fit picks,
     and that reshuffles out-of-sample trades. Fatal: the threshold fit is
     selecting noise, so out-of-sample results are close to random draws.
  2. Fitted thresholds jump between 0 and 5 across adjacent windows. A parameter
     that has real signal should be somewhat stable.
  3. The regime gate HURT (T3 0.949 vs T1 baseline 1.071), which cuts against H2.

Test: replace the fitted threshold with every FIXED value on the grid and see
whether the edge survives without any fitting at all. If fixed thresholds do as
well, the fitting was adding nothing (reassuring, and the result stands on the
strategy rather than on the optimiser). If the edge only exists with fitting,
the walk-forward was laundering an in-sample choice and H3 should not be trusted.

Also reports Sharpe by calendar year, so 2018 and 2020 can be inspected directly.
A short-volatility strategy that shows no damage in those years is not being
tested properly.

Run:  uv run backtest/robustness_h3.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import engine as E  # noqa: E402
import stats as S  # noqa: E402
from run_h3 import build_panel, daily_returns, load_skew  # noqa: E402

RESULT_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_H3_ROBUSTNESS.md"


def run_fixed(panel, expiries, skew, cfg, threshold, cost=E.COST_PCT, haircut=0.0):
    """One straight pass, no fitting, no walk-forward."""
    res = E.run_strategy(panel, expiries, skew, cfg, threshold,
                         cost_pct=cost, credit_haircut=haircut)
    rets = daily_returns(res["equity"])
    return {
        "sharpe": S.annualised_sharpe(rets),
        "total_return": float((1.0 + rets).prod() - 1.0) if not rets.empty else np.nan,
        "max_dd": S.max_drawdown(res["equity"]) if not res["equity"].empty else np.nan,
        "n_trades": len(res["trades"]),
        "returns": rets,
        "trades": res["trades"],
        "refusal_rate": (sum(res["refusals"].values()) / res["opportunities"]
                         if res["opportunities"] else np.nan),
    }


def main() -> None:
    print("=" * 78)
    print("H3 ROBUSTNESS: does the edge survive without the optimiser?")
    print("=" * 78)

    series = D.load_all()
    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    skew = load_skew()

    rows = []
    for cfg in E.TRIALS:
        panel = build_panel(spy, vix, vix3m, cfg.dte_target)
        expiries = E.build_expiries(panel.index)
        print(f"\n--- {cfg.name} ---")
        print(f"{'threshold':>10}{'Sharpe':>10}{'return':>10}{'maxDD':>9}"
              f"{'trades':>8}{'refuse%':>9}")
        grid = E.THRESHOLD_GRID if cfg.use_vrp_gate else [0.0]
        for thr in grid:
            r = run_fixed(panel, expiries, skew, cfg, thr)
            print(f"{thr:>10.1f}{r['sharpe']:>+10.3f}{r['total_return'] * 100:>+9.2f}%"
                  f"{r['max_dd'] * 100:>+8.2f}%{r['n_trades']:>8}"
                  f"{r['refusal_rate'] * 100:>8.1f}%")
            rows.append({"trial": cfg.name, "threshold": thr, **{
                k: v for k, v in r.items() if k not in ("returns", "trades")}})

    df = pd.DataFrame(rows)

    print("\n" + "=" * 78)
    print("FIXED-THRESHOLD SUMMARY per trial (no fitting anywhere)")
    print("=" * 78)
    print(f"{'trial':<22}{'min':>9}{'median':>9}{'max':>9}{'spread':>9}")
    for name, g in df.groupby("trial", sort=False):
        lo, med, hi = g["sharpe"].min(), g["sharpe"].median(), g["sharpe"].max()
        print(f"{name:<22}{lo:>+9.3f}{med:>+9.3f}{hi:>+9.3f}{hi - lo:>9.3f}")

    # Year by year on the best fixed configuration, to expose 2018 and 2020.
    print("\n" + "=" * 78)
    print("YEAR BY YEAR, best trial at its MEDIAN fixed threshold")
    print("=" * 78)
    best_trial = df.groupby("trial")["sharpe"].median().idxmax()
    cfg_best = next(c for c in E.TRIALS if c.name == best_trial)
    g = df[df["trial"] == best_trial].sort_values("sharpe")
    med_thr = float(g.iloc[len(g) // 2]["threshold"])
    print(f"trial {best_trial}, fixed threshold {med_thr:.1f}\n")

    panel = build_panel(spy, vix, vix3m, cfg_best.dte_target)
    expiries = E.build_expiries(panel.index)
    r = run_fixed(panel, expiries, skew, cfg_best, med_thr)
    rets = r["returns"]
    print(f"{'year':>6}{'Sharpe':>10}{'return':>10}{'worst day':>12}{'trades':>8}")
    trades = r["trades"]
    for year, gr in rets.groupby(rets.index.year):
        n = 0
        if not trades.empty:
            n = int((pd.to_datetime(trades['entry']).dt.year == year).sum())
        print(f"{year:>6}{S.annualised_sharpe(gr):>+10.3f}"
              f"{(1 + gr).prod() * 100 - 100:>+9.2f}%{gr.min() * 100:>+11.2f}%{n:>8}")

    print(f"\noverall fixed-threshold Sharpe {r['sharpe']:+.3f}, "
          f"return {r['total_return'] * 100:+.2f}%, maxDD {r['max_dd'] * 100:+.2f}%")

    # What a 4.5 day live window actually implies.
    print("\n" + "=" * 78)
    print("WHAT THIS MEANS FOR A 4.5 DAY LIVE WINDOW")
    print("=" * 78)
    years_span = (panel.index.max() - panel.index.min()).days / 365.25
    trades_per_year = r["n_trades"] / years_span if years_span else np.nan
    ann_ret = (1 + r["total_return"]) ** (1 / years_span) - 1 if years_span else np.nan
    print(f"  trades per year        : {trades_per_year:.1f}")
    print(f"  expected trades in 4.5d: {trades_per_year * 4.5 / 252:.2f}")
    print(f"  annualised return      : {ann_ret * 100:+.2f}%")
    print(f"  expected 4.5d return   : {ann_ret * 4.5 / 252 * 100:+.4f}%")
    print(f"  on $100k               : ${ann_ret * 4.5 / 252 * 100000:+.2f}")
    print("\n  The pre-registered sizing (1% risk per position, one at a time) is")
    print("  statistically sound and produces almost no P&L in a 4.5 day window.")
    print("  That tension is a DEPLOYMENT decision, not a backtest fix. Changing")
    print("  sizing now, after seeing results, is exactly what section 11 forbids.")

    _write(df, best_trial, med_thr, r, trades_per_year, ann_ret, rets, trades)
    print(f"\nwritten to {RESULT_PATH.name}")
    print(f"holdout still sealed: {D.holdout_is_sealed()}")


def _write(df, best_trial, med_thr, r, tpy, ann_ret, rets, trades) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# RESULT: H3 robustness, attacking the result before believing it",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "Development window only, holdout sealed.",
        "",
        "## Why this check exists",
        "",
        "Three things in the H3 output looked wrong:",
        "",
        "1. **Doubling transaction costs improved Sharpe** (+1.728 vs +1.614). Costs "
        "cannot help. Either the threshold fit reshuffles trades, or the fit is "
        "selecting noise.",
        "2. **Fitted thresholds jumped between 0 and 5 in adjacent windows.** A "
        "parameter carrying real signal should show some stability.",
        "3. **The regime gate hurt** (T3 +0.949 against a T1 baseline of +1.071), which "
        "cuts against H2.",
        "",
        "Test: drop the optimiser entirely and run every FIXED threshold.",
        "",
        "## Fixed-threshold results, no fitting anywhere",
        "",
        "| trial | threshold | Sharpe | return | max DD | trades | refusal% |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in df.itertuples(index=False):
        L.append(
            f"| {x.trial} | {x.threshold:.1f} | {x.sharpe:+.3f} | "
            f"{x.total_return * 100:+.2f}% | {x.max_dd * 100:+.2f}% | {x.n_trades} | "
            f"{x.refusal_rate * 100:.1f}% |"
        )
    L += [
        "",
        "## Spread per trial",
        "",
        "| trial | min Sharpe | median | max | spread |",
        "|---|---|---|---|---|",
    ]
    for name, g in df.groupby("trial", sort=False):
        lo, med, hi = g["sharpe"].min(), g["sharpe"].median(), g["sharpe"].max()
        L.append(f"| {name} | {lo:+.3f} | {med:+.3f} | {hi:+.3f} | {hi - lo:.3f} |")

    L += [
        "",
        f"## Year by year: {best_trial} at fixed threshold {med_thr:.1f}",
        "",
        "| year | Sharpe | return | worst day | trades |",
        "|---|---|---|---|---|",
    ]
    for year, gr in rets.groupby(rets.index.year):
        n = 0
        if not trades.empty:
            n = int((pd.to_datetime(trades["entry"]).dt.year == year).sum())
        L.append(f"| {year} | {S.annualised_sharpe(gr):+.3f} | "
                 f"{(1 + gr).prod() * 100 - 100:+.2f}% | {gr.min() * 100:+.2f}% | {n} |")

    L += [
        "",
        f"Overall fixed-threshold Sharpe **{r['sharpe']:+.3f}**, return "
        f"{r['total_return'] * 100:+.2f}%, max drawdown {r['max_dd'] * 100:+.2f}%.",
        "",
        "## What this implies for a 4.5 day live window",
        "",
        f"- trades per year: **{tpy:.1f}**",
        f"- expected trades in 4.5 trading days: **{tpy * 4.5 / 252:.2f}**",
        f"- annualised return: **{ann_ret * 100:+.2f}%**",
        f"- expected 4.5 day return: **{ann_ret * 4.5 / 252 * 100:+.4f}%**, "
        f"about **${ann_ret * 4.5 / 252 * 100000:+.2f}** on $100k",
        "",
        "**The pre-registered sizing is statistically sound and produces almost no P&L "
        "in the hackathon window.** One position at a time, risking 1% of equity, with "
        "a high refusal rate, means the agent may not trade at all during the live week.",
        "",
        "This is a DEPLOYMENT decision, not a backtest fix. Re-sizing now, after seeing "
        "these results, is precisely what pre-registration section 11 forbids. The "
        "choice belongs to Nilay and must be made on risk grounds and recorded as a "
        "deliberate deviation, not folded silently into the research.",
        "",
    ]
    RESULT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
