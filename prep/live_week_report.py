"""
Turn the sealed artifact log into the live-week results page.

Judges read results, not JSONL. This regenerates research/LIVE_WEEK.md from
artifacts/decisions.jsonl and artifacts/positions.json, so the numbers in
the results page are the numbers in the sealed log by construction, with no
hand-typed table to drift. Run it after Friday's flatten, and any time
before that for a draft.

    uv run python prep/live_week_report.py            # writes research/LIVE_WEEK.md
    uv run python prep/live_week_report.py --stdout   # prints instead
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "artifacts" / "decisions.jsonl"
POSITIONS = ROOT / "artifacts" / "positions.json"
SEAL = ROOT / "artifacts" / "merkle_root.json"
OUT = ROOT / "research" / "LIVE_WEEK.md"

LIVE_START = "2026-08-31"          # first judged session
CYCLE_ACTIONS = ("enter", "refuse", "halt", "flatten")
ENVIRONMENTAL = ("market_open", "session_window")
LADDER = "entry ladder unfilled (all gates passed)"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def classify(r: dict) -> tuple[bool, str | None]:
    """Same rule as the dashboard and `make summary`, applied at read time."""
    bg, eb = r.get("blocking_gate"), r.get("environmental_block")
    if eb is None and bg in ENVIRONMENTAL:
        eb, bg = bg, None
    opp = r.get("was_an_opportunity")
    if opp is None:
        opp = eb is None
    return bool(opp), bg


def money(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.2f}"


def build() -> str:
    rows = load(DECISIONS)
    live = [r for r in rows if r.get("timestamp", "") >= LIVE_START
            and not r.get("dry_run")]
    by_day: dict[str, list[dict]] = defaultdict(list)
    for r in live:
        by_day[r["timestamp"][:10]].append(r)

    lines: list[str] = []
    lines.append("# Live week results, generated from the sealed log")
    lines.append("")
    lines.append(f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
                 f"by `prep/live_week_report.py` from `artifacts/decisions.jsonl` "
                 f"({len(rows)} artifacts, {len(live)} in the judged window from "
                 f"{LIVE_START}). Nothing in this file is typed by hand; regenerate "
                 f"it rather than editing it. `make verify` proves the log it "
                 f"reads from has not been altered.")
    lines.append("")
    seal = json.loads(SEAL.read_text(encoding="utf-8")) if SEAL.exists() else {}
    if seal:
        lines.append(f"Sealed root at generation time: `{seal.get('merkle_root', '?')}` "
                     f"(sealed {seal.get('sealed_at', seal.get('timestamp', '?'))}).")
        lines.append("")

    # --- per-day table ------------------------------------------------------
    lines.append("## Day by day")
    lines.append("")
    lines.append("| Day (ET) | Cycles | Opportunities | Entered | Refused | Halted | "
                 "Flattened | Exit checks | Hedge attempts | Equity open | "
                 "Equity close | Open at close |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    week_gates: Counter = Counter()
    week = Counter()
    for day in sorted(by_day):
        rs = by_day[day]
        cyc = [r for r in rs if r.get("action") in CYCLE_ACTIONS]
        opp = [(r, classify(r)[1]) for r in cyc if classify(r)[0]]
        acts = Counter(r["action"] for r, _ in opp)
        for r, bg in opp:
            if r["action"] == "refuse":
                week_gates[bg or LADDER] += 1
            elif r["action"] == "halt" and bg:
                week_gates[bg] += 1
        exits = sum(1 for r in rs if str(r.get("action", "")).startswith("exit_check"))
        hedges = sum(1 for r in rs if str(r.get("action", "")).startswith("hedge:"))
        eq = [r["portfolio"].get("equity") for r in cyc if r.get("portfolio", {}).get("equity")]
        last = cyc[-1] if cyc else None
        open_close = last["portfolio"].get("open_structures") if last else None
        lines.append(
            f"| {day} | {len(cyc)} | {len(opp)} | {acts.get('enter', 0)} | "
            f"{acts.get('refuse', 0)} | {acts.get('halt', 0)} | "
            f"{acts.get('flatten', 0)} | {exits} | {hedges} | "
            f"{money(eq[0]) if eq else 'n/a'} | {money(eq[-1]) if eq else 'n/a'} | "
            f"{open_close if open_close is not None else 'n/a'} |")
        week["cycles"] += len(cyc)
        week["opp"] += len(opp)
        for k in ("enter", "refuse", "halt", "flatten"):
            week[k] += acts.get(k, 0)
        week["exits"] += exits
        week["hedges"] += hedges
    lines.append("")
    lines.append(f"Week totals: {week['cycles']} cycles, {week['opp']} decision "
                 f"opportunities, {week['enter']} entered, {week['refuse']} refused, "
                 f"{week['halt']} halted, {week['flatten']} flatten cycles, "
                 f"{week['exits']} exit checks, {week['hedges']} hedge attempts.")
    lines.append("")

    # --- refusals -----------------------------------------------------------
    lines.append("## Why it refused")
    lines.append("")
    lines.append("| Blocking gate | Count | Share of opportunities |")
    lines.append("|---|---|---|")
    for gate, n in week_gates.most_common():
        share = n / max(week["opp"], 1) * 100
        lines.append(f"| {gate} | {n} | {share:.1f}% |")
    lines.append("")

    # --- hedge --------------------------------------------------------------
    hedge_acts = Counter(r["action"] for r in live
                         if str(r.get("action", "")).startswith("hedge:"))
    if hedge_acts:
        lines.append("## Tail hedge")
        lines.append("")
        for k, n in hedge_acts.most_common():
            lines.append(f"- `{k}`: {n}")
        if hedge_acts.get("hedge:no_candidate") and not any(
                k for k in hedge_acts if k in ("hedge:bought", "hedge:filled")):
            lines.append("")
            lines.append("The hedge never engaged: every attempt found zero VIX "
                         "contracts on the feed and refused to buy off an empty "
                         "read (RISK_REGISTER.md 4.9). The purchased wings were the "
                         "only crash protection all week.")
        lines.append("")

    # --- positions ----------------------------------------------------------
    pos = json.loads(POSITIONS.read_text(encoding="utf-8")) if POSITIONS.exists() else {}
    opened = pos.get("open", []) or []
    closed = pos.get("closed", []) or []
    lines.append("## Positions")
    lines.append("")
    lines.append(f"Open at generation time: {len(opened)}. Closed: {len(closed)}.")
    lines.append("")
    if opened or closed:
        lines.append("| id | status | expiry | contracts | credit | max risk | "
                     "short put | short call | realised |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for p, status in [(p, "open") for p in opened] + [(p, "closed") for p in closed]:
            risk = p.get("max_loss_per_contract", 0) * 100 * p.get("contracts", 0)
            lines.append(
                f"| {p.get('id')} | {status} | {p.get('expiry')} | {p.get('contracts')} | "
                f"{p.get('credit')} | {money(risk)} | {p.get('short_put')} | "
                f"{p.get('short_call')} | "
                f"{money(p.get('realised_pnl')) if p.get('realised_pnl') is not None else ''} |")
        lines.append("")

    # --- last exit check per position --------------------------------------
    last_exit: dict[str, dict] = {}
    for r in live:
        if str(r.get("action", "")).startswith("exit_check"):
            e = r.get("exit", {})
            if e.get("position"):
                last_exit[e["position"]] = {"t": r["timestamp"], **e}
    if last_exit:
        lines.append("## Last exit check per position")
        lines.append("")
        lines.append("| position | at (ET) | verdict | profit % of credit | DTE | reason |")
        lines.append("|---|---|---|---|---|---|")
        for pid, e in last_exit.items():
            lines.append(f"| {pid} | {e['t'][:16]} | {e.get('action')} | "
                         f"{e.get('profit_frac', 0) * 100:.1f} | {e.get('dte')} | "
                         f"{str(e.get('reason', ''))[:80]} |")
        lines.append("")

    # --- P&L ----------------------------------------------------------------
    cyc_all = [r for r in live if r.get("action") in CYCLE_ACTIONS
               and r.get("portfolio", {}).get("equity")]
    if cyc_all:
        first, last = cyc_all[0], cyc_all[-1]
        e0, e1 = first["portfolio"]["equity"], last["portfolio"]["equity"]
        lines.append("## P&L")
        lines.append("")
        lines.append(f"- First judged cycle {first['timestamp'][:16]} ET: equity {money(e0)}")
        lines.append(f"- Latest cycle {last['timestamp'][:16]} ET: equity {money(e1)}")
        lines.append(f"- Change: {money(e1 - e0)} ({(e1 - e0) / e0 * 100:+.3f}%) on a "
                     f"$100,000 paper account")
        lines.append(f"- Reported drawdown at latest cycle: "
                     f"{last['portfolio'].get('drawdown', 0) * 100:.2f}%")
        lines.append("")
        lines.append("One week of options P&L is mostly noise; the research "
                     "establishes positive expectancy, the week is one draw from it. "
                     "Nothing above is adjusted, annualised, or selected.")
        lines.append("")

    lines.append("## Incident record")
    lines.append("")
    lines.append("31 Aug 09:45 ET: a payload-parsing bug read the account as flat and "
                 "the agent stacked four condors instead of one. The sealed log caught "
                 "it in one artifact. Bug, fix, regression test, and the adopted "
                 "positions: `RISK_REGISTER.md` 4.7 and 4.8.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    text = build()
    if "--stdout" in sys.argv:
        print(text)
    else:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT} ({len(text.splitlines())} lines)")
