# HANDOFF

Last updated 2026-08-22. Rewritten from scratch; the 2026-08-19 version is
entirely superseded (that version predates the strategy, the agent, and
everything else below). Read this file first in any new session; it is the
index, not the detail — the files it points to hold the actual reasoning.

## What this project is

Entry for the **Alpaca AI Trading Agents Hackathon** (lablab.ai x Alpaca).
Online build **28 Aug – 4 Sep 2026**, kickoff Fri 28 Aug 20:30 IST, deadline
Fri 4 Sep 20:30 IST. $5,000 pool. Judged on P&L, Technology Implementation,
Creativity & Originality, Presentation & Execution, Social Engagement (no
published weights). Solo entry, by explicit choice.

Binding rules: strategy must trade options (Track 2, Volatility & Event,
locked 2026-08-19); must use Alpaca's MCP server or CLI, not raw REST; final
submission needs a brand-new paper account (the practice account below is
disqualified, has trade history on it); repo must be public **at submission**
(currently already public — flipped early, no downside, see below).

## Repo and deployment state, verified not assumed

- **GitHub: https://github.com/nilaymastaadmi/alpaca-hackathon — PUBLIC**, ~20
  commits, all authored `Nilay Toshniwal <toshniwalnilay@gmail.com>` (rule 9
  clean, checked against the remote, not just locally).
- **Streamlit: https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/
  — confirmed PUBLIC** by following the full redirect chain with `curl -sL`
  (a single-hop check gives a false 303-to-login; the real app is behind an
  auth broker that grants anonymous access and bounces back — 3 redirects,
  final HTTP 200). Renders live artifact data.
- **195 tests passing**, run via `make test` (or
  `uv run --with pytest --with tzdata --with requests python -m pytest tests/ -q`
  if the Makefile target ever drifts — it needs tzdata+requests because
  `agent.py` imports `ZoneInfo("America/New_York")` at module load, and
  Windows ships no IANA tzdata by default).
- Practice account (dev-only, DO NOT submit): `PA308NOY3X36`, keys in
  `.env` (gitignored, never touch this from a shell command directly, see
  `check_keys.ps1` pattern).

## Strategy, in one sentence

Sell defined-risk SPY iron condors (4-leg, wings by fixed width not delta)
only when the volatility risk premium at the actual traded strikes is
measurably rich; refuse otherwise. Full reasoning: `STRATEGY.md`.

**Research** (`research/`): `PREREGISTRATION_R1.md` (committed before any
backtest code existed, provable from git history) plus two dated amendments
(A1: sizing/units fixes; A2: flags that the pricing model's calibration data
falls entirely inside the sealed holdout window — doesn't invalidate anything
reported, but must be disclosed if the holdout is ever spent). Results in
`RESULT_H1_H2.md` (H1 decisive, t=+4.74), `RESULT_PRICING_GATE.md` (failed at
26.78% first, fixed, passed at 10.75%), `RESULT_H3.md` + `RESULT_H3_ROBUSTNESS.md`
(clears its bar but is fragile — doubling costs improved Sharpe, which is
impossible, meaning the optimiser partly selects noise), `RESULT_SWEEP.md`
(EXPLORATORY, not evidence — 35 configs, none promoted).

**Holdout (2023-01-01 to 2026-08-18) has NEVER been touched.** Enforced in
code (`backtest/data.py`'s `window()` raises unless deliberately unsealed).
One shot permitted, only after a dev trial clears its bar. Do not spend it.

**Deployment decisions** (`research/DEPLOYMENT_DECISIONS.md`):
- **D1**: live sizing is 5 concurrent positions at 3% risk each (15% max
  concurrent), a deliberate deviation from the 1%-research sizing, because at
  research sizing the agent expected 0.76 trades all week. Corrected
  2026-08-22 with an independently re-derived empirical P&L range (script:
  `backtest/deployed_config_pnl_range.py`): mean +$207/window, 0% of 1,737
  historical windows breached -10%. This *disagrees* with an earlier
  adversarial audit's more pessimistic estimate by an order of magnitude;
  both readings and the likely reason for the gap are recorded honestly in
  the file rather than picking one.
- **D2**: gate 7 was measuring IV at the wrong tenor (30-day ATM instead of
  the actual ~11-day short strikes sold), a bias of about +1 vol point,
  always in the permissive direction. Fixed in code
  (`signals.short_strike_iv`). **The threshold itself (1.0) stays
  provisional.** `prep/recalibrate_threshold.py` (added 2026-08-22) checks
  readiness on every run and never proposes a number itself — see
  `research/RECALIBRATION_STATUS.md`. As of 2026-08-22: **NOT READY, 1
  usable sample.**
- **D3, PROPOSED not decided**: switch the deployed tenor from T4 (7-14 DTE)
  to T7 (5-10 DTE). A properly pre-registered trial (amendment A3,
  2026-08-22) cleared a freshly recomputed N=7 bar at Sharpe +1.697, best of
  all seven trials, without T6's cost-stress anomaly. Full case and the
  open decision: see D3 below and `research/RESULT_H3_T7.md`. **Not applied
  to `agent/config.py`.**

## The agent (`agent/`)

`mcp_client.py` (real MCP over stdio, verified against Alpaca MCP Server
v3.4.7, 74 tools) → `signals.py` (VRP, term structure, short-strike IV) →
`risk.py` (11 numbered gates, 0-10, circuit breakers distinguished from
ordinary refusals) → `broker.py` (execution, double-open guard, laddered
fills) → `positions.py` (ledger, exits, conservative fallback valuation) →
`hedge.py` (VIX call tail hedge via put-call parity, wired into `agent.py`) →
`artifacts.py` (Merkle-verified decision log, `make verify` recomputes the
root) → `publish.py` (commits artifacts so the deployed dashboard isn't
stale) → `watchdog.py` (kills hung cycles via OS-enforced subprocess timeout,
because a sleeping laptop hangs in-flight HTTP permanently and looks alive
while doing nothing).

Run: `uv run --with requests --with tzdata python agent/agent.py --dry-run`.
Live: same without `--dry-run`, or via `agent/watchdog.py --publish` for
supervised unattended cycles.

## The adversarial audit, and every finding closed (2026-08-20 to 2026-08-22)

A fresh-session audit (`research/AUDIT_2026-08-20.md`, prompt template in
`AUDIT_PROMPT.md`) found real bugs. All fixed, each with tests that reproduce
the original failure:
- A double-open path (an order could duplicate after a lost network response)
- Gate 2 said "HALT and flatten"; only halt was real — now actually flattens
- The tail hedge module existed with 23 tests but was never called anywhere
- Gate 7's tenor mismatch (D2, above)
- A stop-loss blind spot when a single wing's quote went dark
- Several smaller mislabels (gate 9 called a one-way estimate "round trip", a
  backwards idempotency-key docstring, dead code, a fabricated-reading bug in
  the term-structure fallback)
- Documentation corrections: the pricing-model/holdout tension (A2, above),
  D1's dollar figures, a T6-vs-deployed-T4 Sharpe conflation, an overclaiming
  Newey-West sentence, a RISK_REGISTER mechanism error (confirmed against
  Alpaca's own docs: MLeg legs fill together or not at all, so "3 of 4 legs
  filled" cannot happen — the real risk is parent-quantity partial fill)

`RISK_REGISTER.md` tracks status on everything. As of 2026-08-22 two items
are open by design, not by neglect: 2.2 (confirm pre-kickoff work is allowed,
cheap to ask in the Discord at kickoff) and 2.3 (the fresh submission-only
account, deliberately not created yet, see item 4 below). Everything else,
including the laptop-sleep item and a stale Streamlit login-gate label found
during this pass, is MITIGATED, RESOLVED or ACCEPTED.

## What's still open, and whose job each one is

1. **Laptop sleep — THREE separate causes found and fixed across three
   checks, still not proven over a real unattended night.** (1) idle
   timeout, (2) lid-close, (3) found 2026-08-25 when both scheduled tasks
   went quiet for 19+ hours across two nights: display timeout on battery
   was still 180s, and on this Modern Standby machine screen-off drags the
   whole system into suspend regardless of the idle-timeout setting. All
   three now set to "never." A genuine low-battery forced-hibernate was also
   found and deliberately left alone (real safety feature) -- **keep the
   machine on AC for the live week**, don't rely on the sleep fixes alone.
   Full detail and the exact commands: `RISK_REGISTER.md` 4.1. **Given the
   first two "fixes" each turned out incomplete, treat this as unverified
   until the D3 comparison and IV snapshot scheduled tasks show 2-3 clean
   consecutive nights with no missed runs** (`Get-ScheduledTaskInfo` on
   both). `agent/watchdog.py` remains as defence for any other hang cause.
2. **D2 threshold recalibration — decide T7 (D3) first, or run in parallel.**
   `prep/recalibrate_threshold.py` exists and reports NOT READY (1 usable
   sample of the corrected quantity, as of 2026-08-22; Aug 19 was pre-fix,
   Aug 20's logged snapshot had no delta-bearing contract in the traded DTE
   band despite the live D2 verification succeeding that same day, Aug 21
   was missed to the sleep bug now fixed above). Re-run any time; it is
   nightly-safe and self-reports how many more nights are needed from its
   own current variance estimate.
3. **D3 decision: adopt T7 (5-10 DTE) as the deployed tenor, or keep T4.**
   New as of 2026-08-22. See `research/DEPLOYMENT_DECISIONS.md` D3. This is
   the one item on this list that is a genuine judgement call for Nilay, not
   a blocked-on-data or blocked-on-time item — the backtest evidence exists
   now, the question is whether one clean development-window pass is enough
   to change what trades live money in the judged week.
4. **Fresh submission-only paper account.** Deliberately NOT created yet —
   confirmed with Nilay 2026-08-22 there's no reason to rush it. Do it a day
   or two before kickoff (not day-of, in case options-level-3 approval has
   any delay), then run one live fill test on it before 31 Aug.
5. **Presentation: video, slides, cover image.** All mandatory, all still at
   zero. **Nilay's own task** ("we'll make the presentation dw", 2026-08-22),
   not something to push on unprompted.
6. **Social posts** (up to 5, X/LinkedIn) — correctly not started, since the
   rules require they be dated *during* the hackathon window.

## Explicitly investigated and rejected, don't re-raise without new evidence

- **XSP as a second instrument** — checked live 2026-08-22: zero IV, zero
  delta on every contract, same data gap VIX had. Building proper pricing for
  it would replicate days of already-done SPY-specific work. Not a lever.

## A short tenor WAS properly tested, not just the sweep peak (2026-08-22)

The earlier version of this file said the 3-7 DTE sweep number (scoring
almost 2x the deployed tenor) was deliberately not adopted, since it came
from the exploratory sweep labelled "not evidence." That reasoning still
holds for 3-7 DTE specifically. But rather than leave it there, a proper
pre-registered trial was run at a nearby, deliberately-not-cherry-picked
band: **T7 (5-10 DTE)**, amendment A3 to `PREREGISTRATION_R1.md`, registered
before its code existed, with the multiple-testing bar recomputed from N=6
to N=7 (0.760 to 0.792) before the result was seen.

**T7 clears the recomputed bar at Sharpe +1.697, the best of all seven
trials, and does not show T6's noise-selection red flag** (Sharpe falls
under cost stress, the normal direction, instead of rising). Full result:
`research/RESULT_H3_T7.md`. This is now a live, undecided deployment
question, not a rejected path — see **D3** in
`research/DEPLOYMENT_DECISIONS.md`: switch the live tenor from T4 (7-14 DTE)
to T7 (5-10 DTE)? Proposed, not yet decided by Nilay. Not applied to
`agent/config.py`.

## Standing rules for this project, don't relitigate

Windows over WSL (explicit call, 2026-08-19). Solo (explicit call). Track 2
(explicit call, "i need you to choose"). D1 sizing (explicit call, 2026-08-19,
5 concurrent / 3%). Notion pipeline not used for this ("forget notion").
Author on every commit is Nilay Toshniwal, never Claude/Anthropic (global
rule 9). No em-dashes in anything written for this repo (global rule 1) —
matters more than usual here since the repo is public.

## Resume commands

```powershell
cd C:\Users\toshn\alpaca-hackathon
git log --oneline -5              # confirm state matches this file
make test                          # 195 tests, ~13s
uv run --with requests --with tzdata python agent/agent.py --dry-run
```
