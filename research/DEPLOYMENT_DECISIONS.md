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

**Corrected 2026-08-22.** This entry originally said "roughly 10 to 15 trades
and expected P&L to roughly +$700 to +$1,000" with no derivation shown. An
independent adversarial audit flagged that this does not reconcile with actual
trade-count math and proposed a wider, much more pessimistic range instead
(-$13,800 to +$1,400, ~13.5% probability of breaching the drawdown limit).
Rather than adopt either the original guess or the audit's unreproduced number,
re-derived it directly: ran the exact deployed configuration (5 concurrent, 3%
risk, threshold 1.0, both gates, 7-14 DTE) across the full 6.90-year
DEVELOPMENT window, then sliced the resulting trade list into every possible
overlapping 5-trading-session window and read the actual empirical
distribution. Script: `backtest/deployed_config_pnl_range.py`, reproducible.

**What that measured:**

| | |
|---|---|
| Total trades, deployed config, full dev window | 461 (66.8/year) |
| Windows with at least one trade entered | 67.8% of 1,737 |
| Median window P&L | $0 (a plurality of windows see no entry) |
| Mean window P&L | **+$207** |
| 5th to 95th percentile | **-$2,592 to +$1,886** |
| Worst of 1,737 empirical windows | **-$7,568** |
| Windows breaching -10% ($10,000) or -15% ($15,000) | **0 of 1,737 (0.0%)** |

**This does not match either the original guess or the audit's range, and the
gap with the audit specifically is worth stating rather than papering over.**
Two numbers disagree by an order of magnitude: the empirical worst window here
is -$7,568, the audit's proposed range extends to -$13,800; the empirical
breach rate here is 0%, the audit's was ~13.5%. Best available explanation:
this measures what actually happened along one realised 6.9 year price path
(an empirical backtest), while the audit's figures read as a broader
structural or stress-scenario estimate not tied to the specific sequence of
moves that occurred historically: a real distinction, since a finite
historical sample cannot contain every tail scenario that could occur, only
the ones that did. Both framings have a legitimate claim: this section's
numbers are reproducible and grounded in what the strategy actually would have
done; a structural worst-case bound (below) is not sample-dependent at all.
**Neither should be read as a forecast for the specific live week.**

**Trade count corrected too.** Not "10 to 15 trades": closer to 1 trade
entered per week on average (66.8/year over a 5.5-week trading month), highly
irregular, with roughly a third of any given week seeing no entry at all.

### Risk accepted, stated plainly

**Worst case is -15% of equity, and this part did not change.** It is a hard
STRUCTURAL bound, not a probability estimate: defined by position sizing
(5 x 3%) and the long wings, which cap loss per contract regardless of how bad
the move gets. It does not depend on the historical sample the way the table
above does. All five positions sit on the same underlying in the same
direction: short volatility positions are highly correlated, a single large
adverse move takes all five to max loss together, and there is no
diversification between them, only staggering.

That hard cap has never been empirically approached: 0 of 1,737 historical
windows came within half of the -10% gate-2 threshold, let alone -15%. That is
reassuring but not proof of safety going forward: 6.9 years is a short sample
for tail events by construction (the same lesson propdesk's power analysis
already paid for), and the live week is one draw, not a resample of history.

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

---

## D2. Gate 7 measures the traded strikes, not a 30-day ATM proxy; threshold stays provisional

**Found by the 2026-08-20 adversarial audit, fixed 2026-08-22.**

### The bug

Gate 7 computed VRP as `ATM_IV(~29 DTE) - trailing_RV`. The agent sells ~16
delta strikes at 7-14 DTE. Those are different tenors and different strikes,
and the gap between them is not noise.

Measured live, same moment, same underlying: ATM IV at 29 DTE read **13.165**;
the actual short strikes at 11 DTE read **12.135**. A **+1.03 vol point bias**,
against a threshold of 1.0. The gate was reading the entire threshold's worth of
false richness on every evaluation.

**The bias is structural, not incidental.** Gate 6 requires contango, which by
definition means the curve slopes upward with tenor. A longer-dated ATM read
will therefore be biased rich relative to a shorter-dated, further-OTM one on
every single day the regime gate is satisfied. This was never going to average
out; it runs the same direction every time gate 6 passes.

### The fix

`signals.short_strike_iv()` measures IV from the actual call and actual put
the strategy would sell (nearest `short_delta`, at the expiry nearest
`dte_target`), the same selection `broker.build_condor` uses. Gate 7 now takes
that value directly. **When it cannot be measured (no two-sided quotes at the
traded tenor), gate 7 refuses rather than falling back to the old ATM number**;
falling back would silently reintroduce the exact bias this fix removes.

Verified live 2026-08-22 against the real MCP server: short-strike VRP read
**-1.01**, against the old ATM-based reading of **+0.00** at the same moment.
Both happened to refuse today, for genuinely different reasons and different
margins, which is itself confirmation the fix changed what is measured rather
than just relabelling it.

### What is decided and what is not

**Decided:** the measurement is fixed. This is a correctness fix, not a
judgement call, and needed no sign-off.

**Not decided: the threshold value.** `vrp_threshold` stays at 1.0, carried
over unchanged from before the fix. That number was never derived against the
corrected quantity, because no calibration history existed at the 7-14 DTE
tenor when this was fixed: `prep/snapshot_iv.py` only started collecting that
range on 2026-08-20. Re-basing the threshold from real data (rather than
guessing a new number) needs a few more nights of the corrected logger to
accumulate before kickoff on 2026-08-28.

**Deliberately not guessed at.** Inventing a new threshold now, without data,
would repeat exactly the mistake this project has avoided everywhere else:
asserting a number because it seems reasonable rather than because it was
measured. 1.0 unchanged is the safe direction to be wrong in: a threshold set
too high costs trades, not money, which is a mispricing risk this agent is
built to prefer over the alternative.

**Action item, not yet done:** once enough nights of 7-14 DTE history exist,
re-derive `vrp_threshold` from it and record that as its own dated entry here,
on the same footing as this one.

**Tooling added 2026-08-22, not the recalibration itself:**
`prep/recalibrate_threshold.py` checks readiness on every run (safe to run
nightly) and writes `research/RECALIBRATION_STATUS.md`. It measures the
exact quantity gate 7 uses live, defines "enough data" as a 90% CI half-width
under 0.5 vol points (half of `engine.THRESHOLD_GRID`'s own step size), and
deliberately stops at READY/NOT READY -- it never proposes a number or
writes to `config.py`. As of 2026-08-22: **NOT READY, 1 usable sample.**
`vrp_threshold` stays at 1.0.

---

## D3. DECIDED 2026-08-30: switch deployed tenor from T4 (7-14 DTE) to T6 (21-45 DTE)

**Superseded its own earlier conclusion. Originally proposed T7 (5-10 DTE) on
2026-08-22, based on the backtest alone. Eight more days of real live-market
comparison data (`research/D3_COMPARISON_LOG.md`, `agent/agent.py --compare`)
changed the answer. Both the original T7 analysis and the reasoning that
overturned it are kept below, in order, rather than rewritten as if T6 were
obvious from the start.**

### What was tested and why

The live agent deploys T4 (7-14 DTE) over the backtest-best T6 (21-45 DTE)
because a 4.5 day hold captures only 7-9% of a 42 DTE position's credit decay
(`STRATEGY.md` section 4, registered prediction P5). The same reasoning runs
the other direction and had never been tested: a tenor SHORTER than T4 would
capture a LARGER fraction of its own credit in the same 4.5 day window.

Amendment A3 (`PREREGISTRATION_R1.md`) registered T7 (5-10 DTE, both gates,
otherwise identical to T4) BEFORE running it, recomputed the multiple-testing
bar from N=6 to N=7 (0.760 to 0.792, checked against T1-T6 before T7 ran --
no existing verdict flipped), and stated three falsifiable predictions in
advance. Full result: `RESULT_H3_T7.md`.

### What it found

| | T4 (deployed) | T7 (proposed) |
|---|---|---|
| DTE band | 7-14 | 5-10 |
| Out-of-sample Sharpe | +1.201 | **+1.697** (best of all 7 trials) |
| Total return | +9.30% | +17.60% |
| Max drawdown | -3.10% | -3.64% |
| Trades | 165 | 180 |
| Win rate | 78.2% | 89.4% |
| Sharpe under 2x cost | not re-tested for T4 alone at this cut | +1.579 (falls, the normal direction) |

All three registered predictions came out CORRECT:
- **P7** (T7 beats T4 on Sharpe): yes, by a wide margin.
- **P8** (T7's drawdown stays clear of the confirmed-bad 0-3 DTE zone's
  -5.55%, defined as no worse than -4.65%): yes, -3.64%, in the same
  neighbourhood as every other non-0-3-DTE tenor bucket.
- **P9** (T7's Sharpe falls under double-cost stress, unlike T6's anomalous
  rise): yes. This is actually a better robustness signature than T6's
  headline result had -- T6's Sharpe RISING under higher costs was flagged
  in `RESULT_H3_ROBUSTNESS.md` as evidence its optimiser was partly selecting
  noise. T7 does not show that flag.

Per amendment A3's holdout-shot governance, **T7 now stands as the sole
nominee for the one holdout shot**, replacing T6. The holdout itself remains
SEALED -- nothing above touches it, and this proposal does not require
touching it either.

### Why this is NOT auto-applied

1. **It is one development-window walk-forward result**, not a holdout
   confirmation. The whole point of the sealed holdout is that a development
   pass, however clean, is not yet evidence a strategy survives fresh data.
2. **Changing the live tenor changes what actually trades real (paper)
   money in the judged window.** That is exactly the kind of call D1 and D2
   were, made deliberately with numbers in front of the decision-maker, not
   applied automatically because a script produced a bigger number.
3. Operationally, 5-10 DTE fits the 4.5 day live window BETTER than 7-14
   does (a bigger fraction of a shorter position's decay is captured), which
   is a real reason beyond the Sharpe number -- but it also means T7 was
   chosen partly because it should look good in a short live window, which
   is worth being honest about rather than presenting as pure luck.

### If adopted

Changes needed: `agent/config.py` `dte_min=7`->`5`, `dte_max=14`->`10`,
`dte_target=10`->`8`. `short_delta` unchanged (T7 holds it fixed at 0.16 to
isolate tenor as the only variable). Everything else in D1 (5 concurrent,
3% risk each) and D2 (gate 7 measuring the actual traded strikes) is
unaffected by this and would carry over unchanged.

### What changed: eight more days of real evidence

The proposal above was correct that this needed live data, not just a
backtest, before being decided. `agent/agent.py --compare-all` ran T4, T6 and
T7 side by side, hourly, against the real market, from 22 to 29 Aug (21
comparable cycles, 5 separate trading days, none of it touching real orders).

| | T4 (was deployed) | T6 | T7 (proposed above) |
|---|---|---|---|
| Would-enter cycles | **0 / 21** | **10 / 21** | 1 / 21 |
| Days with at least one entry | 0 / 5 | 2 / 5 (the two most recent) | 1 / 5 |
| Gate 7 pass rate, last 2 days | 0% | **100% (13/13)** | 8% (1/13) |
| VRP trend, last 2 days | falling further negative | **+1.0 to +2.8, climbing** | flat near zero |

T7's backtest case (Sharpe +1.697, best of 7, no cost-sensitivity anomaly)
is unchanged and still correct on its own terms. It simply has not been
where the live market's richness actually showed up: 1 real signal in 21
cycles is not meaningfully different from T4's 0. T6 -- the trial passed
over in 2026-08-19's original deployment choice for capturing too little of
its own credit in a short window -- is the one that has actually been
firing, repeatedly, on both of the two most recent real trading days.

### Why this matters more than the backtest ranking

The hackathon's own P&L Performance criterion reads: "Judges will consider
the project's P&L **and how effectively the strategy performs through its
trading activity**." An agent that never trades cannot demonstrate that,
whatever its research says. `research/LIVE_WEEK_TRADE_ODDS.md` already put
T4's odds of even one entry across the judged week at 28-33%; 0-for-21 real
cycles since is consistent with the pessimistic end of that, not a
statistical fluke this project's own discipline should wave away.

### The honest cost of switching, not hidden

1. **T6 carries the cost-sensitivity anomaly** `RESULT_H3_ROBUSTNESS.md`
   flagged: doubling transaction costs improved its backtested Sharpe
   (+1.614 to +1.728), which is only possible if its threshold fit is
   partly selecting noise rather than a clean edge. This was the reason T7
   looked like the safer upgrade over T6 in the first proposal. It is still
   true. It has not stopped T6 from being the one that actually trades.
2. **A 21-45 DTE position will not reach natural expiry inside the judged
   week under any realistic entry timing.** T4 and T7's shorter holds at
   least had a chance of a natural profit-target or DTE exit before 4 Sep;
   T6's cannot. Left alone, the number judges see would be a mark-to-market
   snapshot of an open position, not a realised result.
3. Mitigated, not ignored: found the same day, `event_derisk_fraction` in
   `agent/config.py` existed to handle exactly this class of problem and
   was never wired to an action -- gate 8 blocked new entries near a
   scheduled event but nothing ever reduced an existing one, the same
   "the gate's message overpromises what the code does" bug the drawdown
   breaker's flatten already fixed once, in a different gate. Fixed
   properly this time with a dedicated mechanism rather than reusing gate
   8's event-derisk path: `deadline_flatten_enabled` forces a full,
   unconditional flatten of every open position starting 90 minutes before
   the 4 Sep 11:00 ET submission deadline (market open on the deadline day,
   using the whole available window rather than one attempt at the buzzer),
   and blocks all new entries once that window has started. Tested in
   `tests/test_deadline_flatten.py`; the actual close mechanics reuse
   `_flatten_all`, already covered by `tests/test_flatten.py`.

### Decision

**Adopt T6.** `agent/config.py`: `dte_min=7`->`21`, `dte_max=14`->`45`,
`dte_target=10`->`33`. `short_delta` unchanged at 0.16. D1's sizing (5
concurrent, 3% risk each) and D2's gate-7 fix are unaffected and carry over
unchanged. The deadline-flatten mechanism above ships in the same change,
since deploying a longer-duration tenor without it would be deploying only
half of what this decision actually requires.

This can be revisited if the live week's own early data disagrees with the
comparison harness's read -- the harness keeps running throughout the week
regardless of what is deployed, so that disagreement would be visible, not
silent.


## D4. DECIDED 2026-09-02: freeze all new risk from the flatten window onwards, with no end

**What was found.** The deadline flatten (D3) opens a 1.5 hour window before
the 11:00 ET submission deadline in which every cycle flattens and no entry is
considered. Two gaps, both found while answering "does Alpaca's index-options
announcement change anything":

1. The window is bounded, deliberately, so it does not retrigger closes after
   judging. But the scheduled task fires daily and the Friday session runs to
   16:20 ET, so from 11:00 ET the window test went false and the agent would
   have resumed opening positions after judging, changing the account a judge
   may read days later.
2. The tail hedge ran before the deadline logic and outside it. A hedge bought
   inside the window, or after the deadline, is a position the flatten never
   sells, so it would sit unrealised on the judged number.

**Decision.** `_entries_frozen(cfg, now)` is true from the start of the flatten
window onwards and never turns false again while the deadline mechanism is
enabled. New entries and new hedge buys both check it. The flatten window's
own bound is unchanged. Four tests added. The hedge window (21 to 45 DTE)
stays as it was; see RISK_REGISTER 4.9 for why widening it two sessions before
the deadline is the wrong trade.

**After Friday.** The Windows task keeps its daily trigger through the weekend
only until it is given an end boundary on Thursday morning while idle; the
freeze above is the safety net if that step is missed.

