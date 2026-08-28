# D3 comparison log: T4 vs T6 vs T7

Generated 2026-08-28T19:15:46 by `agent/compare_report.py` from `agent/agent.py --compare-all`, scheduled hourly 19:15-01:15 IST (matching `agent/config.py`'s own trade_window). Purely observational -- every row below is a dry-run decision, no order was ever sent. See `research/DEPLOYMENT_DECISIONS.md` D3 for the backtest case; this file is the live-market evidence gathered in parallel while that decision stays open until kickoff.

| ET timestamp | T4 (7-14 DTE, deployed) | T6 (21-45 DTE) | T7 (5-10 DTE, proposed) |
|---|---|---|---|
| 2026-08-22 09:04 | refuse [g7 fail] (VRP -1.01) | refuse [g7 pass] (VRP +1.21) | refuse [g7 fail] (VRP -1.34) |
| 2026-08-22 12:10 | refuse [g7 fail] (VRP -1.01) | refuse [g7 pass] (VRP +1.21) | refuse [g7 fail] (VRP -1.34) |
| 2026-08-24 01:50 | refuse [g7 fail] (VRP +0.59) | refuse [g7 pass] (VRP +1.63) | refuse [g7 fail] (VRP +0.38) |
| 2026-08-24 16:40 | refuse [g7 fail] (VRP -0.28) | refuse [g7 pass] (VRP +1.21) | refuse [g7 fail] (VRP -0.68) |
| 2026-08-25 12:45 | refuse [g7 fail] (VRP -0.21) | refuse [g7 fail] (VRP +0.98) | refuse [g7 fail] (VRP -0.88) |
| 2026-08-25 13:45 | refuse [g7 fail] (VRP -0.21) | refuse [g7 fail] (VRP +1.00) | refuse [g7 fail] (VRP -0.91) |
| 2026-08-25 14:45 | refuse [g7 fail] (VRP -0.41) | refuse [g7 fail] (VRP +0.88) | refuse [g7 fail] (VRP -1.11) |
| 2026-08-25 15:45 | refuse [g7 fail] (VRP -0.39) | refuse [g7 fail] (VRP +0.90) | refuse [g7 fail] (VRP -1.04) |
| 2026-08-27 02:58 | refuse [g7 fail] (VRP +0.57) | refuse [g7 pass] (VRP +1.01) | refuse [g7 fail] (VRP +0.57) |
| 2026-08-27 11:45 | refuse [g7 fail] (VRP +0.03) | **ENTER** [g7 pass] (VRP +1.77) | refuse [g7 fail] (VRP +0.17) |
| 2026-08-27 12:45 | refuse [g7 fail] (VRP -0.13) | **ENTER** [g7 pass] (VRP +1.59) | refuse [g7 fail] (VRP -0.07) |
| 2026-08-27 13:45 | refuse [g7 fail] (VRP -0.06) | **ENTER** [g7 pass] (VRP +1.69) | refuse [g7 fail] (VRP +0.12) |
| 2026-08-27 14:45 | refuse [g7 fail] (VRP +0.20) | **ENTER** [g7 pass] (VRP +1.84) | refuse [g7 fail] (VRP +0.15) |
| 2026-08-27 15:45 | refuse [g7 fail] (VRP -0.13) | refuse [g7 pass] (VRP +1.58) | refuse [g7 fail] (VRP -0.28) |
| 2026-08-28 09:45 | refuse [g7 fail] (VRP -0.17) | **ENTER** [g7 pass] (VRP +2.82) | **ENTER** [g7 pass] (VRP +1.09) |

## Daily summary

| date | label | cycles | gate7 pass | would-enter | VRP range |
|---|---|---|---|---|---|
| 2026-08-22 | T4 | 2 | 0 | 0 | -1.01 to -1.01 |
| 2026-08-22 | T6 | 2 | 2 | 0 | +1.21 to +1.21 |
| 2026-08-22 | T7 | 2 | 0 | 0 | -1.34 to -1.34 |
| 2026-08-24 | T4 | 2 | 0 | 0 | -0.28 to +0.59 |
| 2026-08-24 | T6 | 2 | 2 | 0 | +1.21 to +1.63 |
| 2026-08-24 | T7 | 2 | 0 | 0 | -0.68 to +0.38 |
| 2026-08-25 | T4 | 4 | 0 | 0 | -0.41 to -0.21 |
| 2026-08-25 | T6 | 4 | 0 | 0 | +0.88 to +1.00 |
| 2026-08-25 | T7 | 4 | 0 | 0 | -1.11 to -0.88 |
| 2026-08-27 | T4 | 6 | 0 | 0 | -0.13 to +0.57 |
| 2026-08-27 | T6 | 6 | 6 | 4 | +1.01 to +1.84 |
| 2026-08-27 | T7 | 6 | 0 | 0 | -0.28 to +0.57 |
| 2026-08-28 | T4 | 1 | 0 | 0 | -0.17 to -0.17 |
| 2026-08-28 | T6 | 1 | 1 | 1 | +2.82 to +2.82 |
| 2026-08-28 | T7 | 1 | 1 | 1 | +1.09 to +1.09 |

## Overall tally

| label | cycles logged | would-enter cycles |
|---|---|---|
| T4 | 15 | 0 |
| T6 | 15 | 5 |
| T7 | 15 | 1 |
