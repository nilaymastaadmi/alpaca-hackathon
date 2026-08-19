# RESULT: R1 hypothesis H3

Run 2026-08-19T14:55:35+00:00. Development window 2016-01-04 to 2022-12-31 (6.99 years). Holdout sealed and verified unreadable by the run itself.

Walk-forward: in-sample 252 days, out-of-sample 63 days, step 63. The VRP entry threshold is the only fitted quantity, chosen on in-sample blocks and applied unchanged to the next out-of-sample block. **Every number below is out-of-sample.**

Pricing: `skew[7-21DTE SPY]: iv/atm = 1 -5.2734k +125.8636k^2  (n=664, k in [-0.0783, +0.0789])`, gated at `research/RESULT_PRICING_GATE.md`. Costs 1.5% of credit round trip, measured from a live fill test.

## Bar

- trials: 6 (fixed in advance)
- E[max under null] = sqrt(2 ln 6) = 1.893
- SE(Sharpe) at 6.99y = 0.401
- **development bar = 0.760**

## Results, out-of-sample, ranked

| trial | Sharpe | return | max DD | trades | win% | PF | expectancy | refusal% |
|---|---|---|---|---|---|---|---|---|
| T6 both, 21-45 DTE | **+1.614** | +9.70% | -2.89% | 83 | 89.2% | 3.38 | +0.132R | 88.1% |
| T5 both, 10 delta | **+1.515** | +7.51% | -1.95% | 188 | 88.8% | 2.18 | +0.044R | 76.5% |
| T2 vrp gate | **+1.392** | +11.34% | -2.51% | 179 | 78.8% | 1.94 | +0.060R | 76.5% |
| T4 both gates | **+1.201** | +9.30% | -3.10% | 165 | 78.2% | 1.85 | +0.056R | 79.2% |
| T1 baseline | **+1.071** | +11.85% | -4.38% | 310 | 73.5% | 1.48 | +0.038R | 0.0% |
| T3 regime gate | **+0.949** | +9.89% | -3.51% | 293 | 73.4% | 1.43 | +0.034R | 23.0% |

**Best: T6 both, 21-45 DTE at Sharpe +1.614 against a bar of 0.760. VERDICT: CLEARS.**

## Sensitivity

Section 7 requires a run at double the measured cost. The credit haircut additionally removes the pricing model's known residual overprice bias, which for a premium seller inflates credits.

| scenario | Sharpe | return |
|---|---|---|
| measured cost 1.5%, no haircut | +1.614 | +9.70% |
| double cost 3.0% | +1.728 | +9.88% |
| credit haircut 10% (model overprices) | +1.576 | +8.63% |
| both | +1.474 | +8.00% |

## Consequence

Section 10: a trial cleared the bar, so **T6 both, 21-45 DTE earns exactly one shot at the sealed holdout**. No other trial may be taken there, and the threshold may not be re-fitted first.

---

## READ THIS BEFORE QUOTING THE NUMBER ABOVE

`RESULT_H3_ROBUSTNESS.md` attacks this result and finds it fragile. Four things
qualify the headline, and none of them were visible from the walk-forward alone:

1. **Doubling transaction costs IMPROVED Sharpe** (+1.728 vs +1.614). Costs cannot
   help. The threshold fit is reshuffling trades, which means the optimiser is
   partly selecting noise.
2. **Fixed-threshold Sharpe varies by up to 1.15** across the grid on a single
   trial. The walk-forward reports one point from a wide, unstable distribution.
3. **The ungated baseline beats the gated variants at matched delta and tenor.**
   T1 (no gates) scores +1.461 fixed, above T4's median +1.089 and above T4 at
   every threshold except its best (+1.417). **On this sample the gates do not
   earn their place on average.**
4. **But the gates do cut tail risk**: max drawdown falls from -4.38% (T1) to
   -1.39% (T5), roughly 3x, and the regime gate stood the strategy down through
   the March 2020 backwardation. That is registered prediction P4's mechanism
   working (drawdown, not return), except that Sharpe did not improve with it.

**Honest reading: the edge is real (H1 is decisive at Newey-West t +4.74), the
defined-risk structure is doing most of the protective work, and the gates buy
drawdown reduction at a cost in average Sharpe.** Whether that trade is worth
making is a risk judgement, not something this backtest settles.

## The finding that matters most for the hackathon

At the pre-registered sizing (1% risk per position, one position at a time):

- trades per year: **42.4**
- expected trades in the 4.5 day live window: **0.76**
- annualised return: **+2.03%**
- **expected P&L over the live window: about +$36 on $100,000**

**The strategy is statistically sound and produces approximately zero P&L in the
window the judges actually measure.** It may not place a single trade.

This is a DEPLOYMENT decision, not a backtest fix. Re-sizing now, after seeing
these results, is exactly what pre-registration section 11 forbids. It has to be
made deliberately, on risk grounds, recorded as a conscious deviation, and
argued in the submission rather than hidden.
