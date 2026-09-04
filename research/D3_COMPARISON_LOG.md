# D3 comparison log: T4 vs T6 vs T7

Generated 2026-09-04T19:15:22 by `agent/compare_report.py` from `agent/agent.py --compare-all`, scheduled hourly 19:15-01:15 IST (matching `agent/config.py`'s own trade_window). Purely observational -- every row below is a dry-run decision, no order was ever sent. See `research/DEPLOYMENT_DECISIONS.md` D3 for the backtest case; this file is the live-market evidence gathered in parallel while that decision stays open until kickoff.

| ET timestamp | T4 (7-14 DTE) | T6 (21-45 DTE, deployed since 30 Aug) | T7 (5-10 DTE) |
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
| 2026-08-28 10:45 | refuse [g7 fail] (VRP -0.62) | **ENTER** [g7 pass] (VRP +2.42) | refuse [g7 fail] (VRP +0.23) |
| 2026-08-28 11:46 | refuse [g7 fail] (VRP -0.72) | **ENTER** [g7 pass] (VRP +2.52) | refuse [g7 fail] (VRP +0.13) |
| 2026-08-28 12:46 | refuse [g7 fail] (VRP -0.36) | **ENTER** [g7 pass] (VRP +2.67) | refuse [g7 fail] (VRP +0.52) |
| 2026-08-28 13:45 | refuse [g7 fail] (VRP -0.44) | **ENTER** [g7 pass] (VRP +2.66) | refuse [g7 fail] (VRP +0.56) |
| 2026-08-28 14:45 | refuse [g7 fail] (VRP -0.76) | **ENTER** [g7 pass] (VRP +2.46) | refuse [g7 fail] (VRP +0.12) |
| 2026-08-28 15:45 | refuse [g7 fail] (VRP -0.83) | refuse [g7 pass] (VRP +2.43) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-29 09:45 | refuse [g7 fail] (VRP -0.58) | refuse [g7 pass] (VRP +2.48) | refuse [g7 fail] (VRP +0.58) |
| 2026-08-29 10:48 | refuse [g7 fail] (VRP -0.58) | refuse [g7 pass] (VRP +2.48) | - |
| 2026-08-29 11:49 | refuse [g7 fail] (VRP -0.58) | refuse [g7 pass] (VRP +2.48) | refuse [g7 fail] (VRP +0.58) |
| 2026-08-30 09:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-30 10:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-30 11:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-30 13:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-30 14:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-30 15:45 | refuse [g7 pass] (VRP +3.06) | refuse [g7 pass] (VRP +3.06) | refuse [g7 fail] (VRP -0.06) |
| 2026-08-31 09:45 | **ENTER** [g7 pass] (VRP +3.42) | **ENTER** [g7 pass] (VRP +3.42) | refuse [g7 fail] (VRP +0.30) |
| 2026-08-31 10:45 | **ENTER** [g7 pass] (VRP +3.28) | **ENTER** [g7 pass] (VRP +3.24) | refuse [g7 fail] (VRP +0.12) |
| 2026-08-31 12:45 | **ENTER** [g7 pass] (VRP +3.19) | **ENTER** [g7 pass] (VRP +3.20) | refuse [g7 fail] (VRP -0.13) |
| 2026-08-31 13:45 | **ENTER** [g7 pass] (VRP +3.17) | **ENTER** [g7 pass] (VRP +3.17) | refuse [g7 fail] (VRP -0.26) |
| 2026-09-01 09:45 | **ENTER** [g7 pass] (VRP +4.51) | **ENTER** [g7 pass] (VRP +4.58) | **ENTER** [g7 pass] (VRP +2.13) |
| 2026-09-01 10:45 | **ENTER** [g7 pass] (VRP +4.42) | **ENTER** [g7 pass] (VRP +4.46) | **ENTER** [g7 pass] (VRP +1.54) |
| 2026-09-01 11:45 | **ENTER** [g7 pass] (VRP +4.33) | **ENTER** [g7 pass] (VRP +4.34) | **ENTER** [g7 pass] (VRP +1.48) |
| 2026-09-01 12:45 | **ENTER** [g7 pass] (VRP +4.64) | **ENTER** [g7 pass] (VRP +4.62) | **ENTER** [g7 pass] (VRP +2.23) |
| 2026-09-01 13:45 | **ENTER** [g7 pass] (VRP +4.60) | **ENTER** [g7 pass] (VRP +4.56) | **ENTER** [g7 pass] (VRP +2.04) |
| 2026-09-01 14:45 | **ENTER** [g7 pass] (VRP +4.95) | **ENTER** [g7 pass] (VRP +4.99) | **ENTER** [g7 pass] (VRP +2.95) |
| 2026-09-01 15:45 | refuse [g7 pass] (VRP +4.86) | refuse [g7 pass] (VRP +4.76) | refuse [g7 pass] (VRP +2.46) |
| 2026-09-02 09:45 | **ENTER** [g7 pass] (VRP +7.01) | **ENTER** [g7 pass] (VRP +7.07) | **ENTER** [g7 pass] (VRP +4.82) |
| 2026-09-02 10:45 | **ENTER** [g7 pass] (VRP +6.30) | **ENTER** [g7 pass] (VRP +6.21) | **ENTER** [g7 pass] (VRP +3.85) |
| 2026-09-02 11:45 | **ENTER** [g7 pass] (VRP +6.49) | **ENTER** [g7 pass] (VRP +6.52) | **ENTER** [g7 pass] (VRP +3.96) |
| 2026-09-02 12:45 | **ENTER** [g7 pass] (VRP +6.54) | **ENTER** [g7 pass] (VRP +6.53) | **ENTER** [g7 pass] (VRP +3.89) |
| 2026-09-02 13:45 | **ENTER** [g7 pass] (VRP +6.40) | **ENTER** [g7 pass] (VRP +6.34) | **ENTER** [g7 pass] (VRP +3.57) |
| 2026-09-02 14:45 | **ENTER** [g7 pass] (VRP +6.32) | **ENTER** [g7 pass] (VRP +6.30) | **ENTER** [g7 pass] (VRP +3.55) |
| 2026-09-02 15:45 | refuse [g7 pass] (VRP +6.21) | refuse [g7 pass] (VRP +6.22) | refuse [g7 pass] (VRP +3.32) |
| 2026-09-03 12:45 | refuse [g7 pass] (VRP +5.18) | refuse [g7 pass] (VRP +5.22) | refuse [g7 pass] (VRP +2.97) |
| 2026-09-03 13:45 | refuse [g7 pass] (VRP +5.15) | refuse [g7 pass] (VRP +5.24) | refuse [g7 pass] (VRP +2.68) |
| 2026-09-03 14:45 | refuse [g7 pass] (VRP +5.00) | refuse [g7 pass] (VRP +4.97) | refuse [g7 pass] (VRP +2.49) |
| 2026-09-03 15:45 | refuse [g7 pass] (VRP +4.98) | refuse [g7 pass] (VRP +4.91) | refuse [g7 pass] (VRP +2.45) |
| 2026-09-04 09:45 | refuse [g7 pass] (VRP +4.73) | refuse [g7 pass] (VRP +4.78) | refuse [g7 pass] (VRP +2.27) |

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
| 2026-08-28 | T4 | 7 | 0 | 0 | -0.83 to -0.17 |
| 2026-08-28 | T6 | 7 | 7 | 6 | +2.42 to +2.82 |
| 2026-08-28 | T7 | 7 | 1 | 1 | -0.06 to +1.09 |
| 2026-08-29 | T4 | 3 | 0 | 0 | -0.58 to -0.58 |
| 2026-08-29 | T6 | 3 | 3 | 0 | +2.48 to +2.48 |
| 2026-08-29 | T7 | 2 | 0 | 0 | +0.58 to +0.58 |
| 2026-08-30 | T4 | 6 | 6 | 0 | +3.06 to +3.06 |
| 2026-08-30 | T6 | 6 | 6 | 0 | +3.06 to +3.06 |
| 2026-08-30 | T7 | 6 | 0 | 0 | -0.06 to -0.06 |
| 2026-08-31 | T4 | 4 | 4 | 4 | +3.17 to +3.42 |
| 2026-08-31 | T6 | 4 | 4 | 4 | +3.17 to +3.42 |
| 2026-08-31 | T7 | 4 | 0 | 0 | -0.26 to +0.30 |
| 2026-09-01 | T4 | 7 | 7 | 6 | +4.33 to +4.95 |
| 2026-09-01 | T6 | 7 | 7 | 6 | +4.34 to +4.99 |
| 2026-09-01 | T7 | 7 | 7 | 6 | +1.48 to +2.95 |
| 2026-09-02 | T4 | 7 | 7 | 6 | +6.21 to +7.01 |
| 2026-09-02 | T6 | 7 | 7 | 6 | +6.21 to +7.07 |
| 2026-09-02 | T7 | 7 | 7 | 6 | +3.32 to +4.82 |
| 2026-09-03 | T4 | 4 | 4 | 0 | +4.98 to +5.18 |
| 2026-09-03 | T6 | 4 | 4 | 0 | +4.91 to +5.24 |
| 2026-09-03 | T7 | 4 | 4 | 0 | +2.45 to +2.97 |
| 2026-09-04 | T4 | 1 | 1 | 0 | +4.73 to +4.73 |
| 2026-09-04 | T6 | 1 | 1 | 0 | +4.78 to +4.78 |
| 2026-09-04 | T7 | 1 | 1 | 0 | +2.27 to +2.27 |

## Overall tally

| label | cycles logged | would-enter cycles |
|---|---|---|
| T4 | 53 | 16 |
| T6 | 53 | 26 |
| T7 | 52 | 13 |
