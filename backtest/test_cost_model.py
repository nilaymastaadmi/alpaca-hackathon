# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py", "pandas", "numpy", "requests"]
# ///
"""
Is the "sell further OTM" finding real, or an artifact of our own cost model?

The sweep showed Sharpe rising monotonically as short-strike delta falls
(0.35 -> +0.814, 0.16 -> +1.155, 0.05 -> +2.056). Monotonic trends are usually
structural. But there is a competing explanation that would produce the same
shape for a bad reason:

  We charge transaction cost as 1.5% OF CREDIT. Real option spreads are closer
  to a fixed number of CENTS per leg. A 5 delta condor collects far less credit
  than a 16 delta condor, so a fixed cents cost is a much larger PERCENTAGE of
  its credit. If so, we are systematically under-charging exactly the configs
  that look best, and the trend is manufactured by the cost model.

Step 1: measure real bid/ask spreads by delta bucket from a live chain.
Step 2: re-run the delta sweep charging a realistic FIXED-CENTS cost.
Step 3: see whether the monotonic trend survives.

Run:  uv run backtest/test_cost_model.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import data as D  # noqa: E402
import engine as E  # noqa: E402
import pricing as P  # noqa: E402
import stats as S  # noqa: E402
from run_h3 import build_panel, daily_returns, load_skew  # noqa: E402

RESULT_PATH = Path(__file__).resolve().parent.parent / "research" / "RESULT_COST_MODEL.md"


def measure_spreads_by_delta():
    """Real per-leg bid/ask from a live SPY chain, bucketed by |delta|."""
    from alpaca.data.historical.option import OptionHistoricalDataClient
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest

    env = D._load_env()
    sc = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    oc = OptionHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    spot = float(sc.get_stock_latest_trade(
        StockLatestTradeRequest(symbol_or_symbols="SPY"))["SPY"].price)
    today = date.today()
    chain = oc.get_option_chain(OptionChainRequest(
        underlying_symbol="SPY",
        expiration_date_gte=today + timedelta(days=7),
        expiration_date_lte=today + timedelta(days=14),
        strike_price_gte=round(spot * 0.85, 2),
        strike_price_lte=round(spot * 1.15, 2),
    ))

    rows = []
    for occ, snap in chain.items():
        q = getattr(snap, "latest_quote", None)
        g = getattr(snap, "greeks", None)
        if not q or not q.bid_price or not q.ask_price or not g:
            continue
        d = getattr(g, "delta", None)
        if d is None:
            continue
        bid, ask = float(q.bid_price), float(q.ask_price)
        mid = (bid + ask) / 2
        if mid <= 0:
            continue
        rows.append({"abs_delta": abs(d), "bid": bid, "ask": ask, "mid": mid,
                     "spread": ask - bid, "half_spread": (ask - bid) / 2,
                     "spread_pct_of_mid": (ask - bid) / mid})
    df = pd.DataFrame(rows)
    if df.empty:
        return spot, df, None

    # Cap the top bucket at 0.45. An open-ended bucket to 1.0 sweeps in deep ITM
    # contracts, whose spreads are large in absolute terms and which this strategy
    # never sells. That contamination produced an $8.24 round trip on the first run.
    df = df[df["abs_delta"] <= 0.45]
    df["bucket"] = pd.cut(df["abs_delta"], [0, 0.075, 0.13, 0.20, 0.30, 0.45],
                          labels=["~0.05", "~0.10", "~0.16", "~0.25", "~0.35"])
    summary = df.groupby("bucket", observed=True).agg(
        n=("spread", "size"),
        median_mid=("mid", "median"),
        median_spread=("spread", "median"),
        median_half=("half_spread", "median"),
        median_spread_pct=("spread_pct_of_mid", "median"),
    )
    return spot, df, summary


def main() -> None:
    print("=" * 84)
    print("COST MODEL TEST: is 'sell further OTM' real or an artifact?")
    print("=" * 84)

    print("\nstep 1: measure real per-leg spreads by delta, live SPY chain 7-14 DTE")
    spot, raw, summary = measure_spreads_by_delta()
    if summary is None:
        print("  no two-sided quotes (market closed). Re-run during the session.")
        sys.exit(1)
    print(f"  spot {spot:.2f}, {len(raw)} quoted contracts\n")
    print(f"{'delta':>8}{'n':>6}{'mid':>9}{'spread':>9}{'half':>8}{'spread% of mid':>16}")
    for b, r in summary.iterrows():
        print(f"{str(b):>8}{int(r['n']):>6}{r['median_mid']:>9.2f}"
              f"{r['median_spread']:>9.2f}{r['median_half']:>8.3f}"
              f"{r['median_spread_pct'] * 100:>15.1f}%")

    # A 4-leg condor crosses 4 half-spreads to open. Use the median half-spread
    # of the short-strike bucket as the per-leg cost, which is conservative
    # because the long wings are further out and marginally cheaper.
    print("\n  A 4 leg condor pays roughly 4 half-spreads to open, 4 to close.")
    for b, r in summary.iterrows():
        rt_dollars = 8 * r["median_half"]
        print(f"    {str(b):>6} short strike: round trip ~${rt_dollars:.3f} per contract")

    print("\nstep 2: re-run the delta sweep with a FIXED-CENTS cost model")
    series = D.load_all()
    spy = D.window(series["SPY"], "dev")
    vix = D.window(series["VIX"], "dev")
    vix3m = D.window(series["VIX3M"], "dev")
    skew = load_skew()

    # Map each delta to its measured round-trip dollar cost per contract.
    delta_to_cost = {}
    label_map = {0.05: "~0.05", 0.10: "~0.10", 0.16: "~0.16",
                 0.25: "~0.25", 0.35: "~0.35"}
    for d, lbl in label_map.items():
        if lbl in summary.index:
            delta_to_cost[d] = float(8 * summary.loc[lbl, "median_half"])
        else:
            delta_to_cost[d] = 0.08

    # SPY was 180 to 470 across the development window and is 770 now. Spreads
    # scale roughly with price level, so deflate the measured dollar cost by the
    # ratio of historical spot to today's spot rather than assuming it constant.
    mean_hist_spot = float(spy["close"].mean())
    scale = mean_hist_spot / spot
    print(f"\n  scaling measured spreads by mean historical spot / today "
          f"({mean_hist_spot:.0f}/{spot:.0f} = {scale:.3f})")

    print(f"\n{'delta':>12}{'cost model':>26}{'Sharpe':>9}{'return':>10}"
          f"{'maxDD':>9}{'trades':>8}")
    rows = []
    for d in (0.05, 0.10, 0.16, 0.25, 0.35):
        cfg = E.TrialConfig("d", True, True, d, 10, 7, 14)
        panel = build_panel(spy, vix, vix3m, cfg.dte_target)
        expiries = E.build_expiries(panel.index)

        # (a) the original percentage-of-credit model
        res_a = E.run_strategy(panel, expiries, skew, cfg, 2.0, cost_pct=0.015)
        ra = daily_returns(res_a["equity"])
        sh_a = S.annualised_sharpe(ra)

        # (b) fixed cents, converted to an equivalent percentage per config by
        #     dividing the measured dollar cost by that config's median credit
        tr = res_a["trades"]
        med_credit = float(tr["credit"].median()) if len(tr) else np.nan
        dollar_rt = delta_to_cost[d] * scale
        equiv_pct = (dollar_rt / med_credit) if med_credit and med_credit > 0 else np.nan
        res_b = E.run_strategy(panel, expiries, skew, cfg, 2.0,
                               cost_pct=equiv_pct / 2 if np.isfinite(equiv_pct) else 0.015)
        rb = daily_returns(res_b["equity"])
        sh_b = S.annualised_sharpe(rb)
        ret_b = float((1 + rb).prod() - 1) if not rb.empty else np.nan
        dd_b = S.max_drawdown(res_b["equity"]) if not res_b["equity"].empty else np.nan

        print(f"{d:>12.2f}{'1.5% of credit':>26}{sh_a:>+9.3f}")
        print(f"{'':>12}{f'${dollar_rt:.3f} = {equiv_pct*100:.1f}% of credit':>26}"
              f"{sh_b:>+9.3f}{ret_b * 100:>+9.2f}%{dd_b * 100:>+8.2f}%"
              f"{len(res_b['trades']):>8}")
        rows.append({"delta": d, "median_credit": med_credit,
                     "dollar_rt": dollar_rt, "equiv_pct": equiv_pct,
                     "sharpe_pct_model": sh_a, "sharpe_fixed_model": sh_b,
                     "return_fixed": ret_b, "dd_fixed": dd_b})

    df = pd.DataFrame(rows)
    print("\n" + "=" * 84)
    still_monotonic = bool(df["sharpe_fixed_model"].is_monotonic_decreasing)
    print(f"  under the ORIGINAL model, Sharpe falls with delta: "
          f"{df['sharpe_pct_model'].is_monotonic_decreasing}")
    print(f"  under the REALISTIC model, Sharpe falls with delta: {still_monotonic}")
    if still_monotonic:
        print("\n  The trend SURVIVES. Selling further OTM is a structural finding,")
        print("  not an artifact of charging cost as a percentage of credit.")
    else:
        print("\n  The trend BREAKS. It was substantially an artifact of the cost")
        print("  model. Do NOT deploy far-OTM strikes on the strength of the sweep.")
    print("=" * 84)

    _write(spot, summary, df, scale, still_monotonic)
    print(f"\nwritten to {RESULT_PATH.name}")


def _write(spot, summary, df, scale, still_monotonic) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# RESULT: cost model test",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        "## The question",
        "",
        "The exploratory sweep showed Sharpe rising monotonically as short-strike delta "
        "falls. Monotonic trends usually indicate structure. But we charge transaction "
        "cost as **1.5% of credit**, while real option spreads are closer to a fixed "
        "number of cents per leg. Far-OTM structures collect much less credit, so a "
        "fixed-cents cost is a far larger percentage for them. That alone would "
        "manufacture the same trend for a bad reason.",
        "",
        f"## Measured spreads, live SPY chain 7-14 DTE, spot {spot:.2f}",
        "",
        "| delta bucket | n | median mid | median spread | half spread | spread % of mid |",
        "|---|---|---|---|---|---|",
    ]
    for b, r in summary.iterrows():
        L.append(f"| {b} | {int(r['n'])} | ${r['median_mid']:.2f} | "
                 f"${r['median_spread']:.2f} | ${r['median_half']:.3f} | "
                 f"{r['median_spread_pct'] * 100:.1f}% |")
    L += [
        "",
        "**The spread as a percentage of the option's own price rises sharply as you go "
        "further out of the money.** That is the mechanism the original cost model missed.",
        "",
        f"Historical spreads scaled by mean development spot / today's spot ({scale:.3f}), "
        "since spreads scale roughly with price level and SPY ranged 180 to 470 over the "
        "window against 770 today.",
        "",
        "## Delta sweep under both cost models",
        "",
        "| delta | median credit | realistic round trip | as % of credit | Sharpe (1.5% model) | Sharpe (realistic) |",
        "|---|---|---|---|---|---|",
    ]
    for r in df.itertuples(index=False):
        L.append(f"| {r.delta:.2f} | ${r.median_credit:.2f} | ${r.dollar_rt:.3f} | "
                 f"{r.equiv_pct * 100:.1f}% | {r.sharpe_pct_model:+.3f} | "
                 f"**{r.sharpe_fixed_model:+.3f}** |")
    L += [
        "",
        f"## Verdict: the trend {'SURVIVES' if still_monotonic else 'BREAKS'}",
        "",
    ]
    if still_monotonic:
        L += [
            "Selling further out of the money is a structural finding, not an artifact of "
            "charging cost as a percentage of credit. It survives a realistic fixed-cents "
            "cost model built from measured live spreads.",
            "",
            "It is still an EXPLORATORY result and still needs its own pre-registration "
            "before deployment.",
        ]
    else:
        L += [
            "The apparent advantage of far-OTM strikes was substantially manufactured by "
            "the cost model. Under realistic costs it does not hold. **Do not deploy "
            "far-OTM strikes on the strength of the sweep**, and treat the 1.5% "
            "round-trip figure as valid only near the 16 delta strikes it was measured on.",
        ]
    L.append("")
    RESULT_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
