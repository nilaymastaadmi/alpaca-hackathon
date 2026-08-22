# /// script
# requires-python = ">=3.11"
# ///
"""
Side-by-side daily report across the D3 tenor candidates (T4 deployed,
T6 old backtest-best, T7 new proposed best -- see research/DEPLOYMENT_DECISIONS.md
D3 and research/RESULT_H3_T7.md).

Reads artifacts/compare/{T4,T6,T7}/decisions.jsonl, written by
`agent/agent.py --compare-all` (or --compare <label> individually), and
writes a dated markdown table to research/D3_COMPARISON_LOG.md. This is
purely observational: none of the compare cycles ever place a real order
(agent.py forces dry_run=True for --compare regardless of flags), so this
report is live-market evidence gathered for free while the D3 decision
stays open, not a track record of real trades.

One row per (ET calendar date, label) using that day's LAST cycle if more
than one ran. "would enter" means every gate passed and a structure was
priced and sized -- the dry-run branch never sends an order, but the
decision itself is real.

Run:  uv run agent/compare_report.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPARE_DIR = ROOT / "artifacts" / "compare"
REPORT_PATH = ROOT / "research" / "D3_COMPARISON_LOG.md"
LABELS = ["T4", "T6", "T7"]


def load_label(label: str) -> dict[str, dict]:
    """Last decision per ET calendar date for one label."""
    path = COMPARE_DIR / label / "decisions.jsonl"
    if not path.exists():
        return {}
    by_date: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        ts = rec.get("timestamp", "")
        day = ts[:10]  # ISO date prefix, timestamp is already ET per agent.py
        if not day:
            continue
        by_date[day] = rec  # later lines overwrite, so the last cycle wins
    return by_date


def gate7(rec: dict) -> str:
    for g in rec.get("gates", []):
        if g.get("gate") == "vrp_threshold":
            return f"{'PASS' if g.get('passed') else 'fail'} ({g.get('reason', '')[:40]})"
    return "n/a"


def row_for(rec: dict) -> str:
    action = rec.get("action", "?")
    sig = rec.get("signals", {})
    vrp = sig.get("short_strike_vrp")
    dte = sig.get("short_strike_dte")
    vrp_s = f"{vrp:+.2f}" if isinstance(vrp, (int, float)) else "n/a"
    marker = "**ENTER**" if action == "enter" else action
    # gate7's own verdict, separate from the overall action: a market-closed
    # or outside-window refusal can still have a genuinely richer VRP reading
    # underneath it, and that divergence between candidates is the point of
    # this report -- collapsing it into one refuse/enter word would hide it.
    g7 = next((g for g in rec.get("gates", []) if g.get("gate") == "vrp_threshold"), None)
    g7_s = "" if g7 is None else (" [g7 pass]" if g7.get("passed") else " [g7 fail]")
    return f"{marker}{g7_s} (VRP {vrp_s}, {dte}d)"


def main() -> None:
    per_label = {label: load_label(label) for label in LABELS}
    all_dates = sorted(set().union(*[set(d) for d in per_label.values()]))

    print(f"D3 comparison, {len(all_dates)} date(s) logged")
    L = [
        "# D3 comparison log: T4 vs T6 vs T7",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')} by "
        "`agent/compare_report.py` from `agent/agent.py --compare-all`. "
        "Purely observational -- every row below is a dry-run decision, no "
        "order was ever sent. See `research/DEPLOYMENT_DECISIONS.md` D3 for "
        "the backtest case; this file is the live-market evidence gathered "
        "in parallel while that decision stays open until kickoff.",
        "",
        "| date | T4 (7-14 DTE, deployed) | T6 (21-45 DTE) | T7 (5-10 DTE, proposed) |",
        "|---|---|---|---|",
    ]
    if not all_dates:
        L.append("| *(no comparison cycles logged yet)* | | | |")
    for d in all_dates:
        cells = []
        for label in LABELS:
            rec = per_label[label].get(d)
            cells.append(row_for(rec) if rec else "-")
        L.append(f"| {d} | {cells[0]} | {cells[1]} | {cells[2]} |")
        print(f"  {d}: " + "  ".join(f"{lb}={row_for(per_label[lb][d]) if d in per_label[lb] else '-'}"
                                     for lb in LABELS))

    n_enter = {label: sum(1 for r in per_label[label].values() if r.get("action") == "enter")
              for label in LABELS}
    L += [
        "",
        "## Tally",
        "",
        "| label | days logged | would-enter days |",
        "|---|---|---|",
    ]
    for label in LABELS:
        L.append(f"| {label} | {len(per_label[label])} | {n_enter[label]} |")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwritten to {REPORT_PATH}")


if __name__ == "__main__":
    main()
