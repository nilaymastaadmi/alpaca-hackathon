# /// script
# requires-python = ">=3.11"
# ///
"""
Side-by-side report across the D3 tenor candidates (T4 deployed, T6 old
backtest-best, T7 new proposed best -- see research/DEPLOYMENT_DECISIONS.md
D3 and research/RESULT_H3_T7.md).

Reads artifacts/compare/{T4,T6,T7}/decisions.jsonl, written by
`agent/agent.py --compare-all` (scheduled hourly, 19:15-01:15 IST, matching
`agent/config.py`'s own trade_window -- see AlpacaHackathon-D3Compare and the
2026-08-25 change from one arbitrary daily snapshot to that window: the
agent itself avoids the first 15 minutes of the session on a measured
spread-widening finding, so a single 21:30 IST reading was both off the
agent's own valid window AND too thin a sample to show how a candidate
behaves across a session). Purely observational: none of the compare cycles
ever place a real order (agent.py forces dry_run=True for --compare
regardless of flags).

One row per CYCLE BATCH (all three labels run seconds apart inside one
--compare-all invocation, grouped here by rounding to the nearest 5 minutes)
rather than collapsing a day to its last reading, so the intraday shape is
visible, not just an end-of-session snapshot. "would enter" means every gate
passed and a structure was priced and sized -- the dry-run branch never
sends an order, but the decision itself is real.

Run:  uv run agent/compare_report.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPARE_DIR = ROOT / "artifacts" / "compare"
REPORT_PATH = ROOT / "research" / "D3_COMPARISON_LOG.md"
LABELS = ["T4", "T6", "T7"]
BATCH_MINUTES = 5


def load_label(label: str) -> list[dict]:
    path = COMPARE_DIR / label / "decisions.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def batch_key(ts: str) -> str | None:
    """Round a timestamp down to the nearest BATCH_MINUTES so the three
    labels' near-simultaneous cycles from one --compare-all run land in the
    same row, without needing them to share an exact timestamp."""
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    floored_minute = (dt.minute // BATCH_MINUTES) * BATCH_MINUTES
    dt = dt.replace(minute=floored_minute, second=0, microsecond=0)
    return dt.isoformat()


def cell(rec: dict | None) -> str:
    if rec is None:
        return "-"
    action = rec.get("action", "?")
    sig = rec.get("signals", {})
    vrp = sig.get("short_strike_vrp")
    vrp_s = f"{vrp:+.2f}" if isinstance(vrp, (int, float)) else "n/a"
    marker = "**ENTER**" if action == "enter" else action
    g7 = next((g for g in rec.get("gates", []) if g.get("gate") == "vrp_threshold"), None)
    g7_s = "" if g7 is None else (" [g7 pass]" if g7.get("passed") else " [g7 fail]")
    return f"{marker}{g7_s} (VRP {vrp_s})"


def main() -> None:
    per_label = {label: load_label(label) for label in LABELS}

    # batch_key -> {label: record}, keeping the LAST record per label within
    # a batch (in the rare case two cycles round into the same bucket).
    batches: dict[str, dict[str, dict]] = defaultdict(dict)
    for label in LABELS:
        for rec in per_label[label]:
            bk = batch_key(rec.get("timestamp", ""))
            if bk:
                batches[bk][label] = rec

    ordered = sorted(batches)
    print(f"D3 comparison, {len(ordered)} cycle batch(es) logged")

    L = [
        "# D3 comparison log: T4 vs T6 vs T7",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')} by "
        "`agent/compare_report.py` from `agent/agent.py --compare-all`, "
        "scheduled hourly 19:15-01:15 IST (matching `agent/config.py`'s own "
        "trade_window). Purely observational -- every row below is a "
        "dry-run decision, no order was ever sent. See "
        "`research/DEPLOYMENT_DECISIONS.md` D3 for the backtest case; this "
        "file is the live-market evidence gathered in parallel while that "
        "decision stays open until kickoff.",
        "",
        "| ET timestamp | T4 (7-14 DTE, deployed) | T6 (21-45 DTE) | T7 (5-10 DTE, proposed) |",
        "|---|---|---|---|",
    ]
    if not ordered:
        L.append("| *(no comparison cycles logged yet)* | | | |")
    for bk in ordered:
        row = batches[bk]
        cells = [cell(row.get(label)) for label in LABELS]
        ts_display = bk[:16].replace("T", " ")
        L.append(f"| {ts_display} | {cells[0]} | {cells[1]} | {cells[2]} |")
        print(f"  {ts_display}: " + "  ".join(f"{lb}={cell(row.get(lb))}" for lb in LABELS))

    # Daily summary, since an hourly schedule makes the per-cycle table long
    # fast: for each ET calendar date, how often did gate 7 pass and how
    # often would each candidate actually have entered.
    by_date: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for label in LABELS:
        for rec in per_label[label]:
            day = rec.get("timestamp", "")[:10]
            if day:
                by_date[day][label].append(rec)

    L += ["", "## Daily summary", "",
          "| date | label | cycles | gate7 pass | would-enter | VRP range |",
          "|---|---|---|---|---|---|"]
    for day in sorted(by_date):
        for label in LABELS:
            recs = by_date[day].get(label, [])
            if not recs:
                continue
            g7_pass = sum(1 for r in recs
                         if any(g.get("gate") == "vrp_threshold" and g.get("passed")
                                for g in r.get("gates", [])))
            n_enter = sum(1 for r in recs if r.get("action") == "enter")
            vrps = [r["signals"]["short_strike_vrp"] for r in recs
                   if isinstance(r.get("signals", {}).get("short_strike_vrp"), (int, float))]
            vrp_range = f"{min(vrps):+.2f} to {max(vrps):+.2f}" if vrps else "n/a"
            L.append(f"| {day} | {label} | {len(recs)} | {g7_pass} | {n_enter} | {vrp_range} |")

    n_enter_total = {label: sum(1 for r in per_label[label] if r.get("action") == "enter")
                     for label in LABELS}
    L += ["", "## Overall tally", "", "| label | cycles logged | would-enter cycles |", "|---|---|---|"]
    for label in LABELS:
        L.append(f"| {label} | {len(per_label[label])} | {n_enter_total[label]} |")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwritten to {REPORT_PATH}")


if __name__ == "__main__":
    main()
