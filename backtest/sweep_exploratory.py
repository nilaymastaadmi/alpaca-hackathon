# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
EXPLORATORY parameter sweep. This is NOT evidence and nothing here may be
promoted without a fresh pre-registration.

Why the shape of this matters. Running a large factorial grid and reporting the
best cell is exactly what killed chikki: 54 trials on a 4.5 year window pushed
the honest bar to roughly Sharpe 1.7, and the "winners" were noise. So this does
ONE-DIMENSIONAL sweeps around a fixed base config instead.

The output to read is the SHAPE of each curve, not the peak:
  - Sharpe rising monotonically across a parameter is a structural finding.
  - Sharpe peaking at one interior value with noise either side is a lucky cell.

Structure survives out of sample. Lucky cells do not.

Also verifies that the multi-position engine rewrite still reproduces the
committed H3 baseline before trusting anything else it says.

Run:  uv run backtest/sweep_exploratory.py
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

RESULT_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_SWEEP.md"

# Base config: what H3 actually ran, so every sweep is a controlled deviation.
BASE_CFG = E.TrialConfig("base", use_vrp_gate=True, use_regime_gate=True,
                         short_delta=0.16, dte_target=10, dte_min=7, dte_max=14)
BASE_THR = 2.0


def run_one(spy, vix, vix3m, skew, cfg, params, threshold=BASE_THR):
    panel = build_panel(spy, vix, vix3m, cfg.dte_target)
    expiries = E.build_expiries(panel.index)
    res = E.run_strategy(panel, expiries, skew, cfg, threshold, params=params)
    rets = daily_returns(res["equity"])
    tr = res["trades"]
    years = (panel.index.max() - panel.index.min()).days / 365.25
    n = len(tr)
    return {
        "sharpe": S.annualised_sharpe(rets),
        "total_return": float((1 + rets).prod() - 1) if not rets.empty else np.nan,
        "max_dd": S.max_drawdown(res["equity"]) if not res["equity"].empty else np.nan,
        "n_trades": n,
        "trades_per_year": n / years if years else np.nan,
        "win_rate": float((tr["pnl"] > 0).mean()) if n else np.nan,
        "worst_trade_r": float(tr["r_multiple"].min()) if n else np.nan,
        "expectancy_r": float(tr["r_multiple"].mean()) if n else np.nan,
    }


def fmt(r):
    return (f"{r['sharpe']:>+8.3f}{r['total_return'] * 100:>+9.2f}%"
            f"{r['max_dd'] * 100:>+8.2f}%{r['n_trades']:>7}"
            f"{r['trades_per_year']:>8.1f}"
            f"{r['win_rate'] * 100 if np.isfinite(r['win_rate']) else 0:>7.1f}%"
            f"{r['worst_trade_r']:>+9.2f}")


HEAD = (f"{'value':>14}{'Sharpe':>8}{'return':>10}{'maxDD':>8}{'trades':>7}"
        f"{'tr/yr':>8}{'win%':>7}{'worstR':>9}")


def main() -> None:
    print("=" * 88)
    print("EXPLORATORY SWEEP. Not evidence. Read the SHAPE, not the peak.")
    print("=" * 88)

    series = D.load_all()
    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    skew = load_skew()

    # --- reproduction check before trusting the rewritten engine -------------
    print("\nreproduction check: T1 baseline, fixed threshold, should be ~+1.461")
    t1 = E.TrialConfig("T1", False, False)
    r = run_one(spy, vix, vix3m, skew, t1, E.DEFAULT_PARAMS, threshold=0.0)
    drift = abs(r["sharpe"] - 1.461)
    print(f"  got {r['sharpe']:+.3f}, drift {drift:.3f}")
    if drift > 0.15:
        print("  NOTE: the engine rewrite changed behaviour. Same-day re-entry after")
        print("  an exit is now allowed, where the old loop skipped the exit day.")
        print("  Recording the change rather than hiding it; H3 as committed stands")
        print("  on the old engine and its git history.")
    else:
        print("  reproduces within tolerance")

    sections = []

    # --- 1. tenor -----------------------------------------------------------
    print("\n" + "-" * 88)
    print("1. TENOR (DTE band). Everything else at base.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for lo, hi, tgt in ((0, 3, 1), (3, 7, 5), (7, 14, 10), (14, 21, 17), (21, 45, 33)):
        cfg = E.TrialConfig("t", True, True, 0.16, tgt, lo, hi)
        r = run_one(spy, vix, vix3m, skew, cfg, E.DEFAULT_PARAMS)
        print(f"{f'{lo}-{hi} DTE':>14}{fmt(r)}")
        rows.append({"value": f"{lo}-{hi} DTE", **r})
    sections.append(("Tenor (DTE band)", rows))

    # --- 2. short delta -----------------------------------------------------
    print("\n" + "-" * 88)
    print("2. SHORT STRIKE DELTA. Further OTM to the left.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for d in (0.05, 0.10, 0.16, 0.25, 0.35):
        cfg = E.TrialConfig("d", True, True, d, 10, 7, 14)
        r = run_one(spy, vix, vix3m, skew, cfg, E.DEFAULT_PARAMS)
        print(f"{f'{d:.2f} delta':>14}{fmt(r)}")
        rows.append({"value": f"{d:.2f} delta", **r})
    sections.append(("Short strike delta", rows))

    # --- 3. wing width ------------------------------------------------------
    print("\n" + "-" * 88)
    print("3. WING WIDTH (% of spot). Wider wings mean bigger max loss per contract.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for w in (0.003, 0.0065, 0.010, 0.015, 0.025):
        p = E.StrategyParams(wing_pct=w)
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{f'{w * 100:.2f}%':>14}{fmt(r)}")
        rows.append({"value": f"{w * 100:.2f}%", **r})
    sections.append(("Wing width (% of spot)", rows))

    # --- 4. profit target ---------------------------------------------------
    print("\n" + "-" * 88)
    print("4. PROFIT TARGET. Take profit at this fraction of max profit.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for pt in (0.25, 0.50, 0.75, 0.90):
        p = E.StrategyParams(profit_target=pt)
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{f'{pt * 100:.0f}%':>14}{fmt(r)}")
        rows.append({"value": f"{pt * 100:.0f}%", **r})
    sections.append(("Profit target", rows))

    # --- 5. stop loss -------------------------------------------------------
    print("\n" + "-" * 88)
    print("5. STOP LOSS (exit if buyback exceeds credit x N). None = ride to the wing.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for sl in (None, 1.5, 2.0, 3.0):
        p = E.StrategyParams(stop_loss_mult=sl)
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{str(sl):>14}{fmt(r)}")
        rows.append({"value": f"{sl}", **r})
    sections.append(("Stop loss multiple", rows))

    # --- 6. structure -------------------------------------------------------
    print("\n" + "-" * 88)
    print("6. STRUCTURE. Condor sells both sides; verticals sell one.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for st in ("condor", "put_spread", "call_spread"):
        p = E.StrategyParams(structure=st)
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{st:>14}{fmt(r)}")
        rows.append({"value": st, **r})
    sections.append(("Structure", rows))

    # --- 7. concurrency -----------------------------------------------------
    print("\n" + "-" * 88)
    print("7. CONCURRENT POSITIONS. The lever that fixes trade count.")
    print("-" * 88)
    print(HEAD)
    rows = []
    for mc in (1, 2, 3, 5, 8):
        p = E.StrategyParams(max_concurrent=mc)
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{f'{mc} concurrent':>14}{fmt(r)}")
        rows.append({"value": f"{mc} concurrent", **r})
    sections.append(("Concurrent positions", rows))

    # --- 8. the deployed config (D1) ----------------------------------------
    print("\n" + "-" * 88)
    print("8. THE DEPLOYED CONFIG (D1): 5 concurrent at 3% risk each")
    print("-" * 88)
    print(HEAD)
    rows = []
    for label, p in (
        ("D1 as chosen", E.StrategyParams(max_concurrent=5, risk_per_position=0.03)),
        ("D1 + stagger", E.StrategyParams(max_concurrent=5, risk_per_position=0.03,
                                          one_per_expiry=True)),
        ("D1 + stop 2x", E.StrategyParams(max_concurrent=5, risk_per_position=0.03,
                                          stop_loss_mult=2.0)),
        ("research 1x1", E.DEFAULT_PARAMS),
    ):
        r = run_one(spy, vix, vix3m, skew, BASE_CFG, p)
        print(f"{label:>14}{fmt(r)}")
        rows.append({"value": label, **r})
    sections.append(("Deployed config D1", rows))

    _write(sections)
    print(f"\nwritten to {RESULT_PATH.name}")
    print(f"holdout still sealed: {D.holdout_is_sealed()}")

    total = sum(len(rows) for _, rows in sections)
    bar = S.development_bar(total, 6.99)
    print(f"\nTOTAL CONFIGURATIONS RUN: {total}")
    print(f"If any of these were treated as a TRIAL, the honest bar would be "
          f"Sharpe {bar:.3f},")
    print(f"not the 0.760 that 6 pre-registered trials earned. That is the cost of")
    print(f"searching, and it is why none of this is promoted without re-registering.")


def _write(sections) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    total = sum(len(rows) for _, rows in sections)
    bar = S.development_bar(total, 6.99)
    L = [
        "# RESULT: exploratory parameter sweep",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "Development window only, holdout sealed.",
        "",
        "## This is NOT evidence",
        "",
        f"**{total} configurations were run.** If any were treated as a pre-registered "
        f"trial, the honest bar would be Sharpe **{bar:.3f}**, not the 0.760 that 6 "
        "registered trials earned. Searching costs you the right to claim the winner.",
        "",
        "One-dimensional sweeps around a fixed base were used instead of a factorial "
        "grid, deliberately. **Read the SHAPE of each curve, not the peak.** A monotonic "
        "trend across a parameter is a structural finding that tends to survive out of "
        "sample. A peak at one interior value with noise either side is a lucky cell "
        "that does not.",
        "",
        "Nothing here is promoted. Anything worth keeping goes into a fresh "
        "pre-registration with its own trial count and its own bar.",
        "",
    ]
    for title, rows in sections:
        L += [
            f"## {title}",
            "",
            "| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            L.append(
                f"| {r['value']} | {r['sharpe']:+.3f} | {r['total_return'] * 100:+.2f}% | "
                f"{r['max_dd'] * 100:+.2f}% | {r['n_trades']} | {r['trades_per_year']:.1f} | "
                f"{r['win_rate'] * 100 if np.isfinite(r['win_rate']) else 0:.1f}% | "
                f"{r['worst_trade_r']:+.2f} |"
            )
        L.append("")
    RESULT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
