You built the video for this project on 2 Sep. This is the update pass. The repo has moved since you last ran, and three things you put on screen are now wrong. Read this whole message before running anything, then work through it in order.

Repo: `C:\Users\toshn\alpaca-hackathon`. Start there. Your own files are still in place: `presentation/video/build.py`, `facts.md`, `storyboard.md`, `final.srt`, `remotion/`, `assets/`.

# Timing, which is tighter than it looks

Today is Friday 4 Sep. Submission closes 20:30 IST. The agent's deadline flatten runs 19:00 to 20:30 IST, so the final realised P&L does not exist until the deadline itself. Do not wait for it. The video narrates Thursday's close as "so far" and says the flatten closes the book before submission. That is accurate and it is the only safe option.

Target: re-rendered video with narration on disk by 14:00 IST, so there are six hours of buffer.

# 1. Three corrections, all factual, all mandatory

**a. The VIX hedge line is wrong.** `final.srt` (around line 167) and the matching narration say Alpaca "served no VIX data all week". That was our error, corrected 3 Sep after probing the feed properly. What is true: the indicative feed quotes the monthly VIX expiries (16 Sep and 21 Oct), and neither fell inside the hedge's 21 to 45 day window at any point during the week, so no candidate was ever quotable. The contracts exist and trade; the window and the feed's coverage never overlapped. Replace the line with:

> "The tail hedge is coded and never engaged: no VIX expiry inside its window was quoted all week."

Source of truth: `RISK_REGISTER.md` section 4.9.

**b. The comparison numbers are stale.** Beat 5 cites T4 0/21, T6 10/21, T7 1/21 from the 22 to 29 Aug window. Those are still true for that window, but the dashboard now shows running totals, and a judge who watches the video then opens the dashboard will see different numbers. Use the current totals and say the window out loud. Read them from `artifacts/compare_summary.json` (`tally`), do not copy from here.

**c. The headline count changed and so did the percentage.** `LIVE_N` and `LIVE_PCT` in `facts.md` are 81 and 95. Read the current values from `make summary` ("decision opportunities (market open, in window)" and the "N of M opportunities" line) or the dashboard headline, which now agree exactly. They also exclude dry runs, which they did not on 2 Sep, so the numbers moved for a reason worth knowing rather than drifting.

# 2. The project has a name now: Glass Box

The submission title is "Glass Box: a pre-registered options agent whose every decision you can verify". "An options agent that refuses to trade" survives as the opening hook, not the name.

Put the wordmark on screen in beat 1, quietly. A lower-third or a small mark that appears over the dashboard recording and fades. Do not add a title card that costs seconds.

The final deck is at `presentation/slides.pdf` (13 slides, dark navy, gold accent, Cambria headings). Match its palette if that is cheap; do not redesign anything to match it.

# 3. One new beat, and one trim to pay for it

This is an AI agents hackathon and a judge will ask where the model is. The video currently does not answer that, and the answer is now our most distinctive claim.

**Add a beat, about 14 seconds, between beat 7 (the incident) and beat 8 (live results).** Label it "Where the AI sits". Content:

> "This is an AI agents hackathon, so the honest question is where the model sits. Ours sits after the decision, never inside it. Once a decision is sealed, a language model reads that artifact and explains it in plain English, and every number it writes is checked against the artifact it came from. Explanations that invent a number are rejected and counted. So far: [EXPLAINED] explained, [REJECTED] rejected."

On screen: the dashboard's explanation box under a decision, with its own label visible ("Explained after the fact... the decision was sealed before this text existed"). Read `[EXPLAINED]` and `[REJECTED]` from `artifacts/explanations.json` (`counts`). Add both to `facts.md` as traced values like everything else.

**Pay for it by trimming beat 8** from 27.6 s to about 20 s. It is the longest beat and carries the most slack. Keep the P&L number, the book line and the flatten sentence; cut the rest.

Total should still land between 2:30 and 3:10.

# 4. Optional, only if the render budget allows

Do not do these if they put the 14:00 IST target at risk.

- Beat 6 (`make verify`) could become `make judge`, which runs the tests, verifies the root, prints the summary and regenerates the results page in one command. Slightly stronger, same screen time.
- One line in beat 4 or 6 that the CLI is a read-only second opinion: "Alpaca's own CLI reads the account back, behind an allowlist that refuses every command that could place an order." Only if a beat has room without growing.

# 5. Narration

Narration is the last blocking item. Generate it with your existing `--voice` path and the Sarvam `rahul` voice already measured at 151 words per minute. If a beat runs long, use `PACE` rather than cutting a number.

Listen to the whole thing once before declaring it done. Specifically check that the corrected hedge sentence reads naturally at pace, since it is longer than the line it replaces.

# 6. Run order

```
node --version                                   # sanity
uv run python prep/live_week_report.py           # regenerates research/LIVE_WEEK.md from the log
# edit presentation/video/facts.md: LIVE_N, LIVE_PCT, LIVE_PNL, plus the new EXPLAINED and REJECTED
uv run presentation/video/build.py --capture     # re-records the dashboard, re-shoots GitHub frames
uv run presentation/video/build.py --voice       # narration
```

`LIVE_PNL` is Thursday's close: equity minus 100,000, from the last cycle in `artifacts/decisions.jsonl` with a `portfolio.equity`. Narrate the sign out loud ("plus"), and keep the words "so far".

# 7. Hard rules, unchanged

- Do not modify anything outside `presentation/video/`. Do not run `agent/watchdog.py` or `agent/agent.py`. Do not place, cancel or inspect orders. The live agent runs tonight on a scheduled task; a second process on that account is the one way this costs us the competition.
- Never show `.env`, `.env.live`, `.env.featherless`, or the dev account `PA308NOY3X36`. The submission account is `PA37R35A5ZGW`.
- No em-dashes in any on-screen text or caption.
- Do not invent a number. Every number spoken or shown traces to a file, and `build.py` already refuses to build otherwise. Keep that guard on.
- Author every commit as Nilay Toshniwal.

# 8. When you are done

Report as numbers: duration, resolution, file size, loudness, beat count, caption count. Then confirm three things explicitly: the hedge sentence is corrected, the comparison numbers match `compare_summary.json`, and `LIVE_N`/`LIVE_PCT` match `make summary`. Say where the file is and what the one command to re-render it would be.

Ask at most one question, and only if a correction above conflicts with something you can see in the repo.
