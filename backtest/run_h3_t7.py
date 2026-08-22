# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
R1 amendment A3: T7, a seventh trial (5-10 DTE) added to the H3 family.

Registered in research/PREREGISTRATION_R1.md amendment A3, committed BEFORE
this file existed (git-provable, same discipline as the original six trials).

This reuses run_h3.py's walk-forward machinery unchanged, so T1-T6 reproduce
their committed RESULT_H3.md numbers exactly -- that reproduction is itself an
integrity check on this script, not just a convenience. Writes to a SEPARATE
file (RESULT_H3_T7.md) rather than overwriting RESULT_H3.md, so the original
six-trial, N=6, bar-0.760 result stays intact as the frozen historical record
run_h3.py itself still reproduces.

Run:  uv run --with alpaca-py --with pandas --with numpy --with requests backtest/run_h3_t7.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import engine as E  # noqa: E402
import run_h3 as R  # noqa: E402
import stats as S  # noqa: E402

RESULT_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_H3_T7.md"

T7 = E.TrialConfig("T7 both, 5-10 DTE", True, True,
                    short_delta=0.16, dte_target=8, dte_min=5, dte_max=10)

# T1-T6 unchanged from engine.TRIALS, T7 appended. N becomes 7.
TRIALS = list(E.TRIALS) + [T7]
N_TRIALS = len(TRIALS)


def main() -> None:
    print("=" * 78)
    print("R1  H3 amendment A3   T7 added, N recomputed to 7, holdout SEALED")
    print("=" * 78)

    series = D.load_all()
    try:
        D.window(series["SPY"], "holdout")
        print("  ERROR: holdout readable, seal broken")
        sys.exit(1)
    except D.HoldoutSealError:
        print("  seal verified")

    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    years = (spy.index.max() - spy.index.min()).days / 365.25

    skew = R.load_skew()
    dev_bar = S.development_bar(N_TRIALS, years)
    print(f"\ndevelopment bar recomputed: {N_TRIALS} trials, {years:.2f} years")
    print(f"  E[max|null] = sqrt(2 ln {N_TRIALS}) = {S.expected_max_null(N_TRIALS):.3f}")
    print(f"  SE(Sharpe)  = {S.sharpe_se(0.5, years):.3f}")
    print(f"  BAR         = {dev_bar:.3f}  (was 0.760 at N=6)")

    results, summaries = {}, []
    for cfg in TRIALS:
        print(f"\n--- {cfg.name} ---")
        panel = R.build_panel(spy, vix, vix3m, cfg.dte_target)
        expiries = E.build_expiries(panel.index)
        res = R.walk_forward(panel, expiries, skew, cfg)
        s = R.summarise_trial(cfg.name, res, years)
        results[cfg.name] = res
        summaries.append(s)
        print(f"  OOS Sharpe {s['sharpe']:+.3f}   total return {s['total_return'] * 100:+.2f}%"
              f"   maxDD {s['max_dd'] * 100:+.2f}%")
        print(f"  trades {s['n_trades']}   win rate "
              f"{s['win_rate'] * 100 if np.isfinite(s['win_rate']) else float('nan'):.1f}%"
              f"   PF {s['profit_factor']:.2f}   expectancy {s['expectancy_r']:+.3f}R")
        print(f"  refusal rate {s['refusal_rate'] * 100:.1f}%  {s['refusals']}")

    # Reproduction check: T1-T6 must match RESULT_H3.md exactly.
    committed = {
        "T1 baseline": 1.071, "T2 vrp gate": 1.392, "T3 regime gate": 0.949,
        "T4 both gates": 1.201, "T5 both, 10 delta": 1.515,
        "T6 both, 21-45 DTE": 1.614,
    }
    print("\nreproduction check against committed RESULT_H3.md:")
    all_match = True
    for s in summaries:
        if s["trial"] in committed:
            match = abs(s["sharpe"] - committed[s["trial"]]) < 0.001
            all_match = all_match and match
            print(f"  {s['trial']:<24} {s['sharpe']:+.3f} vs committed "
                  f"{committed[s['trial']]:+.3f}  {'OK' if match else 'MISMATCH'}")
    if not all_match:
        print("\n  MISMATCH DETECTED. T1-T6 must reproduce exactly. Stopping "
              "before writing a result that cannot be trusted.")
        sys.exit(1)
    print("  all six reproduce exactly. T7's number below is trustworthy under "
          "the same code path.")

    df = pd.DataFrame([{k: v for k, v in s.items()
                        if k not in ("refusals", "thresholds")} for s in summaries])
    df = df.sort_values("sharpe", ascending=False)

    print("\n" + "=" * 78)
    print("SUMMARY, ranked by out-of-sample Sharpe, N=7")
    print("=" * 78)
    for r in df.itertuples(index=False):
        print(f"{r.trial:<24}{r.sharpe:>+9.3f}{r.total_return * 100:>+9.2f}%"
              f"{r.max_dd * 100:>+8.2f}%{r.n_trades:>8}"
              f"{r.win_rate * 100:>6.1f}%{r.profit_factor:>7.2f}"
              f"{r.expectancy_r:>+8.3f}{r.refusal_rate * 100:>8.1f}%")

    best = df.iloc[0]
    cleared = bool(best["sharpe"] >= dev_bar)
    print(f"\nbest overall (N=7): {best['trial']} at Sharpe {best['sharpe']:+.3f} "
          f"vs bar {dev_bar:.3f}")

    by_name = {s["trial"]: s for s in summaries}
    t7 = by_name["T7 both, 5-10 DTE"]
    t7_cleared = bool(t7["sharpe"] >= dev_bar)
    t4 = by_name["T4 both gates"]
    t6 = by_name["T6 both, 21-45 DTE"]
    print(f"\nT7 specifically: Sharpe {t7['sharpe']:+.3f} vs bar {dev_bar:.3f}  "
          f"VERDICT: {'CLEARS' if t7_cleared else 'DOES NOT CLEAR'}")

    # Registered predictions P7-P9.
    p7 = t7["sharpe"] > t4["sharpe"]
    p8 = t7["max_dd"] >= -0.0465  # no worse than -4.65% (1.5x T4's -3.10%)
    print("\nregistered predictions (amendment A3):")
    print(f"  P7 T7 Sharpe > T4's +1.201                 "
          f"{'CORRECT' if p7 else 'WRONG':<8} {t7['sharpe']:+.3f} vs {t4['sharpe']:+.3f}")
    print(f"  P8 T7 maxDD no worse than -4.65% (1.5x T4)  "
          f"{'CORRECT' if p8 else 'WRONG':<8} {t7['max_dd']*100:+.2f}%")

    # Section 7 sensitivity, mandatory, run on T7 specifically regardless of
    # whether it is the overall best -- this is what P9 is checked against.
    print("\nT7 sensitivity (pre-registration section 7):")
    panel = R.build_panel(spy, vix, vix3m, T7.dte_target)
    expiries = E.build_expiries(panel.index)
    sens = []
    for label, cost, haircut in (
        ("measured cost 1.5%, no haircut", 0.015, 0.0),
        ("double cost 3.0%", 0.030, 0.0),
        ("credit haircut 10% (model overprices)", 0.015, 0.10),
        ("both", 0.030, 0.10),
    ):
        rr = []
        st = 0
        dates = panel.index
        while st + R.IS_DAYS + R.OOS_DAYS <= len(dates):
            is_p = panel.iloc[st:st + R.IS_DAYS]
            oos_p = panel.iloc[st + R.IS_DAYS:st + R.IS_DAYS + R.OOS_DAYS]
            bs_, bt_ = -np.inf, E.THRESHOLD_GRID[0]
            for t_ in E.THRESHOLD_GRID:
                r_ = E.run_strategy(is_p, expiries, skew, T7, t_,
                                    cost_pct=cost, credit_haircut=haircut)
                sh_ = S.annualised_sharpe(R.daily_returns(r_["equity"]))
                if np.isfinite(sh_) and sh_ > bs_:
                    bs_, bt_ = sh_, t_
            o_ = E.run_strategy(oos_p, expiries, skew, T7, bt_,
                                cost_pct=cost, credit_haircut=haircut)
            rr.append(R.daily_returns(o_["equity"]))
            st += R.OOS_DAYS
        rets = pd.concat(rr) if rr else pd.Series(dtype=float)
        sh = S.annualised_sharpe(rets)
        tot_ret = float((1.0 + rets).prod() - 1.0) if not rets.empty else np.nan
        sens.append({"label": label, "sharpe": sh, "total_return": tot_ret})
        print(f"  {label:<40} Sharpe {sh:+.3f}   return {tot_ret * 100:+.2f}%")

    p9 = sens[1]["sharpe"] < t7["sharpe"]  # double cost REDUCES Sharpe (normal direction)
    print(f"\n  P9 double cost reduces T7 Sharpe (normal, unlike T6's anomaly)  "
          f"{'CORRECT' if p9 else 'WRONG':<8} {sens[1]['sharpe']:+.3f} vs {t7['sharpe']:+.3f}")

    holdout_note = _holdout_governance(t7, t7_cleared, t6, dev_bar)
    print(f"\n{holdout_note}")

    _write(df, dev_bar, N_TRIALS, years, t7, t7_cleared, p7, p8, p9, t4, sens, holdout_note)
    print(f"\nwritten to {RESULT_PATH.name}")
    print(f"\nholdout still sealed: {D.holdout_is_sealed()}")


def _holdout_governance(t7, t7_cleared, t6, dev_bar) -> str:
    if t7_cleared and t7["sharpe"] > t6["sharpe"]:
        return ("Holdout governance: T7 clears and beats T6. T7 becomes the "
                "sole nominee for the one holdout shot, per amendment A3. "
                "Holdout remains SEALED; this run does not spend it.")
    if t7_cleared:
        return ("Holdout governance: T7 clears but does not beat T6's "
                f"{t6['sharpe']:+.3f}. T6 remains the nominee. Holdout remains SEALED.")
    return ("Holdout governance: T7 does not clear the recomputed bar. "
            "T6 remains the nominee, unchanged. Holdout remains SEALED.")


def _write(df, dev_bar, n_trials, years, t7, t7_cleared, p7, p8, p9, t4, sens, holdout_note) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    L = [
        "# RESULT: amendment A3, trial T7 (5-10 DTE)",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        f"Development window {D.DEV_START} to {D.DEV_END} ({years:.2f} years). "
        "Holdout sealed and verified unreadable by the run itself.",
        "",
        "Registered in `PREREGISTRATION_R1.md` amendment A3, committed before "
        "this file existed. T1-T6 reproduced exactly against the committed "
        "`RESULT_H3.md` before this result was trusted (see script output); "
        "this file reports T7 plus the recomputed N=7 bar.",
        "",
        "## Bar, recomputed at N=7",
        "",
        f"- trials: {n_trials} (T1-T6 fixed 2026-08-19, T7 added 2026-08-22)",
        f"- E[max under null] = sqrt(2 ln {n_trials}) = {S.expected_max_null(n_trials):.3f}",
        f"- SE(Sharpe) at {years:.2f}y = {S.sharpe_se(0.5, years):.3f}",
        f"- **development bar = {dev_bar:.3f}** (was 0.760 at N=6; T1-T6 verdicts "
        "unaffected, checked in the amendment before this ran)",
        "",
        "## All seven, out-of-sample, ranked",
        "",
        "| trial | Sharpe | return | max DD | trades | win% | PF | expectancy | refusal% |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in df.itertuples(index=False):
        L.append(
            f"| {r.trial} | **{r.sharpe:+.3f}** | {r.total_return * 100:+.2f}% | "
            f"{r.max_dd * 100:+.2f}% | {r.n_trades} | {r.win_rate * 100:.1f}% | "
            f"{r.profit_factor:.2f} | {r.expectancy_r:+.3f}R | {r.refusal_rate * 100:.1f}% |"
        )
    L += [
        "",
        f"**T7 (5-10 DTE): Sharpe {t7['sharpe']:+.3f} against the recomputed bar "
        f"{dev_bar:.3f}. VERDICT: {'CLEARS' if t7_cleared else 'DOES NOT CLEAR'}.**",
        "",
        "## Registered predictions (amendment A3)",
        "",
        f"- **P7** T7 Sharpe > T4's +1.201: **{'CORRECT' if p7 else 'WRONG'}** "
        f"({t7['sharpe']:+.3f} vs {t4['sharpe']:+.3f})",
        f"- **P8** T7 maxDD no worse than -4.65% (1.5x T4's -3.10%): "
        f"**{'CORRECT' if p8 else 'WRONG'}** ({t7['max_dd']*100:+.2f}%)",
        f"- **P9** double-cost sensitivity REDUCES T7 Sharpe (the normal "
        f"direction, unlike T6's anomaly): **{'CORRECT' if p9 else 'WRONG'}**",
        "",
        "## Sensitivity (section 7, mandatory)",
        "",
        "| scenario | Sharpe | return |",
        "|---|---|---|",
    ]
    for s in sens:
        L.append(f"| {s['label']} | {s['sharpe']:+.3f} | {s['total_return'] * 100:+.2f}% |")
    L += ["", "## Holdout governance", "", holdout_note, ""]
    RESULT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
