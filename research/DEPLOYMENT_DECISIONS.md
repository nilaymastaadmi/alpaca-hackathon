# DEPLOYMENT DECISIONS

Choices about how the LIVE agent is run, as distinct from how the research was
conducted. Kept separate from `PREREGISTRATION_R1.md` on purpose: the
pre-registration governs what may be claimed as evidence, this file governs what
gets deployed. Mixing them is how a backtest quietly becomes a sales document.

Every entry records the decision, who made it, when, what was known at the time,
and what risk was accepted.

---

## D1. Live sizing: 5 concurrent positions at 3% risk each

**Decided by Nilay, 2026-08-19, after seeing the H3 and robustness results.**

### The deviation

| | Pre-registered (research) | Deployed (live week) |
|---|---|---|
| Risk per position | 1.0% of equity | **3.0% of equity** |
| Concurrent positions | 1 | **5** |
| Max concurrent defined risk | 1.0% | **15.0%** |

The backtest in `RESULT_H3.md` was run at the registered sizing and is **not**
re-run at the deployed sizing to produce a better headline number. Section 11 of
the pre-registration forbids that, and the separation is the point: the research
validated the *edge*, this decision sets the *risk*.

### Why

At the registered sizing the strategy expects **0.76 trades and about +$36 on
$100k** across the 4.5 day live window (`RESULT_H3_ROBUSTNESS.md`). Two problems,
and the second is worse than the first:

1. P&L Performance is a judged criterion and $36 is indistinguishable from zero.
2. **The agent might place no trades at all**, leaving nothing to demonstrate for
   Technology Implementation or Presentation. An autonomous trading agent that
   never trades is a failed demo regardless of how good the reasoning is.

Scaling to 5 concurrent at 3% raises expected activity to roughly 10 to 15 trades
and expected P&L to roughly +$700 to +$1,000.

### Risk accepted, stated plainly

**Worst case is -15% of equity**, and it is a realistic tail rather than a
theoretical one, because all positions sit on the same underlying in the same
direction. Short volatility positions are highly correlated: a single large
adverse move takes all five to max loss together. There is no diversification
between them, only staggering.

Probability of a large enough SPY move inside a specific 4.5 day window is roughly
10 to 15%. A realistic bad week is -5% to -10%; -15% requires everything to break
at once. The loss is hard-capped by the long wings and cannot exceed it.

This was chosen with those numbers in front of the decision-maker. It is not drift.

### Consequences for the build, which are not optional at this size

Three things that were merely planned become load-bearing:

1. **The engine currently supports one position at a time.** `engine.run_strategy`
   holds a single `pos` object. Multi-position support is a real code change, not
   a config flag, and it must include per-position tracking for the audit trail.
2. **The portfolio-level daily loss limit and drawdown circuit breaker stop being
   decorative.** At 1% concurrent risk they were nearly unreachable. At 15% they
   are the primary defence and must actually fire. Both need tests that prove they
   halt trading, not just that they compute a number.
3. **Staggering entries across expiries becomes a risk control, not a preference.**
   Five positions opened the same day on the same expiry is one position at 15%
   wearing a costume.

### How this gets argued in the submission

Do not hide it and do not dress it up. The honest framing is the strong one:

> The research was conducted at 1% risk per position and validated there. For the
> live week we deliberately raised sizing to 5 concurrent positions at 3% each,
> accepting a hard-capped 15% worst case, because at research sizing the agent
> expected fewer than one trade across the judging window. That is a risk decision
> made with the numbers in front of us, recorded before the week started, and
> deliberately kept out of the backtest so the reported Sharpe stays the one we
> pre-registered.

Judges who know what they are looking at will find the separation more convincing
than a single flattering number would have been.

### Still open

Whether the regime gate stays on. The robustness work found it costs average
Sharpe but cuts max drawdown roughly 3x (-4.38% to -1.39% at research sizing) and
stood the strategy down through the March 2020 backwardation. **At 15% concurrent
risk the tail protection is worth more than it was at 1%**, so the argument for
keeping it is stronger now than the Sharpe comparison alone suggests. Not decided
here.
