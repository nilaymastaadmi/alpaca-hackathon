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
cycles = [d for d in decisions if d.get("action") in ("enter", "refuse", "halt")]
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
c2.metric("VRP", f"{sig.get('vrp', 0):+.2f} pts",
          help="ATM implied vol minus trailing 21 day realised vol. Positive "
               "means implied is richer than what actually happened, which is "
               "the premium this agent sells.")
c3.metric("Term structure", f"{sig.get('term_ratio', 0):.3f}",
          "contango" if sig.get("contango") else "BACKWARDATION",
          delta_color="normal" if sig.get("contango") else "inverse")
c4.metric("Open positions", f"{pf.get('open_structures', 0)} / 5")
c5.metric("Drawdown", f"{pf.get('drawdown', 0) * 100:.2f}%",
          help="Circuit breaker halts all trading at -10%.")

# --- the headline number: refusals ---------------------------------------

blocking = Counter(d.get("blocking_gate") for d in cycles if d.get("blocking_gate"))
n_enter = sum(1 for d in cycles if d.get("action") == "enter")
n_refuse = sum(1 for d in cycles if d.get("action") == "refuse")
n_halt = sum(1 for d in cycles if d.get("action") == "halt")
total = max(len(cycles), 1)

st.subheader("What the agent decided")
st.markdown(
    f"**The agent evaluated {len(cycles)} opportunities and declined "
    f"{n_refuse + n_halt} of them ({(n_refuse + n_halt) / total * 100:.0f}%).** "
    "Most trading agents are built to trade. This one measures whether the "
    "premium is actually there first, and the refusals carry the numbers that "
    "caused them."
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

# --- latest decision ------------------------------------------------------

st.subheader(f"Latest decision: {str(latest.get('action', '')).upper()}")
st.caption(f"{latest.get('timestamp', '')}  ·  artifact seq {latest.get('seq')}")

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
              "trailing_rv", "vrp", "near_dte", "far_dte")}, expanded=True)
with s2:
    st.markdown("**Structure considered**")
    st.json(latest.get("structure") or {"note": "no structure priced this cycle"},
            expanded=True)

# --- signal history -------------------------------------------------------

hist = [{"t": d.get("timestamp"), "VRP": d.get("signals", {}).get("vrp"),
         "ATM IV": d.get("signals", {}).get("atm_iv_near"),
         "trailing RV": d.get("signals", {}).get("trailing_rv"),
         "term ratio": d.get("signals", {}).get("term_ratio")}
        for d in cycles if d.get("signals")]
if len(hist) > 1:
    st.subheader("Signal history")
    hdf = pd.DataFrame(hist).set_index("t")
    st.line_chart(hdf[["ATM IV", "trailing RV"]])
    st.caption("When implied sits above realised, premium is rich and the agent "
               "sells it. When the lines cross, it stops.")

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

with st.expander("Raw artifact stream"):
    st.json(decisions[-5:])

st.divider()
st.caption(
    "Research design pre-registered before any backtest code existed "
    "(`research/PREREGISTRATION_R1.md`). Live sizing deviates from research "
    "sizing deliberately and is recorded in `research/DEPLOYMENT_DECISIONS.md`. "
    "Paper trading only."
)
