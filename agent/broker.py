"""
Everything that touches the market, routed through MCP.

Execution follows what the live fill test on 2026-08-19 actually measured, not
what seemed reasonable: a net-credit limit walked from mid toward the crossing
price filled one cent off mid on entry and two on exit, for a 1.5% round trip.
Crossing the full spread at 16 delta would have cost 8.3%.

Two consequences, both enforced here:
  - NEVER send a market order across four legs.
  - Ladder from mid, and stop as soon as it fills.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from config import Config
from hedge import VixQuote, hedge_order, parse_vix_chain
from mcp_client import MCPClient
from signals import Contract, parse_chain


@dataclass
class CondorPlan:
    short_call: Contract
    long_call: Contract
    short_put: Contract
    long_put: Contract
    credit_mid: float
    credit_crossing: float
    wing: float
    expiry: date
    dte: int

    @property
    def est_cost(self) -> float:
        """Half the mid-to-crossing gap, which is what the ladder actually pays."""
        return max((self.credit_mid - self.credit_crossing) / 2.0, 0.0)

    @property
    def max_loss_per_contract(self) -> float:
        return self.wing - self.credit_mid

    def legs(self, opening: bool) -> list[dict]:
        if opening:
            spec = [(self.short_call, "sell", "sell_to_open"),
                    (self.long_call, "buy", "buy_to_open"),
                    (self.short_put, "sell", "sell_to_open"),
                    (self.long_put, "buy", "buy_to_open")]
        else:
            spec = [(self.short_call, "buy", "buy_to_close"),
                    (self.long_call, "sell", "sell_to_close"),
                    (self.short_put, "buy", "buy_to_close"),
                    (self.long_put, "sell", "sell_to_close")]
        return [{"symbol": c.occ, "ratio_qty": "1", "side": s,
                 "position_intent": pi} for c, s, pi in spec]

    def to_dict(self) -> dict:
        return {
            "expiry": self.expiry.isoformat(), "dte": self.dte,
            "short_call": self.short_call.occ, "long_call": self.long_call.occ,
            "short_put": self.short_put.occ, "long_put": self.long_put.occ,
            "strikes": [self.short_put.strike, self.long_put.strike,
                        self.short_call.strike, self.long_call.strike],
            "wing": self.wing,
            "credit_mid": round(self.credit_mid, 3),
            "credit_crossing": round(self.credit_crossing, 3),
            "est_cost": round(self.est_cost, 4),
            "max_loss_per_contract": round(self.max_loss_per_contract, 3),
        }


class Broker:
    def __init__(self, mcp: MCPClient, cfg: Config):
        self.mcp = mcp
        self.cfg = cfg

    # --- reads -------------------------------------------------------------

    def account(self) -> dict:
        r = self.mcp.call("get_account_info")
        return r.get("data", r)

    def clock(self) -> dict:
        r = self.mcp.call("get_clock")
        return r.get("data", r)

    def positions(self) -> list[dict]:
        r = self.mcp.call("get_all_positions")
        d = r.get("data", r)
        return d if isinstance(d, list) else d.get("positions", [])

    def spot(self) -> float:
        r = self.mcp.call("get_stock_snapshot", {"symbols": self.cfg.underlying})
        d = r.get("data", r)
        snap = d.get(self.cfg.underlying, d) if isinstance(d, dict) else {}
        for key in ("latestTrade", "latest_trade"):
            if key in snap and isinstance(snap[key], dict):
                p = snap[key].get("p", snap[key].get("price"))
                if p:
                    return float(p)
        for key in ("dailyBar", "daily_bar", "minuteBar", "minute_bar"):
            if key in snap and isinstance(snap[key], dict):
                c = snap[key].get("c", snap[key].get("close"))
                if c:
                    return float(c)
        raise RuntimeError(f"could not read spot from snapshot: {str(snap)[:200]}")

    def closes(self, days: int = 45) -> list[float]:
        r = self.mcp.call("get_stock_bars", {
            "symbols": self.cfg.underlying, "timeframe": "1Day",
            "days": days, "limit": 400, "sort": "asc",
        })
        d = r.get("data", r)
        bars = d.get(self.cfg.underlying) if isinstance(d, dict) else None
        if bars is None and isinstance(d, dict):
            bars = d.get("bars", {}).get(self.cfg.underlying)
        if not bars:
            raise RuntimeError(f"no bars returned: {str(d)[:200]}")
        return [float(b.get("c", b.get("close"))) for b in bars]

    def chain(self, dte_lo: int, dte_hi: int, spot: float,
              band: float = 0.12, max_pages: int = 25) -> list[Contract]:
        """
        Fetch the chain, FOLLOWING PAGINATION.

        The API returns a next_page_token and the first page comes back as deep
        ITM strikes. Reading only page one silently yields a chain with no ATM
        contracts in it, which surfaces much later as "no quoted contracts near
        30 DTE" rather than as an obvious paging error.
        """
        today = date.today()
        args = {
            "underlying_symbol": self.cfg.underlying,
            "expiration_date_gte": (today + timedelta(days=dte_lo)).isoformat(),
            "expiration_date_lte": (today + timedelta(days=dte_hi)).isoformat(),
            "strike_price_gte": round(spot * (1 - band), 2),
            "strike_price_lte": round(spot * (1 + band), 2),
            "limit": 1000,
        }
        contracts: list[Contract] = []
        seen: set[str] = set()
        token = None
        for _ in range(max_pages):
            if token:
                args["page_token"] = token
            r = self.mcp.call("get_option_chain", dict(args))
            for c in parse_chain(r, self.cfg.underlying):
                if c.occ not in seen:
                    seen.add(c.occ)
                    contracts.append(c)
            data = r.get("data", r) if isinstance(r, dict) else {}
            token = data.get("next_page_token") if isinstance(data, dict) else None
            if not token:
                break
        return contracts

    def vix_chain(self, dte_lo: int, dte_hi: int,
                 max_pages: int = 25) -> list[VixQuote]:
        """
        VIX option chain, parsed into VixQuote. Same pagination lesson as
        chain(): page one is not guaranteed to hold the strikes needed, so
        every page is followed. No strike band is applied, unlike the SPY
        chain: VIX strikes span a much narrower absolute range, and
        recovering a trustworthy forward via put-call parity needs the full
        curve, not a window around spot.
        """
        today = date.today()
        args = {
            "underlying_symbol": "VIX",
            "expiration_date_gte": (today + timedelta(days=dte_lo)).isoformat(),
            "expiration_date_lte": (today + timedelta(days=dte_hi)).isoformat(),
            "limit": 1000,
        }
        quotes: list[VixQuote] = []
        seen: set[str] = set()
        token = None
        for _ in range(max_pages):
            if token:
                args["page_token"] = token
            r = self.mcp.call("get_option_chain", dict(args))
            for q in parse_vix_chain(r):
                if q.occ not in seen:
                    seen.add(q.occ)
                    quotes.append(q)
            data = r.get("data", r) if isinstance(r, dict) else {}
            token = data.get("next_page_token") if isinstance(data, dict) else None
            if not token:
                break
        return quotes

    def place_hedge(self, plan, dry_run: bool = False) -> dict:
        """
        Single-leg buy-to-open for the VIX call, at mid, polled once for a fill.

        Not laddered like the condor: this is a BUY, and an unfilled resting
        buy carries no short exposure the way an unfilled short leg would, so
        the double-open guard built for place_laddered does not apply here in
        the same way. A day order that never fills is a safe state to leave
        alone, not a risk that compounds.
        """
        args = hedge_order(plan)
        if dry_run:
            return {"filled": False, "dry_run": True, "would_send": args}

        try:
            res = self.mcp.call("place_option_order", args)
        except Exception as exc:
            return {"filled": False, "error": str(exc)[:200]}

        d = res.get("data", res)
        oid = d.get("id") if isinstance(d, dict) else None
        filled = self._await_fill(oid)
        if filled:
            return self._fill_result(filled, 1, [{"order_id": oid}])
        return {"filled": False, "order_id": oid, "resting": bool(oid)}

    def quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Latest quotes for specific contracts. Batched, 100 per request."""
        out: dict[str, dict] = {}
        for i in range(0, len(symbols), 100):
            batch = symbols[i:i + 100]
            r = self.mcp.call("get_option_snapshot", {"symbols": ",".join(batch)})
            d = r.get("data", r)
            snaps = d.get("snapshots", d) if isinstance(d, dict) else {}
            if not isinstance(snaps, dict):
                continue
            for sym, snap in snaps.items():
                if isinstance(snap, dict):
                    q = snap.get("latestQuote") or snap.get("latest_quote")
                    if isinstance(q, dict):
                        out[sym] = q
        return out

    def plan_from_position(self, pos) -> "CondorPlan | None":
        """
        Rebuild a closable plan from a ledger position.

        Only the leg symbols matter for a closing order, so prices are left at
        zero and the caller supplies the limit. This exists so closing reuses
        the same laddered execution path as opening rather than a second,
        less-tested code path.
        """
        from datetime import date as _date
        from signals import Contract

        def stub(sym: str | None) -> Contract | None:
            if not sym:
                return None
            from signals import parse_occ
            _, exp, is_call, strike = parse_occ(sym)
            return Contract(sym, strike, is_call, exp, None, None, None, None)

        sc, lc = stub(pos.short_call), stub(pos.long_call)
        sp, lp = stub(pos.short_put), stub(pos.long_put)
        if not all((sc, lc, sp, lp)):
            return None
        exp = _date.fromisoformat(pos.expiry)
        return CondorPlan(sc, lc, sp, lp, 0.0, 0.0,
                          pos.max_loss_per_contract + pos.credit, exp,
                          (exp - _date.today()).days)

    def close_position(self, pos, buyback: float, contracts: int,
                       dry_run: bool = False) -> dict:
        """
        Buy the structure back. Closing is a DEBIT, so limit prices are positive
        and the ladder walks upward, paying more to get out rather than less.
        """
        plan = self.plan_from_position(pos)
        if plan is None:
            return {"filled": False, "error": "could not rebuild plan from position"}
        plan.credit_mid = buyback
        plan.credit_crossing = buyback * 0.85     # walk up to ~18% over mid
        return self.place_laddered(plan, contracts, opening=False, dry_run=dry_run)

    # --- structure building -------------------------------------------------

    def build_condor(self, contracts: list[Contract], spot: float,
                     today: date) -> CondorPlan | None:
        """
        Assemble a same-expiry condor: short strikes at the configured delta,
        wings a fixed width out. Wings are chosen by WIDTH, not by delta: the
        2026-08-19 fill test showed delta-selected wings come out wildly
        asymmetric (22 point put wing against a 9 point call wing, giving 10:1
        risk to reward).
        """
        usable = [c for c in contracts
                  if c.delta is not None and c.mid is not None
                  and self.cfg.dte_min <= c.dte(today) <= self.cfg.dte_max]
        if not usable:
            return None

        by_exp: dict[date, list[Contract]] = {}
        for c in usable:
            by_exp.setdefault(c.expiry, []).append(c)
        # Prefer the expiry nearest the target tenor that has real depth.
        exp = min(by_exp, key=lambda e: (abs((e - today).days - self.cfg.dte_target),
                                         -len(by_exp[e])))
        same = by_exp[exp]
        calls = [c for c in same if c.is_call]
        puts = [c for c in same if not c.is_call]
        if not calls or not puts:
            return None

        wing = max(round(spot * self.cfg.wing_pct), 1.0)
        sc = min(calls, key=lambda c: abs(abs(c.delta) - self.cfg.short_delta))
        sp = min(puts, key=lambda c: abs(abs(c.delta) - self.cfg.short_delta))
        lc = min(calls, key=lambda c: abs(c.strike - (sc.strike + wing)))
        lp = min(puts, key=lambda c: abs(c.strike - (sp.strike - wing)))

        if sp.strike >= sc.strike or lc.strike <= sc.strike or lp.strike >= sp.strike:
            return None

        credit_mid = sc.mid + sp.mid - lc.mid - lp.mid
        credit_crossing = (sc.bid + sp.bid) - (lc.ask + lp.ask)
        if credit_mid <= 0.02:
            return None

        # MAX, not min. An iron condor can only lose on one side at a time, so
        # its max loss is the WIDER wing minus the credit. Taking the minimum
        # understates risk whenever the two wings differ, which happens as soon
        # as a strike is unquoted and the nearest available one is further out.
        # Gate 10 then sizes against a loss that cannot happen and passes a
        # position whose real risk exceeds the cap.
        actual_wing = max(lc.strike - sc.strike, sp.strike - lp.strike)
        return CondorPlan(sc, lc, sp, lp, credit_mid, credit_crossing,
                          actual_wing, exp, (exp - today).days)

    # --- execution ----------------------------------------------------------

    def _resting_orders_for_legs(self, plan: CondorPlan) -> list[dict] | None:
        """
        Ask Alpaca directly whether an order already rests on these exact legs,
        rather than trusting a client_order_id or order_id we may have lost.

        This is the guard against double-open. Four ways it happens without it:
        the MCP call raises AFTER Alpaca already accepted the order, so no oid
        is ever recorded to cancel; _await_fill hits an exception and returns
        None, discarding a real order_id; a parent-quantity partial fill times
        out the poll instead of resolving; or the watchdog kills the process
        mid-ladder. In every case `sell_to_open` is always valid on Alpaca's
        side, so nothing there rejects a genuine duplicate. The external order
        book is the only source of truth a client-side guard can be built on.

        Returns None when the query itself could not be trusted (a transport
        failure, or a response shape that does not parse), meaning safety is
        UNCONFIRMED. Callers must treat that as "assume unsafe", not as "assume
        clear": guessing clear is the exact bug this function exists to close.

        Filters server-side by `symbols`, then re-checks client-side against
        each returned order's legs. Belt and suspenders: `nested=True` is
        documented to roll multi-leg orders up under a `legs` field when
        filtering by symbols, but that behaviour has not been exercised against
        a real resting multi-leg order in this codebase, so it is not trusted
        alone.
        """
        leg_symbols = {c.occ for c in
                       (plan.short_call, plan.long_call, plan.short_put, plan.long_put)}
        try:
            r = self.mcp.call("get_orders", {
                "status": "open", "symbols": ",".join(sorted(leg_symbols)),
                "nested": True, "limit": 50,
            })
        except Exception:
            return None

        d = r.get("data", r) if isinstance(r, dict) else r
        orders = d.get("result", d) if isinstance(d, dict) else d
        if not isinstance(orders, list):
            return None   # unexpected shape; cannot confirm safety, do not guess

        matched = []
        for o in orders:
            if not isinstance(o, dict):
                continue
            seen = set()
            top = o.get("symbol")
            if top:
                seen.add(top)
            for leg in (o.get("legs") or []):
                if isinstance(leg, dict) and leg.get("symbol"):
                    seen.add(leg["symbol"])
            if seen & leg_symbols:
                matched.append(o)
        return matched

    def place_laddered(self, plan: CondorPlan, contracts: int, opening: bool,
                       dry_run: bool = False) -> dict:
        """
        Walk a net limit from mid toward the crossing price, stopping on fill.

        For a credit the limit is NEGATIVE and for a debit POSITIVE, per Alpaca's
        multi-leg convention. Each rung carries a distinct client_order_id, which
        the API documents as an idempotency key, so a timeout can be retried
        without risking a duplicate position.

        Before EVERY rung, including the first, confirms nothing is already
        resting on these legs. See `_resting_orders_for_legs` for why this
        cannot be skipped: an exception after Alpaca already accepted an order
        leaves no local record of it, and `sell_to_open` never rejects a
        genuine duplicate the way a closing order would.
        """
        if opening:
            start, end = -plan.credit_mid, -plan.credit_crossing
        else:
            start = plan.credit_mid
            end = plan.credit_crossing + (plan.credit_mid - plan.credit_crossing) * 2

        rungs = max(self.cfg.price_ladder_rungs, 1)
        attempts: list[dict] = []
        i = 0
        while i < rungs:
            if not dry_run:
                resting = self._resting_orders_for_legs(plan)
                if resting is None:
                    attempts.append({
                        "rung": i + 1, "aborted": True,
                        "reason": "could not confirm no order is resting on "
                                  "these legs; refusing to send a new one "
                                  "rather than risk a duplicate position",
                    })
                    return {"filled": False, "attempts": attempts,
                            "aborted_unsafe": True}
                if resting:
                    existing_id = resting[0].get("id")
                    attempts.append({"rung": i + 1, "found_resting_order": existing_id,
                                     "waited_instead_of_sending": True})
                    filled = self._await_fill(existing_id)
                    if filled:
                        return self._fill_result(filled, i + 1, attempts)
                    self._cancel(existing_id)
                    continue   # do not advance i; re-check clear next pass

            frac = i / (rungs - 1) if rungs > 1 else 1.0
            px = start + (end - start) * frac
            coid = f"vrp-{'open' if opening else 'close'}-{uuid.uuid4().hex[:12]}"
            args = {
                "qty": str(contracts),
                "type": "limit",
                "time_in_force": "day",
                "order_class": "mleg",
                "limit_price": f"{px:.2f}",
                "legs": plan.legs(opening),
                "client_order_id": coid,
            }
            if dry_run:
                attempts.append({"rung": i + 1, "limit_price": round(px, 2),
                                 "dry_run": True, "client_order_id": coid})
                i += 1
                continue

            try:
                res = self.mcp.call("place_option_order", args)
            except Exception as exc:
                # Do NOT retry blindly. The order may have been accepted by
                # Alpaca despite this client-side exception. The resting-order
                # check at the top of the next iteration is what determines
                # whether that happened, rather than guessing here.
                attempts.append({"rung": i + 1, "limit_price": round(px, 2),
                                 "error": str(exc)[:200]})
                i += 1
                continue

            d = res.get("data", res)
            oid = d.get("id") if isinstance(d, dict) else None
            attempts.append({"rung": i + 1, "limit_price": round(px, 2),
                             "order_id": oid, "client_order_id": coid})
            filled = self._await_fill(oid)
            if filled:
                return self._fill_result(filled, i + 1, attempts)
            if oid:
                self._cancel(oid)
            i += 1

        return {"filled": False, "attempts": attempts, "dry_run": dry_run}

    @staticmethod
    def _fill_result(order: dict, rung: int, attempts: list[dict]) -> dict:
        """
        Build the standard success return, distinguishing a full fill from a
        parent-quantity partial. A partial means fewer CONTRACTS filled than
        requested, with all four legs of those contracts filled together
        (Alpaca fills multi-leg orders atomically per contract); it does not
        mean some legs filled and others did not.
        """
        try:
            filled_qty = int(float(order.get("filled_qty", 0)))
        except (TypeError, ValueError):
            filled_qty = None
        return {
            "filled": True,
            "partial": order.get("status") == "partially_filled",
            "filled_qty": filled_qty,
            "filled_avg_price": order.get("filled_avg_price"),
            "rung": rung,
            "order": order,
            "attempts": attempts,
        }

    def _await_fill(self, order_id: str | None) -> dict | None:
        if not order_id:
            return None
        deadline = time.time() + self.cfg.rung_wait_seconds
        while time.time() < deadline:
            try:
                r = self.mcp.call("get_order_by_id", {"order_id": order_id})
            except Exception:
                return None
            d = r.get("data", r)
            status = d.get("status") if isinstance(d, dict) else None
            if status == "filled":
                return d
            if status == "partially_filled":
                # Cancel the remainder immediately rather than let it keep
                # resting. Letting it ride is what would let a LATER rung, or
                # the next agent cycle, stack a second position on top of the
                # portion that already filled.
                self._cancel(order_id)
                return d
            if status in ("canceled", "rejected", "expired"):
                return None
            time.sleep(2)
        return None

    def _cancel(self, order_id: str) -> None:
        try:
            self.mcp.call("cancel_order_by_id", {"order_id": order_id})
        except Exception:
            pass
