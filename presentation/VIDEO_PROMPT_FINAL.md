You built the video for this project on 2 Sep and I gave you a correction list on 3 Sep. This is the final pass. Submission closes TODAY, Friday 4 Sep, 20:30 IST. Read all of this before running anything.

Repo: `C:\Users\toshn\alpaca-hackathon`. Your files are intact: `presentation/video/build.py`, `facts.md`, `storyboard.md`, `final.srt`, `remotion/`, `assets/`.

# The schedule, which decides everything below

- Market opens 19:00 IST. The agent's deadline flatten runs 19:00 to 20:30 IST.
- Submission closes 20:30 IST, the same minute the flatten ends.
- **The final realised P&L therefore does not exist while there is still time to render.** Do not wait for it. Do not plan a re-render after 19:00 IST.

**Target: finished MP4 with narration on disk by 15:00 IST.** That leaves five hours of buffer before submission.

# 1. The P&L is now negative. This changes the script.

Yesterday's close was **99,434.93 equity, so minus 565.07** against the 100,000 start. It was positive when you last built. Do not hide this and do not soften it. Read the current value yourself rather than copying mine: last cycle in `artifacts/decisions.jsonl` with a `portfolio.equity`, minus 100000.

Rewrite the beat 8 line to something like:

> "Live, so far: minus five hundred and sixty five dollars on a hundred thousand dollar paper account, with four condors open and a worst case capped at ten thousand eight hundred and forty. One week of options P and L is mostly noise, and the research says so. In ninety minutes the agent flattens the book and that number becomes realised."

Three things that must survive the rewrite: the sign is spoken out loud, the loss is bounded by construction and you say the cap, and the flatten converts it to realised before judging. A losing week reported precisely is worth more here than a winning week reported vaguely, and the judges of the comparable event placed an entry that lost money live.

# 2. Corrections still outstanding from yesterday

**a. The VIX hedge line is factually wrong** in `final.srt` (around line 167). It says Alpaca "served no VIX data all week". What is true: the feed quotes the monthly VIX expiries (16 Sep, 21 Oct), and neither fell inside the hedge's 21 to 45 day window at any point, so no candidate was ever quotable. Replace with:

> "The tail hedge is coded and never engaged: no VIX expiry inside its window was quoted all week."

Source: `RISK_REGISTER.md` 4.9.

**b. The comparison numbers are stale.** Beat 5 cites T4 0/21, T6 10/21, T7 1/21 from 22 to 29 Aug. Read the current running totals from `artifacts/compare_summary.json` (`tally`) and say the window out loud, because the dashboard now shows the running totals and a judge will compare.

**c. `LIVE_N` and `LIVE_PCT` are stale** (81 and 95 in `facts.md`). Get current values from `make summary` or the dashboard headline. They now agree exactly, and both now exclude dry runs, which they did not when you built.

# 3. The project has a name: Glass Box

Submission title: "Glass Box: a pre-registered options agent whose every decision you can verify". The "refuses to trade" line survives as the opening hook, not the name.

Put the wordmark on screen in beat 1, quietly, over the existing dashboard recording. No new title card, no seconds spent.

The final deck is at `presentation/slides.pdf` (13 slides, dark navy, gold accent). Match the palette only if it is free.

# 4. One new beat, paid for by one trim

A judge at an AI agents hackathon will ask where the model is. The video does not currently answer, and the answer is our most distinctive claim.

**Add roughly 14 seconds between beat 7 (the incident) and beat 8 (live results).** Label "Where the AI sits".

> "This is an AI agents hackathon, so the honest question is where the model sits. Ours sits after the decision, never inside it. Once a decision is sealed, a language model reads that artifact and explains it in plain English, and every number it writes is checked against the artifact it came from. Explanations that invent a number are rejected and counted. So far: [EXPLAINED] explained, [REJECTED] rejected."

On screen: the dashboard's explanation box with its own label visible. Read `[EXPLAINED]` and `[REJECTED]` from `artifacts/explanations.json` (`counts`) and add both to `facts.md` as traced values.

**Pay for it by trimming beat 8** from 27.6 s to about 20 s. Keep the P&L number, the book line and the flatten sentence.

Total should land between 2:30 and 3:10.

# 5. Optional, only if it does not threaten 15:00 IST

- Beat 6: `make verify` could become `make judge`, which runs the tests, verifies the root, prints the summary and regenerates the results page in one command.
- One clause somewhere that the CLI is a read-only second opinion: "Alpaca's own CLI reads the account back, behind an allowlist that refuses every command that could place an order."

# 6. Run order

```
uv run python prep/live_week_report.py
# then edit presentation/video/facts.md: LIVE_N, LIVE_PCT, LIVE_PNL, EXPLAINED, REJECTED
uv run presentation/video/build.py --capture
uv run presentation/video/build.py --voice
```

Narration is the last blocking item. Use your existing Sarvam `rahul` voice, measured at 151 words per minute. If a beat runs long, change `PACE`, do not cut a number. Listen to the whole thing once, and check the corrected hedge sentence and the new negative-P&L line read naturally at pace.

# 7. Hard rules, unchanged

- **Do not modify anything outside `presentation/video/`.** Do not run `agent/watchdog.py` or `agent/agent.py`. Do not place, cancel or inspect orders.
- **After 18:45 IST, stop touching the machine hard.** The live agent starts at 18:50 and must flatten the book between 19:00 and 20:30. Last night 31 consecutive cycles timed out and the session lost 2.7 hours, so do not run heavy captures, browser installs or renders during that window. Be finished by 15:00 IST and this never becomes a question.
- Never show `.env`, `.env.live`, `.env.featherless`, or the dev account `PA308NOY3X36`. The submission account is `PA37R35A5ZGW`.
- No em-dashes in any on-screen text or caption.
- Do not invent a number. `build.py` already refuses to build if a number on screen is not in `facts.md`. Keep that guard on.
- Author every commit as Nilay Toshniwal.

# 8. When you are done

Report as numbers: duration, resolution, file size, loudness, beat count, caption count. Then confirm four things explicitly: the P&L line states the loss and its sign, the hedge sentence is corrected, the comparison numbers match `compare_summary.json`, and `LIVE_N`/`LIVE_PCT` match `make summary`. Give the file path and the one command to re-render.

Ask at most one question, and only if something here conflicts with what you can see in the repo.
