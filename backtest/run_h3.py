# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
R1 hypothesis H3: does the gated short-premium strategy clear its bar?

Development window only. Holdout stays sealed. Six trials fixed in advance by
pre-registration section 4; the only fitted quantity is the VRP entry threshold,
chosen inside in-sample blocks and applied unchanged to the following
out-of-sample block.

Reported development Sharpe is computed on CONCATENATED OUT-OF-SAMPLE blocks
only. In-sample performance is never reported as a result.

Run:  uv run backtest/run_h3.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import engine as E  # noqa: E402
import pricing as P  # noqa: E402
import stats as S  # noqa: E402
import vol as V  # noqa: E402

IS_DAYS, OOS_DAYS = 252, 63
RESULT_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_H3.md"
SKEW_PATH = Path(__file__).resolve().parent / "cache" / "skew_model.json"

N_TRIALS = len(E.TRIALS)


def load_skew() -> P.SkewModel:
    if not SKEW_PATH.exists():
        sys.exit("no calibrated skew model. Run backtest/calibrate_and_validate.py first.")
    d = json.loads(SKEW_PATH.read_text())
    return P.SkewModel(d["b"], d["c"], d["k_min"], d["k_max"],
                       d["n_points"], d["tenor_label"])


def build_panel(spy, vix, vix3m, dte_target: int) -> pd.DataFrame:
    """
    Decision-time inputs only. VRP signal uses TRAILING realised vol per
    amendment A1.2, never forward-looking data.
    """
    rv_trail = V.realised_vol_trailing(spy["close"], 21)
    df = pd.DataFrame({
        "close": spy["close"],
        "vix": vix["close"],
        "vix3m": vix3m["close"],
        "rv_trail": rv_trail,
    }).dropna()
    atm = df.apply(lambda r: P.atm_iv(r["vix"], r["vix3m"], dte_target) * 100.0, axis=1)
    df["atm_iv"] = atm
    df["vrp_signal"] = df["atm_iv"] - df["rv_trail"]
    df["contango"] = df["vix"] / df["vix3m"] < 1.0
    return df


def daily_returns(equity: pd.Series) -> pd.Series:
    if equity.empty:
        return pd.Series(dtype=float)
    return equity.pct_change().dropna()


def walk_forward(panel: pd.DataFrame, expiries, skew, cfg) -> dict:
    """
    Rolling IS/OOS. Threshold fitted on IS only when the trial uses a VRP gate;
    otherwise the grid is irrelevant and a single pass is made.
    """
    dates = panel.index
    oos_returns, chosen, blocks = [], [], []
    all_trades, all_refusals = [], {"vrp": 0, "regime": 0, "no_expiry": 0, "unsized": 0}
    total_opportunities = 0

    start = 0
    while start + IS_DAYS + OOS_DAYS <= len(dates):
        is_panel = panel.iloc[start:start + IS_DAYS]
        oos_panel = panel.iloc[start + IS_DAYS:start + IS_DAYS + OOS_DAYS]

        if cfg.use_vrp_gate:
            best_thr, best_sharpe = E.THRESHOLD_GRID[0], -np.inf
            for thr in E.THRESHOLD_GRID:
                r = E.run_strategy(is_panel, expiries, skew, cfg, thr)
                sh = S.annualised_sharpe(daily_returns(r["equity"]))
                if np.isfinite(sh) and sh > best_sharpe:
                    best_sharpe, best_thr = sh, thr
        else:
            best_thr = 0.0

        out = E.run_strategy(oos_panel, expiries, skew, cfg, best_thr)
        rets = daily_returns(out["equity"])
        oos_returns.append(rets)
        chosen.append(best_thr)
        total_opportunities += out["opportunities"]
        for k, v in out["refusals"].items():
            all_refusals[k] += v
        if not out["trades"].empty:
            all_trades.append(out["trades"])
        blocks.append({
            "oos_start": oos_panel.index[0], "oos_end": oos_panel.index[-1],
            "threshold": best_thr,
            "final_equity": out["final_equity"],
        })
        start += OOS_DAYS

    rets = pd.concat(oos_returns) if oos_returns else pd.Series(dtype=float)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    equity = (1.0 + rets).cumprod() * E.STARTING_EQUITY if not rets.empty else pd.Series(dtype=float)

    return {
        "returns": rets, "equity": equity, "trades": trades,
        "refusals": all_refusals, "opportunities": total_opportunities,
        "thresholds": chosen, "blocks": blocks,
    }


def summarise_trial(name: str, res: dict, years: float) -> dict:
    rets, trades = res["returns"], res["trades"]
    sharpe = S.annualised_sharpe(rets)
    total_ret = float((1.0 + rets).prod() - 1.0) if not rets.empty else np.nan
    mdd = S.max_drawdown(res["equity"]) if not res["equity"].empty else np.nan
    n_trades = len(trades)
    win_rate = float((trades["pnl"] > 0).mean()) if n_trades else np.nan
    pf = S.profit_factor(trades["pnl"]) if n_trades else np.nan
    expectancy_r = float(trades["r_multiple"].mean()) if n_trades else np.nan
    refused = sum(res["refusals"].values())
    refusal_rate = refused / res["opportunities"] if res["opportunities"] else np.nan
    return {
        "trial": name, "sharpe": sharpe, "total_return": total_ret, "max_dd": mdd,
        "n_trades": n_trades, "win_rate": win_rate, "profit_factor": pf,
        "expectancy_r": expectancy_r, "refusal_rate": refusal_rate,
        "refusals": res["refusals"], "thresholds": res["thresholds"],
    }


def main() -> None:
    print("=" * 78)
    print("R1  H3   development window only, holdout SEALED")
    print("=" * 78)
    print(f"run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")

    series = D.load_all()
    print(f"\nholdout sealed: {D.holdout_is_sealed()}")
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

    skew = load_skew()
    print(f"\n{skew.describe()}")

    dev_bar = S.development_bar(N_TRIALS, years)
    print(f"\ndevelopment bar: {N_TRIALS} trials, {years:.2f} years")
    print(f"  E[max|null] = sqrt(2 ln {N_TRIALS}) = {S.expected_max_null(N_TRIALS):.3f}")
    print(f"  SE(Sharpe)  = {S.sharpe_se(0.5, years):.3f}")
    print(f"  BAR         = {dev_bar:.3f}")

    results, summaries = {}, []
    for cfg in E.TRIALS:
        print(f"\n--- {cfg.name} ---")
        panel = build_panel(spy, vix, vix3m, cfg.dte_target)
        expiries = E.build_expiries(panel.index)
        res = walk_forward(panel, expiries, skew, cfg)
        s = summarise_trial(cfg.name, res, years)
        results[cfg.name] = res
        summaries.append(s)
        print(f"  OOS Sharpe {s['sharpe']:+.3f}   total return {s['total_return'] * 100:+.2f}%"
              f"   maxDD {s['max_dd'] * 100:+.2f}%")
        print(f"  trades {s['n_trades']}   win rate "
              f"{s['win_rate'] * 100 if np.isfinite(s['win_rate']) else float('nan'):.1f}%"
              f"   PF {s['profit_factor']:.2f}   expectancy {s['expectancy_r']:+.3f}R")
        print(f"  refusal rate {s['refusal_rate'] * 100:.1f}%  {s['refusals']}")
        if cfg.use_vrp_gate:
            print(f"  thresholds chosen: {s['thresholds']}")

    df = pd.DataFrame([{k: v for k, v in s.items()
                        if k not in ("refusals", "thresholds")} for s in summaries])
    df = df.sort_values("sharpe", ascending=False)

    print("\n" + "=" * 78)
    print("SUMMARY, ranked by out-of-sample Sharpe")
    print("=" * 78)
    print(f"{'trial':<22}{'Sharpe':>9}{'return':>10}{'maxDD':>9}"
          f"{'trades':>8}{'win%':>7}{'PF':>7}{'exp R':>8}{'refuse%':>9}")
    for r in df.itertuples(index=False):
        print(f"{r.trial:<22}{r.sharpe:>+9.3f}{r.total_return * 100:>+9.2f}%"
              f"{r.max_dd * 100:>+8.2f}%{r.n_trades:>8}"
              f"{r.win_rate * 100:>6.1f}%{r.profit_factor:>7.2f}"
              f"{r.expectancy_r:>+8.3f}{r.refusal_rate * 100:>8.1f}%")

    best = df.iloc[0]
    cleared = bool(best["sharpe"] >= dev_bar)
    print(f"\nbest: {best['trial']} at Sharpe {best['sharpe']:+.3f} vs bar {dev_bar:.3f}")
    print(f"VERDICT: {'CLEARS' if cleared else 'DOES NOT CLEAR'} the development bar")

    # Registered predictions.
    print("\nregistered predictions (section 9):")
    by_name = {s["trial"]: s for s in summaries}
    t1, t4 = by_name["T1 baseline"], by_name["T4 both gates"]
    t6 = by_name["T6 both, 21-45 DTE"]
    first4 = [by_name[n] for n in ("T1 baseline", "T2 vrp gate",
                                   "T3 regime gate", "T4 both gates")]
    p3 = max(first4, key=lambda s: s["sharpe"])["trial"] == "T4 both gates"
    p4 = (t4["total_return"] < t1["total_return"]) and (t4["sharpe"] > t1["sharpe"])
    p5 = t6["sharpe"] > t4["sharpe"]
    p6 = np.isfinite(t4["refusal_rate"]) and t4["refusal_rate"] >= 0.30
    for label, ok, detail in (
        ("P3 T4 best of T1-T4", p3, max(first4, key=lambda s: s['sharpe'])['trial']),
        ("P4 T4 lower return but higher Sharpe than T1", p4,
         f"ret {t4['total_return']*100:+.2f}% vs {t1['total_return']*100:+.2f}%, "
         f"Sharpe {t4['sharpe']:+.3f} vs {t1['sharpe']:+.3f}"),
        ("P5 T6 beats T4 on Sharpe", p5, f"{t6['sharpe']:+.3f} vs {t4['sharpe']:+.3f}"),
        ("P6 T4 refuses on >=30% of days", p6, f"{t4['refusal_rate']*100:.1f}%"),
    ):
        print(f"  {label:<48} {'CORRECT' if ok else 'WRONG':<8} {detail}")

    # Section 7: mandatory cost sensitivity at double the measured cost, plus a
    # credit haircut for the pricing model's known optimistic bias.
    print("\nsensitivity (pre-registration section 7 and the gate's residual bias):")
    cfg_best = next(c for c in E.TRIALS if c.name == best["trial"])
    panel = build_panel(spy, vix, vix3m, cfg_best.dte_target)
    expiries = E.build_expiries(panel.index)
    sens = []
    for label, cost, haircut in (
        ("measured cost 1.5%, no haircut", 0.015, 0.0),
        ("double cost 3.0%", 0.030, 0.0),
        ("credit haircut 10% (model overprices)", 0.015, 0.10),
        ("both", 0.030, 0.10),
    ):
        rr, tot_ret = [], None
        st = 0
        dates = panel.index
        while st + IS_DAYS + OOS_DAYS <= len(dates):
            is_p = panel.iloc[st:st + IS_DAYS]
            oos_p = panel.iloc[st + IS_DAYS:st + IS_DAYS + OOS_DAYS]
            thr = 0.0
            if cfg_best.use_vrp_gate:
                bs_, bt_ = -np.inf, E.THRESHOLD_GRID[0]
                for t_ in E.THRESHOLD_GRID:
                    r_ = E.run_strategy(is_p, expiries, skew, cfg_best, t_,
                                        cost_pct=cost, credit_haircut=haircut)
                    sh_ = S.annualised_sharpe(daily_returns(r_["equity"]))
                    if np.isfinite(sh_) and sh_ > bs_:
                        bs_, bt_ = sh_, t_
                thr = bt_
            o_ = E.run_strategy(oos_p, expiries, skew, cfg_best, thr,
                                cost_pct=cost, credit_haircut=haircut)
            rr.append(daily_returns(o_["equity"]))
            st += OOS_DAYS
        rets = pd.concat(rr) if rr else pd.Series(dtype=float)
        sh = S.annualised_sharpe(rets)
        tot_ret = float((1.0 + rets).prod() - 1.0) if not rets.empty else np.nan
        sens.append({"label": label, "sharpe": sh, "total_return": tot_ret})
        print(f"  {label:<40} Sharpe {sh:+.3f}   return {tot_ret * 100:+.2f}%")

    _write(df, dev_bar, cleared, best, years, summaries, sens, skew)
    print(f"\nwritten to {RESULT_PATH.name}")
    print(f"\nholdout still sealed: {D.holdout_is_sealed()}")


def _write(df, dev_bar, cleared, best, years, summaries, sens, skew) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# RESULT: R1 hypothesis H3",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        f"Development window {D.DEV_START} to {D.DEV_END} ({years:.2f} years). "
        "Holdout sealed and verified unreadable by the run itself.",
        "",
        "Walk-forward: in-sample 252 days, out-of-sample 63 days, step 63. The VRP "
        "entry threshold is the only fitted quantity, chosen on in-sample blocks and "
        "applied unchanged to the next out-of-sample block. **Every number below is "
        "out-of-sample.**",
        "",
        f"Pricing: `{skew.describe()}`, gated at "
        "`research/RESULT_PRICING_GATE.md`. Costs 1.5% of credit round trip, measured "
        "from a live fill test.",
        "",
        "## Bar",
        "",
        f"- trials: {N_TRIALS} (fixed in advance)",
        f"- E[max under null] = sqrt(2 ln {N_TRIALS}) = {S.expected_max_null(N_TRIALS):.3f}",
        f"- SE(Sharpe) at {years:.2f}y = {S.sharpe_se(0.5, years):.3f}",
        f"- **development bar = {dev_bar:.3f}**",
        "",
        "## Results, out-of-sample, ranked",
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
        f"**Best: {best['trial']} at Sharpe {best['sharpe']:+.3f} against a bar of "
        f"{dev_bar:.3f}. VERDICT: {'CLEARS' if cleared else 'DOES NOT CLEAR'}.**",
        "",
        "## Sensitivity",
        "",
        "Section 7 requires a run at double the measured cost. The credit haircut "
        "additionally removes the pricing model's known residual overprice bias, which "
        "for a premium seller inflates credits.",
        "",
        "| scenario | Sharpe | return |",
        "|---|---|---|",
    ]
    for s in sens:
        L.append(f"| {s['label']} | {s['sharpe']:+.3f} | {s['total_return'] * 100:+.2f}% |")
    L += ["", "## Consequence", ""]
    if cleared:
        L += [
            f"Section 10: a trial cleared the bar, so **{best['trial']} earns exactly one "
            "shot at the sealed holdout**. No other trial may be taken there, and the "
            "threshold may not be re-fitted first.",
        ]
    else:
        L += [
            "Section 10: no trial cleared the development bar, so **nothing is promoted "
            "and the holdout is NOT touched**. The submission leads with the refusal "
            "behaviour and the risk architecture rather than a claimed edge.",
        ]
    L.append("")
    RESULT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
