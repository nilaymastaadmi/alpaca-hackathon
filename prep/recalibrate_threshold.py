# /// script
# requires-python = ">=3.11"
# dependencies = ["alpaca-py"]
# ///
"""
D2 threshold recalibration READINESS check. Does not recalibrate anything.

research/DEPLOYMENT_DECISIONS.md D2 fixed gate 7 to measure the actual traded
strikes instead of a biased 30-day ATM proxy, and deliberately left
vrp_threshold at 1.0, unchanged, because no calibration history existed yet
at the corrected tenor. "Deliberately not guessed at... 1.0 unchanged is the
safe direction to be wrong in." This script exists to tell us, honestly and
on every run, whether that is still true -- and it stops there. It never
proposes a specific new threshold number and never writes to config.py.
Actually re-deriving vrp_threshold from real data, when there is enough of
it, is its own decision (a D3 entry in DEPLOYMENT_DECISIONS.md) made by
Nilay with the numbers in front of him, exactly like D1 and D2 were.

Uses agent.signals.short_strike_iv() directly, unmodified, so this measures
the EXACT quantity gate 7 acts on live -- not a reimplementation that could
drift from it. Reconstructs Contract objects from prep/iv_history.jsonl and
pairs each day's short-strike IV with a trailing realised vol computed the
same way (agent.signals.realised_vol) from real SPY daily closes fetched
fresh each run.

What "enough data" means, made concrete rather than picked by feel:
engine.py's THRESHOLD_GRID steps in whole vol-point increments (0.0, 1.0,
2.0, ...). Readiness is defined as a 90% CI half-width on the mean corrected
VRP no wider than HALF a grid step (0.5 vol points) -- tight enough that the
threshold's own resolution isn't swamped by sampling noise. This is a moving
target: the required-N projection is refit from the current empirical
standard deviation every run, not fixed in advance.

Only observations from CORRECT_TENOR_FROM onward count. prep/snapshot_iv.py
widened its DTE band from 21-45 to 5-45 on 2026-08-20; anything logged
before that date has zero observations at the 7-14 DTE band gate 7 actually
trades and is excluded, not silently included as if it were usable.

Safe to re-run any time, including nightly alongside the existing scheduled
task. Writes a dated status report to research/RECALIBRATION_STATUS.md so
progress night over night is visible in git history.

Run:  uv run --with alpaca-py prep/recalibrate_threshold.py
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = Path(__file__).resolve().parent / "iv_history.jsonl"
STATUS_PATH = PROJECT_ROOT / "research" / "RECALIBRATION_STATUS.md"

sys.path.insert(0, str(PROJECT_ROOT / "agent"))
import config as CFG  # noqa: E402
import signals as SIG  # noqa: E402

CORRECT_TENOR_FROM = date(2026, 8, 20)
COMPARE_T4_PATH = PROJECT_ROOT / "artifacts" / "compare" / "T4" / "decisions.jsonl"
TARGET_HALF_WIDTH = 0.5   # half of one THRESHOLD_GRID step (1.0 vol point)

# Standard two-sided 90% CI critical values, t_(0.95, df). Small table plus
# linear interpolation rather than adding scipy for one lookup.
T_TABLE = {
    1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895,
    8: 1.860, 9: 1.833, 10: 1.812, 12: 1.782, 15: 1.753, 20: 1.725,
    25: 1.708, 30: 1.697,
}


def t_critical(df: int) -> float:
    if df < 1:
        return float("nan")
    if df >= 30:
        return 1.645  # normal approximation beyond the table
    keys = sorted(T_TABLE)
    if df in T_TABLE:
        return T_TABLE[df]
    lo = max(k for k in keys if k < df)
    hi = min(k for k in keys if k > df)
    frac = (df - lo) / (hi - lo)
    return T_TABLE[lo] + frac * (T_TABLE[hi] - T_TABLE[lo])


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        sys.exit(f"missing .env at {path}")
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def fetch_spy_closes(env: dict[str, str], start: date, end: date) -> dict[date, float]:
    """Real daily closes, start padded 45 calendar days back for trailing RV."""
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    # IEX, not SIP: the Basic plan's recent-data restriction (RISK_REGISTER.md
    # 1.3) rejects SIP requests for recent dates with a 403. Bars this recent
    # can only come from IEX on this subscription.
    client = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    bars = client.get_stock_bars(
        StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=datetime.combine(start - timedelta(days=45), datetime.min.time(),
                                   tzinfo=timezone.utc),
            end=datetime.combine(end + timedelta(days=1), datetime.min.time(),
                                 tzinfo=timezone.utc),
            feed=DataFeed.IEX,
        )
    ).data.get("SPY", [])
    return {b.timestamp.date(): float(b.close) for b in bars}


def build_contracts_for_day(rows: list[dict]) -> list[SIG.Contract]:
    out = []
    for r in rows:
        try:
            _, exp, is_call, strike = SIG.parse_occ(r["occ_symbol"])
        except (ValueError, IndexError, KeyError):
            continue
        out.append(SIG.Contract(
            occ=r["occ_symbol"], strike=strike, is_call=is_call, expiry=exp,
            iv=r.get("implied_volatility"), delta=r.get("delta"),
            bid=None, ask=None,
        ))
    return out


def load_compare_fallback() -> dict[date, list[tuple[float, int]]]:
    """
    Per-date (vrp, dte_used) pairs from the T4 D3-comparison log
    (agent/agent.py --compare-all, hourly 19:15-01:15 IST). T4's preset IS
    the deployed config, so its short_strike_vrp is the exact quantity gate
    7 acts on -- already computed by SIG.compute() against live data, not
    reconstructed here.

    Used only as a FALLBACK when prep/iv_history.jsonl has no usable reading
    for a date (e.g. 2026-08-20, where the once-daily snapshot logger found
    no delta-bearing contracts in the traded band that one time it ran --
    the exact single-shot fragility this exists to backstop). Collapsed to
    ONE mean-VRP sample per date by the caller: multiple hourly cycles on
    the same day are not independent draws, and counting each as its own
    observation would repeat the overlapping-window overcounting mistake H1
    needed Newey-West correction for.
    """
    if not COMPARE_T4_PATH.exists():
        return {}
    out: dict[date, list[tuple[float, int]]] = defaultdict(list)
    for line in COMPARE_T4_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        ts = rec.get("timestamp", "")
        if not ts:
            continue
        d = date.fromisoformat(ts[:10])
        sig = rec.get("signals", {})
        vrp = sig.get("short_strike_vrp")
        dte_used = sig.get("short_strike_dte")
        if isinstance(vrp, (int, float)) and dte_used is not None:
            out[d].append((vrp, dte_used))
    return out


def main() -> None:
    env = load_env(ENV_PATH)
    cfg = CFG.Config()

    if not LOG_PATH.exists():
        sys.exit(f"no log at {LOG_PATH}")

    by_date: dict[date, list[dict]] = defaultdict(list)
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("underlying") != cfg.underlying:
            continue
        d = date.fromisoformat(row["date"])
        if d < CORRECT_TENOR_FROM:
            continue
        by_date[d].append(row)

    log_dates = sorted(by_date)
    compare_fallback = load_compare_fallback()
    compare_dates = sorted(d for d in compare_fallback if d >= CORRECT_TENOR_FROM)
    all_dates = sorted(set(log_dates) | set(compare_dates))
    print(f"correct-tenor log dates found: {len(log_dates)}  {log_dates}")
    print(f"D3-comparison T4 fallback dates found: {len(compare_dates)}  {compare_dates}")
    if not all_dates:
        _write_not_ready(0, None, None, None, "no correct-tenor data logged yet")
        print("\nNOT READY: zero correct-tenor observations. Nothing to report.")
        return

    closes_by_date = fetch_spy_closes(env, all_dates[0], all_dates[-1])
    trading_days = sorted(closes_by_date)

    # (date, vrp, dte_used, is_trading_day, source)
    samples: list[tuple[date, float, int, bool, str]] = []
    skipped = []
    for d in all_dates:
        is_trading_day = d in closes_by_date
        got_sample = False
        snapshot_failure = None

        if d in by_date:
            # 22 closes at/before d (or before the prior trading day if d
            # itself isn't one, e.g. a weekend catch-up run reflecting a
            # stale close).
            prior = [td for td in trading_days if td <= d]
            if len(prior) < 22:
                snapshot_failure = "insufficient SPY close history for trailing RV"
            else:
                window_closes = [closes_by_date[td] for td in prior[-22:]]
                try:
                    rv = SIG.realised_vol(window_closes, window=21)
                    contracts = build_contracts_for_day(by_date[d])
                    short_iv, dte_used = SIG.short_strike_iv(
                        contracts, d, cfg.dte_target, cfg.short_delta,
                        cfg.dte_min, cfg.dte_max)
                    samples.append((d, short_iv - rv, dte_used, is_trading_day, "snapshot"))
                    got_sample = True
                except ValueError as e:
                    snapshot_failure = f"snapshot logger: {e}"

        if not got_sample and d in compare_fallback:
            pairs = compare_fallback[d]
            mean_vrp = sum(v for v, _ in pairs) / len(pairs)
            mean_dte = round(sum(dte for _, dte in pairs) / len(pairs))
            samples.append((d, mean_vrp, mean_dte, is_trading_day,
                           f"D3-compare fallback, mean of {len(pairs)} cycles"))
            got_sample = True

        if not got_sample:
            reason = (f"{snapshot_failure}; no D3-compare fallback either"
                      if snapshot_failure else "no usable reading from either source")
            skipped.append((d, reason))

    print(f"\nusable samples: {len(samples)}")
    for d, vrp, dte_used, is_td, source in samples:
        flag = "" if is_td else "  [captured on non-trading day, likely a stale close]"
        print(f"  {d}  VRP {vrp:+.3f} pts  (dte {dte_used}, {source}){flag}")
    if skipped:
        print(f"\nskipped {len(skipped)}:")
        for d, reason in skipped:
            print(f"  {d}: {reason}")

    n = len(samples)
    if n < 2:
        _write_not_ready(n, None, None, None,
                          "fewer than 2 usable samples, cannot estimate variance yet",
                          samples=samples, skipped=skipped)
        print(f"\nNOT READY: {n} usable sample(s). Need at least 2 to estimate "
              "variance at all, and far more than that to trust it.")
        return

    vrps = [v for _, v, _, _, _ in samples]
    mean = sum(vrps) / n
    var = sum((v - mean) ** 2 for v in vrps) / (n - 1)
    sd = math.sqrt(var)
    tcrit = t_critical(n - 1)
    half_width = tcrit * sd / math.sqrt(n)
    ready = half_width <= TARGET_HALF_WIDTH

    print(f"\nmean corrected VRP: {mean:+.3f} pts   sd: {sd:.3f}   N: {n}")
    print(f"90% CI half-width: {half_width:.3f}  (target <= {TARGET_HALF_WIDTH})")

    if ready:
        print(f"\nREADY: half-width {half_width:.3f} is within the {TARGET_HALF_WIDTH} "
              "target. Enough data exists to responsibly START a proper D3 "
              "recalibration study -- this script still does not propose a new "
              "threshold number itself.")
        _write_ready(samples, mean, sd, half_width, skipped)
    else:
        # Project required N from the current empirical sd (normal approx,
        # a first pass -- refit every run as sd itself is re-measured).
        n_needed = math.ceil((1.645 * sd / TARGET_HALF_WIDTH) ** 2)
        more_needed = max(0, n_needed - n)
        print(f"\nNOT READY. At the current empirical sd ({sd:.3f}), roughly "
              f"{n_needed} total observations would close the gap -- about "
              f"{more_needed} more nights of correctly-collected data, "
              "assuming variance doesn't change much as N grows (it will be "
              "re-measured, and this projection refit, on the next run).")
        _write_not_ready(n, mean, sd, half_width, None, n_needed, more_needed, samples, skipped)


def _write_not_ready(n, mean, sd, half_width, blocking_reason,
                     n_needed=None, more_needed=None, samples=None, skipped=None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# D2 threshold recalibration: readiness status",
        "",
        f"Checked {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "Generated by `prep/recalibrate_threshold.py`, safe to re-run. This "
        "file NEVER contains a proposed new threshold value -- see the "
        "script's docstring for why.",
        "",
        "## Status: NOT READY",
        "",
    ]
    if blocking_reason:
        L.append(blocking_reason)
    else:
        L += [
            f"- usable observations: **{n}**",
            f"- mean corrected VRP so far: **{mean:+.3f}** vol points (sd {sd:.3f})",
            f"- current 90% CI half-width: **{half_width:.3f}** (target <= "
            f"{TARGET_HALF_WIDTH})",
            f"- projected total observations needed at current variance: "
            f"**~{n_needed}** (~{more_needed} more nights)",
            "",
            "`vrp_threshold` in `agent/config.py` stays at 1.0, per D2, until "
            "this crosses into READY.",
        ]
    if samples:
        L += ["", "## Samples so far",
              "", "| date | VRP (pts) | DTE used | trading day | source |",
              "|---|---|---|---|---|"]
        for d, vrp, dte_used, is_td, source in samples:
            L.append(f"| {d} | {vrp:+.3f} | {dte_used} | "
                     f"{'yes' if is_td else 'no (stale close)'} | {source} |")
    if skipped:
        L += ["", "## Skipped", ""]
        for d, reason in skipped:
            L.append(f"- {d}: {reason}")
    L.append("")
    STATUS_PATH.write_text("\n".join(L), encoding="utf-8")


def _write_ready(samples, mean, sd, half_width, skipped) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    n = len(samples)
    L = [
        "# D2 threshold recalibration: readiness status",
        "",
        f"Checked {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "Generated by `prep/recalibrate_threshold.py`, safe to re-run. This "
        "file NEVER contains a proposed new threshold value -- see the "
        "script's docstring for why.",
        "",
        "## Status: READY",
        "",
        f"- usable observations: **{n}**",
        f"- mean corrected VRP: **{mean:+.3f}** vol points (sd {sd:.3f})",
        f"- 90% CI half-width: **{half_width:.3f}** (target <= {TARGET_HALF_WIDTH}, met)",
        "",
        "Enough data exists to responsibly START a proper recalibration "
        "study. This script stops here on purpose: deriving the actual new "
        "threshold number needs its own reasoning (e.g. what false-accept "
        "rate the original 1.0 implicitly assumed, whether to fit against "
        "realised P&L rather than just the VRP distribution's shape), and "
        "that reasoning should be written down and decided by Nilay, dated, "
        "in `research/DEPLOYMENT_DECISIONS.md` as **D4** (D3 is already the "
        "T4-vs-T7 tenor proposal) -- the same way D1, D2 and D3 were, not "
        "mechanically applied by this script.",
        "",
        "## Samples", "",
        "| date | VRP (pts) | DTE used | trading day | source |",
        "|---|---|---|---|---|",
    ]
    for d, vrp, dte_used, is_td, source in samples:
        L.append(f"| {d} | {vrp:+.3f} | {dte_used} | "
                 f"{'yes' if is_td else 'no (stale close)'} | {source} |")
    if skipped:
        L += ["", "## Skipped", ""]
        for d, reason in skipped:
            L.append(f"- {d}: {reason}")
    L.append("")
    STATUS_PATH.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
