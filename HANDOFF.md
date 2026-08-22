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
  provisional** — no re-derivation without real data, and as of 2026-08-22
  only ONE usable night of correct-tenor calibration data exists (see below).

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

`RISK_REGISTER.md` tracks status on everything; as of 2026-08-22 only one
item is still open.

## What's still open, and whose job each one is

1. **Laptop sleep.** `agent/watchdog.py` recovers from a hang but does not
   prevent the laptop sleeping in the first place. **This is Nilay's action,
   not mine** — `powercfg` is a system settings change, out of scope for this
   agent to run unilaterally even with shell access. Commands:
   `powercfg /change standby-timeout-dc 0` and
   `powercfg /change hibernate-timeout-dc 0`. Matters twice: for the live
   week, and right now, because the same bug already ate one calibration
   night (Aug 21's logger run silently didn't fire).
2. **D2 threshold recalibration.** Blocked on data, not effort. As of
   2026-08-22 the corrected-tenor (5-45 DTE) logger has exactly ONE usable
   night (Aug 20; Aug 19 was pre-fix, Aug 21 was missed to the sleep bug).
   Re-deriving a threshold from one observation would repeat the exact
   mistake this project's whole discipline exists to prevent. Depends on #1
   above actually getting fixed so the nightly logger runs reliably through
   kickoff.
3. **Fresh submission-only paper account.** Deliberately NOT created yet —
   confirmed with Nilay 2026-08-22 there's no reason to rush it. Do it a day
   or two before kickoff (not day-of, in case options-level-3 approval has
   any delay), then run one live fill test on it before 31 Aug.
4. **Presentation: video, slides, cover image.** All mandatory, all still at
   zero. **Nilay's own task** ("we'll make the presentation dw", 2026-08-22),
   not something to push on unprompted.
5. **Social posts** (up to 5, X/LinkedIn) — correctly not started, since the
   rules require they be dated *during* the hackathon window.

## Explicitly investigated and rejected, don't re-raise without new evidence

- **XSP as a second instrument** — checked live 2026-08-22: zero IV, zero
  delta on every contract, same data gap VIX had. Building proper pricing for
  it would replicate days of already-done SPY-specific work. Not a lever.
- **Switching to a 3-7 DTE tenor** — the exploratory sweep shows it scoring
  almost 2x the deployed tenor's Sharpe, and it is deliberately NOT adopted.
  That number comes from the sweep explicitly labelled "not evidence" (never
  one of the 6 pre-registered H3 trials), and 3-7 DTE sits uncomfortably
  close to the 0DTE zone already found to be a coin-flip with fat tails a
  single Sharpe number hides. Acting on it would be exactly the cherry-picking
  failure mode the pre-registration discipline exists to prevent.

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
