# RISK REGISTER

Everything that could bite during the live window (28 Aug to 4 Sep 2026) and is
not obvious from the code. Rule exposure, calendar traps, free-tier ceilings that
could be exhausted before the event starts, and operational failure modes.

Status key: **OPEN** needs action, **MITIGATED** handled, **ACCEPTED** known and
tolerated, **RESOLVED** closed with evidence.

---

## 1. Free tier and quota ceilings

### 1.1 Streamlit app login gate. RESOLVED
Originally login-gated (measured 2026-08-20: `HTTP 303 -> /-/login`) because
deploying from a private repo made the app private. Fixed via the app's own
Sharing setting, independent of repo visibility. **Confirmed genuinely public**
by following the FULL redirect chain (`curl -sL -c cookiejar -b cookiejar`,
reading the final status at the end of a 3-hop anonymous-grant auth broker
chain, not a single-hop check): HTTP 200. A single-hop check gives a false
303-to-login even on a genuinely public app, which caused this to be
mis-diagnosed as still broken for a while after the actual fix landed.

### 1.2 Streamlit Community Cloud ceilings. ACCEPTED
- **1 private app** on the free tier. Ours uses it. Public apps are unlimited, so
  once 1.1 is toggled this ceiling stops binding.
- **~1 GB memory.** The dashboard reads JSON off disk and renders tables. Not close.
- **Apps sleep after ~12 hours without traffic**, roughly 30 seconds to wake.
  Mitigation is in `SUBMISSION_CHECKLIST.md`: visit daily during the build week so
  a judge is not the one waking it.
- No custom domains. Irrelevant here.

### 1.3 Alpaca free Basic plan. ACCEPTED, but one detail belongs in the submission
- **200 requests per minute.** Measured live in the rate-limit headers. One agent
  cycle uses roughly 10 to 25 calls, so a 5 minute cadence uses under 5% of the
  budget. Not a risk.
- **Equities: IEX only**, not the full SIP consolidated feed.
- **Options: the INDICATIVE feed, not OPRA.** This is the detail worth stating
  plainly rather than discovering in a judge's question. Every spread, implied vol
  and greek this project measured came from the indicative feed. It is the same
  feed the agent will use during the window, so nothing is invalidated and no
  comparison is broken, but "we measured 1.5% round-trip cost" should carry "on
  Alpaca's indicative options feed" beside it.
- **No monthly volume cap found** on the Basic plan, only the per-minute rate. So
  the ~20,000 historical option bars already pulled have not consumed a quota that
  the live week would need. This was the specific worry and it does not apply.
- Historical option data exists only from **February 2024**, which is why the H3
  pricing model had to be validated against 2024 onward rather than the full
  development window.

### 1.4 Everything else. RESOLVED
GitHub (no Actions in use), PyPI/uv, and CBOE's free unauthenticated CSV endpoints
carry no relevant limits.

---

## 2. Rules exposure

### 2.1 MIT compliance. MITIGATED
Prize terms state "Submissions must be original and MIT-compliant." No LICENSE
existed. MIT LICENSE added. Dependency licences are all compatible: alpaca-py and
streamlit are Apache 2.0, pandas and numpy are BSD.

### 2.2 Pre-kickoff work. OPEN, ask at kickoff
The official rulebook contains **no clause** about when code may be written, and
the event page explicitly says to "get a head start on your project" and to "use
any paper account you like during development". A general lablab guidance article,
not the rulebook, mentioned core AI functionality being built in-window.

Cheap to confirm in the Discord, expensive to assume. Git history is honest about
what was built when, which is the right posture either way.

### 2.3 Reused account disqualification. MITIGATED 2026-08-28
"Projects run on an existing or reused account will not be eligible for judging."
The practice account `PA308NOY3X36` has trade history on it from the fill test and
is permanently disqualified. Never submit it.

Fresh account `PA37R35A5ZGW` created 2026-08-28, credentials in gitignored
`.env.live`, never mixed into `.env`. Genuinely fresh, checked live rather than
assumed: zero orders, zero positions, ACTIVE, not blocked, options level 3
already approved, $100,000 starting equity. `AlpacaHackathon-LiveAgent` points
at it via `--env-file .env.live`; every other tool (comparison harness, ad-hoc
dry-runs) keeps defaulting to the practice account so nothing accidentally
trades or queries on the wrong one. The first live fills on this account
happened 31 Aug 09:45 ET (4 condors through the MCP path, see 4.7).

### 2.4 Commit attribution. RESOLVED
All 16 commits authored and committed as Nilay Toshniwal. No Claude or Anthropic
attribution, no session trailers, no `claude/*` branches. Verified against the
pushed remote, not just locally.

---

## 3. Calendar traps

### 3.1 The window is 4.5 trading days, not 7. MITIGATED
Verified against Alpaca's own `/v2/calendar`. Kickoff Fri 28 Aug 11:00 ET is
mid-session, deadline Fri 4 Sep 11:00 ET is mid-session. Real trading is Mon 31
Aug through Thu 3 Sep plus Friday morning. The agent must be live at Monday's open.

### 3.2 NFP lands INSIDE the window. MITIGATED
Nonfarm payrolls Fri 4 Sep 08:30 ET, 2.5 hours before the submission deadline.
Gate 8 blocks new short premium within one day of a scheduled event (so from
Thursday's session onwards). It does NOT reduce existing exposure; that was
an overpromise in an earlier version of this entry, see 4.6. The open book
rides through the print by decision (2026-09-01, DEPLOYMENT_DECISIONS D3
addendum) and is flattened 09:30 to 11:00 ET Friday.

### 3.3 Labor Day. NO IMPACT
Mon 7 Sep is a market holiday, confirmed absent from the Alpaca calendar. It falls
after the deadline. Note the live agent reads real listed expiries from the chain,
so it cannot pick a non-existent 7 Sep expiry. The BACKTEST's synthetic
Mon/Wed/Fri expiry generator would include it, which is a backtest artifact only.

### 3.4 Quarterly expiry. ACCEPTED
Triple witching is Fri 18 Sep, outside the window. The deployed tenor (T6, 21
to 45 DTE since D3) means every live position expires 2 Oct, well past both
witching and the 15-16 Sep FOMC. Irrelevant either way, because the deadline
flatten closes the book Friday morning before submission.

---

## 4. Operational failure modes

### 4.1 THE BIG ONE: the laptop sleeping kills the agent. Four separate causes found across four checks; all four now fixed, first clean overnight window achieved 2026-08-26
US market hours are 19:00 to 01:30 IST. The agent must run unattended overnight,
every night, Mon 31 Aug to Fri 4 Sep.

`propdesk` documented this exact failure with numbers: "Sleeping the laptop hangs
in-flight HTTP permanently. Threads block inside the client's own session, which
`socket.setdefaulttimeout` does not reach. Observed twice, 11.5h and 4.8h of a
live process producing nothing."

A hung agent does not crash loudly. It sits there looking alive while the trading
window passes. **This is the single most likely way the live week produces no
trades**, and no amount of strategy work protects against it.

**Mitigated: `agent/watchdog.py` exists and is tested.** Every cycle runs in a
separate subprocess with an OS-enforced timeout, since an in-process timer
cannot rescue a thread stuck in a syscall but killing the process can. Smoke
tested with two real supervised cycles (15.3s, 15.0s against a 240s default
timeout). This recovers from a hang; per propdesk's own finding, it does not
prevent the laptop from sleeping in the first place, only shortens how long a
sleep event costs.

**Idle-timeout sleep disabled 2026-08-22.** Nilay ran
`powercfg /change standby-timeout-dc 0` and
`powercfg /change hibernate-timeout-dc 0` (a system settings change, correctly
kept out of scope for this agent to run unilaterally). Verified after the
fact with `powercfg /query SCHEME_CURRENT SUB_SLEEP`: both `STANDBYIDLE` and
`HIBERNATEIDLE` DC indices read `0x00000000` (never), AC already was.

**Then caught mid-test, same day: this was NOT the whole problem.** A test
run that normally takes ~13s took 3545s (59:05). Windows event log
(`Microsoft-Windows-Kernel-Power`, IDs 506/507) showed Modern Standby entered
at 18:38:37 and exited at 19:37:33, **Reason: Lid** -- a ~59 minute gap that
matches the test stall almost to the second. The idle-timeout fix above does
nothing for lid-close: that is a separate Windows power setting
(`SUB_BUTTONS` / lid-close-action GUID `5ca83367-...`), and it was still at
its default (sleep) the whole time.

**Fixed via the registry after `powercfg /query` failed to even show the
setting** on this machine's OEM "SAMSUNG MODE" scheme (a scheme quirk, not a
missing setting -- some OEM schemes hide settings from `/query` that are
still live). Set `ACSettingIndex` and `DCSettingIndex` to `0` (Do Nothing)
directly under
`HKLM:\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\<scheme>\4f971e89-eebd-4455-a8de-9e59040e7347\5ca83367-6e45-459f-a27b-476b1d01c936`,
confirmed written via `Get-ItemProperty` immediately after. **Not physically
verified**: nothing here can close the lid and check. Nilay should close the
lid for 10-15 seconds on both AC and battery and confirm the machine is
still responsive on open, ideally before relying on it for the live week.

**A THIRD, bigger cause found 2026-08-25, from the scheduled tasks
themselves going quiet.** Both `AlpacaHackathon-IVSnapshot` and
`AlpacaHackathon-D3Compare` missed their 21:30/21:40 slot on 2026-08-23,
caught up once at 11:20/11:21 the next day, then missed the 21:30/21:40 slot
AGAIN on 2026-08-24 and stayed asleep until 02:09 on 2026-08-25 (over 5.5
hours, discovered when this session opened the lid). Windows event log
(`Kernel-Power` 506/507, event 42) showed the real cause: **display timeout
on battery power (`VIDEOIDLE` DC) was still 180 seconds**, AC was already 0.
On this Modern Standby machine, the screen turning off routinely drags the
whole system into suspend shortly after, regardless of the `STANDBYIDLE`
("PC goes to sleep after") setting being 0 -- the idle-timeout fix at the
top of this entry closed one path, the lid fix closed a second, and this
was a third, independent path through the exact same symptom. Also found,
separately, and NOT touched: a genuine low-battery forced-hibernate fired
at 03:16 on 2026-08-24 (`BATACTIONCRIT` = Hibernate at 2% battery). That is
a real hardware safety feature, correctly left alone -- the fix here is
**keep the machine on AC power for the live week**, not disable low-battery
protection.

Fixed: `powercfg /change monitor-timeout-dc 0`, verified via
`powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE`: DC now reads
`0x00000000` matching AC. **Given this is the second time a "fixed"
sub-cause turned out to be incomplete, do not treat this as closed on
paper alone.** The real test is an unattended overnight stretch with no
missed scheduled-task runs; the daily D3 comparison and IV snapshot tasks
are themselves now serving as that canary.

**First clean overnight window: 2026-08-26, 21:23 to 12:08 next day (~15
hours), zero sleep/wake events, every scheduled run fired on time.** Real
evidence, not just settings verified on paper.

**A FOURTH, completely different cause found 2026-08-27, invisible to
everything above.** `AlpacaHackathon-D3Compare` failed its 02:40 run with
Win32 error 4320, "the operator or administrator has refused the request"
-- no sleep or wake event logged anywhere near that time, because this
isn't a sleep problem at all. Both scheduled tasks were created with
Windows Task Scheduler's own default: `DisallowStartIfOnBatteries = True`,
`StopIfGoingOnBatteries = True`. On battery power, at the scheduled
moment, the task refuses to even start -- silently, with no sleep event to
find in a log, which is exactly why the three fixes above wouldn't have
caught it. This is a materially different risk from "the machine went to
sleep": the machine can be fully awake and the scheduled run can still
never happen.

Fixed: `Set-ScheduledTask` on both tasks with
`AllowStartIfOnBatteries`/`DontStopIfGoingOnBatteries`/`StartWhenAvailable`.
Verified by manually triggering `AlpacaHackathon-D3Compare` immediately
after: `LastTaskResult` went from the error to `0`, and a genuine new cycle
landed in `research/D3_COMPARISON_LOG.md`.

**This generalises beyond these two tools.** Any Windows Scheduled Task
created with default settings on this machine will refuse to run on
battery. If the live agent itself is ever scheduled the same way for the
hackathon week (rather than run interactively via `agent/watchdog.py`),
its settings need the same fix BEFORE kickoff, checked explicitly, not
assumed from these two tasks having been fixed.

The watchdog remains as defence for any other cause of a hung cycle.

### 4.2 Network interception. ACCEPTED
`reference_machine_state` records this machine hitting TLS interception on at
least one network. Worth knowing which network the agent runs on during the week.

### 4.3 Deployed dashboard shows stale artifacts. MITIGATED
This was open when first written. `agent/publish.py` now commits and pushes
`artifacts/decisions.jsonl`, `merkle_root.json` and `positions.json` from
inside the agent loop when run with `--publish`. Only `artifacts/` is ever
staged (tested), failures return a status rather than raising (a git problem
must not stop the agent managing real positions), and it is opt-in per-run
since it pushes to a remote. `agent/watchdog.py --publish` propagates the flag
through supervised cycles. Confirmed working: a real `Agent artifacts ...`
commit exists in the repo history from an actual `--publish` run.

### 4.4 Parent-quantity partial fills. MITIGATED, mechanism corrected 2026-08-22
This entry originally described the risk as "a condor that fills three of four
legs is a naked short." That is not how MLeg orders behave: confirmed directly
against Alpaca's own documentation, the four legs of a single multi-leg order
"fill together or not at all", so a single MLeg order cannot leave individual
legs mismatched the way this entry claimed.

The real partial-fill risk is at the PARENT QUANTITY, not the legs: a 6-contract
order can fill for 3, with all four legs of those 3 contracts filled together.
`broker._await_fill` now handles `partially_filled` explicitly (cancels the
remainder immediately rather than letting it rest), and `_fill_result` records
the actual `filled_qty` so the ledger stores what was really bought rather than
what was requested. Both are tested in `tests/test_broker.py`.

`positions.reconcile()`'s CRITICAL flag remains correct and necessary, just for
a different cause than originally stated: not a same-order leg mismatch, but
the ledger and the broker disagreeing after the fact (a manual intervention, a
missed fill notification, or a position closed outside the agent's own loop).

### 4.5 Paper engine does not check order size against available liquidity. ACCEPTED
Documented by Alpaca: order quantity is not checked against NBBO size, so paper
can fill far more than really exists. We size as if liquidity were real and say so
in the submission rather than banking the flattery.

### 4.6 T6's 21-45 DTE positions will not close naturally before judging. MITIGATED 2026-08-30
D3 (`research/DEPLOYMENT_DECISIONS.md`) switched the deployed tenor from T4
(7-14 DTE) to T6 (21-45 DTE) on 2026-08-30, because T4 had gone 0-for-21 on
real would-enter cycles while T6 went 10-for-21. The tradeoff: a 21-45 DTE
position opened any day during the live week (31 Aug - 4 Sep) cannot reach
its own natural profit-target or DTE exit before the 4 Sep 11:00 ET
deadline. Left alone, judges would see a mark-to-market snapshot of an open
position rather than a realised result.

Found the same day: `event_derisk_fraction` in `agent/config.py` existed for
exactly this class of problem (reduce exposure ahead of a scheduled event)
and was never wired to an action anywhere -- gate 8 blocked new entries near
NFP/FOMC but nothing ever reduced an existing position, despite README
describing that as what the gate does. The same "the gate's message
overpromises the code" bug 4.4 and the original drawdown-flatten fix (audit,
2026-08-20) already caught once, in different gates.

**Fixed with a dedicated mechanism, not a reuse of the event-derisk path**:
`deadline_flatten_enabled` (default on) forces an unconditional full flatten
of every open position starting 90 minutes before the submission deadline
(market open on 4 Sep, using the whole available window rather than one
attempt at the buzzer) and blocks all new entries once that window opens.
Tested in `tests/test_deadline_flatten.py` (the trigger-window logic, a pure
function of config and time) and `tests/test_flatten.py` (the actual close
mechanics, reused from the drawdown breaker's flatten, unchanged). `gate 8`'s
own `event_derisk_fraction` remains unwired and is a separate, lower-priority
gap -- NFP/FOMC are temporary de-risk-and-resume events where "block new
entries, leave existing ones" is a defensible partial mitigation on its own;
the deadline is final and gets its own mechanism instead of stretching that
one to cover a case it was not designed for.

---

### 4.7 LIVE INCIDENT 2026-08-31: the agent stacked 4 condors believing it was flat every time. FIXED 2026-09-01, positions adopted

What happened, from the sealed artifacts and the broker's own order log:
on the first live morning the agent entered 4 iron condors in 36 minutes
(fills 09:45, 09:55, 10:05, 10:21 ET, 7 contracts each, all expiring
2026-10-02), where the design (`one_per_expiry=True`) intended exactly 1.
Every cycle read the account as flat: gate 5 said 0/5 open at 10:20 while
the broker already held 3 condors. Combined max risk reached $10,840,
10.8% of equity, inside the 15% D1 cap by luck, not by any gate.

Root cause, one line: `broker.positions()` parsed the MCP payload with a
"positions" key that does not exist; the server wraps it as
`{"data": {"result": [...]}}`. It therefore returned [] for EVERY response,
and `reconcile()` dropped each ledger entry as "closed elsewhere" one cycle
after its fill. The bug survived 12 days of dry runs because the practice
account really was flat, so the empty and the broken read were identical.
The orders path 280 lines below parses "result" correctly.

The evidence that pinned it is the project's own audit trail: artifact seq
30 contains BOTH the raw MCP response listing `SPY261002C00792000` AND the
reconcile drop that ignored it, in the same sealed record. The Merkle log
did exactly what it was built for, against its own author.

Second failure in the same window: the watchdog was killed at 19:52 IST
(exit 0xC000013A, a console close or Ctrl+C) after 13 of 85 planned cycles,
so the stacked book then sat unmonitored from Mon 10:21 ET to Tue evening.

Fixes, all landed 2026-09-01 before the Tuesday session:
1. `positions()` parses the real wrapper and RAISES on an unrecognised
   shape rather than defaulting to "flat". An empty book is an active claim
   the whole risk stack builds on, never a safe fallback.
2. `reconcile()` now checks the broker-to-ledger direction too: option legs
   on the traded underlying covered by no ledger position are CRITICAL
   orphans, which gate 0 turns into a HALT. The ledger-to-broker check
   alone passes vacuously on an empty ledger, which is precisely how this
   ran unnoticed.
3. The 3 orphan condors were adopted into the ledger from their real fill
   records (order ids, fill prices, fill timestamps), decided by Nilay
   2026-09-01 over trimming back to 1: 10.8% concurrent risk is within the
   15% D1 cap, and exits, breakers and the deadline flatten now manage all
   4. Realised cost of the incident so far: roughly -$100 unrealised at
   Tuesday 01:40 ET, each position valued at +2% to +5% of max profit.
4. The scheduled task got RestartOnFailure (3 restarts, 5 minutes apart),
   so a killed watchdog self-heals instead of silently ending the day.
5. 9 regression tests in `tests/test_position_sync.py`, including the
   exact live wrapper shape and the exact orphan set from this incident.

### 4.8 Upstream dependency broke the MCP server overnight. PINNED 2026-09-01

`uvx alpaca-mcp-server` re-resolves its environment whenever PyPI moves. On
the morning of 2026-09-01 it started pulling fastmcp 4.0.0 (with mcp 2.1.1),
and alpaca-mcp-server 2.3.0 imports `fastmcp.tools.tool`, which 4.0.0
removed: the server dies at startup, before the first request. Monday's
live run worked only because uvx still had the previous resolution cached
(fastmcp 3.4.7, mcp 1.29.1). Tuesday's session would have started with
zero working cycles; RestartOnFailure would have retried into the same
crash 3 times and stopped.

Caught by running one dry-run cycle against the live account during the
2026-09-01 audit, not by any test: every test mocks this boundary, which is
the correct place for tests to stop and exactly why a daily pre-session
smoke run earns its place. `mcp_client.py` now pins all three packages
(`fastmcp==3.4.7`, `mcp==1.29.1`, `alpaca-mcp-server==2.3.0`). Do not unpin
mid-competition.

---

### 4.9 The tail hedge never engaged live: no VIX expiry inside its window is quoted. ACCEPTED 2026-09-01, facts corrected 2026-09-02

Every live hedge attempt returned `n_quotes=0`: 129 `hedge:no_candidate`
artifacts through 2 Sep 12:50 ET. The first version of this entry said
Alpaca served no VIX option data at all. Re-probed 2026-09-02 after Alpaca
announced index options for live trading, with narrower questions:

- `get_option_chain` VIX, indicative feed, 20 Sep to 25 Oct: quotes ARE
  served, live-stamped, for the 21 Oct monthly (VIX261021C...).
- The same call over the hedge's own window, 21 to 45 days (23 Sep to
  17 Oct): empty snapshot set.
- `get_option_contracts` VIX, calls, strike 20: the VIXW weeklies of 23 Sep
  and 30 Sep exist, are active and tradable (open interest 15,434 and
  2,977), and are exactly the expiries inside the window. The feed
  returns no snapshots for them.
- OPRA feed: 403, "OPRA agreement is not signed", on this account.

So the precise statement is: the indicative feed quotes monthly VIX
expiries only, and no monthly fell inside 21 to 45 days at any point in
the live week (16 Sep was 14 to 16 days out, 21 Oct was 49 to 51). The
hedge's window and the feed's coverage never overlapped. README and
`presentation/WRITEUP.md` corrected the same day.

Decision: hedge stays enabled and the window stays 21 to 45. Widening it
to catch 21 Oct on the last two sessions would buy a position the deadline
flatten deliberately never sells, leaving an unrealised VIX call on the
judged number. From the start of the flatten window onwards, new hedge
buys are frozen along with new entries (`_entries_frozen`, 2026-09-02).
The refusal artifacts remain the evidence that the design refuses to hedge
off an untrustworthy read; the purchased wings were the only crash
protection all week.

- Technology partners were "to be announced" and may add prize surfaces.
- The measured 1.5% round-trip fill is n=1 in calm conditions. Re-run the ladder
  across different sessions before treating it as a constant.

**Resolved 2026-08-29 from the official kickoff email, removed from this
list:** Social Engagement IS a separate podium, 2 teams x $500 plus a month
of Algo Trader Plus each, distinct from the 1st/2nd/3rd prizes. Total pool
is $6,000, not the $5,000 assumed everywhere in this repo until now. See
`HANDOFF.md` and `SUBMISSION_CHECKLIST.md` for the full breakdown.

---

### 4.10 The deadline flatten worked, and two record defects it exposed. RESOLVED 2026-09-04

The submission-deadline flatten fired on schedule at 09:32 ET and closed the
book with 58 minutes to spare. Realised P&L for the week: **-$273.87** on the
$100,000 paper account, against a mark of -$565.07 going in. The ladder
recovered roughly half the mark by filling from mid as post-NFP spreads
tightened, rather than crossing at the open.

Two defects surfaced, both in the RECORD rather than in the trading:

1. **The per-position close reason named the wrong trigger.** `_flatten_all`
   hardcoded "drawdown breaker: portfolio-level HALT and flatten", and the
   deadline flatten reuses that function, so four sealed artifacts say a
   breaker fired when it had not. The enclosing note was correct throughout.
   Fixed the same day: the trigger is a parameter and the deadline path
   passes its own text. The wrong-reason artifacts stay in the log, because
   the log is append-only and rewriting it to look clean would defeat its
   entire purpose. This entry is the correction.

2. **A filled close reported as `close_failed`.** `pos-14aabefe5a` returned
   close_failed on two consecutive flatten attempts. The order had actually
   filled; the confirmation did not arrive inside the poll window. Gate 0
   caught it on the next cycle: the ledger claimed a position the broker had
   no legs for, reconciliation flagged "no legs at broker; closed or
   expired", and cleared it. Ledger, the MCP view and the independent CLI
   read all agree at zero legs. This is the position-integrity gate doing
   exactly what it exists for, on the last position of the competition, and
   it is why that gate checks in both directions.

Accepted, not fixed: the poll window is not lengthened. A close that fills
without a timely confirmation is recoverable by reconciliation on the next
cycle, which is what happened. Blocking a cycle longer to wait would be the
worse trade.

**Why the week lost money, since the strategy's own thesis held.** Implied
volatility stayed above trailing realised on every single day (ATM IV 11.6
to 12.8 against trailing RV 7.2 to 10.3), so the volatility risk premium
being sold was present throughout. The loss came from direction, not from
the premium: SPY rallied from 765.20 to 772.71 on 3 Sep, a 0.98% move that
cost $707 in one session by pushing spot toward the 792 short call. That is
the known cost of being short gamma, and it is exactly what "one week of
options P&L is mostly noise" means in practice. Four trading days is not a
sample; it is one draw.

