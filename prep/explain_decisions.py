"""
The explain layer. A language model narrates each SEALED decision for the
dashboard, after the fact, and never decides anything.

Stance, in one line: the numbers decide, the log proves it, the model only
explains. Concretely:

  1. Runs OUTSIDE the trading loop (a scheduled task, not agent.py). It reads
     the sealed artifact log and writes artifacts/explanations.json. Nothing
     flows back. The decision was sealed before this text existed.
  2. Every number the model writes must appear in the artifact it was given.
     An explanation that invents or rounds a number is REJECTED and the
     rejection is recorded, so the dashboard can say how often the model
     had to be overruled. A hallucinated sentence under a sealed decision
     would be worse than no sentence.
  3. Idempotent and cheap: keyed on the artifact's leaf hash, so each
     decision is explained once, and re-running is a no-op.

    uv run python prep/explain_decisions.py               # explain new decisions (up to --limit)
    uv run python prep/explain_decisions.py --limit 200   # backfill
    uv run python prep/explain_decisions.py --dry-run     # print prompts, call nothing

Needs FEATHERLESS_API_KEY in .env.featherless (gitignored). Featherless
serves an OpenAI-compatible endpoint; Qwen models are ungated there.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "artifacts" / "decisions.jsonl"
OUT = ROOT / "artifacts" / "explanations.json"
ENV = ROOT / ".env.featherless"
API = "https://api.featherless.ai/v1/chat/completions"
LIVE_START = "2026-08-31"
CYCLE_ACTIONS = ("enter", "refuse", "halt", "flatten")
# Tried in order; the first that answers is used. Llama models are gated
# behind a HuggingFace link on Featherless, Qwen is open.
MODELS = ("Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-32B-Instruct",
          "Qwen/Qwen2.5-14B-Instruct", "Qwen/Qwen2.5-7B-Instruct")

SYSTEM = (
    "You explain a trading agent's decision that has ALREADY been made and "
    "sealed. Your reader is a hackathon judge with no options background. "
    "Rules: use only facts present in the JSON; copy every number exactly as "
    "written there, same digits, no rounding, no new numbers; at most three "
    "sentences; plain English; no advice, no praise, no speculation about the "
    "future; no markdown, no bullet points, no em dashes. Say what the agent "
    "did, which check decided it, and the one or two numbers that check was "
    "looking at. If the JSON does not contain something, do not mention it."
)


def load_key() -> str:
    key = os.environ.get("FEATHERLESS_API_KEY", "")
    if not key and ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("FEATHERLESS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("no FEATHERLESS_API_KEY in environment or .env.featherless")
    return key


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


def load_out() -> dict:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"items": {}}


def save_out(doc: dict) -> None:
    # Merge with whatever is on disk first: the scheduled task and a manual
    # backfill can overlap, and each holds its own copy of the items. Keyed
    # on leaf hash, so the union is always correct and nothing is lost.
    on_disk = load_out().get("items", {})
    on_disk.update(doc.get("items", {}))
    doc["items"] = on_disk
    items = doc["items"]
    doc["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc["policy"] = ("Generated after the fact from the sealed artifact by a "
                     "language model that never takes part in the decision. Every "
                     "number is checked against the artifact; explanations that "
                     "invent or alter a number are rejected and counted here.")
    doc["counts"] = {
        "explained": sum(1 for v in items.values() if v.get("grounded")),
        "rejected": sum(1 for v in items.values() if not v.get("grounded")),
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, OUT)          # atomic, so a concurrent publish never sees a half file


def facts_for(rec: dict) -> dict:
    """The only thing the model sees. Compact, rounded once, numbers final."""
    sig = rec.get("signals") or {}
    pf = rec.get("portfolio") or {}
    st = rec.get("structure") or {}
    facts = {
        "timestamp_et": rec.get("timestamp"),
        "action": rec.get("action"),
        "blocking_gate": rec.get("blocking_gate"),
        "note": rec.get("note"),
        "gates": [{"n": g.get("number"), "gate": g.get("gate"),
                   "verdict": "PASS" if g.get("passed") else "BLOCK",
                   "reason": g.get("reason")} for g in rec.get("gates", [])],
        "signals": {k: (round(v, 2) if isinstance(v, float) else v)
                    for k, v in sig.items()
                    if k in ("spot", "short_strike_iv", "trailing_rv", "short_strike_vrp",
                             "term_ratio", "contango", "short_strike_dte")},
        "portfolio": {k: (round(v, 2) if isinstance(v, float) else v)
                      for k, v in pf.items()
                      if k in ("equity", "open_structures", "drawdown")},
    }
    if st:
        facts["structure"] = {k: st.get(k) for k in
                              ("expiry", "short_put", "short_call", "credit", "contracts")
                              if st.get(k) is not None}
    if rec.get("size_contracts"):
        facts["size_contracts"] = rec.get("size_contracts")
    return facts


NUM = re.compile(r"(?<![A-Za-z])[-+]?\$?\d[\d,]*\.?\d*%?")


def grounded(text: str, facts: dict) -> tuple[bool, str]:
    """Every number in the text must appear, digit for digit, in the facts."""
    if chr(0x2014) in text:          # the em dash, kept out of this file too
        return False, "contained an em dash"
    blob = json.dumps(facts, ensure_ascii=False)
    blob_nums = set(re.findall(r"\d[\d,]*\.?\d*", blob))
    # Also accept integer forms of the facts' numbers (13.0 -> 13) and the
    # gate numbers, which the model is allowed to cite.
    loose = set()
    for n in blob_nums:
        loose.add(n.replace(",", ""))
        if "." in n:
            loose.add(n.replace(",", "").rstrip("0").rstrip("."))
    for tok in NUM.findall(text):
        raw = tok.strip("$%+-").replace(",", "")
        if not raw:
            continue
        cand = {raw, raw.rstrip("0").rstrip(".") if "." in raw else raw}
        if not (cand & loose):
            return False, f"used the number {tok} which is not in the artifact"
    return True, ""


def ask(key: str, model: str, facts: dict, timeout: int = 90) -> tuple[str, dict]:
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 220,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Explain this decision.\n\n" +
             json.dumps(facts, ensure_ascii=False, indent=0)},
        ],
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json",
                 # Featherless answers 403 to a bare Python user agent.
                 "User-Agent": "Mozilla/5.0 alpaca-hackathon-explainer/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    text = data["choices"][0]["message"]["content"].strip()
    return text, data.get("usage", {})


def pick_model(key: str) -> str:
    probe = {"action": "refuse", "blocking_gate": "vrp_threshold",
             "gates": [{"n": 7, "gate": "vrp_threshold", "verdict": "BLOCK",
                        "reason": "VRP 0.4 below threshold 1.0"}]}
    for m in MODELS:
        try:
            ask(key, m, probe, timeout=60)
            return m
        except urllib.error.HTTPError as e:
            print(f"  {m}: HTTP {e.code}, trying next")
        except Exception as exc:                          # noqa: BLE001
            print(f"  {m}: {type(exc).__name__}, trying next")
    sys.exit("no model answered")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40, help="max new decisions per run")
    ap.add_argument("--model", default=None)
    ap.add_argument("--dry-run", action="store_true", help="print prompts, call nothing")
    ap.add_argument("--since", default=LIVE_START)
    args = ap.parse_args()

    doc = load_out()
    items = doc.setdefault("items", {})
    todo = [r for r in load_decisions()
            if r.get("action") in CYCLE_ACTIONS
            and not r.get("dry_run")
            and str(r.get("timestamp", "")) >= args.since
            and r.get("leaf_hash")
            and r["leaf_hash"] not in items]
    todo = todo[-args.limit:]         # newest first matters more than oldest
    print(f"{len(todo)} decision(s) to explain, {len(items)} already done")
    if not todo:
        save_out(doc)
        return 0
    if args.dry_run:
        for r in todo[:3]:
            print(json.dumps(facts_for(r), indent=1)[:800])
        return 0

    key = load_key()
    model = args.model or pick_model(key)
    doc["model"] = model
    print(f"model: {model}")

    n_ok = n_rej = n_err = 0
    for i, rec in enumerate(todo, 1):
        facts = facts_for(rec)
        try:
            text, usage = ask(key, model, facts)
        except Exception as exc:                          # noqa: BLE001
            n_err += 1
            print(f"  [{i}/{len(todo)}] seq {rec.get('seq')}: call failed "
                  f"{type(exc).__name__}: {str(exc)[:80]}")
            time.sleep(2)
            continue
        ok, why = grounded(text, facts)
        items[rec["leaf_hash"]] = {
            "seq": rec.get("seq"), "timestamp": rec.get("timestamp"),
            "action": rec.get("action"), "text": text, "grounded": ok,
            "rejected_reason": why, "model": model,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
        n_ok += ok
        n_rej += (not ok)
        flag = "ok " if ok else "REJ"
        print(f"  [{i}/{len(todo)}] {flag} seq {rec.get('seq')} {rec.get('action')}: "
              f"{text[:90]!r}{'' if ok else '  <- ' + why}")
        if i % 10 == 0:
            save_out(doc)
    save_out(doc)
    print(f"done: {n_ok} explained, {n_rej} rejected by grounding, {n_err} call errors; "
          f"{doc['counts']} total")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
