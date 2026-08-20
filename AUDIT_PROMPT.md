# Audit prompt for a fresh session

Copy everything below the line into a new session, run from
`C:\Users\toshn\alpaca-hackathon`.

---

You are auditing a hackathon submission that is 8 days from going live with real
judging. Adopt the posture of three people at once, and do not soften any of them:

- **A buy-side options trader with 15 years running short-volatility books.** You
  have seen people blow up selling premium. You are not impressed by backtests.
- **A judge for this exact hackathon** who has read 60 other submissions today and
  is looking for the reason to score this one down.
- **A staff engineer doing a pre-production readiness review** on a system that
  will run unattended overnight with money at stake.

## What this is

A volatility-risk-premium agent for the Alpaca AI Trading Agents Hackathon (Track
2, Volatility and Event). It sells defined-risk SPY iron condors when implied
volatility is measurably above trailing realised, refuses when it is not, hedges
the tail with VIX calls, and logs every decision into a Merkle-verified artifact
trail.

Live window: **31 Aug to 4 Sep 2026, roughly 4.5 trading days.** Judged on P&L,
technology implementation, creativity, presentation, and social engagement.

Read these first, in this order:
- `README.md`, the pitch and the honest limitations
- `STRATEGY.md`, the plan with every claim tagged measured/sourced/assumed
- `research/PREREGISTRATION_R1.md`, the design committed before any backtest existed
- `research/RESULT_H3_ROBUSTNESS.md`, where the strategy result is attacked
- `RISK_REGISTER.md`, what is already known to be risky
- `agent/`, the live system. `backtest/`, the research.

## Rules of engagement

1. **Verify by running, not by reading.** `make test` (138 tests), `make verify`,
   `make dry-run`. Claims in markdown are claims. Re-derive anything load-bearing.
2. **Assume the previous author was motivated to look good.** Find where the
   framing is more confident than the evidence. There are known soft spots listed
   below; your job is to find the ones NOT listed.
3. **Do not congratulate.** A finding that something is fine is only worth writing
   if you actually tried to break it and failed, and then say how you tried.
4. **Rank by expected cost**, not by how interesting the bug is. A cosmetic issue
   in the demo video may cost more points than a subtle statistical flaw.
5. Research externally and hard. Cite what you find. Published evidence beats
   opinion, and trading-blog content is close to worthless (this project already
   rejected several claims on those grounds).

## Known soft spots, so you go past them rather than rediscovering them

- H3 clears its bar at Sharpe +1.614, but doubling transaction costs IMPROVED
  Sharpe, which is impossible. The optimiser is partly selecting noise. The
  ungated baseline beats the gated variants on average.
- The pricing model carries a residual +10% overprice bias, which for a premium
  seller inflates credits, so H3 is an upper bound.
- Skew is calibrated from a single volatility regime (August 2026) and assumed
  stationary. It steepens in stress.
- The 1.5% round-trip fill cost is n=1, measured once in calm conditions.
- Live sizing (5 concurrent at 3%, so 15% concurrent) deviates deliberately from
  the 1% research sizing. All five positions are the same underlying and the same
  direction, so they hit max loss together.
- Data is Alpaca's INDICATIVE options feed, not OPRA.
- **The agent's ENTRY path has never run end to end.** Every live cycle so far has
  refused, correctly. `place_laddered(opening=True)` has only been exercised by a
  standalone test script, not through the agent's own code path. The ledger write,
  the fill artifact, and the exit that follows are untested in sequence.

## What I want from you

### 1. Break it
Find the failure modes nobody has thought about. Particularly:
- What happens on a **partial fill** of a 4-leg order? On an **assignment**? On an
  **expiry while a position is open**? Trace each path in code and say what breaks.
- Is there any path where the agent can end up **short an unhedged option**?
- What happens if the MCP server dies mid-cycle, returns malformed JSON, or hangs
  after the order is placed but before the response is read?
- Can the agent **double-open** the same structure across cycles?
- Does anything **silently swallow an exception** in a way that would look like a
  quiet, healthy no-trade?

### 2. Attack the numbers
- Re-derive H1 independently. Is `+3.68` vol points and Newey-West `t = +4.74`
  right? Is 21 lags the correct HAC choice for 21-day overlapping windows?
- Is the walk-forward genuinely out of sample, or does anything leak?
- Given the residual pricing bias and the noise-selection problem, **what is the
  honest expected P&L over 4.5 days at the deployed sizing?** State a range.
- Is the tail hedge correctly sized, and does the put-call-parity forward recovery
  hold up under a stressed or thin chain?

### 3. Judge it
Score it against the five published criteria and say where it loses points.
Assume competitors include professional options traders and strong engineers.
**What is the single highest-leverage change in the remaining 8 days?**

### 4. Propose something new
One or two things worth trying BEFORE the window opens that are not in the plan.
Judge them on evidence and on whether they fit 8 days solo, not on novelty. Say
plainly if the honest answer is "add nothing, the risk is execution not ideas."

## Constraints you must respect

- **Do not relitigate settled decisions** without new evidence: Track 2, solo,
  Windows over WSL, the 15% live sizing, and iron condors as the structure. If you
  believe one is wrong, say so once with the evidence and move on.
- **The holdout window (2023-01-01 to 2026-08-18) is SEALED** and has never been
  touched. `data.window(df, "holdout")` raises unless deliberately unsealed. One
  shot is permitted, only after a development trial clears its bar. **Do not spend
  it**, and treat any suggestion to peek as a finding against whoever suggests it.
- Do not add trials to the pre-registered research without incrementing N and
  recomputing the bar. Searching costs you the right to claim the winner.
- Never attribute a commit to Claude or Anthropic. Author is Nilay Toshniwal.
- No em-dashes in any prose you write.

## Deliverable

Write `research/AUDIT_2026-08-20.md`:

1. **Verdict in three sentences.** Would this place top 3? Why or why not?
2. **Findings table**, ranked by expected cost, each with severity, evidence
   (a command that reproduces it, or a file and line), and the fix.
3. **The numbers you re-derived**, with what you got versus what was claimed.
4. **The one change** to make in the remaining 8 days.
5. **What you tried to break and could not.** This is the section that tells me
   how far you actually looked.

Do not commit anything except that file without telling me first.
