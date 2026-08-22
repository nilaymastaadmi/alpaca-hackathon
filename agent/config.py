"""
Every tunable in one place, with the provenance of each number.

A parameter with no recorded reason is a parameter nobody can defend to a judge,
so each one below cites where it came from. Values marked RESEARCH come from the
pre-registered backtest; DEPLOYMENT ones are deliberate deviations recorded in
research/DEPLOYMENT_DECISIONS.md; MEASURED ones came off the live API.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, time


@dataclass(frozen=True)
class Config:
    # --- universe and structure -------------------------------------------
    # MEASURED: SPY round trip 2.5% of credit one way vs QQQ 6.4%, so QQQ costs
    # 2.6x more. Universe stays SPY unless a live cost check clears a candidate.
    underlying: str = "SPY"

    # RESEARCH + COST TEST: 16 delta is where the near-mid fill behaviour we
    # actually measured applies. At 5 delta the option trades near $0.11 with a
    # $0.01 spread, so one tick is 9% of its value and mid fills do not exist.
    short_delta: float = 0.16

    # AMENDMENT A1.1: wing as a percentage of spot, not a flat $5, so the
    # structure means the same thing at SPY 180 and SPY 770.
    wing_pct: float = 0.0065

    # RESEARCH: 4.5 day judging window. 42 DTE captures only 7-9% of its credit
    # in that time; 0-3 DTE was the worst tenor tested at Sharpe +0.238.
    dte_min: int = 7
    dte_max: int = 14
    dte_target: int = 10

    # --- sizing, DEPLOYMENT decision D1 ------------------------------------
    # Deliberate deviation from the 1%/one-position research sizing. At research
    # sizing the agent expected 0.76 trades across the whole judging window.
    max_concurrent: int = 5
    risk_per_position: float = 0.03
    # SWEEP: concurrency saturates at 5. An 8-position cap produced results
    # identical to 5 because a 6th simultaneous opportunity never appears.

    # SWEEP: a stop improved Sharpe (+1.463 -> +1.570) AND drawdown
    # (-13.30% -> -11.16%) on the deployed config. Exploratory, not registered.
    stop_loss_mult: float | None = 2.0

    # RESEARCH: exit at half of max profit, or when time decay stops paying.
    profit_target: float = 0.50
    exit_dte: int = 2

    # Stagger: five positions on one expiry is one position at 15% in a costume.
    one_per_expiry: bool = True

    # --- gates -------------------------------------------------------------
    # H1: mean VRP +3.68 vol points, Newey-West t +4.74. The threshold sits
    # below the mean deliberately: refusing too often is how the agent ends the
    # week with nothing to show.
    vrp_threshold: float = 1.0
    use_regime_gate: bool = True
    # H2: VRP in contango has t +6.13; in backwardation t +0.72, indistinguishable
    # from zero. The gate exists because the edge is only reliably THERE in
    # contango, not because contango pays more (the mean gap is only 0.59).
    contango_max_ratio: float = 1.0

    # --- portfolio circuit breakers ---------------------------------------
    # At 15% concurrent risk these stop being decorative and become the primary
    # defence. See DEPLOYMENT_DECISIONS.md D1.
    daily_loss_limit: float = 0.04      # halt for the session
    max_drawdown_limit: float = 0.10    # halt entirely, flatten
    consecutive_loss_pause: int = 3     # pause after N losses in a row
    consecutive_loss_scale: float = 0.5  # then halve size on resume

    # --- tail hedge --------------------------------------------------------
    # Cboe VXTH methodology overlays 1-month 30-delta VIX calls on an equity
    # book. Consensus sizing across sources is 0.5% to 2% of portfolio.
    # The short-vol book is 15% concurrent risk on ONE underlying in ONE
    # direction, so all five positions hit max loss together in a vol spike.
    # This is the only thing that caps that scenario.
    hedge_enabled: bool = True
    hedge_budget_pct: float = 0.01      # 1% of equity
    # NOT a delta, despite VXTH's own "30 delta" language. Alpaca's VIX chain
    # carries no greeks (verified 2026-08-20), so hedge.build_hedge() proxies
    # the 30-delta rule with strike/forward MONEYNESS instead, recovered via
    # put-call parity. This field was previously named hedge_target_delta at
    # 0.30, which would have been passed straight into build_hedge's
    # target_moneyness parameter and silently picked strikes far BELOW the
    # forward, backwards for a crash-insurance call. Renamed to say what it
    # actually is; see agent/hedge.py for the parity derivation.
    hedge_target_moneyness: float = 1.35
    hedge_dte_min: int = 21
    hedge_dte_max: int = 45

    # --- event awareness ---------------------------------------------------
    # MEASURED: NFP lands Fri 4 Sep 08:30 ET, inside the window and 2.5 hours
    # before the submission deadline. A naked short-gamma book into that could
    # wreck the final P&L in the last hour judges see.
    event_derisk_enabled: bool = True
    event_derisk_fraction: float = 0.50   # cut short-vega exposure by this
    scheduled_events: tuple[tuple[str, str], ...] = (
        ("2026-09-04", "US nonfarm payrolls 08:30 ET"),
        ("2026-09-16", "FOMC decision 14:00 ET"),
    )

    # --- execution ---------------------------------------------------------
    # MEASURED: net-credit mleg limits filled 1 cent off mid on entry, 2 on exit.
    # Never send a market order across four legs.
    price_ladder_rungs: int = 5
    rung_wait_seconds: int = 20
    # MEASURED: 1.5% is the achievable BEST CASE at 16 delta; crossing the full
    # spread there is 8.3%. Reject a structure whose modelled cost exceeds this.
    max_cost_pct_of_credit: float = 0.08

    # --- session -----------------------------------------------------------
    # Market 09:30-16:00 ET. Avoid the first and last 15 minutes: spreads are
    # widest at the open (measured) and liquidity thins into the close.
    trade_window_start: time = time(9, 45)
    trade_window_end: time = time(15, 45)

    paper: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trade_window_start"] = self.trade_window_start.isoformat()
        d["trade_window_end"] = self.trade_window_end.isoformat()
        d["scheduled_events"] = [list(e) for e in self.scheduled_events]
        return d


DEFAULT = Config()
