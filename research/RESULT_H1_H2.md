# RESULT: R1 hypotheses H1 and H2

Run 2026-08-19T14:31:32+00:00. Development window 2016-01-04 to 2022-12-31 (6.99 calendar years). Holdout sealed and verified unreadable.

Design fixed in advance: `research/PREREGISTRATION_R1.md`.

## H1: mean VRP > 0

- observations: 1741
- mean VRP: **+3.68 vol points**, sd 8.46
- naive t: +18.16 (INVALID here, overlapping windows)
- Newey-West t (21 lags): **+4.74**, one-sided p=0.0000
- verdict: **H1 HOLDS**
- registered prediction P1 (mean in 2.0 to 4.0 pts): **CORRECT**

The naive t is reported only to show why it must not be used. 21-day forward windows sampled daily overlap by 20/21, so the independent-observation assumption fails and significance is overstated by roughly sqrt(21).

## H2: VRP in contango > VRP in backwardation

- contango: 1588 days (91.2%), mean VRP **+3.74** pts, NW t +6.13
- backwardation: 153 days, mean VRP **+3.14** pts, NW t +0.72
- gap: **+0.59 vol points**
- verdict: **H2 HOLDS**
- registered prediction P2 (gap >= 1.0 pt): **WRONG**, measured +0.59

## The finding that actually matters, and it is not the mean

P2 was WRONG: the mean gap is only +0.59 vol points, not the 1.0 predicted. Recording the miss rather than dropping it. But the mean is the wrong statistic here, and the distribution shows why.

| | contango | backwardation |
|---|---|---|
| median VRP | +4.76 | **+6.55** |
| 5th percentile | -7.20 | **-46.69** |
| worst | -60.65 | -59.41 |
| days with VRP < -10 pts | 3.1% | **9.8%** |
| Newey-West t | **+6.13** | +0.72 |

**Selling premium in backwardation looks BETTER on the median (+6.55 vs +4.76) and is far worse in the tail (-46.69 vs -7.20 at the 5th percentile).** That is the short-volatility payoff shape in one table: collect a little more, most of the time, then lose enormously.

**The stronger justification for the regime gate is significance, not the mean.** VRP in contango has Newey-West t = +6.13, comfortably significant. In backwardation t = +0.72, which is indistinguishable from zero. So the honest statement is not "contango pays more" but **"VRP is only reliably present in contango"**.

### The caveat that stops this being oversold

The worst observations in BOTH regimes are of similar size (-60.65 contango, -59.41 backwardation), and they are the same event: the February to March 2020 crash. **A crash begins while the term structure is still in contango.** The regime gate therefore reacts, it does not predict. It cannot protect against day one of a shock; what it does is stop the agent from staying short volatility through the rest of it. Any submission language implying the gate anticipates crashes is false.

This is also why the defined-risk structure is not optional. The gate handles the regime; the long wings handle the day the gate is late.
