# Storyboard (final cut, 2026-09-04, narrated)

10 beats. Narration is Sarvam `bulbul:v3`, voice `rahul`, PACE 1.08; build.py measures each
generated file and re-times every beat to it, so the durations in this table are whatever
the last build printed, not an estimate. Target window 2:30 to 3:10. Every number below is
in facts.md with its source, and build.py aborts if a number on screen is not there.

## Visual language

Modelled on the Tata Vayu reference cut. Cream sections (#f3efe3) alternate with ink
sections, and the ink is now the deck's navy (#0a1621, cards #16283c) so the video and
`presentation/slides.pdf` read as one piece. Headlines in Archivo Black reveal word by word
with a yellow (#ffe234) marker swipe on the phrase that matters, green (#35d07f) on the
payoff, red (#e5322d) mono section labels top left, project strip top right.

Captions are stickers, not a subtitle band: black boxes with the numbers in yellow, or
yellow boxes with black text, placed next to the thing they describe and timed to the
narration. The full narration is still written to `final.srt` for the platform's caption
upload, and `subtitles: true` in the timeline turns a burned-in band back on if needed.

The wordmark GLASS BOX sits quietly over the opening dashboard shot and again on the
closing frame, at low contrast. No title card, no seconds spent.

Real footage wherever the product exists: three Playwright screen recordings of the live
dashboard with a visible cursor (`record.py`), shown in a browser frame. The pre-registration
proof is a typed git log, `make judge` is the real output of the four commands that target
runs, and the incident is the artifact's own JSON.

| # | Tone | On screen | Stickers and copy |
|---|---|---|---|
| 1 | ink | Label "Live dashboard, 4 Sep 2026". Real recording: the cursor rests on the title, glides to the equity tile, then to the headline sentence and pulses on "193 (98%)". GLASS BOX fades in quietly under the label. | "Most trading agents are built to trade." then "This one is built to refuse." then "193 of 197 real opportunities: declined." then "Every refusal is a signed artifact." then "That is the point, not a bug." |
| 2 | cream | Label "The thesis". Headline "Options are priced richer than the move that [follows]." A terminal types `git log --diff-filter=A --reverse ...` and prints the four real commits, highlighting 19:57:13 and 20:01:47, then "19:57 pre-registered. 20:01 first backtest commit. Four minutes, in the right order." | "Pre-registered before a single line of backtest code." |
| 3 | ink | Label "Hypothesis 1, out of sample". +3.68, 1,741, t = +4.74 in green appear as spoken; then t = +18.16 in grey with a red strike and the overlapping-windows explanation. | "Real edge. Honest number." |
| 4 | cream | Label "Before any order". Headline "Eleven numbered gates, then a [stagger rule]." 11 mono chips appear in narration order (breakers 0, 2, 3 in red), then the filled stagger chip; a flow row and the MCP line. | "Gates 0, 2 and 3 are circuit breakers. A breach means stop, not skip." |
| 5 | ink | Label "Three tenors, one live market". Headline "The one that actually trades [won]." Three cards with the RUNNING totals from `compare_summary.json`: T4 16/52 and T7 13/51 with crosses, T6 26/52 with a check that turns green. Source line names the window. | "26 of 52 cycles, against 16 and 13." |
| 6 | ink | Label "One command". Terminal types `make judge` and prints the four steps it runs, each with its real output: 233 passed, VERIFIED in green, the summary counts, the results page written. | "Edited after the fact? This line would not say VERIFIED." |
| 7 | cream | Label "The part I did not plan". Headline "On the first live morning it stacked [four] condors instead of one." Artifact card with three real excerpts from seq 30; right column, four check cards: bug, fix, 9 tests, 3 orphans adopted. | "Same sealed record. Artifact seq 30." |
| 8 | ink | Label "Where the AI sits". Real recording of the dashboard's explanation box: the plain-English text, then the label under it that says the decision was sealed before the text existed and names the counts. Big 238 and big 0 below. | "The model never takes part in deciding." plus the checking rule in the side note. |
| 9 | ink | Label "Live, so far". Big -$565.07 in red, mono book line, then the bounded-loss sticker, the noise sticker, a check card for the flatten and a cross card for the hedge. Browser frame on the right plays the positions recording, ending on MERKLE ROOT VERIFIED. | "Loss bounded by construction, not by luck." then "One week of options P&L is mostly noise. The research says so." |
| 10 | cream | Label "Verify it yourself". Three commands type: git clone, cd, `make judge`. Headline "You do not have to [trust me]." GitHub README in a browser frame. Footer "233 tests. Paper trading only. MIT." plus the wordmark. | none; the headline is the caption. |

Crossfades of 0.3 s between every pair of beats. No music.

## What changed on 4 Sep, the final pass

- **The P&L went negative and the beat was rewritten around it.** Beat 9 speaks the sign
  ("minus five hundred and sixty five dollars and seven cents"), states the structural cap
  ($10,840 worst case against $3,108 of credit collected), and says the flatten converts the
  number to realised in ninety minutes. A losing week reported precisely.
- **The hedge sentence was factually wrong and is corrected.** It used to say Alpaca served
  no VIX data all week. RISK_REGISTER 4.9: the indicative feed does quote VIX, but monthlies
  only, and neither 16 Sep (14 to 16 days out) nor 21 Oct (49 to 51) fell inside the hedge's
  21 to 45 day window. The line is now "no VIX expiry inside its window was quoted all week".
- **Beat 5 now quotes running totals**, 16/52, 26/52, 13/51 from `compare_summary.json`, and
  says the window out loud, because the dashboard shows running totals and a judge will compare.
- **LIVE_N and LIVE_PCT are 197 and 98**, and the definition changed too: dry runs are now
  excluded, so this is not the same denominator as the 81 the 2 Sep cut showed.
- **233 tests, not 211**, everywhere.
- **New beat 8, "Where the AI sits"**, because an AI agents hackathon will ask. Paid for by
  trimming beat 9 and tightening beat 5.
- **Beat 6 became `make judge`**, which is one real command that runs the tests, verifies the
  root, prints the summary and rebuilds the results page.
- Ink tone moved to the deck's navy so the video matches `presentation/slides.pdf`.

## Re-render

Edit the live values in facts.md, then:

    uv run presentation/video/build.py --capture --voice

`--capture` re-shoots the GitHub frames and re-records the three dashboard clips (about
4 minutes), `--voice` regenerates only the beats whose narration text changed (cached by
text hash), `make judge` and `make summary` re-run for the terminal beats, and Remotion
renders (about 7 minutes). Without `--capture` it is render only, about 7 minutes.
