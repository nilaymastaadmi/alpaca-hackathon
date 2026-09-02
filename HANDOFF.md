# HANDOFF

Last updated 2026-09-01 (live-week status added; body below otherwise from
2026-08-22, which superseded the 2026-08-19 version entirely). Read this
file first in any new session; it is the index, not the detail: the files
it points to hold the actual reasoning.

## Live week status, as of Tue 2026-09-01 morning

- **The agent is LIVE on the fresh account `PA37R35A5ZGW` and holds 4 iron
  condors** (28 contract-sets, all exp 2026-10-02, max risk $10,840 = 10.8%
  of equity, P&L about -$100). It was supposed to be 1 position; a parse
  bug read the account as flat every cycle and stacked 4. Full incident,
  root cause, and fix: `RISK_REGISTER.md` 4.7. The 3 extras were ADOPTED
  into the ledger (Nilay's call, 2026-09-01), not closed.
- **A second same-day save:** fastmcp 4.0.0 shipped upstream and kills
  `alpaca-mcp-server` at startup; versions now pinned in `mcp_client.py`.
  See `RISK_REGISTER.md` 4.8. Do not unpin during the competition.
- The daily task (`AlpacaHackathon-LiveAgent`, 18:50 IST, 85 cycles x 5
  min) now has RestartOnFailure 3x5min; Monday's run was killed at cycle
  13 of 85 by a console close (exit 0xC000013A). Do not close the console
  window it opens.
- Flatten policy per Nilay 2026-09-01: trade the maximum available cycles.
  Deadline flatten stays as configured, Friday 09:30-11:00 ET, AFTER the
  08:30 ET NFP print. Gate 8 blocks new entries 3-4 Sep as designed.
- Tests: 211 passing (9 new regression tests in
  `tests/test_position_sync.py`). Merkle seal verifies.

## What this project is

Entry for the **Alpaca AI Trading Agents Hackathon** (lablab.ai x Alpaca).
Online build **28 Aug – 4 Sep 2026**, kickoff Fri 28 Aug 20:30 IST, deadline
Fri 4 Sep 20:30 IST. **$6,000 total prize pool, corrected 2026-08-29 from the
official kickoff email** (this file previously said $5,000, never verified
against a primary source): 1st $2,500 + $300 Featherless credits, 2nd
$1,500, 3rd $1,000, **Social Engagement is confirmed as its own podium, not
folded into the main score: 2 teams x $500 plus a month of Algo Trader Plus
each.** That was an open question in `RISK_REGISTER.md` until now. Judged
on P&L, Technology Implementation, Creativity & Originality, Presentation &
Execution, Social Engagement (no published weights). Solo entry, by
explicit choice.

Binding rules, per the official email: autonomous agent using Alpaca's
Trading API; must use Alpaca's MCP server or CLI, not raw REST; strategy
must incorporate options trading; final submission needs a brand-new paper
account starting at exactly $100,000 (the practice account below is
disqualified, has trade history on it); repo must be public **at submission**
(currently already public: flipped early, no downside, see below). **New
from the same email, not yet in `SUBMISSION_CHECKLIST.md`: a one-page
write-up covering AI logic, risk gates, and Alpaca infrastructure
implementation**: distinct from the "long description" submission field,
not yet drafted.

**Resolved 2026-08-29, checked against the live hackathon page directly.**
There is no "Track 2" or "Volatility and Event" track on the current page ,
just one main challenge, "Options Alpha Agents," open-ended ("options,
trading agents, portfolio income, or other approaches"). "Track 2" was
either dropped between 19 Aug and now or was always this repo's own
shorthand, not an official category. Fixed in `README.md`'s tagline;
`STRATEGY.md` keeps "Track 2" as informal internal shorthand with a note
explaining it, since the underlying research reasoning is unaffected.

**Also confirmed from the live page, not previously precise:**
- Prize pool is **$6,000 cash** (1st $2,500, 2nd $1,500, 3rd $1,000, Social
  Engagement 2x$500) **plus $300 in Featherless credit for 1st place and
  $25 per participant regardless of placement**: the page states both
  "$6,000" and "$6,300" depending on whether the Featherless credits are
  counted; $6,000 is the cash actually paid by AlpacaDB.
- Payment mechanics, relevant if this places: prizes pay to an
  **individual**, not a team/company; requires **W-9 (US) or W-8BEN
  (non-US)**, government photo ID, bank details; **non-US payments face
  30% US withholding unless a tax-treaty claim is filed on the W-8BEN**;
  paid within 90 days of documents clearing.
- Submission fields include a **"Demo application platform"** field
  distinct from the Application URL itself (i.e., naming Streamlit Cloud
  specifically, not just the link).
- **Corrected 2026-09-01: the showcase is LIVE and rotating, these are real
  current competitors.** A repeat page read a day apart showed a different
  entry set both times, so the earlier "almost certainly carried-over"
  guess was wrong and is withdrawn. As of 1 Sep the showcase lists roughly
  40 entries, of which one, "VRP Engine: Autonomous Options Agent on
  Alpaca," pitches a near-identical strategy (VRP harvesting, defined-risk
  spreads, risk gates, API+MCP+CLI), and at least 6 more lead with
  refuses-by-default / auditable / deterministic-gates framing (Vetoed,
  Aegis, EdgeStack, Horizon Blackline, SPY Sentinel AI, Vermilion). The
  refusal line is no longer a differentiator on its own; the pre-registered
  research discipline (git-provable timestamps, N-corrected bars, sealed
  holdout, recorded wrong predictions) is what nobody else claims, and the
  pitch should lead with it.

## Repo and deployment state, verified not assumed

- **GitHub: https://github.com/nilaymastaadmi/alpaca-hackathon: PUBLIC**, ~20
  commits, all authored `Nilay Toshniwal <toshniwalnilay@gmail.com>` (rule 9
  clean, checked against the remote, not just locally).
- **Streamlit: https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/
 : confirmed PUBLIC** by following the full redirect chain with `curl -sL`
  (a single-hop check gives a false 303-to-login; the real app is behind an
  auth broker that grants anonymous access and bounces back: 3 redirects,
  final HTTP 200). Renders live artifact data.
- **195 tests passing**, run via `make test` (or
  `uv run --with pytest --with tzdata --with requests python -m pytest tests/ -q`
  if the Makefile target ever drifts: it needs tzdata+requests because
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
falls entirely inside the sealed holdout window: doesn't invalidate anything
reported, but must be disclosed if the holdout is ever spent). Results in
`RESULT_H1_H2.md` (H1 decisive, t=+4.74), `RESULT_PRICING_GATE.md` (failed at
26.78% first, fixed, passed at 10.75%), `RESULT_H3.md` + `RESULT_H3_ROBUSTNESS.md`
(clears its bar but is fragile: doubling costs improved Sharpe, which is
impossible, meaning the optimiser partly selects noise), `RESULT_SWEEP.md`
(EXPLORATORY, not evidence: 35 configs, none promoted).

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
  readiness on every run and never proposes a number itself: see
  `research/RECALIBRATION_STATUS.md`. As of 2026-08-22: **NOT READY, 1
  usable sample.**
- **D3, DECIDED 2026-08-30**: deployed tenor switched from T4 (7-14 DTE) to
  **T6 (21-45 DTE)**. Not T7, despite T7 having the cleaner backtest case
  (Sharpe +1.697, no cost-stress anomaly): eight days of live comparison
  data (`research/D3_COMPARISON_LOG.md`) showed T4 at 0/21 would-enter
  cycles and T7 at 1/21, while T6 went 10/21, all in the two most recent
  days, with VRP climbing. An agent that never trades cannot score on the
  P&L Performance criterion regardless of research quality. T6's known
  cost-sensitivity anomaly is real and disclosed, not hidden. Applied to
  `agent/config.py`. Shipped together with a new `deadline_flatten_enabled`
  mechanism (forces a full flatten 90 minutes before the 4 Sep submission
  deadline) since T6's longer hold will not reach natural expiry inside the
  judged week otherwise. Full reasoning: `research/DEPLOYMENT_DECISIONS.md`
  D3.

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
- Gate 2 said "HALT and flatten"; only halt was real: now actually flattens
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
  filled" cannot happen: the real risk is parent-quantity partial fill)

`RISK_REGISTER.md` tracks status on everything. As of 2026-08-22 two items
are open by design, not by neglect: 2.2 (confirm pre-kickoff work is allowed,
cheap to ask in the Discord at kickoff) and 2.3 (the fresh submission-only
account, deliberately not created yet, see item 4 below). Everything else,
including the laptop-sleep item and a stale Streamlit login-gate label found
during this pass, is MITIGATED, RESOLVED or ACCEPTED.

## What's still open, and whose job each one is

1. **Laptop sleep/scheduling: FOUR separate causes found and fixed.** (1)
   idle timeout, (2) lid-close, (3) display timeout on battery dragging
   Modern Standby into suspend regardless of the idle setting -- first
   clean 15-hour overnight window achieved 2026-08-26 with zero sleep
   events. (4) found 2026-08-27, a DIFFERENT class of bug: both scheduled
   tasks had Task Scheduler's default `DisallowStartIfOnBatteries`, so on
   battery the run is silently refused with no sleep event at all -- fixed
   via `Set-ScheduledTask`, verified by a successful manual re-trigger.
   **If the live agent is ever run via a Scheduled Task rather than
   interactively, check its settings for this explicitly** -- do not
   assume it inherits the fix just because these two tasks got it. A
   genuine low-battery forced-hibernate was also found and deliberately
   left alone (real safety feature) -- **keep the machine on AC for the
   live week** regardless of all four fixes. Full detail:
   `RISK_REGISTER.md` 4.1. `agent/watchdog.py` remains as defence for any
   other hang cause.
2. **D2 threshold recalibration: still open, independent of D3 now that D3
   is decided.** `prep/recalibrate_threshold.py` exists and self-reports
   readiness; last checked NOT READY. Re-run any time; nightly-safe. Note
   the threshold it is calibrating (gate 7's VRP bar) now governs T6's
   21-45 DTE strikes, not T4's, since D3 switched tenors: the readiness
   check reads whatever `agent/config.py` currently deploys, so this is
   already correct without needing its own update.
2b. **LIVE_WEEK_TRADE_ODDS.md's 28-33% figure was about T4 specifically,
   and D3 (below) responds directly to it.** That analysis is why D3 was
   revisited rather than left as a backtest-only proposal. Worth a fresh
   odds calculation for T6 once a few live week days exist, but the
   qualitative answer already changed: T6 has been entering multiple times
   a day on real market data, not sitting at zero.

3. **D3: DECIDED, see below.** Deployed tenor is T6 (21-45 DTE), not T4
   or T7. Full reasoning: `research/DEPLOYMENT_DECISIONS.md` D3.
4. **Fresh submission-only paper account: CREATED 2026-08-28.** Account
   number **`PA37R35A5ZGW`** (this is the ID to submit: not the practice
   one). Verified live via the real MCP path, not assumed from the
   dashboard: status ACTIVE, not blocked, options_trading_level 3 already
   approved, zero orders, zero positions, $100,000 starting equity,
   created_at 2026-08-28T06:31:05Z. Genuinely fresh and distinct from
   `PA308NOY3X36`.

   Credentials live in **`.env.live`**, gitignored (`.env.*` pattern),
   deliberately kept separate from `.env` (the practice account) so
   nothing accidentally mixes the two. `agent.py` and `watchdog.py` both
   take `--env-file` now (defaults to `.env` if omitted): the comparison
   harness and any ad-hoc dry-run keep using the practice account unless
   `--env-file .env.live` is passed explicitly.

   Every `Decision` artifact now also records `account_number` (added
   2026-08-28), since the artifact log itself now spans a switch between
   two accounts and nothing else in the record said which one produced a
   given entry.

   **Still to do, needs the market open: run ONE live fill test on the
   fresh account before Monday 31 Aug**, the same check already done on
   the practice account. Not run yet: market was closed both times this
   was touched today.

4b. **`AlpacaHackathon-LiveAgent` scheduled task, created 2026-08-27,
   pointed at the fresh account 2026-08-28.** Fires daily 18:50 IST
   starting **Mon 31 Aug** (10 min before the 19:00 open), runs
   `watchdog.py --publish --max-cycles 85 --env-file .env.live` (~7h at
   the 5min interval, self-terminating after the 01:30 IST close so each
   night's run ends clean). Battery restrictions already removed at
   creation. Smoke-tested end to end on 2026-08-27 against the practice
   account (1 dry-run cycle, completed, auto-published, commit
   `621665e`) and again on 2026-08-28 against the fresh account directly
   via `agent.py --dry-run --env-file .env.live` (completed, real
   `account_number` in the artifact). **Friday 28 Aug's post-kickoff
   session is deliberately NOT covered**: run it by hand if wanted.
5. **Presentation: video and slide polish wait for real live-week data,
   deliberately** (Nilay, 2026-08-30). Cover image and a slide draft exist
   in `presentation/`; the deck's live-results slide is a marked
   placeholder. The one-page write-up (AI logic, risk gates, Alpaca
   infrastructure) does not need real results and is not deferred -- see
   `presentation/WRITEUP.md`.
6. **Social posts: DECLINED, not merely unstarted.** Nilay confirmed
   2026-08-30 there will be no social posts for this submission. This
   forfeits the Social Engagement judging axis and both $500 podium slots
   entirely -- a deliberate scope decision, not a gap to close. Do not
   draft, suggest, or post social content for this project; do not re-raise
   this as an open item.

## Explicitly investigated and rejected, don't re-raise without new evidence

- **XSP as a second instrument**: checked live 2026-08-22: zero IV, zero
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
`research/RESULT_H3_T7.md`. This made T7 the natural first pick, and it was
proposed as such (D3) on this basis alone.

**It was not, in the end, what got deployed.** Eight days of live comparison
data disagreed with the backtest-only picture: T7 traded almost as rarely as
T4 (1/21 live cycles), while T6 -- backtest-flagged but not backtest-broken
-- actually fired repeatedly on real market data. D3 was revised 2026-08-30
to deploy T6 instead, with the known caveat disclosed rather than hidden.
See `research/DEPLOYMENT_DECISIONS.md` D3 for the full reasoning on both
sides.

## Standing rules for this project, don't relitigate

Windows over WSL (explicit call, 2026-08-19). Solo (explicit call). Track 2
(explicit call, "i need you to choose"). D1 sizing (explicit call, 2026-08-19,
5 concurrent / 3%). Notion pipeline not used for this ("forget notion").
Author on every commit is Nilay Toshniwal, never Claude/Anthropic (global
rule 9). No em-dashes in anything written for this repo (global rule 1) ,
matters more than usual here since the repo is public.

## Resume commands

```powershell
cd C:\Users\toshn\alpaca-hackathon
git log --oneline -5              # confirm state matches this file
make test                          # 195 tests, ~13s
uv run --with requests --with tzdata python agent/agent.py --dry-run
```
