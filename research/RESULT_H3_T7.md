# RESULT: amendment A3, trial T7 (5-10 DTE)

Run 2026-08-22T10:55:33+00:00. Development window 2016-01-04 to 2022-12-31 (6.99 years). Holdout sealed and verified unreadable by the run itself.

Registered in `PREREGISTRATION_R1.md` amendment A3, committed before this file existed. T1-T6 reproduced exactly against the committed `RESULT_H3.md` before this result was trusted (see script output); this file reports T7 plus the recomputed N=7 bar.

## Bar, recomputed at N=7

- trials: 7 (T1-T6 fixed 2026-08-19, T7 added 2026-08-22)
- E[max under null] = sqrt(2 ln 7) = 1.973
- SE(Sharpe) at 6.99y = 0.401
- **development bar = 0.792** (was 0.760 at N=6; T1-T6 verdicts unaffected, checked in the amendment before this ran)

## All seven, out-of-sample, ranked

| trial | Sharpe | return | max DD | trades | win% | PF | expectancy | refusal% |
|---|---|---|---|---|---|---|---|---|
| T7 both, 5-10 DTE | **+1.697** | +17.60% | -3.64% | 180 | 89.4% | 2.34 | +0.093R | 76.6% |
| T6 both, 21-45 DTE | **+1.614** | +9.70% | -2.89% | 83 | 89.2% | 3.38 | +0.132R | 88.1% |
| T5 both, 10 delta | **+1.515** | +7.51% | -1.95% | 188 | 88.8% | 2.18 | +0.044R | 76.5% |
| T2 vrp gate | **+1.392** | +11.34% | -2.51% | 179 | 78.8% | 1.94 | +0.060R | 76.5% |
| T4 both gates | **+1.201** | +9.30% | -3.10% | 165 | 78.2% | 1.85 | +0.056R | 79.2% |
| T1 baseline | **+1.071** | +11.85% | -4.38% | 310 | 73.5% | 1.48 | +0.038R | 0.0% |
| T3 regime gate | **+0.949** | +9.89% | -3.51% | 293 | 73.4% | 1.43 | +0.034R | 23.0% |

**T7 (5-10 DTE): Sharpe +1.697 against the recomputed bar 0.792. VERDICT: CLEARS.**

## Registered predictions (amendment A3)

- **P7** T7 Sharpe > T4's +1.201: **CORRECT** (+1.697 vs +1.201)
- **P8** T7 maxDD no worse than -4.65% (1.5x T4's -3.10%): **CORRECT** (-3.64%)
- **P9** double-cost sensitivity REDUCES T7 Sharpe (the normal direction, unlike T6's anomaly): **CORRECT**

## Sensitivity (section 7, mandatory)

| scenario | Sharpe | return |
|---|---|---|
| measured cost 1.5%, no haircut | +1.697 | +17.60% |
| double cost 3.0% | +1.579 | +16.22% |
| credit haircut 10% (model overprices) | +1.316 | +12.81% |
| both | +1.214 | +11.72% |

## Holdout governance

Holdout governance: T7 clears and beats T6. T7 becomes the sole nominee for the one holdout shot, per amendment A3. Holdout remains SEALED; this run does not spend it.
