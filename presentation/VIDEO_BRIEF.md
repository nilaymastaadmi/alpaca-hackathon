# Video brief for whoever is producing the MP4

Target: 3 minutes, 16:9, MP4. Judges watch dozens of these; the first 15
seconds decide whether they keep watching. Lead with the counter-intuitive
claim, then show the evidence on screen rather than describing it.

Everything below is true as of 2 Sep. Numbers marked LIVE change daily;
pull the final ones from the dashboard on Thursday before recording.

## What to have open for screen capture

- Dashboard: https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app
  (wake it first, it sleeps after 12 idle hours)
- Terminal in the repo, ready to run `make verify` and `make summary`
- GitHub: https://github.com/nilaymastaadmi/alpaca-hackathon
  (`research/PREREGISTRATION_R1.md` open, then its git history)
- `presentation/slides_draft.pdf` for the architecture and comparison slides
- The artifact `artifacts/decisions.jsonl`, scrolled to the 31 Aug 09:45 ET
  entry, for the incident beat

## Script (about 430 words, 3 minutes at a natural pace)

**[0:00, dashboard headline visible]**
Most trading agents are built to trade. This one is built to refuse. Over the
live week it evaluated LIVE_N real opportunities and declined LIVE_PCT percent
of them, and every refusal is a signed artifact you can verify yourself. Let me
show you why that is the point, not a bug.

**[0:20, pre-registration file, then its git history]**
The thesis is the volatility risk premium: SPY options are priced richer than
the movement that follows. Before writing a single line of backtest code, I
pre-registered the hypotheses, the trial count, and a multiple-testing bar.
The git history proves the order. Seven years of data, out of sample: mean
premium 3.68 vol points, Newey-West t of 4.74. The edge is real, and the
number is honest.

**[0:50, architecture slide]**
The agent sells that premium with defined-risk iron condors on SPY, only after
eleven numbered gates pass: position integrity, timing, a drawdown breaker,
loss limits, a contango regime filter, the premium threshold at the exact
strikes it would sell, macro-event proximity, cost, sizing, and a stagger rule.
Every call goes through Alpaca's official MCP server, and every request and
response is recorded.

**[1:15, comparison slide]**
The deployed tenor was not picked from the backtest ranking. Three candidate
strategies raced live in parallel for eight days on real market data, risking
nothing, and the one that actually traded won.

**[1:35, terminal: make verify]**
Every decision, fill and refusal is hashed into a Merkle tree, sealed before
outcomes are known. One command recomputes the root. If anything had been
edited after the fact, this would fail.

**[1:50, the 31 Aug artifact on screen]**
Here is the strongest evidence I have that this works. On the first live
morning, a payload-parsing bug read the account as flat, and the agent stacked
four condors instead of one. The sealed log caught it: one artifact holds both
the raw broker response with the legs, and the reconciliation that ignored
them. The bug, the fix, the regression test, and the adopted positions are all
in the record. I did not hide it, because the record would not let me.

**[2:25, dashboard positions and P&L]**
Live P&L: LIVE_PNL on a hundred thousand dollar paper account, realised by a
deadline flatten ninety minutes before submission, not a mark-to-market
snapshot. One week of options P&L is mostly noise, and the write-up says so.
The tail hedge is designed and coded, and never engaged, because no VIX expiry
inside its window had a quote all week. That refusal is logged every cycle too.

**[2:50, repo README]**
Clone it. Run make test, make verify, make summary. You do not have to trust
me. That is the whole design.

## Placeholders to fill Thursday

- LIVE_N, LIVE_PCT: dashboard headline, "Of N real decision opportunities"
- LIVE_PNL: equity minus 100,000, in dollars, after Friday's flatten if the
  video is cut Friday, otherwise Thursday's close with "so far"

## Do not

- Do not use em-dashes in on-screen text.
- Do not show the dev account PA308NOY3X36 anywhere. The submission account
  is PA37R35A5ZGW.
- Do not claim the hedge protects the book. It never engaged live.
- Do not say "Track 2". The challenge is "Options Alpha Agents".
