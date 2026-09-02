# Live week results, generated from the sealed log

Generated 2026-09-02T16:53:40+00:00 by `prep/live_week_report.py` from `artifacts/decisions.jsonl` (805 artifacts, 784 in the judged window from 2026-08-31). Nothing in this file is typed by hand; regenerate it rather than editing it. `make verify` proves the log it reads from has not been altered.

Sealed root at generation time: `c8420479d41011cff31cb646f34ea183a54ea7bd462d4f812396d3ddc4857405` (sealed 2026-09-02T16:50:15+00:00).

## Day by day

| Day (ET) | Cycles | Opportunities | Entered | Refused | Halted | Flattened | Exit checks | Hedge attempts | Equity open | Equity close | Open at close |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-31 | 13 | 8 | 4 | 4 | 0 | 0 | 0 | 11 | $100,000.00 | $99,871.90 | 0 |
| 2026-09-01 | 84 | 71 | 0 | 71 | 0 | 0 | 344 | 78 | $99,896.93 | $100,036.93 | 4 |
| 2026-09-02 | 42 | 37 | 0 | 37 | 0 | 0 | 172 | 40 | $100,036.93 | $100,120.93 | 4 |

Week totals: 139 cycles, 116 decision opportunities, 4 entered, 112 refused, 0 halted, 0 flatten cycles, 516 exit checks, 129 hedge attempts.

## Why it refused

| Blocking gate | Count | Share of opportunities |
|---|---|---|
| stagger | 108 | 93.1% |
| entry ladder unfilled (all gates passed) | 4 | 3.4% |

## Tail hedge

- `hedge:no_candidate`: 129

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
| pos-adopt-bf4b6642 | 2026-09-02T12:50 | hold | 0.9 | 30 | holding: +1% of max profit, 30 DTE |
| pos-adopt-66ee2bf5 | 2026-09-02T12:50 | hold | 5.7 | 30 | holding: +6% of max profit, 30 DTE |
| pos-adopt-642a8824 | 2026-09-02T12:50 | hold | 0.0 | 30 | holding: +0% of max profit, 30 DTE |
| pos-14aabefe5a | 2026-09-02T12:50 | hold | -0.9 | 30 | holding: -1% of max profit, 30 DTE |

## P&L

- First judged cycle 2026-08-31T09:20 ET: equity $100,000.00
- Latest cycle 2026-09-02T12:50 ET: equity $100,120.93
- Change: $120.93 (+0.121%) on a $100,000 paper account
- Reported drawdown at latest cycle: -0.03%

One week of options P&L is mostly noise; the research establishes positive expectancy, the week is one draw from it. Nothing above is adjusted, annualised, or selected.

## Incident record

31 Aug 09:45 ET: a payload-parsing bug read the account as flat and the agent stacked four condors instead of one. The sealed log caught it in one artifact. Bug, fix, regression test, and the adopted positions: `RISK_REGISTER.md` 4.7 and 4.8.
