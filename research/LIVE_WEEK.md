# Live week results, generated from the sealed log

Generated 2026-09-04T07:45:24+00:00 by `prep/live_week_report.py` from `artifacts/decisions.jsonl` (1390 artifacts, 1368 in the judged window from 2026-08-31). Nothing in this file is typed by hand; regenerate it rather than editing it. `make verify` proves the log it reads from has not been altered.

Sealed root at generation time: `e4ce452c697f8c90df21415e83a929b952cff7fef9648ed9472985ad96557b94` (sealed 2026-09-04T07:04:03+00:00).

## Day by day

| Day (ET) | Cycles | Opportunities | Entered | Refused | Halted | Flattened | Exit checks | Hedge attempts | Equity open | Equity close | Open at close |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-31 | 13 | 8 | 4 | 4 | 0 | 0 | 0 | 11 | $100,000.00 | $99,871.90 | 0 |
| 2026-09-01 | 84 | 71 | 0 | 71 | 0 | 0 | 344 | 78 | $99,896.93 | $100,036.93 | 4 |
| 2026-09-02 | 84 | 71 | 0 | 71 | 0 | 0 | 340 | 77 | $100,036.93 | $100,141.93 | 4 |
| 2026-09-03 | 57 | 46 | 0 | 46 | 0 | 0 | 227 | 49 | $99,336.93 | $99,434.93 | 4 |
| 2026-09-04 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | n/a | n/a | n/a |

Week totals: 238 cycles, 196 decision opportunities, 4 entered, 192 refused, 0 halted, 0 flatten cycles, 915 exit checks, 215 hedge attempts.

## Why it refused

| Blocking gate | Count | Share of opportunities |
|---|---|---|
| stagger | 142 | 72.4% |
| event_proximity | 46 | 23.5% |
| entry ladder unfilled (all gates passed) | 4 | 2.0% |

## Tail hedge

- `hedge:no_candidate`: 215

The hedge never engaged: every attempt found zero VIX contracts on the feed and refused to buy off an empty read (RISK_REGISTER.md 4.9). The purchased wings were the only crash protection all week.

## Positions

Open at generation time: 4. Closed: 0.

| id | status | expiry | contracts | credit | max risk | short put | short call | realised |
|---|---|---|---|---|---|---|---|---|
| pos-adopt-bf4b6642 | open | 2026-10-02 | 7 | 1.11 | $2,723.00 | SPY261002P00731000 | SPY261002C00792000 |  |
| pos-adopt-66ee2bf5 | open | 2026-10-02 | 7 | 1.14 | $2,702.00 | SPY261002P00732000 | SPY261002C00792000 |  |
| pos-adopt-642a8824 | open | 2026-10-02 | 7 | 1.1 | $2,730.00 | SPY261002P00731000 | SPY261002C00792000 |  |
| pos-14aabefe5a | open | 2026-10-02 | 7 | 1.09 | $2,684.50 | SPY261002P00731000 | SPY261002C00792000 |  |

## Last exit check per position

| position | at (ET) | verdict | profit % of credit | DTE | reason |
|---|---|---|---|---|---|
| pos-adopt-bf4b6642 | 2026-09-04T03:04 | hold | -11.7 | 28 | holding: -12% of max profit, 28 DTE |
| pos-adopt-66ee2bf5 | 2026-09-04T03:04 | hold | -10.1 | 28 | holding: -10% of max profit, 28 DTE |
| pos-adopt-642a8824 | 2026-09-04T03:04 | hold | -12.7 | 28 | holding: -13% of max profit, 28 DTE |
| pos-14aabefe5a | 2026-09-04T03:04 | hold | -13.8 | 28 | holding: -14% of max profit, 28 DTE |

## P&L

- First judged cycle 2026-08-31T09:20 ET: equity $100,000.00
- Latest cycle 2026-09-03T16:35 ET: equity $99,434.93
- Change: $-565.07 (-0.565%) on a $100,000 paper account
- Reported drawdown at latest cycle: -0.80%

One week of options P&L is mostly noise; the research establishes positive expectancy, the week is one draw from it. Nothing above is adjusted, annualised, or selected.

## Independent check through Alpaca's CLI

Read back with the official Alpaca CLI 0.0.14 (read-only commands only), a different Alpaca surface from the MCP path the agent trades through. If the ledger, the MCP view and this disagreed, that would show up here.

- Account `PA37R35A5ZGW`, status ACTIVE, options level 3
- Equity $99,434.93, cash $103,102.93
- Open option legs reported by the broker: 6
- Portfolio history (1D, base $100,000.00 as of 2026-08-27): equity 100,000 -> 99,540 -> 100,436 -> 100,506 -> 99,596
- Daily P&L over the same points: +0 , -460 , +896 , +70 , -910

## Incident record

31 Aug 09:45 ET: a payload-parsing bug read the account as flat and the agent stacked four condors instead of one. The sealed log caught it in one artifact. Bug, fix, regression test, and the adopted positions: `RISK_REGISTER.md` 4.7 and 4.8.
