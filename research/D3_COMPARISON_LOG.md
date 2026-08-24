# D3 comparison log: T4 vs T6 vs T7

Generated 2026-08-25T02:10:42 by `agent/compare_report.py` from `agent/agent.py --compare-all`. Purely observational -- every row below is a dry-run decision, no order was ever sent. See `research/DEPLOYMENT_DECISIONS.md` D3 for the backtest case; this file is the live-market evidence gathered in parallel while that decision stays open until kickoff.

| date | T4 (7-14 DTE, deployed) | T6 (21-45 DTE) | T7 (5-10 DTE, proposed) |
|---|---|---|---|
| 2026-08-22 | refuse [g7 fail] (VRP -1.01, 10d) | refuse [g7 pass] (VRP +1.21, 34d) | refuse [g7 fail] (VRP -1.34, 9d) |
| 2026-08-24 | refuse [g7 fail] (VRP -0.28, 10d) | refuse [g7 pass] (VRP +1.21, 32d) | refuse [g7 fail] (VRP -0.68, 8d) |

## Tally

| label | days logged | would-enter days |
|---|---|---|
| T4 | 2 | 0 |
| T6 | 2 | 0 |
| T7 | 2 | 0 |
