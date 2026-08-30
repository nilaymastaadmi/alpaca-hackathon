# One-page write-up: AI logic, risk gates, Alpaca infrastructure

**An options agent that refuses to trade.** Alpaca AI Trading Agents Hackathon 2026, Options Alpha Agents challenge. Solo entry, Nilay Toshniwal.

## AI logic

The thesis: options are systematically priced richer than the movement that follows, a gap called the volatility risk premium (VRP). Tested on 6.99 years of SPY, out of sample, against hypotheses pre-registered before any backtest code existed (`research/PREREGISTRATION_R1.md`, provable from git history). Mean VRP is +3.68 vol points over 1,741 observations, Newey-West corrected t = +4.74 (the naive t of +18.16 is invalid, since overlapping 21-day windows are not independent observations). The edge is real and decisive.

The agent sells that gap with a defined-risk iron condor on SPY, entering only when implied volatility at the exact strikes it is about to sell clears a measured threshold against trailing realised volatility. Seven trial configurations were pre-registered and tested (dev bar recomputed to 0.792 as trials were added, N=7); the deployed tenor is 21-45 DTE, chosen not from the backtest ranking alone but from eight days of live paper-market comparison against three candidates run in parallel: the deployed tenor traded on 2 of 5 real days while two shorter alternatives traded on 0 and 1 respectively. Full reasoning in `research/DEPLOYMENT_DECISIONS.md`.

A refusal is not a failure mode. It is logged with the same detail as a fill, carrying the measured numbers that produced it, so the decision is auditable rather than asserted.

## Risk gates

Every decision passes through 10 numbered gates before a structure is priced: position integrity (ledger matches broker), trading-window timing, a portfolio drawdown breaker, a daily loss limit, a consecutive-loss pause, capacity, a term-structure regime filter (contango required, since VRP is only reliably significant there), the VRP threshold itself, a scheduled-macro-event proximity check, and a structure/cost sanity check. Gates 2 and 3 are circuit breakers, distinguished in code from ordinary refusals: a refusal means no trade now, a breach means stop and flatten.

Sizing is a deliberate, recorded deviation from the 1%-per-position research sizing: 5 concurrent positions at 3% risk each, 15% hard cap, chosen because research sizing implied under one trade across the whole judged week. A tail hedge (long VIX calls, 1% of equity, Cboe's VXTH methodology, forward recovered via put-call parity since the feed carries no index greeks) covers the fact that five short-volatility positions are correlated and lose together in a shock. A dedicated deadline-flatten mechanism forces a full close of every open position starting 90 minutes before the submission deadline, since the deployed tenor will not reach natural expiry inside the judged week otherwise, a mark-to-market snapshot at an arbitrary instant is not what this agent is built to report as a result.

## Alpaca infrastructure

Every runtime decision goes through Alpaca's official MCP server (JSON-RPC over stdio), not the REST SDK, verified against Alpaca MCP Server v3.4.7 with 74 tools exposed. Every request and response is recorded, so "the rules-required MCP path was used" is checkable, not claimed.

Execution ladders orders from the mid price across up to 5 rungs rather than crossing the spread, measured at 1.5% of credit round trip on a real live fill. A double-open guard checks for a resting order on the same legs before every rung, including the first, closing a race condition where a lost network response could otherwise duplicate a position. Every decision, fill, and refusal is written to an append-only log covered by a SHA-256 Merkle tree with domain-separated leaves and nodes; the root is sealed before outcomes are known and anyone can recompute it (`make verify`) to confirm nothing was edited after the fact. 202 automated tests cover the gates, the execution ladder, the flatten logic, and the deadline mechanism specifically.
