"""
The position ledger and exit logic.

Why a ledger rather than inferring structures from broker positions: Alpaca
returns option positions as individual LEGS. Four rows might be one condor, or
two unrelated verticals, or one condor plus a leftover leg from a partial fill.
Reconstructing intent from legs is guesswork, and guessing wrong means closing
half a position and leaving naked short options open, which is the single worst
failure mode available to a short-premium agent.

So the agent records what it opened, and reconciles that record against the
broker every cycle. When they disagree the broker wins and the disagreement is
logged, because the broker is the truth and a silent divergence is how an
"unattended" agent quietly becomes an unhedged one.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

LEDGER_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "positions.json"


@dataclass
class OpenPosition:
    id: str
    opened_at: str
    expiry: str
    contracts: int
    credit: float                       # per contract, at entry
    max_loss_per_contract: float
    short_call: str | None
    long_call: str | None
    short_put: str | None
    long_put: str | None
    entry_limit: float | None = None
    entry_order_id: str | None = None
    peak_profit_frac: float = 0.0       # best profit fraction seen, for reporting

    @property
    def legs(self) -> list[str]:
        return [s for s in (self.short_call, self.long_call,
                            self.short_put, self.long_put) if s]

    @property
    def notional_risk(self) -> float:
        return self.max_loss_per_contract * 100.0 * self.contracts

    def dte(self, today: date) -> int:
        return (date.fromisoformat(self.expiry) - today).days

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExitSignal:
    should_exit: bool
    reason: str
    profit_frac: float
    buyback: float
    unrealised: float

    def to_dict(self) -> dict:
        return {
            "should_exit": self.should_exit, "reason": self.reason,
            "profit_frac": round(self.profit_frac, 4),
            "buyback": round(self.buyback, 3),
            "unrealised": round(self.unrealised, 2),
        }


class Ledger:
    def __init__(self, path: Path = LEDGER_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[OpenPosition]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text())
        return [OpenPosition(**p) for p in raw.get("open", [])]

    def save(self, positions: list[OpenPosition]) -> None:
        self.path.write_text(json.dumps(
            {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "open": [p.to_dict() for p in positions]},
            indent=2), encoding="utf-8")

    def add(self, pos: OpenPosition) -> None:
        cur = self.load()
        cur.append(pos)
        self.save(cur)

    def remove(self, pos_id: str) -> None:
        self.save([p for p in self.load() if p.id != pos_id])

    def update(self, pos: OpenPosition) -> None:
        self.save([pos if p.id == pos.id else p for p in self.load()])


def new_position(plan_dict: dict, contracts: int, credit: float,
                 entry_limit: float | None, order_id: str | None) -> OpenPosition:
    return OpenPosition(
        id=f"pos-{uuid.uuid4().hex[:10]}",
        opened_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        expiry=plan_dict["expiry"],
        contracts=contracts,
        credit=credit,
        max_loss_per_contract=plan_dict["max_loss_per_contract"],
        short_call=plan_dict.get("short_call"),
        long_call=plan_dict.get("long_call"),
        short_put=plan_dict.get("short_put"),
        long_put=plan_dict.get("long_put"),
        entry_limit=entry_limit,
        entry_order_id=order_id,
    )


def value_from_quotes(pos: OpenPosition, quotes: dict[str, dict]) -> float | None:
    """
    Current cost per contract to buy the structure back, from live mid quotes.

    Returns None if any leg is unquoted. Refusing to value a position on partial
    data is deliberate: a structure priced from three of four legs looks cheaper
    than it is, and that error points toward holding a loser.
    """
    def mid(sym: str | None) -> float | None:
        if not sym or sym not in quotes:
            return None
        q = quotes[sym]
        bid, ask = q.get("bp", q.get("bid_price")), q.get("ap", q.get("ask_price"))
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return None
        return (float(bid) + float(ask)) / 2.0

    sc, lc = mid(pos.short_call), mid(pos.long_call)
    sp, lp = mid(pos.short_put), mid(pos.long_put)
    have_call = pos.short_call is None or (sc is not None and lc is not None)
    have_put = pos.short_put is None or (sp is not None and lp is not None)
    if not (have_call and have_put):
        return None

    v = 0.0
    if pos.short_call and sc is not None and lc is not None:
        v += sc - lc
    if pos.short_put and sp is not None and lp is not None:
        v += sp - lp
    return v


def evaluate_exit(pos: OpenPosition, buyback: float | None, today: date,
                  profit_target: float, exit_dte: int,
                  stop_loss_mult: float | None) -> ExitSignal:
    """
    Exit rules, in priority order. Time first, because an unquoted position that
    is about to expire must still be closed.
    """
    dte = pos.dte(today)

    if buyback is None:
        if dte <= exit_dte:
            return ExitSignal(True, f"expiry in {dte}d and legs are unquoted; "
                                    f"close on time rather than hold blind",
                              0.0, 0.0, 0.0)
        return ExitSignal(False, "legs unquoted, cannot value; holding", 0.0, 0.0, 0.0)

    profit_frac = (pos.credit - buyback) / pos.credit if pos.credit else 0.0
    unrealised = (pos.credit - buyback) * 100.0 * pos.contracts

    if dte <= exit_dte:
        return ExitSignal(True, f"{dte} DTE reached the {exit_dte} day exit; "
                                f"gamma rises sharply into expiry",
                          profit_frac, buyback, unrealised)
    if profit_frac >= profit_target:
        return ExitSignal(True, f"captured {profit_frac * 100:.0f}% of max profit, "
                                f"target {profit_target * 100:.0f}%",
                          profit_frac, buyback, unrealised)
    if stop_loss_mult is not None and buyback >= pos.credit * stop_loss_mult:
        return ExitSignal(True, f"buyback {buyback:.2f} reached "
                                f"{stop_loss_mult:.1f}x the {pos.credit:.2f} credit; "
                                f"stop out before the wing",
                          profit_frac, buyback, unrealised)
    return ExitSignal(False, f"holding: {profit_frac * 100:+.0f}% of max profit, "
                             f"{dte} DTE", profit_frac, buyback, unrealised)


def reconcile(ledger_positions: list[OpenPosition],
              broker_symbols: set[str]) -> tuple[list[OpenPosition], list[dict]]:
    """
    Compare the ledger against what the broker actually holds.

    Three outcomes per position:
      - every leg present: healthy
      - no legs present: closed or expired elsewhere, drop it
      - SOME legs present: a partial close or an assignment. This is the
        dangerous one, because a condor missing its long wing is a naked short.
        Flagged loudly rather than quietly repaired.
    """
    healthy, issues = [], []
    for p in ledger_positions:
        present = [s for s in p.legs if s in broker_symbols]
        if len(present) == len(p.legs):
            healthy.append(p)
        elif not present:
            issues.append({"position": p.id, "severity": "info",
                           "issue": "no legs at broker; closed or expired",
                           "expected_legs": p.legs})
        else:
            issues.append({"position": p.id, "severity": "CRITICAL",
                           "issue": "PARTIAL position at broker. A condor missing "
                                    "a long wing is a naked short. Needs manual "
                                    "inspection before any further trading",
                           "expected_legs": p.legs, "present_legs": present})
            healthy.append(p)
    return healthy, issues
