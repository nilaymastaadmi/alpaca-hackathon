# Live week results, generated from the sealed log

Generated 2026-09-04T14:14:01+00:00 by `prep/live_week_report.py` from `artifacts/decisions.jsonl` (1446 artifacts, 1422 in the judged window from 2026-08-31). Nothing in this file is typed by hand; regenerate it rather than editing it. `make verify` proves the log it reads from has not been altered.

Sealed root at generation time: `f0feb4d26376b9e4deaf0fc077d7d5b5f25dfc11d9add7e61f5192a0022662f1` (sealed 2026-09-04T14:11:09+00:00).

## Day by day

| Day (ET) | Cycles | Opportunities | Entered | Refused | Halted | Flattened | Exit checks | Hedge attempts | Equity open | Equity close | Open at close |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-31 | 13 | 8 | 4 | 4 | 0 | 0 | 0 | 11 | $100,000.00 | $99,871.90 | 0 |
| 2026-09-01 | 84 | 71 | 0 | 71 | 0 | 0 | 344 | 78 | $99,896.93 | $100,036.93 | 4 |
| 2026-09-02 | 84 | 71 | 0 | 71 | 0 | 0 | 340 | 77 | $100,036.93 | $100,141.93 | 4 |
| 2026-09-03 | 57 | 46 | 0 | 46 | 0 | 0 | 227 | 49 | $99,336.93 | $99,434.93 | 4 |
| 2026-09-04 | 18 | 9 | 0 | 9 | 0 | 0 | 34 | 0 | $99,434.93 | $99,726.13 | 0 |

Week totals: 256 cycles, 205 decision opportunities, 4 entered, 201 refused, 0 halted, 0 flatten cycles, 945 exit checks, 215 hedge attempts.

## Why it refused

| Blocking gate | Count | Share of opportunities |
|---|---|---|
| stagger | 142 | 69.3% |
| event_proximity | 55 | 26.8% |
| entry ladder unfilled (all gates passed) | 4 | 2.0% |

## Tail hedge

- `hedge:no_candidate`: 215

The hedge never engaged: every attempt found zero VIX contracts on the feed and refused to buy off an empty read (RISK_REGISTER.md 4.9). The purchased wings were the only crash protection all week.

## Positions

Open at generation time: 0. Closed: 0.

## Last exit check per position

| position | at (ET) | verdict | profit % of credit | DTE | reason |
|---|---|---|---|---|---|
| pos-adopt-bf4b6642 | 2026-09-04T09:32 | hold | -5.4 | 28 | holding: -5% of max profit, 28 DTE |
| pos-adopt-66ee2bf5 | 2026-09-04T09:32 | hold | -4.0 | 28 | holding: -4% of max profit, 28 DTE |
| pos-adopt-642a8824 | 2026-09-04T09:35 | hold | -11.8 | 28 | holding: -12% of max profit, 28 DTE |
| pos-14aabefe5a | 2026-09-04T09:35 | hold | -12.8 | 28 | holding: -13% of max profit, 28 DTE |

## P&L

- First judged cycle 2026-08-31T09:20 ET: equity $100,000.00
- Latest cycle 2026-09-04T10:11 ET: equity $99,726.13
- Change: $-273.87 (-0.274%) on a $100,000 paper account
- Reported drawdown at latest cycle: -0.51%

One week of options P&L is mostly noise; the research establishes positive expectancy, the week is one draw from it. Nothing above is adjusted, annualised, or selected.

## Independent check through Alpaca's CLI

Read back with the official Alpaca CLI 0.0.14 (read-only commands only), a different Alpaca surface from the MCP path the agent trades through. If the ledger, the MCP view and this disagreed, that would show up here.

- Account `PA37R35A5ZGW`, status ACTIVE, options level 3
- Equity $99,726.13, cash $99,726.13
- Open option legs reported by the broker: 0
- Portfolio history (1D, base $100,000.00 as of 2026-08-28): equity 99,540 -> 100,436 -> 100,506 -> 99,596
- Daily P&L over the same points: -460 , +896 , +70 , -910

## Incident record

31 Aug 09:45 ET: a payload-parsing bug read the account as flat and the agent stacked four condors instead of one. The sealed log caught it in one artifact. Bug, fix, regression test, and the adopted positions: `RISK_REGISTER.md` 4.7 and 4.8.
