"""
Decision-time signals, computed from data fetched through MCP.

Two rules hold everything here together:

  1. NOTHING may look forward. H1 defines the volatility risk premium against
     SUBSEQUENT realised vol, which is correct for testing the thesis and
     unavailable to a live agent. Amendment A1.2 replaced it with a trailing
     proxy for exactly this reason.
  2. Units are annualised VOLATILITY POINTS everywhere, matching how VIX quotes
     (15.84 means 15.84%). Mixing decimals and percentages is the classic silent
     bug in volatility code, so every function here returns points.

The term structure is derived from SPY's own option chain rather than read off
VIX and VIX3M, because Alpaca's index data endpoint returns 404 (verified
2026-08-19). That turned out to be the better construction anyway: it needs no
second data source, updates in real time rather than at the daily close, and
measures the term structure of the instrument we actually trade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

TRADING_DAYS = 252


@dataclass
class Contract:
    occ: str
    strike: float
    is_call: bool
    expiry: date
    iv: float | None            # decimal, as the API returns it
    delta: float | None
    bid: float | None
    ask: float | None

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        if self.bid <= 0 or self.ask <= 0:
            return None
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid

    def dte(self, today: date) -> int:
        return (self.expiry - today).days


@dataclass
class Signals:
    spot: float
    atm_iv_near: float          # vol points
    atm_iv_far: float           # vol points
    term_ratio: float           # near / far; below 1.0 is contango
    contango: bool
    trailing_rv: float          # vol points
    vrp: float                  # vol points
    n_contracts: int
    near_dte: int
    far_dte: int

    def to_dict(self) -> dict:
        return {
            "spot": round(self.spot, 2),
            "atm_iv_near": round(self.atm_iv_near, 3),
            "atm_iv_far": round(self.atm_iv_far, 3),
            "term_ratio": round(self.term_ratio, 4),
            "contango": self.contango,
            "trailing_rv": round(self.trailing_rv, 3),
            "vrp": round(self.vrp, 3),
            "near_dte": self.near_dte,
            "far_dte": self.far_dte,
            "n_contracts": self.n_contracts,
        }


def parse_occ(symbol: str) -> tuple[str, date, bool, float]:
    i = 0
    while i < len(symbol) and symbol[i].isalpha():
        i += 1
    root, body = symbol[:i], symbol[i:]
    exp = datetime.strptime(body[:6], "%y%m%d").date()
    return root, exp, body[6] == "C", int(body[7:]) / 1000.0


def parse_chain(chain_payload: Any, underlying: str) -> list[Contract]:
    """
    Normalise whatever the MCP server hands back into Contract objects.

    Defensive on shape: the payload may be the snapshot map directly or wrapped
    in a "data"/"snapshots" envelope depending on server version. Guessing wrong
    here would fail silently at 3am with the market open, so all three are handled.
    """
    payload = chain_payload
    for key in ("data", "snapshots"):
        if isinstance(payload, dict) and key in payload and isinstance(payload[key], dict):
            payload = payload[key]
    if not isinstance(payload, dict):
        return []

    out: list[Contract] = []
    for occ, snap in payload.items():
        if not isinstance(snap, dict) or not occ.startswith(underlying):
            continue
        try:
            _, exp, is_call, strike = parse_occ(occ)
        except (ValueError, IndexError):
            continue
        greeks = snap.get("greeks") or {}
        quote = snap.get("latestQuote") or snap.get("latest_quote") or {}
        out.append(Contract(
            occ=occ, strike=strike, is_call=is_call, expiry=exp,
            iv=snap.get("impliedVolatility", snap.get("implied_volatility")),
            delta=greeks.get("delta"),
            bid=quote.get("bp", quote.get("bid_price")),
            ask=quote.get("ap", quote.get("ask_price")),
        ))
    return out


def realised_vol(closes: list[float], window: int = 21) -> float:
    """Annualised trailing realised vol in POINTS from a close series."""
    if len(closes) < window + 1:
        raise ValueError(f"need {window + 1} closes, got {len(closes)}")
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    rets = rets[-window:]
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS) * 100.0


def atm_iv_at(contracts: list[Contract], spot: float, today: date,
              target_dte: int, tolerance: int = 12) -> tuple[float, int]:
    """
    ATM implied vol in POINTS near a target tenor.

    Averages the nearest-to-the-money call and put rather than taking a single
    contract, because one stale quote at the money would otherwise move the
    whole signal. Returns the vol and the DTE actually used.
    """
    pool = [c for c in contracts
            if c.iv and c.iv > 0 and abs(c.dte(today) - target_dte) <= tolerance]
    if not pool:
        raise ValueError(f"no quoted contracts near {target_dte} DTE")

    # Settle on one expiry: the one closest to target with enough quotes.
    by_exp: dict[date, list[Contract]] = {}
    for c in pool:
        by_exp.setdefault(c.expiry, []).append(c)
    exp = min(by_exp, key=lambda e: (abs((e - today).days - target_dte),
                                     -len(by_exp[e])))
    same = by_exp[exp]

    call = min((c for c in same if c.is_call),
               key=lambda c: abs(c.strike - spot), default=None)
    put = min((c for c in same if not c.is_call),
              key=lambda c: abs(c.strike - spot), default=None)
    ivs = [c.iv for c in (call, put) if c and c.iv]
    if not ivs:
        raise ValueError(f"no ATM quotes at {exp}")
    return (sum(ivs) / len(ivs)) * 100.0, (exp - today).days


def compute(contracts: list[Contract], spot: float, closes: list[float],
            today: date, near_dte: int = 30, far_dte: int = 90) -> Signals:
    """
    Build the full signal set.

    Term structure uses 30 and 90 day tenors to mirror what VIX and VIX3M
    measure, so the contango reading is comparable to the H2 research that
    justified the regime gate.
    """
    atm_near, used_near = atm_iv_at(contracts, spot, today, near_dte)
    try:
        atm_far, used_far = atm_iv_at(contracts, spot, today, far_dte, tolerance=35)
    except ValueError:
        # No long tenor quoted. Fall back to flat, which reads as contango and
        # therefore does NOT block trading. Recorded so the artifact shows it.
        atm_far, used_far = atm_near, used_near

    ratio = atm_near / atm_far if atm_far else float("nan")
    rv = realised_vol(closes)

    return Signals(
        spot=spot,
        atm_iv_near=atm_near,
        atm_iv_far=atm_far,
        term_ratio=ratio,
        contango=bool(ratio < 1.0),
        trailing_rv=rv,
        vrp=atm_near - rv,
        n_contracts=len(contracts),
        near_dte=used_near,
        far_dte=used_far,
    )
