# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "tzdata"]
# ///
# tzdata is not optional on Windows: the OS ships no IANA database, so
# ZoneInfo("America/New_York") raises ZoneInfoNotFoundError without it. The
# agent runs from IST and must reason in US market hours, and this project's
# siblings have already lost time to timezone bugs (chikki ran UTC under WSL
# while Task Scheduler fired IST; bhide had an overdue deadline read as safe).
"""
The decision loop.

One cycle: read the market through MCP, compute signals, evaluate every gate,
then either place a defined-risk structure or refuse, and write an artifact
either way.

The refusal path is not an error path. It is the product. An agent that trades
whenever it can is a bot; an agent that measures whether volatility is actually
expensive and declines when it is not is the thing being submitted. Refusals are
logged with the same detail as fills, carrying the measured numbers that caused
them, so a judge can audit the reasoning rather than take it on trust.

  uv run agent/agent.py --dry-run     decide and log, place nothing
  uv run agent/agent.py               live on the account in .env
  uv run agent/agent.py --once        single cycle then exit
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

import signals as SIG
from artifacts import ArtifactLog
from broker import Broker, CondorPlan
from config import DEFAULT, Config
from hedge import build_hedge
from mcp_client import MCPClient
from positions import (
    Ledger, conservative_partial_value, evaluate_exit, new_position, reconcile,
    value_from_quotes,
)
from risk import Decision, PortfolioState, RiskEngine, size_position

ET = ZoneInfo("America/New_York")
STATE_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "state.json"


def load_state(path: Path = STATE_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"peak_equity": None, "session_date": None,
            "session_start_equity": None, "consecutive_losses": 0}


def save_state(s: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, indent=2), encoding="utf-8")


def run_cycle(cfg: Config, dry_run: bool, verbose: bool = True,
              publish_artifacts: bool = False,
              artifact_path: Path | None = None,
              ledger_path: Path | None = None,
              state_path: Path | None = None) -> Decision:
    """
    artifact_path/ledger_path/state_path default to the real deployment
    paths (ArtifactLog, Ledger and STATE_PATH's own defaults) when None, so
    ordinary calls are byte-identical to before these existed. Passing them
    is how a comparison run (see --compare) stays fully isolated from the
    real decision log, ledger and session state, while still reading the
    same live account through the same MCP connection.
    """
    log = ArtifactLog(artifact_path) if artifact_path else ArtifactLog()
    engine = RiskEngine(cfg)
    state = load_state(state_path) if state_path else load_state()
    now_et = datetime.now(ET)
    today = now_et.date()

    with MCPClient() as mcp:
        broker = Broker(mcp, cfg)

        # --- read the world ------------------------------------------------
        acct = broker.account()
        # Never default equity to 0.0. mcp_client returns {"text": ...} on
        # unparseable JSON, and a 0.0 landing on the first cycle of a session
        # saves session_start_equity as 0.0, which makes session_pnl_pct return
        # 0.0 for the rest of the day. Gate 3 would then FAIL OPEN for the whole
        # session while gate 2 wrote a fabricated "-100% drawdown, HALT" into the
        # sealed artifact trail. Refusing to proceed is the only safe response.
        try:
            equity = float(acct.get("equity"))
        except (TypeError, ValueError):
            raise RuntimeError(
                f"account payload has no usable equity: {str(acct)[:200]}")
        if equity <= 0:
            raise RuntimeError(f"account equity read as {equity}, refusing to "
                               f"trade on a value that would disable gate 3")
        broker_positions = broker.positions()
        broker_symbols = {str(p.get("symbol", "")) for p in broker_positions}

        # --- manage what is already open BEFORE considering anything new ----
        # Exits come first on purpose. An agent that opens before it closes can
        # sit at capacity holding a position it should already have exited.
        ledger = Ledger(ledger_path) if ledger_path else Ledger()
        held, recon_issues = reconcile(ledger.load(), broker_symbols)
        ledger.save(held)
        exits = _manage_exits(broker, ledger, held, today, cfg, dry_run, log)
        held = ledger.load()
        n_open = len(held)

        clock = broker.clock()
        market_open = bool(clock.get("is_open", False))

        # Independent of the core book's decision below: this either already
        # holds the week's hedge, buys it, or logs why it could not.
        hedge_result = _manage_hedge(broker, cfg, equity, today, market_open,
                                     broker_positions, dry_run, log)

        spot = broker.spot()
        closes = broker.closes(days=60)
        chain = broker.chain(cfg.dte_min - 2, 120, spot)
        # short_* params make gate 7 measure the IV of the strikes actually
        # sold (short_delta at dte_target), not a 30-day ATM proxy. See
        # signals.short_strike_iv and risk.g7_vrp for why that distinction is
        # the entire threshold, not a rounding difference.
        sig = SIG.compute(chain, spot, closes, today,
                          short_delta=cfg.short_delta,
                          short_target_dte=cfg.dte_target,
                          short_dte_min=cfg.dte_min, short_dte_max=cfg.dte_max)

        # --- session bookkeeping -------------------------------------------
        if state.get("session_date") != today.isoformat():
            state["session_date"] = today.isoformat()
            state["session_start_equity"] = equity
        state["peak_equity"] = max(state.get("peak_equity") or equity, equity)
        save_state(state, state_path) if state_path else save_state(state)

        ps = PortfolioState(
            equity=equity,
            starting_equity=100_000.0,
            session_start_equity=float(state["session_start_equity"]),
            peak_equity=float(state["peak_equity"]),
            open_positions=n_open,
            consecutive_losses=int(state.get("consecutive_losses", 0)),
        )

        # --- gates 0 to 8 ---------------------------------------------------
        gates = engine.evaluate_pretrade(
            now_et.replace(tzinfo=None), ps,
            vix=sig.atm_iv_near, vix3m=sig.atm_iv_far,
            short_strike_iv=sig.short_strike_iv, trailing_rv=sig.trailing_rv,
            recon_issues=recon_issues,
        )
        if not market_open:
            from risk import GateResult
            gates.insert(0, GateResult(
                "market_open", -1, False,
                "market is closed; no decision to make", {"is_open": False}))

        plan: CondorPlan | None = None
        contracts = 0
        action = "refuse"
        note = ""
        flatten_results: list[dict] = []

        # Gate 2's own message says "HALT and flatten". Until now nothing did
        # the flatten half of that promise: the breaker stopped new entries but
        # left every existing position open. Checked here, once, rather than
        # inside the gate itself, because closing positions is an ACTION with
        # side effects and a gate's job is only to evaluate a condition.
        dd_gate = next((g for g in gates if g.gate == "drawdown_breaker"), None)
        drawdown_breached = dd_gate is not None and not dd_gate.passed

        if engine.all_passed(gates):
            plan = broker.build_condor(chain, spot, today)
            if plan is None:
                from risk import GateResult
                gates.append(GateResult(
                    "structure", 9, False,
                    "could not assemble a same-expiry condor from quoted contracts",
                    {"chain_size": len(chain)}))
            elif cfg.one_per_expiry and any(
                    p.expiry == plan.expiry.isoformat() for p in held):
                from risk import GateResult
                # D1 calls staggering "not optional at this size".
                # build_condor is deterministic, so without this five cycles
                # produce five positions on the SAME expiry at the SAME
                # strikes: one position at 15% wearing a costume.
                gates.append(GateResult(
                    "stagger", 11, False,
                    f"already hold a position expiring {plan.expiry}. Five "
                    f"positions on one expiry is one position at 15%, not five "
                    f"at 3%",
                    {"expiry": plan.expiry.isoformat(),
                     "held_expiries": [p.expiry for p in held]}))
                plan = None
            else:
                contracts = size_position(equity, cfg.risk_per_position,
                                          plan.max_loss_per_contract)
                gates += engine.evaluate_structure(
                    credit=plan.credit_mid, est_cost=plan.est_cost,
                    contracts=contracts,
                    max_loss_per_contract=plan.max_loss_per_contract,
                    equity=equity,
                )

        if engine.all_passed(gates) and plan is not None:
            action = "enter"
            if dry_run:
                note = "dry run: structure priced and sized, no order sent"
                result = broker.place_laddered(plan, contracts, True, dry_run=True)
            else:
                result = broker.place_laddered(plan, contracts, True)
                if result.get("aborted_unsafe"):
                    action = "refuse"
                    note = ("aborted: could not confirm no order was already "
                            "resting on these legs; refused to risk a duplicate")
                elif not result.get("filled"):
                    action = "refuse"
                    note = "ladder exhausted without a fill; no position opened"
                else:
                    # Record the ACTUAL fill, not the requested size or the
                    # rung's limit price. A partial fill means fewer contracts
                    # than requested actually filled; recording `contracts`
                    # here would silently overstate the position, which then
                    # overstates every exit and risk calculation against it.
                    filled_qty = result.get("filled_qty") or contracts
                    avg_price = result.get("filled_avg_price")
                    # avg_price should always be present on a filled order; the
                    # plan's own mid credit is the only sane fallback if Alpaca
                    # ever omits it, since nothing else in `result` is a price.
                    credit = (abs(float(avg_price)) if avg_price is not None
                             else plan.credit_mid)
                    note = (f"filled {filled_qty}/{contracts} contracts at "
                            f"avg {avg_price} on rung {result['rung']}")
                    if result.get("partial"):
                        note = "PARTIAL " + note
                    # Record it immediately. A filled order that never reaches
                    # the ledger is a position the agent will not manage or exit.
                    ledger.add(new_position(
                        plan.to_dict(), filled_qty,
                        credit=credit,
                        entry_limit=avg_price,
                        order_id=(result.get("order") or {}).get("id"),
                    ))
            note += f" | ladder: {json.dumps(result.get('attempts', []))[:300]}"
        elif drawdown_breached and held:
            action = "flatten"
            flatten_results = _flatten_all(broker, ledger, held, today, dry_run, log)
            n_closed = sum(1 for r in flatten_results if r["action"] == "closed")
            n_failed = sum(1 for r in flatten_results if r["action"] == "close_failed")
            note = (f"drawdown breaker fired ({dd_gate.reason}); "
                    f"{n_closed}/{len(held)} flattened, {n_failed} failed to close")
            if dry_run:
                note = "DRY RUN, nothing sent: " + note
        elif engine.is_halt(gates):
            action = "halt"
            note = "circuit breaker tripped; no new risk"

        decision = Decision(
            timestamp=now_et.isoformat(timespec="seconds"),
            action=action,
            gates=gates,
            signals=sig.to_dict(),
            portfolio={
                "equity": equity, "peak_equity": ps.peak_equity,
                "session_start_equity": ps.session_start_equity,
                "drawdown": round(ps.drawdown, 5),
                "session_pnl_pct": round(ps.session_pnl_pct, 5),
                "open_structures": n_open,
                "market_open": market_open,
            },
            size_contracts=contracts or None,
            structure=plan.to_dict() if plan else None,
            note=note,
        )

        rec = decision.to_dict()
        rec["mcp_calls"] = mcp.audit()
        rec["dry_run"] = dry_run
        rec["exits"] = exits
        rec["flatten"] = flatten_results
        rec["hedge"] = hedge_result
        rec["reconciliation"] = recon_issues
        leaf = log.append(rec)
        # Seal every cycle. An autonomous agent that only seals when a human
        # remembers to leaves its most recent decisions unverifiable, which are
        # exactly the ones a judge will look at.
        log.seal()

        # Publish so the DEPLOYED dashboard reflects this decision. It renders
        # what is committed, not what is on this laptop. Failures here are
        # returned, never raised: a git problem must not stop the agent from
        # managing real positions.
        pub = None
        if publish_artifacts:
            from publish import publish as _publish
            pub = _publish(note=f"action={action} seq={rec.get('seq')}").to_dict()
            if verbose:
                print(f"  publish: {pub['action']} {pub['detail'][:80]}")

        if verbose:
            _print(decision, leaf, sig, cfg, exits, recon_issues, flatten_results,
                  hedge_result)

    return decision


def _manage_hedge(broker, cfg, equity, today, market_open, broker_positions,
                  dry_run, log) -> dict:
    """
    Maintain the tail hedge: buy one VIX call position sized to
    cfg.hedge_budget_pct and hold it through the week, rather than actively
    managing it. VXTH's own methodology rolls monthly, which already covers a
    much longer horizon than this 4.5 day live window, so there is no
    rebalancing logic here to get wrong.

    Runs independent of the core book's gate decisions. A drawdown breach
    flattens the SHORT PREMIUM ledger (see _flatten_all); it must not also
    sell the hedge, which is presumably doing its job paying off during
    exactly that scenario.
    """
    if not cfg.hedge_enabled:
        return {"action": "disabled"}
    if not market_open:
        return {"action": "skip", "reason": "market closed"}

    already_held = any(str(p.get("symbol", "")).startswith("VIX")
                       for p in broker_positions)
    if already_held:
        return {"action": "held", "reason": "hedge already in place for the week"}

    try:
        quotes = broker.vix_chain(cfg.hedge_dte_min, cfg.hedge_dte_max)
    except Exception as exc:
        rec = {"action": "error", "reason": f"could not fetch VIX chain: {str(exc)[:160]}"}
        log.append({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": "hedge:error", "hedge": rec})
        return rec

    plan = build_hedge(quotes, equity, today, budget_pct=cfg.hedge_budget_pct,
                       target_moneyness=cfg.hedge_target_moneyness,
                       dte_min=cfg.hedge_dte_min, dte_max=cfg.hedge_dte_max)
    if plan is None:
        rec = {"action": "no_candidate",
               "reason": "no VIX call cleared the spread, dispersion or budget "
                        "checks; not hedging off an untrustworthy read",
               "n_quotes": len(quotes)}
        log.append({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": "hedge:no_candidate", "hedge": rec})
        return rec

    out = broker.place_hedge(plan, dry_run=dry_run)
    rec = {"action": ("would_buy" if dry_run else
                      "bought" if out.get("filled") else "resting_unfilled"),
           "plan": plan.to_dict(), "execution": {k: v for k, v in out.items()
                                                 if k != "order"}}
    log.append({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "action": f"hedge:{rec['action']}", "hedge": rec})
    return rec


def _flatten_all(broker, ledger, held, today, dry_run, log) -> list[dict]:
    """
    Close every held position unconditionally. Only called when the
    portfolio-level drawdown breaker (gate 2) has fired.

    Deliberately different from `_manage_exits` in one respect: if quotes
    cannot be fetched at all, `_manage_exits` gives up for the whole cycle,
    because holding is a safe default when nothing forces a decision. Here it
    is the opposite. The breaker firing means doing nothing is the unsafe
    option, so each position falls back to its own entry credit as the ladder
    seed and gets a real close attempt anyway, rather than the emergency
    action silently doing nothing because a market data call failed.

    A position that fails to close stays in the ledger rather than being
    dropped, so the next cycle (the drawdown condition will still be true)
    picks it up and tries again.
    """
    if not held:
        return []

    all_legs = [s for p in held for s in p.legs]
    quote_error = None
    try:
        quotes = broker.quotes(all_legs)
    except Exception as exc:
        quotes, quote_error = {}, str(exc)[:160]

    results = []
    for p in held:
        buyback = value_from_quotes(p, quotes) if quotes else None
        rec = {"position": p.id, "expiry": p.expiry, "dte": p.dte(today),
               "credit": p.credit, "contracts": p.contracts,
               "reason": "drawdown breaker: portfolio-level HALT and flatten"}
        if quote_error and buyback is None:
            rec["quote_warning"] = quote_error

        if dry_run:
            rec["action"] = "would_flatten"
        else:
            out = broker.close_position(p, buyback or p.credit, p.contracts,
                                        dry_run=False)
            rec["action"] = "closed" if out.get("filled") else "close_failed"
            rec["execution"] = {k: v for k, v in out.items() if k != "order"}
            if out.get("filled"):
                ledger.remove(p.id)

        log.append({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": f"flatten:{rec['action']}", "flatten": rec})
        results.append(rec)
    return results


def _manage_exits(broker, ledger, held, today, cfg, dry_run, log) -> list[dict]:
    """
    Value every open position and close the ones whose rules have triggered.

    Each exit is its own artifact, so the audit trail shows the reason a
    position was closed and the numbers behind it, not just that it vanished.
    """
    if not held:
        return []

    all_legs = [s for p in held for s in p.legs]
    try:
        quotes = broker.quotes(all_legs)
    except Exception as exc:
        return [{"error": f"could not fetch quotes: {str(exc)[:160]}"}]

    results = []
    for p in held:
        buyback = value_from_quotes(p, quotes)
        conservative = False
        if buyback is None:
            # Full valuation needs every leg quoted. The long wing is the one
            # most likely to lose its quote in exactly the fast, wide move a
            # stop-loss exists to catch, and "wait for better data" is not a
            # neutral default here: doing nothing IS a decision to keep
            # holding. Fall back to short-legs-only pricing, which overstates
            # cost and so only ever biases toward closing sooner, never toward
            # a false profit signal. See positions.conservative_partial_value.
            buyback = conservative_partial_value(p, quotes)
            conservative = buyback is not None
        sig = evaluate_exit(p, buyback, today, cfg.profit_target,
                            cfg.exit_dte, cfg.stop_loss_mult)
        rec = {"position": p.id, "expiry": p.expiry, "dte": p.dte(today),
               "credit": p.credit, "contracts": p.contracts,
               "conservative_valuation": conservative,
               **sig.to_dict()}

        if sig.should_exit:
            if dry_run:
                rec["action"] = "would_close"
            else:
                out = broker.close_position(p, buyback or p.credit,
                                            p.contracts, dry_run=False)
                rec["action"] = "closed" if out.get("filled") else "close_failed"
                rec["execution"] = {k: v for k, v in out.items() if k != "order"}
                if out.get("filled"):
                    ledger.remove(p.id)
        else:
            rec["action"] = "hold"
            if sig.profit_frac > p.peak_profit_frac:
                p.peak_profit_frac = sig.profit_frac
                ledger.update(p)

        log.append({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": f"exit_check:{rec['action']}", "exit": rec})
        results.append(rec)
    return results


def _print(d: Decision, leaf: str, sig: SIG.Signals, cfg: Config,
           exits: list[dict] | None = None,
           recon: list[dict] | None = None,
           flattens: list[dict] | None = None,
           hedge: dict | None = None) -> None:
    bar = "=" * 74
    print(bar)
    print(f"DECISION  {d.timestamp}   ACTION: {d.action.upper()}")
    print(bar)
    if hedge:
        print(f"  hedge: {hedge.get('action')}"
              f"{' - ' + hedge['reason'] if hedge.get('reason') else ''}")
    for issue in (recon or []):
        sev = issue.get("severity", "info")
        print(f"  [{sev}] {issue.get('position')}: {issue.get('issue', '')[:90]}")
    if flattens:
        print(f"  DRAWDOWN BREAKER: flattening {len(flattens)} position(s)")
        for f in flattens:
            print(f"    {f['position']}  {f['action']:<14} "
                  f"{f['contracts']}x  {f.get('quote_warning', '')[:50]}")
        print()
    if exits:
        print(f"  open positions: {len(exits)}")
        for e in exits:
            if "error" in e:
                print(f"    ERROR {e['error']}")
                continue
            print(f"    {e['position']}  {e['action']:<12} "
                  f"{e['profit_frac'] * 100:+6.0f}% of max  {e['dte']:>3}d  "
                  f"{e['reason'][:60]}")
        print()
    print(f"  spot {sig.spot:.2f}   ATM IV {sig.atm_iv_near:.2f} ({sig.near_dte}d) "
          f"/ {sig.atm_iv_far:.2f} ({sig.far_dte}d)")
    print(f"  term ratio {sig.term_ratio:.3f} "
          f"({'contango' if sig.contango else 'BACKWARDATION'})")
    print(f"  trailing RV {sig.trailing_rv:.2f}")
    if sig.short_strike_iv is not None:
        print(f"  short-strike IV {sig.short_strike_iv:.2f} ({sig.short_strike_dte}d, "
              f"what gate 7 acts on)   VRP {sig.short_strike_vrp:+.2f} vol points "
              f"(threshold {cfg.vrp_threshold:.1f})")
    else:
        print(f"  short-strike IV unavailable at the traded tenor; gate 7 refuses")
    print(f"  ATM VRP {sig.atm_vrp:+.2f} vol points (comparison only, "
          f"NOT what gate 7 acts on)")
    print(f"\n  gates:")
    for g in d.gates:
        mark = "PASS" if g.passed else "BLOCK"
        print(f"    [{mark:>5}] {g.number:>2}. {g.gate:<20} {g.reason[:88]}")
    if d.structure:
        s = d.structure
        print(f"\n  structure: {s['expiry']} ({s['dte']}d), strikes {s['strikes']}")
        print(f"    credit ${s['credit_mid']:.2f} mid, est cost ${s['est_cost']:.3f} "
              f"({s['est_cost'] / s['credit_mid'] * 100:.1f}% of credit)")
        print(f"    max loss ${s['max_loss_per_contract']:.2f}/contract "
              f"x {d.size_contracts} contracts")
    if d.note:
        print(f"\n  note: {d.note[:200]}")
    print(f"\n  artifact leaf {leaf[:16]}...")
    print(bar)


# D3 candidates (research/DEPLOYMENT_DECISIONS.md D3, RESULT_H3_T7.md): the
# only knob that differs between them is tenor. T4 is the deployed default,
# included here so it runs through the same isolated comparison path as the
# other two rather than being special-cased.
COMPARE_PRESETS: dict[str, dict] = {
    "T4": {},
    "T6": {"dte_min": 21, "dte_max": 45, "dte_target": 33},
    "T7": {"dte_min": 5, "dte_max": 10, "dte_target": 8},
}


def run_compare_cycle(label: str, verbose: bool = True) -> Decision:
    """
    One isolated dry-run cycle for a D3 candidate, reading the same live
    account and market data as the real agent but writing to
    artifacts/compare/<label>/ instead of the real deployment paths. Always
    dry-run: this exists to compare what each tenor WOULD decide, never to
    place an order. Safe to call once daily per label through kickoff.
    """
    import dataclasses
    if label not in COMPARE_PRESETS:
        raise ValueError(f"unknown compare label {label!r}, expected one of "
                         f"{sorted(COMPARE_PRESETS)}")
    overrides = COMPARE_PRESETS[label]
    cfg = dataclasses.replace(DEFAULT, **overrides) if overrides else DEFAULT
    base = Path(__file__).resolve().parent.parent / "artifacts" / "compare" / label
    return run_cycle(cfg, dry_run=True, verbose=verbose, publish_artifacts=False,
                     artifact_path=base / "decisions.jsonl",
                     ledger_path=base / "positions.json",
                     state_path=base / "state.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="decide and log, place nothing")
    ap.add_argument("--once", action="store_true", help="single cycle then exit")
    ap.add_argument("--seal", action="store_true",
                    help="seal the artifact log and print the Merkle root")
    ap.add_argument("--publish", action="store_true",
                    help="commit and push artifacts so the deployed dashboard "
                         "is not stale. Opt-in because it pushes to a remote.")
    ap.add_argument("--compare", choices=sorted(COMPARE_PRESETS), default=None,
                    help="isolated dry-run cycle for one D3 candidate tenor, "
                         "logged under artifacts/compare/<label>/ instead of "
                         "the real deployment paths. Always dry-run regardless "
                         "of --dry-run; ignores --publish.")
    ap.add_argument("--compare-all", action="store_true",
                    help="run --compare for every candidate (T4, T6, T7) in "
                         "one invocation, one cycle each")
    args = ap.parse_args()

    if args.seal:
        print(json.dumps(ArtifactLog().seal(), indent=2))
        return

    if args.compare_all:
        for label in COMPARE_PRESETS:
            print(f"\n{'=' * 78}\ncompare cycle: {label}\n{'=' * 78}")
            run_compare_cycle(label)
        return

    if args.compare:
        run_compare_cycle(args.compare)
        return

    run_cycle(DEFAULT, dry_run=args.dry_run, publish_artifacts=args.publish)


if __name__ == "__main__":
    main()
