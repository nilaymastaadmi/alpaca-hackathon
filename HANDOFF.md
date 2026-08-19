# HANDOFF

Last updated 2026-08-19. First version of this file, nothing to supersede.

## What this project is

Entry for the **Alpaca AI Trading Agents Hackathon** (lablab.ai x Alpaca), online build
28 Aug - 4 Sep 2026, kickoff 28 Aug 8:30 PM IST. $5,000 prize pool, judged partly on paper-account
P&L. Full rules/requirements digest lives in Claude memory, not here: see
`project_sep2026_hackathon_run.md` in the memory system (or ask Claude to recall it). Short
version of what's binding:

- Strategy **must trade options** (pick one of 4 tracks: directional / volatility-event /
  hedging / income-overlay).
- Must use Alpaca's **MCP server or CLI**, not just the raw REST API.
- Final submission needs a **brand-new, never-reused** Alpaca paper account, separate from
  whatever was used for practice/dev. **The account set up below is the practice account and
  must NOT be the one submitted.**

## State as of 2026-08-19, verified this session (not just claimed)

**No project code exists yet.** This session was pure environment setup, zero lines of strategy
or agent code written. `git status` confirms the repo has **no commits at all**, everything is
untracked:

```
On branch main
No commits yet
Untracked files: .gitignore  check_keys.ps1  check_keys.sh
```

(`.env` doesn't even show as untracked, `.gitignore` is correctly excluding it, checked directly.)

**Environment: Windows, by explicit decision, not WSL.** Owner was told WSL was more consistent
with every other personal project (propdesk, nebula, career-ops, tata-vayu-hackathon all live
there) and chose Windows anyway ("run it in windows then"). Don't relitigate this.

- Project root: `C:\Users\toshn\alpaca-hackathon`
- `uv`/`uvx` installed at `C:\Users\toshn\.local\bin`, package cache warmed (`uvx alpaca-mcp-server
  --help` runs in ~2s now, first run took longer downloading 70 packages)
- git identity confirmed correct (global): `Nilay Toshniwal <toshniwalnilay@gmail.com>`
- A duplicate copy exists at `~/alpaca-hackathon` in WSL (where this was originally built before
  the Windows switch). It's orphaned now, not deleted, not being used. Ignore it unless told
  otherwise.

**Alpaca practice account, live-verified via direct API call this session** (not just assumed
from the dashboard):

- Signed up with owner's **college email**, deliberately as a throwaway/practice account
- account_number `PA308NOY3X36`, internal id (UUID) `db5804bb-c39f-43d6-8b75-9d4e74a42672`
- `options_approved_level: 3` and `options_trading_level: 3` (max tier) **by default**, no extra
  approval needed for any of the 4 hackathon tracks, confirmed by an actual `/v2/account` response
- Keys live in `C:\Users\toshn\alpaca-hackathon\.env` (gitignored):
  `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER_TRADE=true`

**MCP server registered and connected**, checked via `claude mcp list` immediately before writing
this file:

```
alpaca: uvx alpaca-mcp-server --env-file C:\Users\toshn\alpaca-hackathon\.env - Connected
```

Registered at **user scope**, so it's available in any Claude Code session on this machine, not
just ones opened in this folder. Full tool list (account, orders, positions, options chains,
quotes, watchlists, etc.) is in the `alpaca-mcp-server` README on GitHub if needed.

**Known gotcha from this session:** putting the raw secret key directly in a shell command (even
just to `curl` a test) gets blocked by Claude Code's auto-mode permission classifier. Route any
raw-credential check through a script that reads `.env` internally instead (see
`check_keys.ps1` in this folder for the pattern), the literal secret should never appear in a
command string handed to a tool call.

## Resume commands

```powershell
cd C:\Users\toshn\alpaca-hackathon
claude mcp list          # confirm alpaca still shows Connected
.\check_keys.ps1          # direct REST smoke test, bypasses MCP entirely
```

If a **new** Claude Code session is running (required for it to see the Alpaca tools at all,
registering mid-session doesn't hot-load), just ask it directly: "what's my Alpaca paper account
balance" or similar, no special setup needed.

## Decisions made, don't relitigate

- **Windows over WSL**: owner's explicit call, 2026-08-19, against the recommendation.
- **College-email account is practice-only.** A second, completely untouched account must be
  created specifically for the graded submission. Do not let the practice account's trade history
  end up in what gets submitted.
- **Options approval needs no separate step**: confirmed empirically, don't re-derive or
  re-question this.

## Track decision, locked 2026-08-19, do not relitigate

**Track 2: Volatility & Event Trading Agents.** Mechanism: systematic short-premium iron condors
(4-leg, defined-risk), entered when an underlying's IV rank is elevated, harvesting the volatility
risk premium. Owner's instruction driving this: "i want to win it... i need you to choose", full
reasoning (track-fit, propdesk evidence bar, precursor-hackathon winner pattern, why not the other
3 tracks) lives in Claude memory (`project_sep2026_hackathon_run.md`), not duplicated here.

**Team: solo**, by explicit choice, despite teams being allowed up to 6.

**Not logging this in the career-ops Notion pipeline**: owner said "forget notion" 2026-08-19;
Bhide (`~/bhide`) is the live deadline pipeline now anyway, Notion is legacy.

## Not yet done / open

1. **No fresh submission-only account created yet**: fine to leave until closer to the actual
   build, but don't forget it needs to happen before anything gets submitted.
2. **Pre-kickoff IV/greeks history logger**: being built this session (2026-08-19). Needed
   because Alpaca's option chain snapshot only exposes current IV, not a trailing window, and the
   Track 2 strategy needs IV rank. Runs daily on the practice account (explicitly allowed
   pre-kickoff per the hackathon page) so real history exists by the 28 Aug kickoff.
3. **Agent decision loop, rule-engine risk gates, and cockpit dashboard**: not started, this is
   Aug 28+ build work. Architecture direction (reusing propdesk's rule-engine pattern and Chikki's
   cockpit pattern) is decided; code is not written.

## Verified this session (2026-08-19, second pass)

MCP tools now actually tested (not just direct REST): `get_account_info` called successfully,
confirmed live against the practice account. `place_option_order` confirmed to support multi-leg
(`order_class="mleg"`, up to 4 legs), needed for the iron condor structure the locked track uses.
