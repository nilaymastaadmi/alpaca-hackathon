# RESULT: H3 robustness, attacking the result before believing it

Run 2026-08-19T14:59:54+00:00. Development window only, holdout sealed.

## Why this check exists

Three things in the H3 output looked wrong:

1. **Doubling transaction costs improved Sharpe** (+1.728 vs +1.614). Costs cannot help. Either the threshold fit reshuffles trades, or the fit is selecting noise.
2. **Fitted thresholds jumped between 0 and 5 in adjacent windows.** A parameter carrying real signal should show some stability.
3. **The regime gate hurt** (T3 +0.949 against a T1 baseline of +1.071), which cuts against H2.

Test: drop the optimiser entirely and run every FIXED threshold.

## Fixed-threshold results, no fitting anywhere

| trial | threshold | Sharpe | return | max DD | trades | refusal% |
|---|---|---|---|---|---|---|
| T1 baseline | 0.0 | +1.461 | +19.60% | -2.88% | 373 | 0.0% |
| T2 vrp gate | 0.0 | +1.447 | +15.73% | -2.66% | 282 | 61.1% |
| T2 vrp gate | 1.0 | +1.447 | +15.26% | -2.09% | 256 | 68.6% |
| T2 vrp gate | 2.0 | +1.250 | +12.59% | -2.85% | 224 | 76.2% |
| T2 vrp gate | 3.0 | +1.039 | +9.84% | -2.87% | 192 | 81.9% |
| T2 vrp gate | 4.0 | +0.983 | +7.33% | -1.93% | 141 | 88.9% |
| T2 vrp gate | 5.0 | +0.672 | +4.88% | -3.58% | 98 | 93.0% |
| T3 regime gate | 0.0 | +1.116 | +14.36% | -3.78% | 355 | 20.4% |
| T4 both gates | 0.0 | +1.417 | +15.12% | -3.34% | 270 | 64.7% |
| T4 both gates | 1.0 | +1.406 | +14.52% | -2.92% | 245 | 71.2% |
| T4 both gates | 2.0 | +1.155 | +10.77% | -2.54% | 214 | 78.1% |
| T4 both gates | 3.0 | +0.766 | +6.68% | -3.96% | 179 | 83.7% |
| T4 both gates | 4.0 | +1.023 | +6.97% | -1.43% | 125 | 90.5% |
| T4 both gates | 5.0 | +0.683 | +4.53% | -2.53% | 83 | 94.3% |
| T5 both, 10 delta | 0.0 | +1.845 | +14.91% | -1.39% | 293 | 62.8% |
| T5 both, 10 delta | 1.0 | +1.959 | +14.62% | -1.57% | 267 | 70.0% |
| T5 both, 10 delta | 2.0 | +2.025 | +13.56% | -1.36% | 233 | 76.9% |
| T5 both, 10 delta | 3.0 | +1.499 | +8.98% | -2.20% | 194 | 82.8% |
| T5 both, 10 delta | 4.0 | +0.879 | +4.83% | -2.47% | 135 | 89.9% |
| T5 both, 10 delta | 5.0 | +0.896 | +4.28% | -2.08% | 95 | 93.4% |
| T6 both, 21-45 DTE | 0.0 | +1.761 | +15.53% | -3.22% | 140 | 75.3% |
| T6 both, 21-45 DTE | 1.0 | +1.534 | +13.11% | -2.48% | 131 | 79.1% |
| T6 both, 21-45 DTE | 2.0 | +1.440 | +10.78% | -2.20% | 116 | 84.7% |
| T6 both, 21-45 DTE | 3.0 | +1.376 | +9.91% | -2.82% | 102 | 88.7% |
| T6 both, 21-45 DTE | 4.0 | +0.723 | +5.11% | -3.76% | 76 | 92.8% |
| T6 both, 21-45 DTE | 5.0 | +1.510 | +8.17% | -1.27% | 59 | 95.3% |

## Spread per trial

| trial | min Sharpe | median | max | spread |
|---|---|---|---|---|
| T1 baseline | +1.461 | +1.461 | +1.461 | 0.000 |
| T2 vrp gate | +0.672 | +1.144 | +1.447 | 0.775 |
| T3 regime gate | +1.116 | +1.116 | +1.116 | 0.000 |
| T4 both gates | +0.683 | +1.089 | +1.417 | 0.735 |
| T5 both, 10 delta | +0.879 | +1.672 | +2.025 | 1.146 |
| T6 both, 21-45 DTE | +0.723 | +1.475 | +1.761 | 1.039 |

## Year by year: T5 both, 10 delta at fixed threshold 0.0

| year | Sharpe | return | worst day | trades |
|---|---|---|---|---|
| 2016 | +2.702 | +2.85% | -0.42% | 37 |
| 2017 | +3.966 | +3.89% | -0.28% | 57 |
| 2018 | +0.873 | +1.07% | -0.42% | 34 |
| 2019 | +0.860 | +1.18% | -1.01% | 41 |
| 2020 | +1.659 | +1.78% | -0.55% | 44 |
| 2021 | +3.067 | +3.06% | -0.59% | 52 |
| 2022 | +0.324 | +0.25% | -0.30% | 28 |

Overall fixed-threshold Sharpe **+1.845**, return +14.91%, max drawdown -1.39%.

## What this implies for a 4.5 day live window

- trades per year: **42.4**
- expected trades in 4.5 trading days: **0.76**
- annualised return: **+2.03%**
- expected 4.5 day return: **+0.0363%**, about **$+36.32** on $100k

**The pre-registered sizing is statistically sound and produces almost no P&L in the hackathon window.** One position at a time, risking 1% of equity, with a high refusal rate, means the agent may not trade at all during the live week.

This is a DEPLOYMENT decision, not a backtest fix. Re-sizing now, after seeing these results, is precisely what pre-registration section 11 forbids. The choice belongs to Nilay and must be made on risk grounds and recorded as a deliberate deviation, not folded silently into the research.
