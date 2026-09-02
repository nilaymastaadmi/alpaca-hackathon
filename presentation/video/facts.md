# facts.md: every number the video uses, with its source

Written 2026-09-02 by the video session. `build.py` reads the PARAMS block below
and refuses to build if a number on screen is not in this file. Anything that
could not be traced was cut from the script (list at the bottom).

## PARAMS (parsed by build.py; the three LIVE values are what you edit Thursday)

```
LIVE_N=81
LIVE_PCT=95
LIVE_PNL=36.93
VOICE=rahul
PACE=1.0
```

- LIVE_N, LIVE_PCT: dashboard headline, read 2026-09-02 IST afternoon: "Of 81 real
  decision opportunities (market open, inside the trading window), the agent entered 4
  and declined 77 (95%)." Same numbers from `make summary` run 2026-09-02:
  "decision opportunities (market open, in window): 81" and "refusals by blocking gate
  (77 of 81 opportunities)". Source of the wording: `dashboard/app.py` lines 153-155.
- LIVE_PNL: equity minus 100,000. Equity 100,036.93 from `artifacts/decisions.jsonl`
  seq 554, `portfolio.equity`, timestamp 2026-09-02T01:47:09-04:00 (Tuesday close
  carried into the Wednesday pre-session cycle). Narrated as "so far" until the
  Friday flatten. Sign is spoken: positive reads "plus", negative reads "minus".
- VOICE, PACE: Sarvam bulbul:v3 speaker and pace. `rahul` measured at 151 words per
  minute at pace 1.0 on a 29-word sample (11.52 s). PACE is the knob if the total
  runs long.

## Numbers spoken or shown, by beat

| Beat | Number | Source (file, line or field) |
|---|---|---|
| 1 | 81 opportunities, 95% declined, 4 entered, 77 declined | Dashboard headline (above); `make summary` 2026-09-02 |
| 2 | Pre-registration commit `96ee715`, 2026-08-19 19:57:13 +0530, "Pre-register R1 before any backtest code exists" | `git log --reverse --date=iso -- research/PREREGISTRATION_R1.md` |
| 2 | First backtest commit `997701c`, 2026-08-19 20:01:47 +0530, "R1 H1 and H2: thesis validated, one registered prediction wrong" | `git log --reverse --date=iso -- backtest/` |
| 3 | 6.99 years of SPY, out of sample | `presentation/WRITEUP.md` AI logic para 1; `README.md` "The thesis" |
| 3 | Mean VRP +3.68 vol points, 1,741 observations | `README.md` table under "The thesis"; WRITEUP para 1; slide 5 |
| 3 | Newey-West t = +4.74; naive t +18.16 invalid (overlapping 21-day windows) | `README.md` same table and the paragraph after it; WRITEUP para 1 |
| 4 | 11 numbered gates (0 to 10) plus a stagger rule; gates 0, 2, 3 are circuit breakers | `README.md` Architecture; WRITEUP "Risk gates" |
| 4 | Gate names 0-10: position_integrity, session_window, drawdown_breaker, daily_loss_limit, consecutive_losses, capacity, regime, vrp_threshold, event_proximity, cost, sizing | `artifacts/decisions.jsonl` seq 30 `gates[]` (number and name fields) |
| 4 | Alpaca's official MCP server, 74 tools, JSON-RPC 2.0 over stdio, every request and response recorded | `README.md` Architecture para 1; WRITEUP "Alpaca infrastructure" |
| 5 | Live comparison 22 to 29 Aug (8 days), 21 cycles, 5 trading days | `research/DEPLOYMENT_DECISIONS.md` D3, "What changed" |
| 5 | Would-enter cycles: T4 0/21, T6 10/21, T7 1/21. Days with an entry: T4 0/5, T6 2/5, T7 1/5 | D3 table under "What changed" |
| 5 | Deployed tenor T6 = 21 to 45 DTE; alternatives T4 7-14 DTE, T7 5-10 DTE | D3 "Decision"; WRITEUP para 2 |
| 6 | `VERIFIED: 555 artifacts, root 9f5162884f30bb2e... matches the seal written 2026-09-02T05:47:17+00:00` | Real output of the Makefile `verify` target, run 2026-09-02. build.py re-runs it at build time so the count and root are current |
| 6 | SHA-256 Merkle tree, domain-separated leaves and nodes, sealed before outcomes are known | `README.md` "Verify it yourself"; `artifacts/merkle_root.json` `algorithm` field |
| 7 | 31 Aug 2026, first live morning; fills at 09:45, 09:55, 10:05, 10:21 ET; 7 contracts each; expiry 2026-10-02; 4 condors where the design intended 1 | `RISK_REGISTER.md` 4.7 para 1 |
| 7 | Artifact seq 30, timestamp 2026-08-31T09:50:05-04:00: gate 5 reads "0/5 positions open"; `mcp_calls[1]` `get_all_positions` result contains `SPY261002C00792000`; `reconciliation[0]` says "no legs at broker; closed or expired" for `pos-d041f0056d` | `artifacts/decisions.jsonl` seq 30; named in RISK_REGISTER 4.7 para 3 |
| 7 | Root cause: `positions()` parsed a "positions" key that does not exist; the server wraps the list as `{"data": {"result": [...]}}` | RISK_REGISTER 4.7 para 2 |
| 7 | 9 regression tests in `tests/test_position_sync.py` | RISK_REGISTER 4.7 fix 5; `pytest --collect-only` on that file: 9 collected |
| 7 | Combined max risk $10,840 = 10.8% of equity | RISK_REGISTER 4.7 para 1 |
| 8 | Equity $100,036.93; P&L +$36.93 so far | seq 554 `portfolio.equity` (see PARAMS) |
| 8 | 4 condors, 28 contracts (4 x 7), $3,108 credit | `artifacts/positions.json`: credits 1.11, 1.14, 1.10, 1.09 x 7 contracts x 100 = 777 + 798 + 770 + 763 = 3,108 |
| 8 | Worst case capped at $10,840 | `positions.json` max_loss_per_contract 3.89 + 3.86 + 3.90 + 3.835 = 15.485 x 700 = 10,839.50; RISK_REGISTER 4.7 says $10,840 |
| 8 | Deadline flatten starts 90 minutes before the 4 Sep 11:00 ET submission deadline | RISK_REGISTER 4.6; WRITEUP "Risk gates" last sentence |
| 8 | Tail hedge designed and coded, never engaged live; Alpaca served zero VIX contracts on both feeds; refusal logged every cycle | RISK_REGISTER 4.9; README "A tail hedge" paragraph |
| 8 | 90 `hedge:no_candidate` artifacts in the log (12 of 12 since 28 Aug as of 1 Sep) | `make summary` 2026-09-02; RISK_REGISTER 4.9 |
| 9 | 211 tests | `pytest tests/ --collect-only`: 211 collected; README "Verify it yourself" |
| 9 | github.com/nilaymastaadmi/alpaca-hackathon | `git remote -v`; SUBMISSION_FORM.md |
| all | Challenge name "Options Alpha Agents"; solo entry; paper account PA37R35A5ZGW | SUBMISSION_FORM.md; WRITEUP.md line 3 |

## Traceable but cut for time (not in the video)

- 85 cycles ran on Tuesday 1 Sep: 85 `refuse` records dated 2026-09-01 in `decisions.jsonl`; `HANDOFF.md` line 19 says the scheduled task runs 85 cycles. 344 exit checks: 344 `exit_check:hold` records dated 2026-09-01.
- 1.5% of credit round trip on a real fill (README "Measured, not assumed"; n=1 per RISK_REGISTER open items). 5 ladder rungs (WRITEUP).
- Prize pool $6,000 (RISK_REGISTER, resolved 2026-08-29). First live refusal: IV 12.81 vs trailing realised 13.28 (README para 1).
- Multiple-testing bar 0.791 with N=7 (WRITEUP). Cut because D3 and slide 7 say 0.792; see discrepancies.

## Discrepancies found while tracing (not fixed; all outside presentation/video/)

1. `presentation/WRITEUP.md` says "Alpaca MCP Server v3.4.7 with 74 tools". README and RISK_REGISTER 4.8 say alpaca-mcp-server 2.3.0 on FastMCP 3.4.7. The video says "Alpaca's official MCP server" and "74 tools" with no version number.
2. Multiple-testing bar: WRITEUP and SUBMISSION_FORM say 0.791; DEPLOYMENT_DECISIONS D3 and slide 7 say 0.792. The video does not quote it.
3. README "What the research found that did NOT work" still says "The deployed agent trades 7-14 DTE (T4)". D3 switched to T6 (21-45 DTE) on 30 Aug. The video follows D3 and WRITEUP.
4. `slides_draft.pdf` page 8 says "10 risk gates" and page 10 shows T4 as deployed. Both stale, so the video renders its own architecture and comparison visuals from README and D3 instead of using those two slides full frame. Slide 5 (H1 numbers) is current and is used.
5. RISK_REGISTER 4.7 gives fill times 09:45, 09:55, 10:05, 10:21 ET. The enter artifacts are seq 28, 32, 36, 42 with cycle timestamps 09:45:05, 09:55:05, 10:05:05, 10:20:05 ET; `positions.json` opened_at for the fourth is 14:21:40Z = 10:21:40 ET. The video uses the fill times from 4.7.
6. The dev account PA308NOY3X36 appears 18 times inside `artifacts/decisions.jsonl` (2 early records carry it as `account_number`). The seq 30 excerpt rendered on screen is built from named fields only, and build.py greps every rendered text asset and caption for that string and aborts if found.
7. `make` is not installed on this machine (Git Bash and PowerShell both lack it). build.py runs the exact commands the Makefile targets run and labels them `make verify` and `make summary` on screen, which is what a judge would type.
