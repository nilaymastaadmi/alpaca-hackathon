# Storyboard (editorial cut, 2026-09-02 evening)

9 beats, 425 spoken words. At 150 words per minute that is 2:50 of speech plus 0.3 s of
lead-in and 0.5 s of silence per beat and a 1.5 s hold on the last frame, minus the
crossfades: 2:55 for the silent cut. build.py measures the real narration files once
`--voice` has run and re-times every beat to them; if the total lands above 2:55 the PACE
param in facts.md moves to 1.05 (about 2:50). Every number below is in facts.md with its
source.

## Visual language

Modelled on the Tata Vayu reference cut. Cream sections (#f3efe3) alternate with ink
sections (#0f1115). Headlines in Archivo Black reveal word by word, with a yellow
(#ffe234) marker swipe on the one phrase that matters and a green (#35d07f) swipe on the
payoff. Section labels are red (#e5322d) JetBrains Mono caps, top left; a small strip
top right reads "VRP agent / Nilay Toshniwal / Options Alpha Agents" on every beat.

Captions are not subtitles. Each beat carries two to five short stickers, black boxes
with the numbers in yellow or yellow boxes with black text, placed next to the thing
they describe and timed to the narration. The full narration still goes into final.srt
for the platform's caption upload, and `subtitles: true` in the timeline turns the
bottom-band subtitles back on if a judge platform needs them burned in.

Real footage instead of screenshots wherever the product exists: the dashboard is a
Playwright screen recording with a visible cursor (`record.py`), shown inside a browser
frame. The pre-registration proof is a typed git log. The incident is the artifact's own
JSON. Nothing is illustrated that could be shown.

| # | Start | Dur | Tone | On screen | Stickers and copy |
|---|---|---|---|---|---|
| 1 | 0:00 | 21.2 s | ink | Browser frame, real dashboard recording: the cursor rests on the title, glides to the equity tile, then to the headline sentence and pulses on "77 (95%)". Label "Live dashboard, 2 Sep 2026". | "Most trading agents are built to trade." then "This one is built to refuse." then "77 of 81 real opportunities: declined." then "Every refusal is a signed artifact." then "That is the point, not a bug." Each replaces the last, timed to the narration. |
| 2 | 0:21 | 17.2 s | cream | Label "The thesis". Headline "Options are priced richer than the move that [follows]." Sub-line on the VRP fades out when the black sticker lands; a terminal card rises and types `git log --diff-filter=A --reverse --date=iso -- research/PREREGISTRATION_R1.md backtest/`, prints the 4 real lines, highlights 19:57:13 and 20:01:47 in yellow on "The git history", then a line "19:57 pre-registered. 20:01 first backtest commit. Four minutes, in the right order." | "Pre-registered before a single line of backtest code." |
| 3 | 0:38 | 16.8 s | ink | Label "Hypothesis 1, out of sample". Three big stats appear as spoken: +3.68 (mean VRP, vol points), 1,741 (daily observations, 6.99 years), t = +4.74 in green (Newey-West corrected). Then t = +18.16 in grey with a red strike, and the sub-line on why overlapping windows invalidate it. | "Real edge. Honest number." |
| 4 | 0:54 | 22.0 s | cream | Label "Before any order". Headline "Eleven numbered gates, then a [stagger rule]." 11 mono chips appear one by one in narration order (breakers 0, 2, 3 in red), then a filled yellow chip for the stagger rule. A flow row appears on "Every call": market data, signals, 11 gates, execute or refuse, Merkle artifact, with a mono line about the MCP server. | "Gates 0, 2 and 3 are circuit breakers. A breach means stop, not skip." |
| 5 | 1:16 | 16.4 s | ink | Label "22 to 29 Aug, live, in parallel". Headline "Three tenors raced on the real market. The one that traded [won]." (green on "won"). Three cards: T4 with a cross, T7 with a cross, T6 with a check that turns green on "won". Source line at the bottom. | "2 of 5 days, against 0 and 1." |
| 6 | 1:32 | 14.8 s | ink | Label "One command". Full terminal card types two comment lines, then `make verify`, then the real output captured at build time; VERIFIED in green. | "Edited after the fact? This line would not say VERIFIED." and "555 sealed artifacts, one root." (count from the live output). |
| 7 | 1:46 | 31.2 s | cream | Label "The part I did not plan". Headline "On the first live morning it stacked [four] condors instead of one." Mono sub-line with the four fill times. Dark artifact card with three real excerpts from seq 30: gate 5 "0/5 positions open", the get_all_positions response listing SPY261002C00792000, the reconciliation that dropped it. Right column: 4 check cards, bug, fix, 9 tests, 3 orphans adopted. | "Same sealed record. Artifact seq 30." |
| 8 | 2:17 | 27.6 s | ink | Label "Live, so far". Big "+$36.93 so far" (LIVE_PNL), mono line with the book (4 condors, 28 contracts, $3,108 credit, worst case $10,840). Browser frame on the right plays the positions recording, ending on the dashboard's own MERKLE ROOT VERIFIED badge. Two cards for the hedge: check "designed and coded", cross "never engaged live, 0 VIX contracts, 90 refusals". | "Friday: a deadline flatten closes every position 90 minutes before submission." then "One week of options P&L is mostly noise. The write-up says so." |
| 9 | 2:44 | 10.2 s | cream | Label "Verify it yourself". Four commands type in red-prompt mono: git clone, make test, make verify, make summary. Headline "You do not have to [trust me]." Sub "That is the whole design." Browser frame on the right shows the real GitHub README. Footer "211 tests. Paper trading only. MIT." | none; the headline is the caption. |

Crossfades of 0.3 s between every pair of beats. No music. Narration is added last:
until `build.py --voice` has run, the cut is silent and the stickers are timed at 150 wpm.

## Narration (unchanged from the first cut, also the .srt)

1. Most trading agents are built to trade. This one is built to refuse. Over the live week it evaluated 81 real opportunities and declined 95 percent of them, and every refusal is a signed artifact you can verify yourself. Let me show you why that is the point, not a bug.
2. The thesis is the volatility risk premium: SPY options are priced richer than the movement that follows. Before a single line of backtest code, I pre-registered the hypotheses, the trial count, and a multiple-testing bar. The git history proves the order.
3. Nearly seven years of SPY, out of sample: mean premium 3.68 vol points over 1,741 observations, Newey-West t of 4.74. The naive t of 18 is invalid, because the windows overlap. The edge is real, and the number is honest.
4. The agent sells that premium with defined-risk iron condors, only after eleven numbered gates pass: position integrity, timing, circuit breakers, a contango filter, the premium threshold at the exact strikes it would sell, event proximity, cost, sizing, and a stagger rule. Every call goes through Alpaca's official MCP server, request and response recorded.
5. The deployed tenor was not picked from the backtest ranking. Three candidates raced live in parallel for eight days on real market data, risking nothing. The one that actually traded won: two days of five, against zero and one.
6. Every decision, fill and refusal is hashed into a Merkle tree, sealed before outcomes are known. One command recomputes the root. If anything had been edited after the fact, this line would not say verified.
7. Here is the strongest evidence that this works. On the first live morning, a payload-parsing bug read the account as flat, and the agent stacked four condors instead of one. The sealed log caught it: one artifact holds both the raw broker response with the legs, and the reconciliation that ignored them. Bug, fix, regression tests and the adopted positions are all in the record. I did not hide it. The record would not let me.
8. Live P&L so far: plus 36 dollars and 93 cents on a hundred thousand dollar paper account. On Friday a deadline flatten closes every position ninety minutes before submission. Realised, not marked. One week of options P&L is mostly noise, and the write-up says so. The tail hedge is coded and never engaged: Alpaca served no VIX data all week. That refusal is logged every cycle too.
9. Clone it. Run make test, make verify, make summary. You do not have to trust me. That is the whole design.

## What changed from VIDEO_BRIEF.md, and why

- Wording tightened in beats 2, 4, 7, 8 for pace (brief was about 430 words with the
  placeholders; this is 425 with them filled). Meaning unchanged.
- Beat 3 says "nearly seven years" and shows 6.99, so the spoken and shown numbers agree.
- Beat 5 adds the spoken result "two days of five, against zero and one" so the number on
  screen is also said aloud.
- Beat 6 ends "this line would not say verified" instead of "this would fail", because
  the green word is on screen at that moment.
- Beat 8: the brief's "realised by a deadline flatten, not a mark-to-market snapshot" is
  only true after Friday's flatten. The line says "so far" and puts the flatten in the
  future tense, which is true whichever day the video is cut.
- Slides 8 and 10 are not used (stale "10 risk gates", "T4 deployed"); slide 5 is no
  longer used either, its three numbers are set natively so the typography matches.
- Bottom-band subtitles replaced by stickers after the first cut read as machine-made.

## Thursday re-render

Edit LIVE_N, LIVE_PCT, LIVE_PNL in facts.md, then:

    uv run presentation/video/build.py --capture

`--capture` re-shoots the GitHub frames and re-records the two dashboard clips (about
3 minutes), `make verify` and `make summary` re-run for the terminal beats, and Remotion
re-renders (about 6 minutes). Add `--voice` once the visuals are approved: beats whose
text changed get fresh Sarvam narration, the rest is cached by text hash.
