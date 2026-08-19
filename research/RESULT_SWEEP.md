# RESULT: exploratory parameter sweep

Run 2026-08-19T18:27:58+00:00. Development window only, holdout sealed.

## This is NOT evidence

**35 configurations were run.** If any were treated as a pre-registered trial, the honest bar would be Sharpe **1.070**, not the 0.760 that 6 registered trials earned. Searching costs you the right to claim the winner.

One-dimensional sweeps around a fixed base were used instead of a factorial grid, deliberately. **Read the SHAPE of each curve, not the peak.** A monotonic trend across a parameter is a structural finding that tends to survive out of sample. A peak at one interior value with noise either side is a lucky cell that does not.

Nothing here is promoted. Anything worth keeping goes into a fresh pre-registration with its own trial count and its own bar.

## Tenor (DTE band)

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| 0-3 DTE | +0.238 | +3.56% | -5.55% | 343 | 49.7 | 79.3% | -1.01 |
| 3-7 DTE | +2.010 | +28.08% | -2.76% | 351 | 50.8 | 82.3% | -1.01 |
| 7-14 DTE | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 14-21 DTE | +1.175 | +9.02% | -2.60% | 137 | 19.8 | 83.9% | -1.01 |
| 21-45 DTE | +1.440 | +10.78% | -2.20% | 116 | 16.8 | 86.2% | -0.97 |

## Short strike delta

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| 0.05 delta | +2.056 | +8.03% | -0.76% | 262 | 37.9 | 96.2% | -0.80 |
| 0.10 delta | +2.025 | +13.56% | -1.36% | 233 | 33.7 | 90.1% | -1.01 |
| 0.16 delta | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 0.25 delta | +1.046 | +14.38% | -4.98% | 204 | 29.5 | 68.6% | -1.01 |
| 0.35 delta | +0.814 | +16.02% | -8.00% | 202 | 29.3 | 61.4% | -1.04 |

## Wing width (% of spot)

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| 0.30% | +1.252 | +13.57% | -2.69% | 211 | 30.6 | 76.8% | -1.01 |
| 0.65% | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 1.00% | +1.178 | +9.91% | -2.38% | 213 | 30.8 | 82.2% | -1.01 |
| 1.50% | +0.763 | +5.36% | -2.13% | 215 | 31.1 | 83.3% | -1.01 |
| 2.50% | +0.468 | +2.30% | -2.10% | 217 | 31.4 | 82.9% | -1.01 |

## Profit target

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| 25% | +0.275 | +2.64% | -4.24% | 249 | 36.1 | 83.9% | -1.01 |
| 50% | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 75% | +1.037 | +9.42% | -3.12% | 203 | 29.4 | 76.8% | -1.01 |
| 90% | +0.988 | +8.99% | -3.19% | 203 | 29.4 | 76.8% | -1.01 |

## Stop loss multiple

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| None | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 1.5 | +1.444 | +11.04% | -1.95% | 230 | 33.3 | 70.4% | -0.78 |
| 2.0 | +1.306 | +10.85% | -2.14% | 222 | 32.2 | 75.2% | -0.79 |
| 3.0 | +1.255 | +11.59% | -2.26% | 215 | 31.1 | 80.5% | -1.00 |

## Structure

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| condor | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| put_spread | +0.519 | +3.57% | -1.78% | 256 | 37.1 | 88.7% | -1.00 |
| call_spread | +0.098 | +0.66% | -4.11% | 252 | 36.5 | 81.0% | -1.00 |

## Concurrent positions

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| 1 concurrent | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
| 2 concurrent | +1.251 | +21.10% | -3.92% | 386 | 55.9 | 79.3% | -1.01 |
| 3 concurrent | +1.434 | +29.51% | -4.52% | 510 | 73.9 | 80.6% | -1.01 |
| 5 concurrent | +1.474 | +31.38% | -4.30% | 535 | 77.5 | 80.9% | -1.01 |
| 8 concurrent | +1.474 | +31.38% | -4.30% | 535 | 77.5 | 80.9% | -1.01 |

## Deployed config D1

| value | Sharpe | return | max DD | trades | trades/yr | win% | worst trade (R) |
|---|---|---|---|---|---|---|---|
| D1 as chosen | +1.463 | +132.32% | -13.30% | 535 | 77.5 | 80.9% | -1.01 |
| D1 + stagger | +1.121 | +70.55% | -11.25% | 390 | 56.5 | 79.5% | -1.01 |
| D1 + stop 2x | +1.570 | +123.58% | -11.16% | 529 | 76.6 | 78.6% | -1.01 |
| research 1x1 | +1.155 | +10.77% | -2.54% | 214 | 31.0 | 80.4% | -1.01 |
