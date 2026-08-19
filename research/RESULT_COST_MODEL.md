# RESULT: cost model test

Run 2026-08-19T18:30:32+00:00.

## The question

The exploratory sweep showed Sharpe rising monotonically as short-strike delta falls. Monotonic trends usually indicate structure. But we charge transaction cost as **1.5% of credit**, while real option spreads are closer to a fixed number of cents per leg. Far-OTM structures collect much less credit, so a fixed-cents cost is a far larger percentage for them. That alone would manufacture the same trend for a bad reason.

## Measured spreads, live SPY chain 7-14 DTE, spot 769.77

| delta bucket | n | median mid | median spread | half spread | spread % of mid |
|---|---|---|---|---|---|
| ~0.05 | 405 | $0.11 | $0.01 | $0.005 | 13.3% |
| ~0.10 | 51 | $0.83 | $0.02 | $0.010 | 2.0% |
| ~0.16 | 41 | $1.39 | $0.02 | $0.010 | 1.3% |
| ~0.25 | 39 | $2.24 | $0.02 | $0.010 | 1.0% |
| ~0.35 | 48 | $3.65 | $0.03 | $0.015 | 0.8% |

**The spread as a percentage of the option's own price rises sharply as you go further out of the money.** That is the mechanism the original cost model missed.

Historical spreads scaled by mean development spot / today's spot (0.404), since spreads scale roughly with price level and SPY ranged 180 to 470 over the window against 770 today.

## Delta sweep under both cost models

| delta | median credit | realistic round trip | as % of credit | Sharpe (1.5% model) | Sharpe (realistic) |
|---|---|---|---|---|---|
| 0.05 | $0.10 | $0.016 | 16.0% | +2.056 | **+1.591** |
| 0.10 | $0.23 | $0.032 | 13.9% | +2.025 | **+1.533** |
| 0.16 | $0.39 | $0.032 | 8.3% | +1.155 | **+0.896** |
| 0.25 | $0.70 | $0.032 | 4.6% | +1.046 | **+0.905** |
| 0.35 | $1.07 | $0.048 | 4.5% | +0.814 | **+0.628** |

## Verdict: the trend BREAKS

The apparent advantage of far-OTM strikes was substantially manufactured by the cost model. Under realistic costs it does not hold. **Do not deploy far-OTM strikes on the strength of the sweep**, and treat the 1.5% round-trip figure as valid only near the 16 delta strikes it was measured on.

---

## Correction and the real conclusion

The automated monotonic verdict printed on the first run was driven by a
**bucketing bug, not a market fact**: the top delta bucket spanned 0.30 to 1.00
and swept in deep ITM contracts, whose spreads are large in absolute terms and
which this strategy never sells. That produced an $8.24 round trip and a -92%
result. Bucket now capped at 0.45 delta. The corrected picture:

| delta | median option price | median spread | **spread as % of its own price** |
|---|---|---|---|
| ~0.05 | $0.11 | $0.01 | **13.3%** |
| ~0.10 | $0.83 | $0.02 | 2.0% |
| ~0.16 | $1.39 | $0.02 | 1.3% |
| ~0.25 | $2.24 | $0.02 | 1.0% |
| ~0.35 | $3.65 | $0.03 | 0.8% |

**The spread as a fraction of the option's own price rises 16x from 35 delta to
5 delta.** The hypothesis was right: the original cost model did systematically
under-charge the configurations that looked best.

### What survives

Under realistic fixed-cents costs the far-OTM advantage **shrinks but does not
vanish**: 5 delta falls from +2.056 to +1.591, 10 delta from +2.025 to +1.533,
and both still beat 16 delta at +0.896. So the direction of the finding holds
and its magnitude was overstated by roughly 30%.

### The more important correction, which affects everything

At 16 delta the spread-crossing cost is **8.3% of credit**, but the live fill
test measured **1.5%**. Both are right, and the gap is the whole point:

- 8.3% assumes crossing the full half-spread on all four legs.
- 1.5% is what we actually achieved, because net-credit `mleg` limits filled
  one cent off mid.

**So 1.5% is the achievable best case, not the cost.** Treat the cost model as a
RANGE of 1.5% to 8.3% at 16 delta, not a point estimate, and expect the top of
that range in stressed markets when mid fills stop happening.

### Why this specifically kills far-OTM strikes for deployment

A 5 delta option trades at $0.11 with a $0.01 spread. The minimum tick IS the
spread, so "filling near mid" is not available: you are either at the bid or at
the ask, and one tick is 9% of the contract's value. **The near-mid execution
advantage we measured at 16 delta does not extend to 5 delta, because tick size
dominates.** The backtest cannot see this, because it models prices continuously.

Deploy at 16 delta, where the measured fill behaviour actually applies.
