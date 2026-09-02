# Storyboard

9 beats, 425 spoken words. At 150 words per minute that is 2:50 of speech plus 0.3 s of
lead-in and 0.5 s of silence per beat and a 1.5 s hold on the last frame, minus the
crossfades: 2:57 planned for the silent cut. build.py measures the real narration files and reports the
total; if it lands above 2:55 the PACE param in facts.md moves to 1.05 (about 2:50).
Every number below is in facts.md with its source.

Visual language: dark ground (#0b0f14), white text, one accent (amber #f5b942) for the
beat's single number, green (#3ddc84) only for the VERIFIED line and the winning
column. Captions burn in as white text on a dark band at the bottom, 2 lines max,
about 42 characters per line, chunked from the spoken line. No em-dashes anywhere.

| # | Start (silent cut, measured) | Dur | On screen | Big number | Spoken line (= caption text, chunked) |
|---|---|---|---|---|---|
| 1 | 0:00 | 21.2 s | Live dashboard capture (`b01_dashboard.png`), slow push-in from the title to the headline sentence "Of 81 real decision opportunities ... declined 77 (95%)". The sentence gets a highlight bar as the narration reaches "81". | **95% declined** (81 opportunities) | Most trading agents are built to trade. This one is built to refuse. Over the live week it evaluated 81 real opportunities and declined 95 percent of them, and every refusal is a signed artifact you can verify yourself. Let me show you why that is the point, not a bug. |
| 2 | 0:20 | 17.2 s | Left: `research/PREREGISTRATION_R1.md` rendered as a document (`b02_prereg.png`). Right: terminal typing `git log --diff-filter=A --reverse --date=iso -- research/PREREGISTRATION_R1.md backtest/` (the command the file itself tells judges to run) and printing the real lines: `96ee715 2026-08-19 19:57:13 Pre-register R1 before any backtest code exists` then `997701c 2026-08-19 20:01:47 R1 H1 and H2: thesis validated...`. The two timestamps light up in order. | **19:57 then 20:01** | The thesis is the volatility risk premium: SPY options are priced richer than the movement that follows. Before a single line of backtest code, I pre-registered the hypotheses, the trial count, and a multiple-testing bar. The git history proves the order. |
| 3 | 0:37 | 16.8 s | Slide 5 of the approved deck rendered full frame (`b03_slide05.png`, its numbers are current). The +3.68, 1,741 and t = +4.74 tiles pulse as each is spoken; the naive t bar gets a strike. | **+3.68 vol points**, then **t = +4.74** | Nearly seven years of SPY, out of sample: mean premium 3.68 vol points over 1,741 observations, Newey-West t of 4.74. The naive t of 18 is invalid, because the windows overlap. The edge is real, and the number is honest. |
| 4 | 0:54 | 22.0 s | Remotion-native pipeline: market data (MCP) to signals to 11 gates to execute or refuse to Merkle artifact, drawn from the README diagram. The 11 gate names (0 to 10) light up one by one in time with the list, gates 0, 2, 3 tagged "breaker", the stagger rule last. Footer tag: "Alpaca MCP server, 74 tools, JSON-RPC over stdio, every call recorded". | **11 gates** | The agent sells that premium with defined-risk iron condors, only after eleven numbered gates pass: position integrity, timing, circuit breakers, a contango filter, the premium threshold at the exact strikes it would sell, event proximity, cost, sizing, and a stagger rule. Every call goes through Alpaca's official MCP server, request and response recorded. |
| 5 | 1:16 | 16.4 s | Remotion-native table from D3: columns T4 (7-14 DTE), T6 (21-45 DTE), T7 (5-10 DTE); rows "would-enter cycles" 0/21, 10/21, 1/21 and "days with an entry" 0/5, 2/5, 1/5. Header "22 to 29 Aug, 21 live cycles, no orders sent". T6 column turns green and gets the "deployed" tag on "won". | **2 of 5 days** | The deployed tenor was not picked from the backtest ranking. Three candidates raced live in parallel for eight days on real market data, risking nothing. The one that actually traded won: two days of five, against zero and one. |
| 6 | 1:32 | 14.8 s | Full-frame terminal. Types `make verify`, prints the real captured output: `VERIFIED: 555 artifacts, root 9f5162884f30bb2e... matches the seal written 2026-09-02T05:47:17+00:00`. The word VERIFIED turns green on "verified". | **555 artifacts** | Every decision, fill and refusal is hashed into a Merkle tree, sealed before outcomes are known. One command recomputes the root. If anything had been edited after the fact, this line would not say verified. |
| 7 | 1:46 | 31.2 s | The longest beat. Header "artifacts/decisions.jsonl, seq 30, 2026-08-31 09:50:05 ET". A code panel scrolls the real excerpt: gate 5 `"reason": "0/5 positions open"`; then the `get_all_positions` result with `SPY261002C00792000` highlighted amber; then `reconciliation: "no legs at broker; closed or expired"` highlighted amber, with a bracket labelled "same sealed record". Bottom strip: four fill times 09:45, 09:55, 10:05, 10:21 ET appear one by one, then "design intended 1". Closing overlay: "bug, fix, 9 regression tests, positions adopted: all in the record". | **4 condors, not 1** | Here is the strongest evidence that this works. On the first live morning, a payload-parsing bug read the account as flat, and the agent stacked four condors instead of one. The sealed log caught it: one artifact holds both the raw broker response with the legs, and the reconciliation that ignored them. Bug, fix, regression tests and the adopted positions are all in the record. I did not hide it. The record would not let me. |
| 8 | 2:17 | 27.6 s | Dashboard "Open positions (4)" section capture (`b08_positions.png`) dimmed under number cards: "+$36.93 so far, on $100,000 paper" (LIVE_PNL), then "4 condors, 28 contracts, $3,108 credit, worst case $10,840", then "deadline flatten: 90 minutes before submission". Last card: "VIX tail hedge: coded, never engaged. 0 VIX contracts served. Refusal logged every cycle." | **+$36.93 so far** | Live P&L so far: plus 36 dollars and 93 cents on a hundred thousand dollar paper account. On Friday a deadline flatten closes every position ninety minutes before submission. Realised, not marked. One week of options P&L is mostly noise, and the write-up says so. The tail hedge is coded and never engaged: Alpaca served no VIX data all week. That refusal is logged every cycle too. |
| 9 | 2:44 | 10.2 s | GitHub README capture (`b09_readme.png`) with a slow drift, then the closing card: `github.com/nilaymastaadmi/alpaca-hackathon`, `make test, make verify, make summary`, "211 tests". Hold 1.5 s on the card. | **211 tests** | Clone it. Run make test, make verify, make summary. You do not have to trust me. That is the whole design. |

Crossfades of 0.3 s between every pair of beats. No music. Narration is added last:
until `build.py --voice` has run, the cut is silent with captions timed at 150 wpm.

## What changed from VIDEO_BRIEF.md, and why

- Wording tightened in beats 2, 4, 7, 8 for pace (brief was about 430 words with the
  placeholders; this is 425 with them filled). Meaning unchanged.
- Beat 3 says "nearly seven years" and shows 6.99, so the spoken and shown numbers agree.
- Beat 5 adds the spoken result "two days of five, against zero and one" so the big
  number on screen is also said aloud.
- Beat 6 ends "this line would not say verified" instead of "this would fail", because
  the green word is on screen at that moment.
- Beat 7 says "regression tests" and shows "9 regression tests" (RISK_REGISTER 4.7).
- Beat 8: the brief's line "realised by a deadline flatten ... not a mark-to-market
  snapshot" is only true after Friday's flatten. If the video is cut Thursday, the
  number is a Thursday mark. The line now says "so far" and describes the Friday
  flatten in the future tense, which is true on both days.
- Architecture (beat 4) and comparison (beat 5) are rendered natively instead of using
  slides 8 and 10: slide 8 says "10 risk gates" and slide 10 shows T4 as deployed,
  both stale against README and D3.

## Thursday re-render

Edit LIVE_N, LIVE_PCT, LIVE_PNL in facts.md, then run `uv run presentation/video/build.py`.
Beats 1 and 8 get new narration (the others are cached by text hash), `make verify` and
`make summary` are re-run for the terminal beats, and the dashboard is re-captured only
with `--capture`. Expected wall time: under 10 minutes.
