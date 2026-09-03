# An options agent that refuses to trade

**Alpaca AI Trading Agents Hackathon 2026. Main challenge: Options Alpha Agents.**

Most trading agents are built to trade. This one measures whether volatility is
actually expensive before selling it, and declines when it is not. On its first
live run it refused, because implied volatility was 12.81 against a trailing
realised 13.28: volatility was cheap, so there was nothing worth selling.

**Every decision it makes, including every refusal, is a signed artifact you can
verify yourself.**

```bash
make verify
# VERIFIED: 6 artifacts, root 08b9f090be7f3f09... matches the seal written 2026-08-20T12:27:42+00:00
```

(The count and root advance as the agent runs. What matters is that the line says
VERIFIED, meaning the log you are reading is the log that was sealed.)

Live dashboard: https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/

---

## The thesis, and the evidence for it

Options are systematically more expensive than the movement that follows. The
agent sells that gap with defined risk, and only when it is measurably present.

Tested on 6.99 years of SPY, out of sample, against a design pre-registered
**before any backtest code existed** (`research/PREREGISTRATION_R1.md`, provable
from git history):

| Finding | Result |
|---|---|
| Mean volatility risk premium | **+3.68 vol points** over 1,741 observations |
| Significance, Newey-West corrected | **t = +4.74**, one-sided p < 0.0001 |
| Naive t (reported only to show why it is wrong) | +18.16 |

The naive t is invalid here: 21-day forward windows sampled daily overlap by 20
of 21 days, so observations are not independent. The correction shrank t by
3.8x, which is in the right neighbourhood for a Newey-West estimate at 21 lags,
though not exact confirmation the machinery is optimally tuned: an independent
review flagged that 21 lags likely undercorrects the true autocorrelation
length, and that a longer lag window or a Hansen-Hodrick estimator gives a
somewhat lower, still decisively significant t (in the 3.9 to 4.3 range rather
than 4.74). **H1 holds under any of these**, so the finding is not in question,
only the second-decimal precision of how hard the significance clears its bar.

**One distinction worth being precise about: H1's +3.68 is VIX-referenced, and
the live agent does not trade on that number.** H1 tests the thesis using
VIX minus subsequent realised vol, which needs no pricing model and is the
right test for "does this edge exist at all." Gate 7, the one the live agent
actually acts on, measures the implied vol of the specific strikes it is about
to sell, at the tenor it actually trades: a different, narrower quantity, for
reasons in `research/DEPLOYMENT_DECISIONS.md` D2. The two numbers are not
interchangeable and can disagree on any given day; on 2026-08-22 H1's style of
measurement read +0.00 while gate 7's actual live reading was -1.01, which is
why the agent refused. H1 is the evidence the mechanism is real. Gate 7 is what
decides whether today is a day to use it.

## What the research found that did NOT work

A submission that only reports its wins is a sales document. These are in the
repo with the same weight as the successes.

- **One registered prediction was wrong.** P2 predicted the regime gate would
  show a mean advantage of at least 1.0 vol point. Measured: **0.59**. The mean
  was the wrong statistic. Backwardation has a *higher* median premium (+6.55 vs
  +4.76) and a far worse tail (5th percentile -46.69 vs -7.20). The gate is
  justified because the premium is only *reliably present* in contango
  (t +6.13 against t +0.72), not because contango pays more.
- **The pricing model failed its own gate first**, at 26.78% median error against
  a pre-registered 15% threshold, so H3 was not run while it stood. Cause: VIX is
  a variance-swap rate inflated by put skew, not at-the-money implied vol.
  Measured by inverting Black-Scholes on 3,513 real option bars: market ATM IV is
  **0.853 of VIX**, stable across tenor and year. Corrected on 2024 data only so
  the re-gate on 2025 to 2026 stayed out of sample. It then passed at 10.75%.
- **The strategy result is fragile and the repo says so.** H3's best trial
  (T6, 21-45 DTE) clears its bar at Sharpe +1.614, but doubling transaction
  costs *improved* Sharpe, which is impossible and means the optimiser is
  partly selecting noise. **The deployed agent trades that same T6 tenor,
  with the fragility disclosed rather than hidden.** It was first deployed
  on T4 (7-14 DTE, Sharpe +1.201) because the 4.5 day window seemed to rule
  out the longer tenor; eight days of live comparison then showed T4 entering
  on 0 of 5 days against T6's 2 of 5, and the switch is recorded with its
  costs in `research/DEPLOYMENT_DECISIONS.md` D3. The ungated baseline beats
  the gated variants on average, at either tenor. Full write-up in
  `research/RESULT_H3_ROBUSTNESS.md`.
- **"Sell further out of the money" was an artifact of our own cost model.**
  Charging cost as a percentage of credit under-charged exactly the configs that
  looked best. Measured reality: the spread is 0.8% of a 35-delta option's price
  and **13.3% of a 5-delta option's**, a 16x range.

## Measured, not assumed

Every number the agent depends on was taken off the live API rather than
estimated.

| Measurement | Value | Why it mattered |
|---|---|---|
| Round-trip execution cost | **1.5% of credit** | A real 4-leg condor, laddered from mid. Crossing the full spread would be 8.3%. |
| Trading window | **4.5 days, not 7** | From Alpaca's own calendar. Kickoff and deadline are both mid-session. |
| API round trip | **246 ms** | Rules out anything whose edge lives inside a second. |
| SPY vs QQQ cost | **2.6x** | Universe selection became a measured gate, not a preference. |
| VIX forward (put-call parity) | **17.63**, dispersion 0.046 | Index options carry no greeks on this feed, so the forward is recovered from parity. |

## Architecture

```
market data ──> signals ──> 11 risk gates ──> execute or refuse ──> artifact
   (MCP)          │             │                    (MCP)            │
                  │             │                                     v
                  │             └── circuit breakers halt        Merkle tree
                  │                                                   │
                  └── term structure derived from the chain      make verify
```

**Everything at runtime goes through Alpaca's MCP server**, not the REST SDK. The
rules require it, and a project that calls REST directly does not satisfy them
however well it trades. `agent/mcp_client.py` spawns the official server and
speaks JSON-RPC 2.0 over stdio. Verified against alpaca-mcp-server 2.3.0
(FastMCP 3.4.7) with 74 tools exposed; all three package versions are pinned,
because fastmcp 4.0.0 shipped mid-competition and kills the unpinned server at
import. Every MCP request and response is recorded, including failures, so
"we used the MCP server" is checkable rather than claimed.

**Alpaca's official CLI is the second, read-only opinion.** Not an execution
path and never will be: `prep/alpaca_cli.py` enforces an allowlist of read
commands, so `order submit`, `position close-all` and `order cancel-all` are
refused before the process starts. Reporting uses it deliberately, because
reading the account back through a different Alpaca surface than the one that
wrote to it is a real check. The results page carries that independent read
(`make results`), and `prep/flatten_watch.py` witnesses Friday's deadline
close minute by minute from outside the agent.

**Eleven numbered gates (0 to 10), plus a stagger rule** that refuses a second
position on an expiry already held. Evaluated at decision time rather than
applied afterwards as a filter, because the rules are path dependent. All gates
are evaluated rather than short-circuiting on the first failure, so one artifact
shows the whole picture. Gates 0, 2 and 3 are **circuit breakers** distinguished
from ordinary refusals in code: a refusal means no trade now, a halt means stop.

**A tail hedge, designed and coded but honestly inoperative live.** Long VIX
calls following Cboe's VXTH methodology, sized at 1% of equity, with the VIX
forward recovered from put-call parity because index options expose no greeks on
this feed. Live, no VIX expiry inside the hedge's 21 to 45 day window had a
single quote on the feed all week: the indicative feed quotes the monthly VIX
expiries (16 Sep at 14 days, 21 Oct at 49 days) and returns nothing for the VIXW
weeklies that sit inside the window, although those contracts exist and trade
(RISK_REGISTER 4.9). So the agent logged a refusal to hedge off an empty read
every cycle rather than pretending, and the purchased wings remained the only
crash protection. The refusal artifacts are the evidence.

**An explain layer that never decides.** This is an AI agents hackathon and the
intelligence here is deterministic and measured, so the honest place for a
language model is after the decision, not inside it. `prep/explain_decisions.py`
runs outside the trading loop, reads each sealed artifact, and asks a model
(Qwen 2.5 72B via Featherless) for three plain sentences a judge can read. Every
number in the text is checked against the artifact; an explanation that invents
or alters a number is rejected, the rejection is recorded, and the dashboard
shows the count. The model explains; the numbers decide; the log proves it.

**A watchdog**, because the most likely way to lose the week is not strategic.
US hours are 19:00 to 01:30 IST, and a sleeping laptop hangs in-flight HTTP
permanently. Each cycle runs in a separate subprocess with an OS-enforced
timeout, since an in-process timer cannot rescue a thread stuck in a syscall.

## Verify it yourself

```bash
make test      # 233 tests
make verify    # recompute the Merkle root over every logged decision
make dry-run   # run one full cycle, place nothing
make dash      # the dashboard, locally
```

The artifact log is a SHA-256 Merkle tree with domain-separated leaves and nodes.
The root is sealed before outcomes are known. If any decision had been edited,
added, or removed after the fact, the root would not match. The tests prove the
detection works even when a forger recomputes the leaf hashes consistently.

## Honest limitations

- **Paper fills flatter us.** Alpaca's paper engine does not simulate queue
  position or price improvement, and does not check order size against available
  liquidity. A 4-leg structure filling one cent off mid is almost certainly
  generous versus live. We size as if liquidity were real and report the fills we
  actually got rather than banking the optimism.
- **The data is the indicative options feed, not OPRA.** Every spread, implied
  vol and greek here comes from it. Same feed live, so nothing is invalidated,
  but the 1.5% cost figure carries that qualifier.
- **One week of options P&L is mostly noise.** The backtest does not predict the
  live week. It establishes that the strategy has positive expectancy, so the
  live days are a draw from a favourable distribution rather than a coin flip.
- **Live sizing deviates from research sizing, deliberately.** The research ran
  at 1% risk per position; the live agent runs 5 concurrent at 3%, accepting a
  hard-capped 15% worst case. Recorded before the week started in
  `research/DEPLOYMENT_DECISIONS.md` and kept out of the backtest so the reported
  Sharpe stays the pre-registered one.

## Repo map

| Path | What |
|---|---|
| `agent/` | The live agent: MCP client, signals, 11 gates, execution, hedge, watchdog |
| `backtest/` | Pre-registered research. Holdout sealed in code, not by memory |
| `research/` | Pre-registration, every result including the failures, deployment decisions |
| `dashboard/` | Streamlit cockpit, reads artifacts off disk so it renders with the market closed |
| `prep/` | Capability probes and the daily IV logger |
| `tests/` | 233 tests |
| [`RISK_REGISTER.md`](RISK_REGISTER.md) | What could bite during the live window, and what is done about it |
| [`STRATEGY.md`](STRATEGY.md) | Why short volatility, why iron condors, why this tenor |

Licensed MIT. Paper trading only.
