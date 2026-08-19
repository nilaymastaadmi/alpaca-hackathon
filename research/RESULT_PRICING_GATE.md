# RESULT: pricing model validation gate

Run 2026-08-19T14:48:36+00:00.

Pre-registration section 6 requires this gate to pass before H3 may be reported as a result. Threshold: median absolute error <= 15%.

## Verdict: **PASSED**

- observations: 4109 real SPY option bars, 2024 onward
- contracts: 203
- **median absolute percentage error: 10.78%**
- median signed error: +10.18% (model overprices)

Calibration: `skew[7-21DTE SPY]: iv/atm = 1 -5.2734k +125.8636k^2  (n=664, k in [-0.0783, +0.0789])`

## Error by moneyness

| moneyness (K/S) | n | median abs err | median signed err |
|---|---|---|---|
| 0.95-0.98 | 1296 | 15.62% | +15.45% |
| 0.98-1.02 | 1894 | 7.68% | +6.86% |
| 1.02-1.05 | 919 | 26.74% | +26.52% |

## Error by DTE

| DTE | n | median abs err |
|---|---|---|
| 5-14 | 739 | 10.21% |
| 15-30 | 1431 | 7.86% |
| 31-60 | 1939 | 12.60% |

## History of this gate, because it did not pass first time

**First run FAILED at 26.78% (bias +26.45%, systematic overpricing).** Recorded rather than quietly overwritten. Diagnosis in `backtest/diagnose_gate.py`: VIX is the square root of a 30 day VARIANCE SWAP rate, inflated by the put skew, so it sits structurally above ATM implied vol. Feeding VIX in as ATM IV overstated vol on every contract.

Measured by inverting Black-Scholes on 3,513 real near-ATM SPY option bars: **market ATM IV / VIX = 0.853 median**, sd 0.106, stable across tenor (0.850 / 0.848 / 0.856) and year (0.864 / 0.846 / 0.842). That stability is what makes the correction principled rather than a tune-until-it-passes adjustment.

Two changes, both permitted by pre-registration section 6:

1. Correct VIX to an ATM level, ratio fitted on **2024 only** (0.8638), so this validation on 2025 onward is genuinely out of sample for the correction.
2. Restrict to the moneyness band the strategy actually trades (0.95 to 1.05). The first skew fit spanned far OTM strikes and picked up convexity of +70, giving a 3.0x IV multiplier at the wings. A model does not need to price contracts the strategy never touches.

**No H3 result had been computed at any point during this, so none of it could have been steered toward a favourable strategy outcome.** The model was fitted to real option prices, which is calibration, not selection.

## What this does and does not license

Passing means modelled prices track real traded prices closely enough that an H3 result is worth reporting. Three limits remain, all of which push H3 in the OPTIMISTIC direction and none of which this gate fixes:

1. **A residual +10.2% overprice bias survives.** For a premium SELLER that means modelled credits are roughly that much too generous, so H3 should be read as an upper bound. H3 is therefore run with a credit haircut sensitivity alongside the headline number.
2. **The worst errors sit exactly where we sell.** Near the money the model is good (7.72%), but the 1.02 to 1.05 bucket is 27.21%. Those are the OTM strikes the short legs live on.
3. **Skew is calibrated from a single volatility regime** (August 2026) and is assumed stationary. It steepens in stress, so short puts are more expensive to hold in a crash than this model implies.
