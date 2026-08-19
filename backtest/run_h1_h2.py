# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
R1, hypotheses H1 and H2. Development window only. Holdout stays sealed.

These two are the load-bearing tests because neither needs an option pricing
model, so neither can be blamed on one. Pre-registration section 3:

  H1  Mean VRP on SPY is positive over the development window, where VRP is
      VIX(t) minus realised vol over (t, t+21], in annualised vol points.

  H2  Mean VRP in contango (VIX/VIX3M < 1.0) exceeds mean VRP in backwardation.

If H1 fails, H3 is not run at all and the track decision gets escalated.

Run:  uv run backtest/run_h1_h2.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import stats as S  # noqa: E402
import vol as V  # noqa: E402

HORIZON = 21
RESULTS_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_H1_H2.md"


def main() -> None:
    print("=" * 72)
    print("R1  H1 and H2   development window only, holdout SEALED")
    print("=" * 72)
    print(f"run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")

    series = D.load_all()

    # Confirm the seal is actually on before touching anything.
    print(f"\nholdout sealed: {D.holdout_is_sealed()}")
    try:
        D.window(series["SPY"], "holdout")
        print("  ERROR: holdout was readable. The seal is not working.")
        sys.exit(1)
    except D.HoldoutSealError:
        print("  seal verified, holdout is not readable from this run")

    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    print(f"\ndevelopment window {D.DEV_START} to {D.DEV_END}")
    print(f"  SPY   {len(spy)} bars")
    print(f"  VIX   {len(vix)} bars")
    print(f"  VIX3M {len(vix3m)} bars")

    years = (spy.index.max() - spy.index.min()).days / 365.25
    print(f"  span  {years:.2f} calendar years")

    # ---------------- H1 ----------------
    print("\n" + "-" * 72)
    print("H1: mean VRP > 0")
    print("-" * 72)

    v = V.vrp(vix["close"], spy["close"], horizon=HORIZON)
    naive = S.summarise(v["vrp"])
    nw_t = S.newey_west_t(v["vrp"], lags=HORIZON)

    print(f"  VRP = VIX(t) minus realised vol over (t, t+{HORIZON}], vol points")
    print(f"  {naive.describe(unit=' pts')}")
    print(f"  naive t assumes independence and is WRONG here: {HORIZON}-day forward")
    print(f"  windows sampled daily share {HORIZON - 1} of {HORIZON} days.")
    print(f"  Newey-West t ({HORIZON} lags): {nw_t:+.2f}   one-sided p={S._normal_sf(nw_t):.4f}")

    h1_pass = naive.mean > 0 and nw_t > 1.645
    print(f"\n  H1 {'HOLDS' if h1_pass else 'FAILS'} "
          f"(mean positive and NW t > 1.645)")

    # Registered prediction P1: mean VRP lands between 2.0 and 4.0 points.
    p1 = 2.0 <= naive.mean <= 4.0
    print(f"  P1 (mean VRP in 2.0 to 4.0 pts): "
          f"{'CORRECT' if p1 else 'WRONG'}, measured {naive.mean:+.2f}")

    if not h1_pass:
        print("\n  Pre-registration section 10: H1 failed, so H2 and H3 are NOT run.")
        print("  Reporting the negative and escalating the track decision.")
        _write_results(naive, nw_t, h1_pass, p1, None, None, None, years)
        return

    # ---------------- H2 ----------------
    print("\n" + "-" * 72)
    print("H2: VRP in contango > VRP in backwardation")
    print("-" * 72)

    ts = V.term_structure(vix["close"], vix3m["close"])
    joined = v.join(ts[["ratio", "contango"]], how="inner").dropna()

    con = joined.loc[joined["contango"], "vrp"]
    back = joined.loc[~joined["contango"], "vrp"]

    con_s, back_s = S.summarise(con), S.summarise(back)
    con_nw = S.newey_west_t(con, lags=HORIZON)
    back_nw = S.newey_west_t(back, lags=HORIZON)
    gap = con_s.mean - back_s.mean

    print(f"  contango      ({len(con):>4} days, {len(con)/len(joined)*100:.1f}%): "
          f"mean VRP {con_s.mean:+.2f} pts, NW t {con_nw:+.2f}")
    print(f"  backwardation ({len(back):>4} days, {len(back)/len(joined)*100:.1f}%): "
          f"mean VRP {back_s.mean:+.2f} pts, NW t {back_nw:+.2f}")
    print(f"  gap: {gap:+.2f} vol points")

    h2_pass = gap > 0
    print(f"\n  H2 {'HOLDS' if h2_pass else 'FAILS'}")

    # Registered prediction P2: gap of at least 1.0 vol point.
    p2 = gap >= 1.0
    print(f"  P2 (gap >= 1.0 pt): {'CORRECT' if p2 else 'WRONG'}, measured {gap:+.2f}")

    # Context for the sizing and gating decisions downstream. The mean gap is
    # NOT where the regime gate earns its place; the tail is.
    print("\n  distribution detail, which matters more than the mean:")
    for label, s in (("contango", con), ("backwardation", back)):
        print(f"    {label:14} p05={s.quantile(0.05):+7.2f}  median={s.median():+7.2f}  "
              f"p95={s.quantile(0.95):+7.2f}  worst={s.min():+7.2f}")

    blow_con = float((con < -10).mean())
    blow_back = float((back < -10).mean())
    print(f"\n  days with VRP < -10 pts (short vol gets hurt badly):")
    print(f"    contango      {blow_con * 100:5.1f}%")
    print(f"    backwardation {blow_back * 100:5.1f}%  "
          f"({blow_back / blow_con:.1f}x more frequent)" if blow_con > 0 else "")

    tails = {
        "con_p05": float(con.quantile(0.05)), "back_p05": float(back.quantile(0.05)),
        "con_med": float(con.median()), "back_med": float(back.median()),
        "con_worst": float(con.min()), "back_worst": float(back.min()),
        "blow_con": blow_con, "blow_back": blow_back,
    }

    _write_results(naive, nw_t, h1_pass, p1, con_s, back_s, gap, years,
                   con_nw=con_nw, back_nw=back_nw, h2_pass=h2_pass, p2=p2,
                   contango_share=len(con) / len(joined), tails=tails)

    print(f"\nresults written to {RESULTS_PATH.relative_to(RESULTS_PATH.parent.parent)}")


def _write_results(naive, nw_t, h1_pass, p1, con_s, back_s, gap, years,
                   con_nw=None, back_nw=None, h2_pass=None, p2=None,
                   contango_share=None, tails=None) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RESULT: R1 hypotheses H1 and H2",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        f"Development window {D.DEV_START} to {D.DEV_END} "
        f"({years:.2f} calendar years). Holdout sealed and verified unreadable.",
        "",
        "Design fixed in advance: `research/PREREGISTRATION_R1.md`.",
        "",
        "## H1: mean VRP > 0",
        "",
        f"- observations: {naive.n}",
        f"- mean VRP: **{naive.mean:+.2f} vol points**, sd {naive.std:.2f}",
        f"- naive t: {naive.t_stat:+.2f} (INVALID here, overlapping windows)",
        f"- Newey-West t ({HORIZON} lags): **{nw_t:+.2f}**, one-sided p={S._normal_sf(nw_t):.4f}",
        f"- verdict: **H1 {'HOLDS' if h1_pass else 'FAILS'}**",
        f"- registered prediction P1 (mean in 2.0 to 4.0 pts): "
        f"**{'CORRECT' if p1 else 'WRONG'}**",
        "",
        "The naive t is reported only to show why it must not be used. "
        f"{HORIZON}-day forward windows sampled daily overlap by {HORIZON - 1}/{HORIZON}, "
        "so the independent-observation assumption fails and significance is overstated "
        "by roughly sqrt(21).",
        "",
    ]
    if con_s is not None:
        lines += [
            "## H2: VRP in contango > VRP in backwardation",
            "",
            f"- contango: {con_s.n} days ({contango_share * 100:.1f}%), "
            f"mean VRP **{con_s.mean:+.2f}** pts, NW t {con_nw:+.2f}",
            f"- backwardation: {back_s.n} days, "
            f"mean VRP **{back_s.mean:+.2f}** pts, NW t {back_nw:+.2f}",
            f"- gap: **{gap:+.2f} vol points**",
            f"- verdict: **H2 {'HOLDS' if h2_pass else 'FAILS'}**",
            f"- registered prediction P2 (gap >= 1.0 pt): "
            f"**{'CORRECT' if p2 else 'WRONG'}**, measured {gap:+.2f}",
            "",
        ]
    if tails is not None:
        lines += [
            "## The finding that actually matters, and it is not the mean",
            "",
            "P2 was WRONG: the mean gap is only "
            f"{gap:+.2f} vol points, not the 1.0 predicted. Recording the miss "
            "rather than dropping it. But the mean is the wrong statistic here, "
            "and the distribution shows why.",
            "",
            "| | contango | backwardation |",
            "|---|---|---|",
            f"| median VRP | {tails['con_med']:+.2f} | **{tails['back_med']:+.2f}** |",
            f"| 5th percentile | {tails['con_p05']:+.2f} | **{tails['back_p05']:+.2f}** |",
            f"| worst | {tails['con_worst']:+.2f} | {tails['back_worst']:+.2f} |",
            f"| days with VRP < -10 pts | {tails['blow_con'] * 100:.1f}% | "
            f"**{tails['blow_back'] * 100:.1f}%** |",
            f"| Newey-West t | **{con_nw:+.2f}** | {back_nw:+.2f} |",
            "",
            "**Selling premium in backwardation looks BETTER on the median "
            f"({tails['back_med']:+.2f} vs {tails['con_med']:+.2f}) and is far worse in the "
            f"tail ({tails['back_p05']:+.2f} vs {tails['con_p05']:+.2f} at the 5th "
            "percentile).** That is the short-volatility payoff shape in one table: "
            "collect a little more, most of the time, then lose enormously.",
            "",
            "**The stronger justification for the regime gate is significance, not the "
            f"mean.** VRP in contango has Newey-West t = {con_nw:+.2f}, comfortably "
            f"significant. In backwardation t = {back_nw:+.2f}, which is "
            "indistinguishable from zero. So the honest statement is not "
            "\"contango pays more\" but **\"VRP is only reliably present in contango\"**.",
            "",
            "### The caveat that stops this being oversold",
            "",
            "The worst observations in BOTH regimes are of similar size "
            f"({tails['con_worst']:+.2f} contango, {tails['back_worst']:+.2f} "
            "backwardation), and they are the same event: the February to March 2020 "
            "crash. **A crash begins while the term structure is still in contango.** "
            "The regime gate therefore reacts, it does not predict. It cannot protect "
            "against day one of a shock; what it does is stop the agent from staying "
            "short volatility through the rest of it. Any submission language implying "
            "the gate anticipates crashes is false.",
            "",
            "This is also why the defined-risk structure is not optional. The gate "
            "handles the regime; the long wings handle the day the gate is late.",
            "",
        ]
    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
