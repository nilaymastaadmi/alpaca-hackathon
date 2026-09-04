# facts.md: every number the video uses, with its source

Written 2026-09-02, restyled the same evening, final pass 2026-09-04 before submission.
`build.py` reads the PARAMS block below and refuses to build if a number on screen is not
in this file. Anything that could not be traced was cut from the script (list at the bottom).

## PARAMS (parsed by build.py; the live values are what you edit before a re-render)

```
LIVE_N=197
LIVE_PCT=98
LIVE_PNL=-565.07
EXPLAINED=238
REJECTED=0
VOICE=rahul
PACE=1.12
```

- LIVE_N, LIVE_PCT: dashboard headline, read 2026-09-04 12:56 IST: "Of 197 real decision
  opportunities (market open, inside the trading window), the agent entered 4 and declined
  193 (98%)." Same from `make summary` run 2026-09-04: "decision opportunities (market
  open, in window): 197" and "refusals by blocking gate (193 of 197 opportunities)".
  193/197 = 97.97%, rendered as 98. Wording: `dashboard/app.py`. **The definition changed
  since 2 Sep: dry-run cycles are now excluded**, so this count is not comparable to the
  81 the earlier cut showed.
- LIVE_PNL: equity minus 100,000. Equity **99,434.93** from `artifacts/decisions.jsonl`,
  the last record carrying `portfolio.equity` (seq 1390, 2026-09-04T03:03:55-04:00), so
  **-565.07**. The sign is spoken: `pnl_words()` renders it "minus five hundred and
  sixty five dollars and seven cents". Still open at render time, realised by the
  19:00 to 20:30 IST deadline flatten.
- EXPLAINED, REJECTED: `artifacts/explanations.json` -> `counts` -> `{"explained": 238,
  "rejected": 0}`, generated 2026-09-04T07:23:05+00:00. Same two numbers appear on the
  dashboard under the latest decision.
- VOICE, PACE: Sarvam bulbul:v3 speaker and pace. `rahul` measured at 151 words per
  minute at pace 1.0 on a 29-word sample (11.52 s). PACE is the knob if the total runs
  long: raised to 1.12 on 4 Sep so ten beats fit inside 3:10.

## Numbers spoken or shown, by beat

| Beat | Number | Source (file, line or field) |
|---|---|---|
| 1 | 197 opportunities, 4 entered, 193 declined, 98% | Dashboard headline and `make summary`, both 2026-09-04 |
| 1 | Wordmark "GLASS BOX" | `presentation/slides.pdf` page 1: "GLASS BOX / An options agent whose every decision you can verify" |
| 2 | Pre-registration commit `96ee715`, 2026-08-19 19:57:13 +0530, "Pre-register R1 before any backtest code exists" | `git log --diff-filter=A --reverse -- research/PREREGISTRATION_R1.md` |
| 2 | First backtest commit `997701c`, 2026-08-19 20:01:47 +0530 | same command, `backtest/` |
| 3 | 6.99 years of SPY out of sample; mean VRP +3.68 vol points over 1,741 observations | `README.md` table under "The thesis"; WRITEUP para 1 |
| 3 | Newey-West t = +4.74; naive t +18.16 invalid (21-day windows overlap by 20 of 21); correction shrinks t by 3.8x | `README.md` same table and the paragraph after it |
| 4 | 11 numbered gates (0 to 10) plus a stagger rule; gates 0, 2, 3 are circuit breakers | `README.md` Architecture; WRITEUP "Risk gates" |
| 4 | Gate names 0-10 | `artifacts/decisions.jsonl` seq 30 `gates[]` |
| 4 | Alpaca's official MCP server, 74 tools, JSON-RPC over stdio, every request and response recorded | `README.md` Architecture para 1 |
| 5 | **T4 16 of 52, T6 26 of 52, T7 13 of 51 would-enter cycles** | `artifacts/compare_summary.json` -> `tally`, read 2026-09-04. Running totals for the whole shadow run, NOT the 22 to 29 Aug window the earlier cut quoted; the beat says the window out loud |
| 5 | Deployed tenor T6 = 21 to 45 DTE; alternatives T4 7-14, T7 5-10 | `research/DEPLOYMENT_DECISIONS.md` D3 "Decision" |
| 6 | `make judge` runs tests, verify, summary and the results page in one command | `Makefile` line 40: `judge: test verify summary results` |
| 6 | `VERIFIED: 1390 artifacts, root e4ce452c697f8c90...` | Real output of the Makefile `verify` target; build.py re-runs it at build time so the count and root are current at render |
| 7 | 31 Aug 2026, fills 09:45, 09:55, 10:05, 10:21 ET, 7 contracts each, 4 condors where the design intended 1; combined max risk $10,840 = 10.8% of equity | `RISK_REGISTER.md` 4.7 para 1 |
| 7 | Artifact seq 30: gate 5 "0/5 positions open"; `mcp_calls[1]` `get_all_positions` contains `SPY261002C00792000`; `reconciliation[0]` "no legs at broker; closed or expired" | `artifacts/decisions.jsonl` seq 30; named in RISK_REGISTER 4.7 |
| 7 | 9 regression tests in `tests/test_position_sync.py`; 3 orphan condors adopted | RISK_REGISTER 4.7 fixes 3 and 5 |
| 8 | **238 explained, 0 rejected** | `artifacts/explanations.json` `counts` (see PARAMS) |
| 8 | Explain layer runs after the seal, never inside the decision; every number checked against the artifact | `artifacts/explanations.json` `policy`; `dashboard/app.py` `show_explanation()` label |
| 8 | Model: Qwen/Qwen2.5-72B-Instruct | `artifacts/explanations.json` `model` (named on the dashboard, not spoken) |
| 9 | **P&L -$565.07 so far on a $100,000 paper account** | seq 1390 `portfolio.equity` (see PARAMS) |
| 9 | 4 condors, 28 contracts (4 x 7), $3,108 credit collected | `artifacts/positions.json`: credits 1.11, 1.14, 1.10, 1.09 x 7 x 100 = 3,108 |
| 9 | Worst case capped at $10,840 | `positions.json` max_loss_per_contract 3.89 + 3.86 + 3.90 + 3.835 = 15.485 x 700 = 10,839.50; RISK_REGISTER 4.7 rounds to $10,840 |
| 9 | Deadline flatten runs 90 minutes before the 4 Sep 11:00 ET deadline, so 19:00 to 20:30 IST | RISK_REGISTER 4.6; WRITEUP "Risk gates" |
| 9 | **Tail hedge coded, never engaged: no VIX expiry inside its 21 to 45 day window was quoted all week** | `RISK_REGISTER.md` 4.9 (corrected 2026-09-02): the indicative feed quotes monthly VIX expiries only; 16 Sep was 14 to 16 days out and 21 Oct was 49 to 51, so neither fell inside the window. 216 `hedge:no_candidate` artifacts, `make summary` |
| 10 | **233 tests** | `pytest tests/ --collect-only`: 233 collected, 2026-09-04 |
| 10 | github.com/nilaymastaadmi/alpaca-hackathon | `git remote -v`; SUBMISSION_FORM.md |
| all | Challenge "Options Alpha Agents"; solo entry; paper account PA37R35A5ZGW | SUBMISSION_FORM.md |
| 1, 8, 9 | Dashboard footage `assets/dash_top.mp4`, `dash_explain.mp4`, `dash_positions.mp4` | Recorded by `record.py` from the public dashboard on 2026-09-04 (Playwright, real scroll and cursor) |

## Traceable but cut for time (not in the video)

- Gate 8 (event proximity) refused 46 of 197 opportunities, 23.4%, because nonfarm
  payrolls sits inside its window (`make summary` 2026-09-04). The strongest cut item:
  it is the event-awareness gate firing for real, and there was no room.
- Alpaca's CLI as a read-only second opinion behind a command allowlist.
- 1.5% of credit round trip on a real fill; 5 ladder rungs; prize pool $6,000.
- Multiple-testing bar 0.791 (WRITEUP) vs 0.792 (D3): the video does not quote it.

## Discrepancies found while tracing (not fixed; all outside presentation/video/)

1. **RESOLVED 4 Sep 13:15.** The deck was a day stale (1,052 artifacts, 147 of 151, 97%)
   while this video was being cut. Commit `ef9d55a` rebuilt it from the same log, and
   `presentation/slides.pdf` now reads 1,390 sealed artifacts, 193 of 197 declined, 98%
   and 233 tests: the same numbers this video speaks and shows. Checked page by page
   after the rebuild, no action left.
2. `presentation/WRITEUP.md` says "Alpaca MCP Server v3.4.7 with 74 tools". README and
   RISK_REGISTER 4.8 say alpaca-mcp-server 2.3.0 on FastMCP 3.4.7. The video says
   "Alpaca's official MCP server" and "74 tools" with no version number.
3. Multiple-testing bar: WRITEUP and SUBMISSION_FORM say 0.791; D3 and the deck say 0.792.
   The video does not quote it.
4. README "What the research found that did NOT work" still says "The deployed agent
   trades 7-14 DTE (T4)". D3 switched to T6 (21-45 DTE) on 30 Aug. The video follows D3.
5. RISK_REGISTER 4.7 gives fill times 09:45, 09:55, 10:05, 10:21 ET; the enter artifacts
   are seq 28, 32, 36, 42 with cycle timestamps 09:45:05, 09:55:05, 10:05:05, 10:20:05 ET
   and `positions.json` opened_at 14:21:40Z for the fourth. The video uses 4.7's times.
6. The dev account PA308NOY3X36 appears inside `artifacts/decisions.jsonl` (2 early
   records carry it as `account_number`). The seq 30 excerpt on screen is built from named
   fields only, and build.py aborts if that string reaches any rendered text or caption.
7. `make` is not installed on this machine. build.py runs the exact commands the Makefile
   targets run and labels them `make judge` and `make summary` on screen, which is what a
   judge would type.
