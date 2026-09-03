"""
Live cockpit for the VRP agent.

Reads everything straight off disk, with no API calls. That is deliberate, and
it is the lesson from chikki's cockpit: a dashboard that needs a live API to
render is a dashboard that dies during the demo, at the exact moment it matters.
This one renders with the market closed, the network down, and the MCP server
stopped, because every number on it was written by the agent when it ran.

Run locally:   streamlit run dashboard/app.py
Deploy:        Streamlit Community Cloud, which the rules require alongside a
               public repo and a live application URL.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))

ARTIFACTS = ROOT / "artifacts"
DECISIONS = ARTIFACTS / "decisions.jsonl"
ROOT_FILE = ARTIFACTS / "merkle_root.json"
POSITIONS = ARTIFACTS / "positions.json"

st.set_page_config(page_title="VRP Agent", page_icon="V", layout="wide")


# --- loading --------------------------------------------------------------

@st.cache_data(ttl=30)
def load_decisions() -> list[dict]:
    if not DECISIONS.exists():
        return []
    out = []
    for line in DECISIONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


@st.cache_data(ttl=30)
def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def verify_log() -> tuple[bool, str]:
    """
    Recompute the Merkle root and compare it to the seal.

    Wrapped defensively because this runs on Streamlit Cloud, where a broken
    import would otherwise take down the whole page. A dashboard that cannot
    verify should say so plainly and keep rendering everything else, rather
    than showing a stack trace where the verification badge belongs.
    """
    try:
        from artifacts import ArtifactLog
        import artifacts as A
        A.ROOT_PATH = ROOT_FILE          # anchor to this deployment's paths
        return ArtifactLog(DECISIONS).verify()
    except Exception as exc:
        return False, f"verifier unavailable in this environment: {exc}"


decisions = load_decisions()
# Dry runs are rehearsals, not decisions the account could have acted on, and
# are excluded from every count here so this page, `make summary` and the deck
# report the same numbers. They stay in the sealed log and the raw stream.
cycles = [d for d in decisions
          if d.get("action") in ("enter", "refuse", "halt") and not d.get("dry_run")]
exits = [d for d in decisions if str(d.get("action", "")).startswith("exit_check")]

st.title("Volatility Risk Premium Agent")
st.caption(
    "Sells defined-risk option premium on SPY only when volatility is measurably "
    "expensive, and refuses when it is not. Every decision below, including every "
    "refusal, is a signed artifact you can verify yourself."
)

if not decisions:
    st.warning("No decisions logged yet. Run `make dry-run` to produce one.")
    st.stop()

latest = cycles[-1] if cycles else decisions[-1]
sig = latest.get("signals", {})
pf = latest.get("portfolio", {})

# --- headline -------------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
equity = pf.get("equity")
c1.metric("Equity", f"${equity:,.0f}" if equity else "n/a",
          f"{pf.get('session_pnl_pct', 0) * 100:+.2f}% today")
short_vrp = sig.get("short_strike_vrp")
c2.metric("VRP (short strikes)",
          f"{short_vrp:+.2f} pts" if short_vrp is not None else "n/a",
          help="Implied vol of the actual strikes the agent would sell minus "
               "trailing 21 day realised vol. This is what gate 7 acts on. "
               "n/a means the traded tenor had no two-sided quote that cycle "
               "(gate 7 refuses rather than falling back to a biased proxy).")
c3.metric("Term structure", f"{sig.get('term_ratio', 0):.3f}",
          "contango" if sig.get("contango") else "BACKWARDATION",
          delta_color="normal" if sig.get("contango") else "inverse")
c4.metric("Open positions", f"{pf.get('open_structures', 0)} / 5")
c5.metric("Drawdown", f"{pf.get('drawdown', 0) * 100:.2f}%",
          help="Circuit breaker halts all trading at -10%.")

# --- the headline number: refusals ---------------------------------------

# Opportunity accounting mirrors `make summary` (agent/artifacts.py): a cycle
# only counts as a decision when the market was open and inside the trading
# window. This headline used to count every logged cycle, so 21 market-closed
# rows inflated the refusal rate a judge would then fail to reproduce from
# the summary command the README invites them to run. Legacy records logged
# an environmental gate as the blocking one; reclassify at read time, never
# by rewriting the sealed log.
ENVIRONMENTAL = ("market_open", "session_window")


def _classify(d: dict) -> tuple[bool, str | None]:
    bg, eb = d.get("blocking_gate"), d.get("environmental_block")
    if eb is None and bg in ENVIRONMENTAL:
        eb, bg = bg, None
    was_opp = d.get("was_an_opportunity")
    if was_opp is None:
        was_opp = eb is None
    return bool(was_opp), bg


opp = [(d, bg) for d in cycles for is_opp, bg in [_classify(d)] if is_opp]
n_env = len(cycles) - len(opp)
n_enter = sum(1 for d, _ in opp if d.get("action") == "enter")
n_refuse = sum(1 for d, _ in opp if d.get("action") == "refuse")
n_halt = sum(1 for d, _ in opp if d.get("action") == "halt")
n_declined = len(opp) - n_enter
blocking: Counter = Counter()
for d, bg in opp:
    if d.get("action") == "refuse":
        blocking[bg or "entry ladder unfilled (all gates passed)"] += 1
    elif d.get("action") == "halt" and bg:
        blocking[bg] += 1

st.subheader("What the agent decided")
st.markdown(
    f"**Of {len(opp)} real decision opportunities (market open, inside the "
    f"trading window), the agent entered {n_enter} and declined {n_declined} "
    f"({n_declined / max(len(opp), 1) * 100:.0f}%).** Another {n_env} logged "
    "cycles fell outside market hours and are recorded for completeness, not "
    "counted as decisions. Most trading agents are built to trade. This one "
    "measures whether the premium is actually there first, and the refusals "
    "carry the numbers that caused them."
)

a, b = st.columns([1, 2])
with a:
    st.dataframe(pd.DataFrame(
        {"outcome": ["entered", "refused", "halted"],
         "count": [n_enter, n_refuse, n_halt]}
    ).set_index("outcome"), width="stretch")
with b:
    if blocking:
        bl = pd.DataFrame(sorted(blocking.items(), key=lambda x: -x[1]),
                          columns=["blocking gate", "times"]).set_index("blocking gate")
        st.bar_chart(bl, horizontal=True)
    else:
        st.info("No refusals recorded yet.")

# --- three agents, one market ---------------------------------------------

cmp = load_json(ARTIFACTS / "compare_summary.json")
if cmp.get("daily"):
    st.subheader("Three agents, one market")
    deployed = cmp.get("deployed", "T6")
    st.markdown(
        "The deployed tenor was not picked from the backtest ranking. Three "
        "candidate configurations have run as dry-run shadow agents against the "
        "same live prices, every hour of the trading window, placing nothing. "
        "This is the scoreboard the deployment decision was made on "
        f"(`research/DEPLOYMENT_DECISIONS.md` D3). Deployed: **{deployed}**."
    )
    cols = st.columns(3)
    for col, label in zip(cols, ("T4", "T6", "T7")):
        tl = cmp.get("tally", {}).get(label, {})
        col.metric(f"{label}: {cmp.get('labels', {}).get(label, '')}",
                   f"{tl.get('would_enter', 0)} would-enter",
                   f"of {tl.get('cycles', 0)} shadow cycles", delta_color="off")
    grid: dict[str, dict[str, str]] = {}
    for row in cmp["daily"]:
        grid.setdefault(row["date"], {})[row["label"]] = (
            f"{row['would_enter']} / {row['cycles']}")
    st.dataframe(pd.DataFrame.from_dict(grid, orient="index")
                 .reindex(columns=["T4", "T6", "T7"]).fillna(""),
                 width="stretch")
    st.caption("Would-enter cycles / shadow cycles per day. Would-enter means "
               "every gate passed and a structure was priced and sized; the "
               "dry-run branch never sends the order, the decision is real. "
               "Per-cycle table: `research/D3_COMPARISON_LOG.md`.")

# --- latest decision ------------------------------------------------------

st.subheader(f"Latest decision: {str(latest.get('action', '')).upper()}")
st.caption(f"{latest.get('timestamp', '')}  ·  artifact seq {latest.get('seq')}")

# --- the explain layer ------------------------------------------------------
# A language model narrates each SEALED decision after the fact, outside the
# trading loop, and every number it writes is checked against the artifact.
# The model explains; the numbers decide. See prep/explain_decisions.py.
EXPL = load_json(ARTIFACTS / "explanations.json")
EXPL_ITEMS = EXPL.get("items", {})


def show_explanation(rec: dict) -> None:
    item = EXPL_ITEMS.get(str(rec.get("leaf_hash")))
    if not item:
        if EXPL_ITEMS:
            st.caption("Plain-English explanation pending: the explain layer runs "
                       "every 10 minutes, after the decision is sealed, never before.")
        return
    counts = EXPL.get("counts", {})
    label = (f"Explained after the fact by {item.get('model', 'a language model')} "
             f"from the sealed artifact. The decision was sealed before this text "
             f"existed and the model never takes part in deciding. Every number "
             f"is checked against the artifact: {counts.get('explained', 0)} "
             f"explanations accepted, {counts.get('rejected', 0)} rejected for "
             f"inventing or altering a number.")
    if item.get("grounded"):
        st.info(item.get("text", ""))
        st.caption(label)
    else:
        st.warning(f"The model's explanation of this decision was REJECTED by the "
                   f"grounding check: it {item.get('rejected_reason', 'failed')}. "
                   f"The decision stands on its numbers; the rejected text is kept "
                   f"in artifacts/explanations.json.")
        st.caption(label)


show_explanation(latest)

gates = latest.get("gates", [])
if gates:
    gdf = pd.DataFrame([{
        "#": g.get("number"),
        "gate": g.get("gate"),
        "verdict": "PASS" if g.get("passed") else "BLOCK",
        "reason": g.get("reason", ""),
    } for g in gates]).sort_values("#")

    def shade(row):
        colour = "#0b3d1e" if row["verdict"] == "PASS" else "#4a1220"
        return [f"background-color: {colour}"] * len(row)

    st.dataframe(gdf.style.apply(shade, axis=1), hide_index=True,
                 width="stretch")

s1, s2 = st.columns(2)
with s1:
    st.markdown("**Signals**")
    st.json({k: sig.get(k) for k in
             ("spot", "atm_iv_near", "atm_iv_far", "term_ratio", "contango",
              "trailing_rv", "atm_vrp", "short_strike_iv", "short_strike_dte",
              "short_strike_vrp", "near_dte", "far_dte")}, expanded=True)
with s2:
    st.markdown("**Structure considered**")
    st.json(latest.get("structure") or {"note": "no structure priced this cycle"},
            expanded=True)

# --- explore any decision -------------------------------------------------

with st.expander("Explore any decision: pick a cycle, see the numbers that decided it"):
    options = {
        f"{str(d.get('timestamp', ''))[:16]}   {str(d.get('action', '')).upper()}"
        f"   {d.get('blocking_gate') or ''}": d
        for d in reversed(cycles)
    }
    pick = st.selectbox("cycle", list(options), label_visibility="collapsed")
    chosen = options[pick]
    show_explanation(chosen)
    cg = chosen.get("gates", [])
    if cg:
        st.dataframe(pd.DataFrame([{
            "#": g.get("number"), "gate": g.get("gate"),
            "verdict": "PASS" if g.get("passed") else "BLOCK",
            "reason": g.get("reason", ""),
        } for g in cg]).sort_values("#"), hide_index=True, width="stretch")
    st.json({"note": chosen.get("note"), "signals": chosen.get("signals"),
             "structure": chosen.get("structure"),
             "leaf_hash": chosen.get("leaf_hash")}, expanded=False)

# --- what the agent asked Alpaca -------------------------------------------

calls = latest.get("mcp_calls") or []
if calls:
    st.subheader("What the agent asked Alpaca this cycle")
    n_fail = sum(1 for c in calls if not c.get("ok"))
    total_ms = sum(float(c.get("duration_ms") or 0) for c in calls)
    m1, m2, m3 = st.columns(3)
    m1.metric("MCP calls", len(calls))
    m2.metric("Round trips, total", f"{total_ms / 1000:.1f} s")
    m3.metric("Failed", n_fail)
    st.dataframe(pd.DataFrame([{
        "#": i + 1, "tool": c.get("tool"), "ok": bool(c.get("ok")),
        "ms": round(float(c.get("duration_ms") or 0)),
        "arguments": json.dumps(c.get("arguments", {}))[:70],
    } for i, c in enumerate(calls)]), hide_index=True, width="stretch")
    st.caption("Every runtime call goes through Alpaca's official MCP server "
               "over JSON-RPC and is recorded inside the sealed artifact, "
               "failures included. The rules require the MCP path; this is "
               "how you check it was used rather than claimed.")

# --- signal history -------------------------------------------------------

hist = [{"t": d.get("timestamp"),
         "short-strike VRP": d.get("signals", {}).get("short_strike_vrp"),
         "ATM IV": d.get("signals", {}).get("atm_iv_near"),
         "trailing RV": d.get("signals", {}).get("trailing_rv"),
         "term ratio": d.get("signals", {}).get("term_ratio")}
        for d in cycles if d.get("signals")]
if len(hist) > 1:
    st.subheader("Signal history")
    hdf = pd.DataFrame(hist).set_index("t")
    st.line_chart(hdf[["ATM IV", "trailing RV"]])
    st.caption("When implied sits above realised, premium is rich and the agent "
               "sells it. When the lines cross, it stops. (Both lines are the "
               "30-day ATM comparison; gate 7 itself acts on the short-strike "
               "VRP shown above, not this chart.)")

# --- open positions -------------------------------------------------------

pos = load_json(POSITIONS).get("open", [])
st.subheader(f"Open positions ({len(pos)})")
if pos:
    st.dataframe(pd.DataFrame([{
        "id": p["id"], "expiry": p["expiry"], "contracts": p["contracts"],
        "credit": p["credit"],
        "max risk": round(p["max_loss_per_contract"] * 100 * p["contracts"], 0),
        "short put": p.get("short_put"), "short call": p.get("short_call"),
    } for p in pos]), hide_index=True, width="stretch")
else:
    st.info("Flat. No open structures.")

if exits:
    st.markdown("**Recent exit checks**")
    st.dataframe(pd.DataFrame([{
        "position": e["exit"].get("position"), "action": e["exit"].get("action"),
        "profit %": round(e["exit"].get("profit_frac", 0) * 100, 1),
        "dte": e["exit"].get("dte"), "reason": e["exit"].get("reason", "")[:70],
    } for e in exits[-10:]]), hide_index=True, width="stretch")

# --- verification ---------------------------------------------------------

st.subheader("Verify this yourself")
sealed = load_json(ROOT_FILE)
ok, msg = verify_log()

v1, v2 = st.columns([1, 2])
with v1:
    if ok:
        st.success("MERKLE ROOT VERIFIED")
    else:
        st.error("VERIFICATION FAILED")
    st.metric("Artifacts", len(decisions))
with v2:
    st.code(sealed.get("merkle_root", "not sealed yet"), language=None)
    st.caption(msg)

st.markdown(
    "Every decision is hashed into a SHA-256 Merkle tree with domain-separated "
    "leaves and nodes. The root is sealed before outcomes are known. Clone the "
    "repo and run `make verify` to recompute it: if any decision had been edited, "
    "added, or removed after the fact, the root would not match. You do not have "
    "to trust the operator."
)

with st.expander("Try to tamper with it"):
    st.markdown("Change one number in one sealed decision, in memory only, "
                "and recompute the root. Nothing on disk is touched.")
    if st.button("Move the latest decision's spot price by one cent and re-verify"):
        try:
            from artifacts import leaf_hash, merkle_root

            def _leaves(rs: list[dict]) -> list[str]:
                out = []
                for r in rs:
                    r = dict(r)
                    r.pop("leaf_hash", None)
                    out.append(leaf_hash(r))
                return out

            idx = max(i for i, r in enumerate(decisions)
                      if r.get("action") in ("enter", "refuse", "halt", "flatten"))
            victim = json.loads(json.dumps(decisions[idx]))
            victim.setdefault("signals", {})
            victim["signals"]["spot"] = round(
                float(victim["signals"].get("spot") or 0) + 0.01, 2)
            honest = merkle_root(_leaves(decisions))
            forged = merkle_root(_leaves(decisions[:idx] + [victim] + decisions[idx + 1:]))
            st.code(f"sealed root      {sealed.get('merkle_root', '?')}\n"
                    f"honest recompute {honest}\n"
                    f"after tampering  {forged}", language=None)
            if forged != sealed.get("merkle_root"):
                st.error(f"Detected. One cent on artifact seq {victim.get('seq')} "
                         f"changed its leaf and the root no longer matches the "
                         f"seal. This is what a judge's `make verify` would "
                         f"print if the operator had edited the log.")
            else:
                st.warning("Roots compared; see above.")
        except Exception as exc:                          # noqa: BLE001
            st.warning(f"Tamper demo unavailable in this environment: {exc}")

with st.expander("Raw artifact stream"):
    st.json(decisions[-5:])

st.divider()
st.caption(
    "Research design pre-registered before any backtest code existed "
    "(`research/PREREGISTRATION_R1.md`). Live sizing deviates from research "
    "sizing deliberately and is recorded in `research/DEPLOYMENT_DECISIONS.md`. "
    "Paper trading only."
)
