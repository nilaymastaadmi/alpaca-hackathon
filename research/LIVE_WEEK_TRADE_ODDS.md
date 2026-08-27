# Will the agent trade at all during the judged week?

Written 2026-08-27, one day before kickoff. This is the single most
important open question going into the live week, and it is not a
research question -- the research is settled. It is a deployment question
about whether the deployed threshold is calibrated for the volatility
regime the judged week will actually happen in.

## The problem, stated plainly

**The agent has never once decided to enter, across every cycle ever
logged.** 13 production artifacts (2026-08-20 to 2026-08-22) plus 9 D3
comparison cycle batches (2026-08-22 to 2026-08-27): every single one
refused. Gate 7 (VRP threshold) is the blocker in nearly all of them.

That is not a bug. The agent is doing exactly what it was built to do,
and "the edge is not there, so the agent trades rarely or not at all" is
explicitly a valid outcome under `PREREGISTRATION_R1.md` section 10. The
backtest agrees: at research sizing the expected number of trades across
a 4.5 day window was **0.76**, and D1's re-derivation put the deployed
config at roughly **one trade per week**, with about a third of weeks
seeing no entry at all.

**The tension is that P&L Performance is a judged criterion.** An agent
that refuses all week is intellectually honest and scores zero on that
axis.

## What the live data says about the odds

From `RECALIBRATION_STATUS.md`, the corrected-tenor VRP (the exact
quantity gate 7 acts on) across n=5 usable observations:

| | |
|---|---|
| mean VRP | **+0.114** vol points |
| sd | 0.623 |
| deployed threshold | **1.0** |
| threshold's distance from the mean | **1.42 sd** |

Treating each trading day as one draw from that distribution:

| | |
|---|---|
| P(a given day clears gate 7) | **~7.7%** |
| P(at least one entry across the 4.5 day window) | **~28 to 33%** |

**So roughly a two-in-three chance the agent places no trade at all
during the judged week**, if the current volatility regime holds.

### What lowering the threshold would do

| threshold | P(day clears) | P(>=1 entry in 5 days) |
|---|---|---|
| **1.0 (deployed)** | 7.7% | **33%** |
| 0.75 | 15.4% | 57% |
| 0.5 | 26.8% | 79% |
| 0.25 | 41.4% | 93% |
| 0.0 | 57.3% | 99% |

## How much to trust these numbers

**Not very much, and the reasons matter:**

1. **n=5.** That is a tiny sample for estimating a mean, let alone a
   variance. The sd of 0.623 could easily be off by a third in either
   direction, and every probability above moves with it.
2. **Normal approximation.** VRP is not normally distributed -- `RESULT_H1_H2.md`
   already established it has a fat left tail (5th percentile -7.20 in
   contango, -46.69 in backwardation). The right tail that matters here
   is less studied, so the true P(clear) could be higher than a normal
   fit suggests.
3. **The days are not independent.** Volatility regimes persist. A calm
   week stays calm. That makes the "at least one in 5 days" figure
   **optimistic**: if the regime is compressed on Monday it will probably
   still be compressed on Thursday, so the real number is likely lower
   than 33%, not higher.
4. **Current regime is unusually calm and may not persist.** Five
   observations from one late-August week say very little about what
   the first week of September does, and NFP lands inside the window
   (4 Sep), which is exactly the kind of event that can reprice
   volatility fast.

Point 3 is the one that should worry us most: it pushes the honest
estimate DOWN, not up.

## The decision this forces, and who owns it

**Not a research decision.** `PREREGISTRATION_R1.md` governs what may be
claimed as evidence, and nothing here changes any claim. This is a D4
deployment decision in the same family as D1 (sizing) and D2 (which
quantity gate 7 measures), and it belongs to Nilay with the numbers in
front of him.

The options, stated without picking one:

**A. Leave the threshold at 1.0.** The intellectually cleanest choice.
The agent trades only when volatility is genuinely rich by the standard
set before the week began. Accepts a roughly two-in-three chance of zero
P&L, and leans the submission on the refusal behaviour, the risk
architecture, and the research trail -- which are the genuinely strong
parts of this entry. The `README.md` framing ("An options agent that
refuses to trade") already tells this story well.

**B. Recalibrate the threshold from the measured data.** This is what D2
always said should happen ("re-derive `vrp_threshold` from it and record
that as its own dated entry"), and `RECALIBRATION_STATUS.md` is about to
cross into READY (half-width 0.594 against a 0.5 target, one or two more
nights). The honest version of this is NOT "lower it until it trades" --
it is deriving what threshold the original 1.0 was implicitly targeting
in a different vol regime, and setting the equivalent for this one. That
reasoning has to be written down BEFORE the number is chosen, or it is
just curve-fitting to get a trade.

**C. Something in between**, e.g. keep 1.0 but let the tail hedge and
the comparison candidates carry the demo, or adopt T7 (D3) whose shorter
tenor reads VRP differently.

## What must NOT happen

Picking a threshold on Monday because the agent has not traded yet, and
back-filling a justification. That is precisely the failure mode
`PREREGISTRATION_R1.md` section 11 exists to forbid, and it would
poison the most credible part of this submission -- the part a judge who
knows what they are looking at will actually respect. If the threshold
changes, it changes with its reasoning recorded first, dated, in
`DEPLOYMENT_DECISIONS.md` as D4.
