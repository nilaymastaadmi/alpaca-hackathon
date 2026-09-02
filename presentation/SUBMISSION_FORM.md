# Submission form, pre-filled. Copy-paste on Thursday night.

Every field on the lablab.ai submission form, with the exact text to paste.
Check the live form once for any field added since 29 Aug; nothing here
should need thinking on the night.

## Project title

Glass Box: a pre-registered options agent whose every decision you can verify

(Decided 2026-09-02 after reading the previous lablab.ai trading winners: every one led with verifiability and numbers, none with a slogan. "Refuses to trade" stays as the opening hook inside the description and the video, not as the name.)

## Short description (one line)

Pre-registered SPY iron-condor agent on Alpaca MCP: 11 risk gates, 219 tests, 850+ sealed decisions in a Merkle log a judge recomputes with one command, three strategies raced live in parallel, and a log that caught its own author's bug on day one.

## Long description

Most trading agents are built to trade. This one is built to measure first.

The thesis is the volatility risk premium: SPY options are systematically priced richer than the movement that follows. Tested on 6.99 years of SPY out of sample, against hypotheses pre-registered before any backtest code existed (provable from git history): mean VRP +3.68 vol points over 1,741 observations, Newey-West t = +4.74. Seven configurations were pre-registered and tested against a multiple-testing-corrected bar (0.791, N=7), and the deployed tenor was chosen from eight days of live paper-market comparison, three candidates run in parallel, not from the backtest ranking alone.

The agent sells that premium with defined-risk iron condors and only after 11 numbered gates pass: position integrity checked in both directions, trading-window timing, a drawdown breaker, a daily loss limit, a consecutive-loss pause, capacity, a contango regime filter, the VRP threshold itself at the exact strikes it would sell, a macro-event proximity check, a cost ceiling, a sizing check, plus a stagger rule that refuses a second position on an expiry already held. A refusal is logged with the same detail as a fill, carrying the numbers that caused it.

Every runtime call goes through Alpaca's official MCP server over JSON-RPC, recorded request by request. Orders ladder from mid across up to 5 rungs instead of crossing the spread, measured at 1.5% of credit round trip on a real fill. A dedicated deadline mechanism flattens the book 90 minutes before submission so the result is realised, not a mark-to-market snapshot.

The language model sits after the decision, not inside it: an explain layer (Qwen 2.5 72B on Featherless, outside the trading loop) narrates every sealed decision in plain English, and every number it writes is checked against the artifact, with rejections counted on the dashboard. The model explains; the numbers decide.

Every decision, fill and refusal is hashed into a SHA-256 Merkle tree sealed before outcomes are known. `make verify` recomputes it. That trail has already caught its own author: on the first live morning a payload-parsing bug read the account as flat and the agent stacked four condors instead of one. The proof was a single sealed artifact holding both the raw broker response with the legs and the reconciliation that ignored them. The bug, the fix, the regression test, and the adopted positions are all in the record. 211 tests. Live week P&L is reported exactly as it happened, and the write-up says plainly which designed components (the VIX tail hedge) never engaged live and why.

## Category / challenge

Options Alpha Agents (the single main challenge; there are no sub-tracks on the live page)

## Technology tags

Python, Alpaca MCP Server, Model Context Protocol, Streamlit, Featherless, Qwen 2.5, options, iron condor, volatility risk premium, Merkle tree, pre-registration, pytest

## Cover image (16:9, PNG or JPG)

`presentation/cover_image.jpg` (1600 x 900)

## Video presentation (MP4)

Nilay's source is producing it. Brief for them: `presentation/VIDEO_BRIEF.md`. Confirm the file exists locally BEFORE opening the form.

## Slide presentation (PDF)

`presentation/slides_draft.pdf`, replaced by the final export on Thursday.

## Public GitHub repository

https://github.com/nilaymastaadmi/alpaca-hackathon

## Application URL

https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app

Wake it 10 minutes before submitting, and again Friday morning; Community Cloud sleeps after roughly 12 idle hours.

## Demo application platform

Streamlit Community Cloud

## Alpaca paper account ID

PA37R35A5ZGW

Created 2026-08-28 for this submission. NOT PA308NOY3X36, which is the dev account.

## Social post links (up to 5)

Leave empty. Decided 2026-08-30, do not re-raise.

## One-page write-up (AI logic, risk gates, Alpaca infrastructure)

`presentation/WRITEUP.md`, final-numbers pass Thursday. If the form takes a file, export it to PDF; if it takes text, paste the Markdown body.

## Thursday night order of operations

1. `make test` (expect 211 passed), `make verify` (expect VERIFIED), `make summary`.
2. Wake the dashboard, confirm the Merkle badge reads VERIFIED on the public URL.
3. Confirm the video MP4 and the final slides PDF exist and open.
4. Fill the form top to bottom from this file. Account ID last, read it twice.
5. Submit, then reopen the submission page and confirm every field and file landed.
