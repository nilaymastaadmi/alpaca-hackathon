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
from datetime import datetime, timezone
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
    same row, without needing them to share an exact timestamp.

    Normalises to UTC before flooring, not after: agent.py's main decision
    record uses ET while its hedge/exit/flatten sub-artifacts used UTC until
    2026-08-26 (a real bug, fixed at the source, not just here). Flooring an
    un-normalised timestamp compares clock digits, not real instants, so two
    records written seconds apart could land in different rows purely
    because one carried a UTC offset and the other ET's -04:00 -- exactly
    what produced the phantom 16:45-19:45 rows this fix removes. Historical
    entries written before the source fix still carry the old, inconsistent
    offsets, so this stays defensive rather than assuming every record from
    here on is ET."""
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
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
        "| ET timestamp | T4 (7-14 DTE) | T6 (21-45 DTE, deployed since 30 Aug) | T7 (5-10 DTE) |",
        "|---|---|---|---|",
    ]
    if not ordered:
        L.append("| *(no comparison cycles logged yet)* | | | |")
    for bk in ordered:
        row = batches[bk]
        cells = [cell(row.get(label)) for label in LABELS]
        # Display each batch's OWN recorded timestamp (T4 preferred, since
        # it always has a full decision cycle), not the UTC-normalised
        # bucket key -- that key exists only to group same-instant records
        # correctly, not to be read. Records written before the 2026-08-26
        # timestamp fix may still show a UTC-flavoured time here; that is a
        # known historical artifact, not a new bug.
        rep = row.get("T4") or row.get("T6") or row.get("T7")
        ts_display = (rep.get("timestamp", bk) if rep else bk)[:16].replace("T", " ")
        L.append(f"| {ts_display} | {cells[0]} | {cells[1]} | {cells[2]} |")
        print(f"  {ts_display}: " + "  ".join(f"{lb}={cell(row.get(lb))}" for lb in LABELS))

    # Daily summary, since an hourly schedule makes the per-cycle table long
    # fast: for each ET calendar date, how often did gate 7 pass and how
    # often would each candidate actually have entered. Built from the
    # deduplicated `batches`, not raw per_label records -- each real cycle
    # writes TWO lines (a hedge sub-entry, then the main decision), so
    # counting raw records here double-counted "cycles" even though the
    # per-cycle table above was already correct.
    by_date: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in batches.values():
        for label, rec in row.items():
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

    cycles_by_label = {label: sum(1 for row in batches.values() if label in row)
                       for label in LABELS}
    n_enter_total = {label: sum(1 for row in batches.values()
                                if row.get(label, {}).get("action") == "enter")
                     for label in LABELS}
    L += ["", "## Overall tally", "", "| label | cycles logged | would-enter cycles |", "|---|---|---|"]
    for label in LABELS:
        L.append(f"| {label} | {cycles_by_label[label]} | {n_enter_total[label]} |")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwritten to {REPORT_PATH}")

    # Machine-readable twin of the tables above, for the dashboard's
    # "three agents, one market" panel. The per-candidate logs themselves
    # stay gitignored (a judge browsing artifacts/ should only find the
    # deployed agent's sealed decisions); this summary carries no orders,
    # only counts and the latest verdict per candidate.
    daily = []
    for day in sorted(by_date):
        for label in LABELS:
            recs = by_date[day].get(label, [])
            if not recs:
                continue
            vrps = [r["signals"]["short_strike_vrp"] for r in recs
                    if isinstance(r.get("signals", {}).get("short_strike_vrp"), (int, float))]
            daily.append({
                "date": day, "label": label, "cycles": len(recs),
                "gate7_pass": sum(1 for r in recs if any(
                    g.get("gate") == "vrp_threshold" and g.get("passed")
                    for g in r.get("gates", []))),
                "would_enter": sum(1 for r in recs if r.get("action") == "enter"),
                "vrp_min": min(vrps) if vrps else None,
                "vrp_max": max(vrps) if vrps else None,
            })
    last_bk = ordered[-1] if ordered else None
    last = {}
    if last_bk:
        for label, rec in batches[last_bk].items():
            last[label] = {"timestamp": rec.get("timestamp"),
                           "action": rec.get("action"),
                           "blocking_gate": rec.get("blocking_gate"),
                           "short_strike_vrp": rec.get("signals", {}).get("short_strike_vrp")}
    summary = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "labels": {"T4": "7 to 14 DTE", "T6": "21 to 45 DTE, deployed since 30 Aug",
                   "T7": "5 to 10 DTE"},
        "deployed": "T6",
        "daily": daily,
        "tally": {label: {"cycles": cycles_by_label[label],
                          "would_enter": n_enter_total[label]} for label in LABELS},
        "last_batch": last,
    }
    out = ROOT / "artifacts" / "compare_summary.json"
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"summary written to {out}")


if __name__ == "__main__":
    main()
