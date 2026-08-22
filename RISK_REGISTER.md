# RISK REGISTER

Everything that could bite during the live window (28 Aug to 4 Sep 2026) and is
not obvious from the code. Rule exposure, calendar traps, free-tier ceilings that
could be exhausted before the event starts, and operational failure modes.

Status key: **OPEN** needs action, **MITIGATED** handled, **ACCEPTED** known and
tolerated, **RESOLVED** closed with evidence.

---

## 1. Free tier and quota ceilings

### 1.1 Streamlit app was LOGIN-GATED. OPEN, needs one toggle
Deploying from a private repo made the app private. Measured 2026-08-20:
`HTTP 303 -> /-/login`, health endpoint returns `{"status":"ok"}`, so the app is
running but **not viewable by anyone without an invite**.

The submission requires an Application URL "for interactive evaluation". A judge
hitting a login wall scores what they can see, which is nothing.

**Fix, one toggle, no redeploy:** App settings, Sharing, "Who can view this app",
select "This app is public and searchable". App visibility is INDEPENDENT of repo
visibility, so the repo can stay private while the app is public.

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

### 2.3 Reused account disqualification. OPEN until the fresh account exists
"Projects run on an existing or reused account will not be eligible for judging."
The practice account `PA308NOY3X36` has trade history on it from the fill test and
is permanently disqualified. Tracked in `SUBMISSION_CHECKLIST.md`.

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
Gate 8 blocks new short premium within one day of a scheduled event and cuts
existing exposure. Tested.

### 3.3 Labor Day. NO IMPACT
Mon 7 Sep is a market holiday, confirmed absent from the Alpaca calendar. It falls
after the deadline. Note the live agent reads real listed expiries from the chain,
so it cannot pick a non-existent 7 Sep expiry. The BACKTEST's synthetic
Mon/Wed/Fri expiry generator would include it, which is a backtest artifact only.

### 3.4 Quarterly expiry. ACCEPTED
Triple witching is Fri 18 Sep, outside the window. A position opened 3 Sep at the
14 DTE maximum expires 17 Sep, just before it. FOMC is 15-16 Sep, also outside.
Both are irrelevant if we are flat at submission, which the checklist recommends
for separate reasons.

---

## 4. Operational failure modes

### 4.1 THE BIG ONE: the laptop sleeping kills the agent. OPEN
US market hours are 19:00 to 01:30 IST. The agent must run unattended overnight,
every night, Mon 31 Aug to Fri 4 Sep.

`propdesk` documented this exact failure with numbers: "Sleeping the laptop hangs
in-flight HTTP permanently. Threads block inside the client's own session, which
`socket.setdefaulttimeout` does not reach. Observed twice, 11.5h and 4.8h of a
live process producing nothing."

A hung agent does not crash loudly. It sits there looking alive while the trading
window passes. **This is the single most likely way the live week produces no
trades**, and no amount of strategy work protects against it.

Needs a decision before kickoff: disable sleep for the week, run somewhere that
does not sleep, or add a watchdog that kills and restarts a cycle whose progress
has stalled. `propdesk` found a watchdog can recover from it but not prevent it.

### 4.2 Network interception. ACCEPTED
`reference_machine_state` records this machine hitting TLS interception on at
least one network. Worth knowing which network the agent runs on during the week.

### 4.3 Deployed dashboard shows stale artifacts. OPEN
The dashboard renders whatever artifacts are COMMITTED. Nothing currently commits
them as the agent runs, so a judge opening the URL on 3 Sep sees decisions dated
20 Aug, on a page whose entire pitch is "here is what the agent decided". Needs a
commit-artifacts step in the agent loop.

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

---

## 5. Watch list, no action yet

- Technology partners were "to be announced" and may add prize surfaces.
- Whether Social Engagement is a separate podium, as it was in the precursor
  Kraken event, is ambiguous on the page. Ask at kickoff.
- The measured 1.5% round-trip fill is n=1 in calm conditions. Re-run the ladder
  across different sessions before treating it as a constant.
