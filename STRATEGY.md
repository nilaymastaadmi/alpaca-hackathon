# STRATEGY, Alpaca AI Trading Agents Hackathon

Written 2026-08-19, after a research pass. Companion to `HANDOFF.md` (which holds environment
state). This file holds the *plan* and the *evidence behind it*. Nothing here is built yet.

Every claim below is tagged: **[measured]** = verified against the live API or a primary source
this session. **[sourced]** = from published research/competitor evidence. **[assumed]** = a
judgement call, flagged so it can be attacked later.

---

## 1. The binding constraint: the agent gets ~4.5 live trading days, not 7

**[measured]**: pulled from Alpaca's own `/v2/calendar` for the window:

| Date | Session | Usable? |
|---|---|---|
| Fri 28 Aug | 09:30–16:00 ET | Kickoff is 11:00 ET (= 20:30 IST). Ceremony + planning. ~0 |
| Sat 29 – Sun 30 Aug | closed | Build sprint |
| Mon 31 Aug | 09:30–16:00 ET | **full day** |
| Tue 1 Sep | 09:30–16:00 ET | **full day** |
| Wed 2 Sep | 09:30–16:00 ET | **full day** |
| Thu 3 Sep | 09:30–16:00 ET | **full day** |
| Fri 4 Sep | 09:30–16:00 ET | **09:30–11:00 only**: submission closes 11:00 ET (20:30 IST) |
| Mon 7 Sep | *absent from calendar* | Labor Day, confirmed closed (after deadline anyway) |

**Consequence: the agent must be live and trading at Monday 31 Aug 09:30 ET or a quarter of the
P&L window is gone.** That makes the weekend (29–30 Aug) the real build sprint, not a buffer.
Everything in the plan below is arranged around that single deadline.

This one fact invalidates the obvious version of the strategy, see §4.

---

## 2. What actually wins this, from the one directly comparable event

lablab.ai ran the near-identical **AI Trading Agents** hackathon (Kraken CLI + ERC-8004),
30 Mar – 12 Apr 2026: 2,752 participants, 631 teams, 107 apps. **[measured]** from the recap page.
The Alpaca event currently shows ~1,121 registered, a smaller field.

**[sourced]** Every single finalist led with risk engineering and verifiability, not returns:

| Finalist | What it led with |
|---|---|
| Vertex Sentinel | "fail-closed security layer", circuit breakers, no key delegation |
| **JudyAI WaveRider** | 7-layer risk mgmt, walk-forward validation, ERC-8004 identity, *built with Claude Code* |
| Vartovii Sentinel-8004 | signed trade permits, "judge-friendly proof artifacts" |
| ARIA | 3 strategies, **13 risk gates**, every decision posted on-chain |
| Swiftward Harness | multi-agent analysis + "declarative risk engine" |

Recurring vocabulary across all five: *risk gates, circuit breakers, fail-closed, proof
artifacts, verifiable*. Not one led with a return number.

### The single most important data point

**JudyAI WaveRider was a finalist while LOSING money live:** −$377 (−0.38%) on $100k over 11+
days, 40% win rate on 24 trades. **[sourced]**

What it won on instead:
- Walk-forward optimisation, 8 rolling windows (IS=90d / OOS=30d), **366 out-of-sample trades**
- 82.2% OOS win rate, profit factor 3.75, expectancy +0.58R, max DD −8.7%
- 7 named risk layers; live drawdown held to −0.4%
- 93 tests (59 unit / 21 integration / 13 integrity)
- **214 audit artifacts under a SHA-256 Merkle tree, judges run `make verify` to recompute the
  root hash themselves**
- An explicitly honest framing: *a production agent that loses 0.38% in bad markets beats a demo
  agent showing 80% win rates on cherry-picked data*

**Three conclusions, and they drive the whole plan:**

1. **A modest or even slightly negative P&L does not disqualify you.** A blow-up probably does.
   So the objective is *not* maximise expected return, it is **minimise variance while keeping
   the reasoning defensible**, and pour the freed-up effort into the deterministic criteria.
2. **Independently verifiable artifacts are the highest-leverage single feature.** `make verify`
   is a proven trick on this exact judging panel. Copy the mechanism.
3. **Their strategy substance was actually weak**: EMA/RSI/MACD/Bollinger, precisely the
   indicator family `propdesk` killed as evidence-free content-farm material. They won on
   *process*. Nilay can bring rigorous process **and** a strategy with real published backing.
   That is a strictly stronger position than the finalist who placed.

---

## 3. Judging maths

Five criteria **[measured]** from the rules page: P&L Performance, Technology Implementation,
Creativity & Originality, Presentation & Execution, Social Engagement (up to 5 posts). No
published weights. **[sourced, official kickoff email, 2026-08-29]** Social Engagement also
carries its own separate prize podium (2 teams x $500 plus a month of Algo Trader Plus each),
on top of whatever weight it has in the main score. Total pool $6,000, not $5,000.

P&L is **one of five**, and over 4.5 days it is mostly noise for everyone. The other four are
fully deterministic and fully under our control. **[assumed]** Effort should split roughly
30% strategy / 70% engineering-validation-presentation, the inverse of most entrants' instinct.

---

## 4. Track decision, re-examined rather than defended

**Staying with Track 2, Volatility & Event Trading Agents.** But the research broke the naive
version of it, and the mechanism changes substantially.

### What the research killed

**[sourced]** 0DTE iron condors are roughly break-even at best: ~70.19% win rate across 230,000
trades, against a structure needing >70% just to break even. Short gamma means a breach costs
2–3× the credit, and the underlying exceeds its expected move ~32% of the time. "90% probability
of profit" structures systematically underperform because losses accelerate non-linearly.
**A naive 0DTE condor bot is a coin-flip dressed as a strategy. Not building that.**

**[measured]** And the opposite error is just as bad. A 42-DTE condor held across the 4.5-day
window captures only ~7–9% of its credit in theta while paying ~2.5% up front to enter, the
edge barely clears the toll. **45 DTE is the textbook VRP tenor and it is wrong for this window.**

### What the research validated

**[measured], the decisive test, run live against the account this session.** propdesk R2/R3
died because real gross edge was destroyed by transaction costs (edge was ¼–⅓ of cost). So I
measured the same thing here before committing. Same-expiry 16-delta/5-delta condor, 42 DTE,
quoted ~15 min after the open (i.e. spreads near their widest):

| | Credit @ mid | One-way spread cost | Round trip |
|---|---|---|---|
| **SPY** | $4.47 | $0.11, **2.5% of credit** | **~4.9%** |
| **QQQ** | $6.01 | $0.38, **6.4% of credit** | **~12.8%** |

**This is a completely different cost regime from propdesk's FX work.** Against a VRP edge where
implied exceeds realised by 2–4 vol points ~85% of the time **[sourced]**, a ~5% round-trip toll
is survivable. The strategy is cost-viable, *on SPY*.

**And it hands us a real instrument decision with a number behind it: QQQ costs 2.6× more to
trade than SPY.** Per-leg spreads were $0.02–0.11 on SPY vs $0.16–0.23 on QQQ. Universe
selection becomes a measured gate, not a guess.

### The fill test, run live 2026-08-19, and it resolved the biggest unknown favourably

**[measured]** A real 4-leg `mleg` iron condor, 1 contract, SPY 31 Aug expiry (12 DTE), placed on
the practice account during the session and walked up a 5-rung price ladder from mid toward the
crossing price:

| | Mid | Crossing | **Actual fill** |
|---|---|---|---|
| Entry (credit) | $2.04 | $1.98 | **$2.03**: rung 2 of 5 |
| Exit (debit) | $2.04 | $2.11 | **$2.06**: rung 2 of 5 |

**Measured round trip: −$0.03 on $2.04 credit = −1.5%.** Account reconciles exactly
($100,000 → $99,996.80; −$3.00 from the round trip on the ×100 multiplier). Ended flat, 0
positions, 0 resting orders.

**Three things this settles:**

1. **Net-credit `mleg` limits fill near mid, not at the crossing price.** One cent off mid on
   entry, two cents on exit. The paper engine evaluates the *net* limit against the combined
   market rather than demanding each leg be independently marketable at the touch. The worst-case
   assumption in the cost model was ~3× too pessimistic.
2. **Iron condors clear their toll comfortably. The single-vertical-spread fallback is not
   needed**: though it stays documented in §9 in case behaviour changes under stress.
3. **Short-tenor spreads are tight on SPY**: per-leg $0.01–0.05 at 12 DTE, one-way toll 3.2% of
   credit *if* crossing, and we do not have to cross.

**[assumed], the honest caveat, and it belongs in the submission.** This is the *paper* engine,
which by Alpaca's own documentation simulates neither queue position nor price improvement. A
4-leg structure filling one cent off mid is almost certainly generous versus live, where a market
maker would make you come to them. We are judged on paper P&L, so this is the environment that
counts, but the submission should state plainly that live fills would be worse rather than
quietly banking the optimism. n=1, one underlying, one expiry, calm conditions; re-run at
different times before treating 1.5% as a constant.

### A design flaw the test exposed, which reading could not have

Selecting **wings by delta** produced badly asymmetric wings: the 5-delta put sat 22 points from
the short put while the 5-delta call sat only 9 points out. Max loss on the put side was
$1,996 against $204 of credit, roughly **10:1 risk/reward**, which is exactly the adverse ratio
§4 says destroys condor sellers.

**Fix, now part of the design: short strikes chosen by delta, wings by FIXED WIDTH** (~$5–10).
That caps max loss predictably and symmetrically instead of letting the delta surface decide how
much you can lose.

### The other capabilities, verified

**[measured]** Index options **are** listed and `tradable=True` on this account, SPX, XSP, VIX,
all `style=european`. European + cash-settled means **no early-assignment risk at all**, which
removes an entire failure class from a short-premium agent. XSP is 1/10 SPX (≈770, similar
notional to SPY) so it sizes sensibly against $100k.

**[measured]** But index *market data* returns **HTTP 404** on every symbol format tried
(`SPX,VIX,VIX3M` / `^SPX,^VIX` / `I:SPX`). Alpaca's own index-options announcement said index
data was "coming in the coming months", that still appears true. **So a VIX/VIX3M term-structure
regime filter cannot be read directly off Alpaca.** Fallback in §5. (Worth one retry through the
MCP's `get_index_latest_values` once that server reconnects, in case the REST path differs.)

**[measured]** Paper fills match **NBBO**, and Alpaca explicitly does *not* simulate market
impact, latency slippage, queue position, or price improvement. Order size is **not** checked
against NBBO quantity, you can fill far more size than really exists, and 10% of eligible fills
come back partial. Practical read: we will never get mid-price improvement, so **every cost
estimate must assume we cross the spread**, exactly as measured above. It also means we should
*not* let paper's unlimited-size fiction flatter the results, size as if liquidity were real.

### Why not the other three tracks

- **Track 1 (Directional)**: the default choice, so the crowded one, and it is where entrants
  reach for exactly the SMA/RSI/MACD family propdesk already killed. Highest P&L variance of the
  four, in a contest where variance is the main risk.
- **Track 3 (Hedging)**: most on-theme with the "risk engineering wins" finding, and genuinely
  tempting. Rejected because a hedging agent **structurally bleeds in an up market**: the base
  case is a small steady loss on the P&L criterion for 4.5 days. Its best ideas get absorbed into
  our design anyway (see the NFP de-risk in §5).
- **Track 4 (Income)**: lowest variance, but the track text explicitly grades *consistency across
  many cycles*, which 4.5 days cannot demonstrate. Also the most mechanically obvious, so likely
  the second-most crowded.

---

## 5. The agent: "Sells volatility only when volatility is actually expensive"

One sentence, per hackathon-mode's idea-lock: **an options agent that measures the volatility
risk premium directly, sells defined-risk premium only when that premium is genuinely rich, sits
flat when it is not, and de-risks ahead of scheduled macro events.**

The differentiator, stated plainly: **most entrants will sell premium on a schedule. Ours
measures whether the premium is actually there, and refuses to trade when it isn't.**

### 5.1 Derived parameters (each with a reason, not a default)

| Parameter | Choice | Why |
|---|---|---|
| **Tenor** | **7–14 DTE** | Derived from §1 + §4. 42 DTE captures ~7–9% of credit in 4.5 days (barely clears the 2.5% entry toll); 0DTE is break-even with brutal gamma. 7–14 DTE captures roughly 40–50% of credit over the window with wings still capping the tail. |
| **Universe** | **SPY primary**; others only if measured round-trip cost <6% of credit | Measured: SPY 4.9%, QQQ 12.8%. Cost gate is a rule, re-measured live, not a fixed list. |
| **Structure** | Defined-risk iron condor / credit spread | Wings cap the loss by construction, the one structural containment for VRP's known failure mode (it inverts violently, not gradually). |
| **Short strikes** | ~16 delta | Standard VRP tenor; also where measured spreads were tightest. |
| **Wing width** | **Fixed $5–10, NOT by delta** | **[measured]** Delta-selected wings came out wildly asymmetric (22pt put wing vs 9pt call wing) giving ~10:1 risk/reward. Fixed width caps max loss predictably. |
| **Execution** | Net-credit limit, laddered from mid | **[measured]** Fills near mid (1–2¢), so never send market orders across 4 legs. |
| **Instrument** | SPY to start; **XSP/SPX as a stretch** | European + cash-settled removes early assignment entirely. Gated on option-chain data actually being available for index roots, untested, see §7. |

### 5.2 The signal stack

1. **VRP measurement (the core).** Compare implied vol from the live chain against a *forecast* of
   realised vol, HAR-RV (Corsi 2009: daily + weekly + monthly realised-vol components, and it
   outperforms GARCH/ARFIMA on this job **[sourced]**). Trade only when `IV − forecast_RV` clears
   a threshold. **This is the bit that makes it a Track 2 entry rather than a premium-selling
   bot**: it reasons about whether volatility is mispriced, not about price direction.
2. **Term-structure regime gate.** Contango = calm = tailwind for short premium; backwardation =
   stress = stand down. **[sourced]** Contango holds ~85% of days 1990–2025, and 21 of 22 total-
   backwardation episodes preceded a >5% S&P drawdown within 30 days. Since Alpaca gives no VIX
   data **[measured]**, derive the curve from ATM IV at two expiries on SPY's own chain
   (near-term vs ~3-month). **This fallback is arguably the better demo**: building the vol term
   structure from raw chains reads as more sophisticated than reading a VIX quote.
3. **Event awareness.** **[measured]** **Nonfarm payrolls lands Friday 4 Sep, 08:30 ET, inside
   the window, ~2.5 hours before the submission deadline.** (FOMC is 15–16 Sep, safely outside.)
   A short-gamma book held naked into NFP could wreck the final P&L in the last hour the judges
   see. The agent carries an event calendar and cuts short-vega exposure into scheduled macro
   events.

### 5.3 The memorable layer

Tata Vayu won on the rupee-cost layer, output translated into the judges' currency. The
equivalent here:

> **"On N of M evaluated opportunities the agent declined to trade, and here is the measured VRP
> that made it decline."**

Plus the NFP beat: a log entry on Thursday's close reading *"NFP tomorrow 08:30 ET, reducing
short-vega exposure by X%"*, a demo moment showing the agent knew about an event it had never
been explicitly told to fear. Refusals are the product. Everyone else will show trades.

### 5.4 Risk gates (hard constraints inside the loop, not filters after)

Straight from propdesk's `compliance.py` lesson, rules are path-dependent, so they must be
enforced at decision time. Named and numbered explicitly, because the finalist evidence says
judges reward legible risk architecture ("7 layers", "13 gates"):

1. Max risk per position (% of equity)
2. Max concurrent short vega / total defined risk outstanding
3. VRP floor, no trade when measured premium is not rich
4. Regime block, no new short premium in backwardation
5. Event block, flatten//reduce ahead of calendar events
6. Daily loss limit → halt for the session
7. Consecutive-loss throttle → halve size, then pause
8. Cost gate, reject any structure whose round-trip cost exceeds X% of credit **[measured basis]**

### 5.5 Verifiability (the highest-leverage feature)

Copy what demonstrably worked on this panel:
- Every decision, **including refusals**: written as a structured artifact with the inputs that
  produced it (IV, forecast RV, VRP, regime, gate outcomes).
- SHA-256 Merkle tree over the artifact set; a `make verify` target that lets a judge recompute
  the root hash independently.
- Real test suite. JudyAI shipped 93 tests; propdesk shipped 39 then 72. This is a known strength
 , use it.

---

## 6. Plan of record

### Phase 0, now → Fri 28 Aug (pre-kickoff, ~9 days)
Nothing here is hackathon *submission* work; it is all groundwork that is legal to do early
(the rules explicitly allow any paper account for development).

1. **Keep the IV logger running.** Already scheduled daily 21:30 IST. By kickoff: ~9 days of real
   IV/greeks history across 7 underlyings. Nobody starting on the 28th will have this.
2. **Extend the logger to capture what the signals actually need**: ATM IV at two expiries (for
   the derived term structure) and daily close bars (for HAR-RV). Currently it logs 21–45 DTE
   only; 7–14 DTE needs adding, since that is the chosen tenor.
3. **Settle the two open API unknowns** (§7), they change instrument choice, and finding out on
   the 29th would cost a build day.
4. **Build and validate the backtest harness offline.** This is the real pre-work. By kickoff we
   should be able to state a walk-forward result, so the submission's claim is never "we made
   money in 4 days."
5. **Create the fresh submission-only paper account** (~26–27 Aug). Keys in a separate env file;
   the practice account must never appear in the submission.

### Phase 1, Fri 28 Aug 20:30 IST, kickoff
Attend, confirm nothing in the rules changed (tracks, account rules, deadline), check whether
technology partners were announced, partner prizes were "to be announced" and could add a
cheap second prize surface.

### Phase 2, Sat 29 – Sun 30 Aug, the build sprint
Demo-path-first, per hackathon-mode. Build in the order the demo shows things:
1. Decision loop end-to-end at toy quality, read chain → compute VRP → gate → place one paper
   condor → log the artifact. Prove the whole path before deepening any part of it.
2. **First real multi-leg order early**: the single riskiest unknown (§7). Five-line proof.
3. Risk gates.
4. Artifact log + Merkle verification.
5. Cockpit dashboard (reuse Chikki's FastAPI + static-HTML-off-disk pattern), doubles as demo
   material for the Presentation criterion.

**Freeze features at 75% of elapsed time.** Target: agent live and trading Mon 31 Aug 09:30 ET.

### Phase 3, Mon 31 Aug – Thu 3 Sep, live
Agent runs. Daily: verify it traded (or correctly refused), check gates fired as designed, capture
screenshots/logs as they happen rather than reconstructing them later. Build-in-public posts here
(up to 5, tagging @lablabai and @AlpacaHQ), cheap points on a scored criterion, and the honest
"here's what my agent refused to do today" angle suits the strategy.

### Phase 4, Thu 3 Sep evening → Fri 4 Sep 11:00 ET
- Thursday close: the NFP de-risk beat fires. Capture it, it is the demo's best moment.
- **Submit Thursday night / Friday early, not at the deadline.** Deadline servers die at 23:58.
- Friday morning is rehearsal and buffer only. Verify the submission actually landed, "submitted"
  is a claim that needs evidence.

---

## 7. Open unknowns, ranked by what they would cost

| # | Unknown | Status |
|---|---|---|
| 1 | **Do `mleg` orders fill in paper, and at what net price?** | ✅ **RESOLVED 2026-08-19, favourably.** Fills near mid; round trip 1.5%. See §4. Cost model holds; vertical-spread fallback not needed. |
| 3 | Does 7–14 DTE hold the tight SPY spreads seen at 42 DTE? | ✅ **RESOLVED**: yes. Per-leg $0.01–0.05 at 12 DTE. |
| 2 | Is option chain data (quotes/IV/greeks) available for **index** roots (XSP/SPX/VIX)? Contracts are tradable **[measured]** but index *underlying* data 404s. | Open, medium, decides SPY vs XSP. Read-only, before kickoff. |
| 4 | `SPXW` returned **0 contracts** while SPX/XSP returned contracts, root naming or genuinely unlisted? | Open, low, only matters for index 0DTE. |
| 5 | Technology partners unannounced, possible extra prize surface | Open, low, resolves at kickoff. |
| 6 | Does near-mid fill behaviour hold **under stress** (wide spreads, fast tape) and at other times of day? n=1 so far. | Open, medium. Re-run the ladder across sessions during Phase 0. |

---

## 8. Pre-mortem: the four ways this dies

1. **A big adverse move breaches short strikes mid-week.** Contained, not eliminated: defined-risk
   wings cap the loss, position sizing keeps a full loss at ~1% of equity, and the regime gate
   should stand the agent down before the worst of it. Accepted risk, this is the strategy's
   inherent shape.
2. **The agent trades nothing all week.** A real possibility if the VRP threshold is set too high
  , and a flat P&L is a weak submission. Mitigation: calibrate the threshold against the logged
   IV history *before* kickoff, and treat "declined to trade" as a first-class logged outcome so
   even a quiet week produces a rich artifact trail. **[assumed]**: this is the risk I am least
   sure about, and the calibration data is exactly what Phase 0 is buying.
3. **Multi-leg fills behave differently than modelled** (unknown #1). Fallback: two vertical credit
   spreads instead of one condor, or single-leg legs assembled sequentially. Costs more; still works.
4. **The demo dies live.** Standard mitigations: cached artifact set, a recorded run, and the
   dashboard reading from disk so it renders even with the market closed and the API down.

---

## 9. What would change my mind

Stated in advance, so a later session can hold this to account rather than rationalising:

- **Unknown #1 resolving badly** (net-credit limits don't fill, must cross to the far touch on all
  four legs), round-trip cost roughly doubles. Iron condors may stop clearing their toll; fall
  back to single vertical credit spreads (2 legs, half the cost).
- **Measured VRP is not actually rich during the window.** If the logged history shows IV running
  at or below forecast RV, the honest move is fewer/no trades, and the submission's story becomes
  the discipline of refusing, backed by the artifact trail. That is a defensible submission, and
  it is the one propdesk's whole research history says to make rather than manufacture edge.
- **Technology partners announced at kickoff with a materially better prize surface**: worth a
  re-read, not a rebuild.

Not open for re-litigation without new evidence: the track choice, Windows over WSL, solo, and
that the practice account is dev-only.
