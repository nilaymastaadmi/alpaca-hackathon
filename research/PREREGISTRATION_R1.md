# PRE-REGISTRATION R1: volatility risk premium harvesting on SPY

**Committed 2026-08-19, before any backtest code exists and before any result has been seen.**

Provable from git history:

```bash
git log --diff-filter=A --format='%H %ad %s' -- research/PREREGISTRATION_R1.md backtest/
```

The pre-registration must appear strictly earlier than any file under `backtest/`. If it does
not, this document is worthless and should be treated as such.

## 0. Why this exists

Two prior projects by the same author died of the same disease, diagnosed from opposite
directions: `chikki` evaluated 54 trials on a 4.5 year window (bar needed ~1.7 Sharpe), and
`propdesk` R1/R2/R3 ran 68 cumulative trials and correctly refused to promote anything. The
lesson recorded there is exact: **few trials plus a long window is the fix, not a lower bar.**

This registration exists so that the hackathon submission can make an honest claim. The live
trading window is roughly 4.5 days (see `STRATEGY.md` section 1), which is far too short to
distinguish skill from luck. Without a pre-registered out-of-sample result, any live P&L is an
anecdote. With one, the live week becomes a single draw from a distribution that was
characterised in advance.

**The backtest does not predict the live week. It establishes whether the strategy has positive
expectancy at all, so that the live 4.5 days is a draw from a favourable distribution rather
than a coin flip.** Any submission language implying otherwise is overclaiming.

## 1. Data, and its provenance

| Input | Source | Coverage | Verified |
|---|---|---|---|
| SPY daily OHLC | Alpaca `/v2/stocks/bars` | 2016-01-04 to present, 2,659 bars | yes, 2026-08-19 |
| VIX daily OHLC | CBOE official CSV | 1990-01-02 to 2026-08-18, 9,254 rows | yes, 2026-08-19 |
| VIX3M daily OHLC | CBOE official CSV | 2009-09-18 to 2026-08-18, 4,255 rows | yes, 2026-08-19 |
| Historical option bars | Alpaca `/v1beta1/options/bars` | 2024 onward, per contract | yes, 2026-08-19 |
| Live option chain IV/greeks | Alpaca, collected daily by `prep/snapshot_iv.py` | 2026-08-19 onward | yes, running |

Binding overlap for the full strategy test: **2016-01-04 to 2026-08-18, 10.6 calendar years.**

CBOE is the primary source for VIX rather than a data aggregator. `propdesk` R1 recorded a
specific failure here: Yahoo reported one index's open as exactly the prior close on 99.0% of
rows, which silently voided two hypotheses. **A stale-data gate is therefore mandatory**: any
series whose open equals the prior close on more than 5% of rows is declared unusable and the
hypothesis depending on it is reported as untestable, not as failed.

## 2. Windows, fixed now

- **Development: 2016-01-04 to 2022-12-31, 7.0 years.** All fitting, all trials, all inspection.
- **Sealed holdout: 2023-01-01 to 2026-08-18, 3.6 years.** Not loaded, not plotted, not
  inspected until a development trial has cleared its bar. One shot only.

## 3. Hypotheses

**H1 (thesis test, needs no option pricing model).** Over the development window, the mean
volatility risk premium on SPY is positive, where VRP is defined as VIX close on day t minus the
subsequent realised volatility of SPY over the following 21 trading days, annualised.

**H2 (regime gate test, needs no option pricing model).** Mean VRP conditional on contango
(VIX / VIX3M < 1.0) exceeds mean VRP conditional on backwardation (ratio >= 1.0).

**H3 (strategy test, requires a pricing model, see section 6).** A defined-risk short-premium
strategy on SPY, gated per the trial definitions in section 4, sized per section 5, and charged
the measured transaction cost from section 7, produces a positive annualised Sharpe ratio net of
costs that clears the bar in section 8.

H1 and H2 are the load-bearing hypotheses because they require no modelling assumptions. H3 is
secondary and carries the caveats in section 6. **If H1 fails, H3 is not run at all.**

## 4. Trials, counted and fixed at SIX

Every trial the project runs counts toward the multiple-testing correction. Six is the total,
committed now. Each trial tests one design decision from `STRATEGY.md`, so this is a directed
test, not a parameter sweep.

| Trial | Configuration |
|---|---|
| T1 | Baseline. Sell whenever a position slot is free. No VRP gate, no regime gate. |
| T2 | VRP gate only |
| T3 | Regime gate only (VIX/VIX3M contango filter) |
| T4 | Both gates |
| T5 | Both gates, 10-delta short strikes instead of 16-delta |
| T6 | Both gates, 21 to 45 DTE instead of 7 to 14 DTE |

Fixed across all six trials, not fitted: underlying SPY, wing width $5, one position at a time,
exit at 50% of max profit or at 2 DTE, cost model from section 7.

**Exactly one parameter is fitted, and only inside in-sample windows: the VRP entry threshold**,
over a pre-committed grid of 0.0, 1.0, 2.0, 3.0, 4.0, 5.0 volatility points. Fitting one
parameter on a grid of six is the entire optimisation surface. Nothing else is tuned.

Walk-forward inside the development window: in-sample 252 trading days, out-of-sample 63 trading
days, step 63 days. The threshold is refit on each in-sample block and applied unchanged to the
following out-of-sample block. Reported development results are the concatenated out-of-sample
blocks only.

## 5. Sizing rule, fixed now

Risk per position is capped at 1.0% of account equity, where risk is defined as
`(wing width - credit received) x 100 x contracts`. Contracts are floored to an integer, minimum
1, and the position is skipped entirely if 1 contract would exceed the cap. One position at a
time, so maximum concurrent defined risk is 1.0% of equity.

This is deliberately small. `propdesk` established that sizing moves outcomes more than signal
quality does (vol targeting was worth roughly two Sharpe points there), and section 2 of
`STRATEGY.md` establishes that a blow-up is the main disqualifying risk in this competition
while a modest result is not.

## 6. Pricing model, and what it cannot do

Historical option chains with per-strike IV are not available for the development window. Option
prices are therefore **modelled**, using Black-Scholes with:

- Underlying: SPY close
- Implied vol level: VIX, scaled to the target tenor by the VIX/VIX3M term structure
- Skew: a parametric shape in log-moneyness, calibrated from the real chain snapshots being
  collected daily by `prep/snapshot_iv.py`, then applied historically scaled by VIX level
- Rate: constant 4.0%, dividends 1.2%

**Three limitations, stated before results are seen:**

1. **Skew is assumed stationary.** It is not. Skew steepens in stress, which makes short puts
   more expensive to hold than this model implies. **This biases H3 optimistically, exactly in
   the crashes that matter most.**
2. Modelled prices cannot reproduce real bid/ask dynamics or fill behaviour.
3. The skew calibration uses snapshots from August 2026 only, a single volatility regime.

**Mitigation, committed now:** the pricing model is validated against real Alpaca historical
option bars over 2024 onward before H3 is reported. If modelled prices deviate from actual traded
prices by more than 15% median absolute error on that sample, **H3 is reported as untestable
rather than as a result.** This is the same gate that `propdesk` applied when it declared H3
void rather than failed on stale data.

## 7. Cost model, measured rather than assumed

Round trip cost is charged at **1.5% of credit received**, taken from the live fill test run
2026-08-19 (entry filled $2.03 against $2.04 mid, exit $2.06 against $2.04 mid, on a real SPY
12 DTE condor). Full detail in `STRATEGY.md` section 4.

`propdesk` R2 recorded that its R1 cost assumption was roughly 5x wrong in the optimistic
direction, which is the single most dangerous class of backtest error. Two guards:

- **A sensitivity run at 3.0% round trip (double the measured cost) is mandatory** and reported
  alongside the headline number. If the result only survives at 1.5%, that is stated plainly.
- Gross and net results are always reported together. `propdesk` R2 found a strategy with gross
  Sharpe +4.26 and net -13.49; reporting either alone would have been a lie.

## 8. Success bars, computed now, before any result

Standard error of an annualised Sharpe ratio is `sqrt((1 + SR^2 / 2) / T)` with T in **calendar
years**. Note the absence of a frequency term: sampling more finely improves the volatility
estimate, not the drift estimate. This was corrected explicitly in `propdesk` R2 and is not
re-derived here.

**Development bar.** Six trials. Expected maximum of N draws under the null grows as
`sqrt(2 ln N)`; for N = 6 that is 1.893. At T = 7.0 years and an assumed SR near 0.5, SE = 0.401.

> **Development bar: annualised Sharpe >= 0.76, net of costs, on concatenated out-of-sample
> blocks.**

**Holdout bar.** Single shot, one-sided 5%, z = 1.645. At T = 3.6 years, SE = 0.559.

> **Holdout bar: annualised Sharpe >= 0.92, net of costs.**

**The holdout bar is higher than the development bar because the window is shorter. This is
correct, not an error.** Anything landing between 0.76 and 0.92 is expected to fail the holdout,
and that expectation is recorded here in advance.

Secondary metrics reported but **not** used as promotion gates: expectancy in R multiples, profit
factor, win rate, maximum drawdown, number of trades, percentage of days with no position.

## 9. Registered predictions

Stated in advance so that being wrong is recorded rather than quietly dropped. `propdesk` R3 got
3 of 4 right and recorded the miss; that record is worth more than a clean sheet.

- **P1.** H1 holds. Mean VRP is positive and lands between 2.0 and 4.0 volatility points,
  matching the published range.
- **P2.** H2 holds. VRP in contango exceeds VRP in backwardation by at least 1.0 volatility point.
- **P3.** Among T1 to T4, the best risk-adjusted result is T4 (both gates).
- **P4.** The gates improve Sharpe mainly by cutting drawdown, not by raising return. Specifically,
  T4 has lower total return than T1 but a higher Sharpe.
- **P5.** T6 (21 to 45 DTE) beats T4 on Sharpe as a general strategy, **and is still the wrong
  choice for the live window**, because a 4.5 day hold captures only 7 to 9% of a 42 DTE
  position's credit. If P5 holds, the live configuration stays 7 to 14 DTE anyway, and the
  reasoning is stated in the submission rather than hidden.
- **P6.** At least 30% of development days produce no position, because the VRP gate refuses.
  The refusal rate is a headline output, not a side effect.

## 10. Consequence rules, both directions

- **H1 fails** (mean VRP not positive): the thesis is dead. H2 and H3 are not run. Report the
  negative, and escalate the track decision to Nilay rather than substituting a different
  strategy silently.
- **H1 holds, no trial clears 0.76 on development**: nothing is promoted, the holdout is **not**
  touched, and the negative result is reported. The submission then leads with the refusal
  behaviour and the risk architecture, which is a legitimate entry.
- **A trial clears 0.76**: that single trial gets one shot at the holdout. No others.
- **Holdout fails 0.92**: reported as a failure. The strategy is **not** re-specified, the
  threshold is **not** re-fit, and no R2 is started on this data.
- **"The edge is not there, so the agent should trade rarely or not at all" is a valid reported
  result** and is not treated as a failed project.

## 11. What must not happen

1. Adding trials after seeing results without incrementing N and recomputing the bar.
2. Touching the sealed holdout more than once, or before a development trial clears.
3. Adjusting the cost model downward after seeing a result.
4. Reporting gross Sharpe without net alongside it.
5. Reporting a data artifact as evidence against a hypothesis. Void it instead, per section 1.
6. Letting the live week's outcome retroactively change anything written in this document.

---

## Amendment A1, written 2026-08-19 BEFORE any H3 trial was run

Recorded here rather than silently applied. No H3 result existed when this was
written, so none of it can be results-driven. Two changes and one clarification.

**A1.1 Wing width becomes a percentage of spot, not $5.** Section 4 fixed wing
width at $5. That was written against SPY near 770 and is wrong for a backtest
spanning 2016 to 2022, where SPY ranged roughly 180 to 470. A flat $5 wing is
2.8% of spot in 2016 and 0.65% in 2026, so it would silently change the strategy
across the sample. **Wing width becomes 0.65% of spot, rounded to the nearest $1
strike, minimum $1**, which equals $5 at SPY 770 and holds the economics constant.
Risk per position is capped at 1.0% of equity either way, so this affects
granularity, not risk.

**A1.2 The decision-time VRP signal uses TRAILING realised vol, not a HAR-RV
forecast.** H1 defines VRP against SUBSEQUENT realised vol, which is correct for
testing the thesis but is not available to a live agent. `STRATEGY.md` section
5.2 mentioned HAR-RV. Fitting HAR coefficients would add fitted parameters beyond
the single one this registration permits, so the strategy instead uses the
parameter-free proxy:

> `VRP_signal(t) = ATM_IV(t) - trailing 21 day realised vol(t)`, in vol points.

Uses only past data, adds no fitted parameters, and is the comparison most
practitioners actually make. HAR-RV may be revisited later as a separate
registered trial, not folded into this one.

**A1.3 Clarification: ATM_IV(t) means the VIX-corrected level**, per the
validation work in `RESULT_PRICING_GATE.md` (market ATM IV runs at 0.853 of VIX).
The raw VIX print is not the ATM implied vol and must not be used as one.

---

Author: Nilay Toshniwal. Registered 2026-08-19, before `backtest/` existed.
