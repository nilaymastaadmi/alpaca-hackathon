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
from mcp_client import MCPClient
from positions import (
    Ledger, evaluate_exit, new_position, reconcile, value_from_quotes,
)
from risk import Decision, PortfolioState, RiskEngine, size_position

ET = ZoneInfo("America/New_York")
STATE_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "state.json"


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"peak_equity": None, "session_date": None,
            "session_start_equity": None, "consecutive_losses": 0}


def save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, indent=2), encoding="utf-8")


def run_cycle(cfg: Config, dry_run: bool, verbose: bool = True) -> Decision:
    log = ArtifactLog()
    engine = RiskEngine(cfg)
    state = load_state()
    now_et = datetime.now(ET)
    today = now_et.date()

    with MCPClient() as mcp:
        broker = Broker(mcp, cfg)

        # --- read the world ------------------------------------------------
        acct = broker.account()
        equity = float(acct.get("equity", 0.0))
        broker_positions = broker.positions()
        broker_symbols = {str(p.get("symbol", "")) for p in broker_positions}

        # --- manage what is already open BEFORE considering anything new ----
        # Exits come first on purpose. An agent that opens before it closes can
        # sit at capacity holding a position it should already have exited.
        ledger = Ledger()
        held, recon_issues = reconcile(ledger.load(), broker_symbols)
        ledger.save(held)
        exits = _manage_exits(broker, ledger, held, today, cfg, dry_run, log)
        held = ledger.load()
        n_open = len(held)

        clock = broker.clock()
        market_open = bool(clock.get("is_open", False))

        spot = broker.spot()
        closes = broker.closes(days=60)
        chain = broker.chain(cfg.dte_min - 2, 120, spot)
        sig = SIG.compute(chain, spot, closes, today)

        # --- session bookkeeping -------------------------------------------
        if state.get("session_date") != today.isoformat():
            state["session_date"] = today.isoformat()
            state["session_start_equity"] = equity
        state["peak_equity"] = max(state.get("peak_equity") or equity, equity)
        save_state(state)

        ps = PortfolioState(
            equity=equity,
            starting_equity=100_000.0,
            session_start_equity=float(state["session_start_equity"]),
            peak_equity=float(state["peak_equity"]),
            open_positions=n_open,
            consecutive_losses=int(state.get("consecutive_losses", 0)),
        )

        # --- gates 1 to 8 ---------------------------------------------------
        gates = engine.evaluate_pretrade(
            now_et.replace(tzinfo=None), ps,
            vix=sig.atm_iv_near, vix3m=sig.atm_iv_far,
            atm_iv=sig.atm_iv_near, trailing_rv=sig.trailing_rv,
        )
        if not market_open:
            from risk import GateResult
            gates.insert(0, GateResult(
                "market_open", 0, False,
                "market is closed; no decision to make", {"is_open": False}))

        plan: CondorPlan | None = None
        contracts = 0
        action = "refuse"
        note = ""

        if engine.all_passed(gates):
            plan = broker.build_condor(chain, spot, today)
            if plan is None:
                from risk import GateResult
                gates.append(GateResult(
                    "structure", 9, False,
                    "could not assemble a same-expiry condor from quoted contracts",
                    {"chain_size": len(chain)}))
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
                if not result.get("filled"):
                    action = "refuse"
                    note = "ladder exhausted without a fill; no position opened"
                else:
                    note = (f"filled at {result['limit_price']} on rung "
                            f"{result['rung']}")
                    # Record it immediately. A filled order that never reaches
                    # the ledger is a position the agent will not manage or exit.
                    ledger.add(new_position(
                        plan.to_dict(), contracts,
                        credit=abs(float(result["limit_price"])),
                        entry_limit=result["limit_price"],
                        order_id=(result.get("order") or {}).get("id"),
                    ))
            note += f" | ladder: {json.dumps(result.get('attempts', []))[:300]}"
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
        rec["reconciliation"] = recon_issues
        leaf = log.append(rec)
        # Seal every cycle. An autonomous agent that only seals when a human
        # remembers to leaves its most recent decisions unverifiable, which are
        # exactly the ones a judge will look at.
        log.seal()

        if verbose:
            _print(decision, leaf, sig, cfg, exits, recon_issues)

    return decision


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
        sig = evaluate_exit(p, buyback, today, cfg.profit_target,
                            cfg.exit_dte, cfg.stop_loss_mult)
        rec = {"position": p.id, "expiry": p.expiry, "dte": p.dte(today),
               "credit": p.credit, "contracts": p.contracts,
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


def _count_option_structures(positions: list[dict]) -> int:
    """
    Count STRUCTURES, not legs. A condor is four position rows but one unit of
    risk, and the capacity gate is about units of risk.
    """
    legs = [p for p in positions
            if len(str(p.get("symbol", ""))) > 15]   # OCC symbols are long
    return max(1, round(len(legs) / 4)) if legs else 0


def _print(d: Decision, leaf: str, sig: SIG.Signals, cfg: Config,
           exits: list[dict] | None = None,
           recon: list[dict] | None = None) -> None:
    bar = "=" * 74
    print(bar)
    print(f"DECISION  {d.timestamp}   ACTION: {d.action.upper()}")
    print(bar)
    for issue in (recon or []):
        sev = issue.get("severity", "info")
        print(f"  [{sev}] {issue.get('position')}: {issue.get('issue', '')[:90]}")
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
    print(f"  trailing RV {sig.trailing_rv:.2f}   "
          f"VRP {sig.vrp:+.2f} vol points (threshold {cfg.vrp_threshold:.1f})")
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="decide and log, place nothing")
    ap.add_argument("--once", action="store_true", help="single cycle then exit")
    ap.add_argument("--seal", action="store_true",
                    help="seal the artifact log and print the Merkle root")
    args = ap.parse_args()

    if args.seal:
        print(json.dumps(ArtifactLog().seal(), indent=2))
        return

    run_cycle(DEFAULT, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
