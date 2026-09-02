You are producing the mandatory video for my hackathon submission. Deadline for the finished MP4 on disk: Thursday 3 Sep 2026, 22:00 IST. Submission itself is Friday 4 Sep 11:00 ET (20:30 IST). Today is Wednesday 2 Sep.

# What you are making

One MP4, 16:9, 1920x1080, H.264 video + AAC audio, 2:30 to 3:00 long, under 150 MB, at `C:\Users\toshn\alpaca-hackathon\presentation\video\final.mp4`, plus an `.srt` caption file next to it. Build it as a SCRIPT, not a manual edit: one command (`uv run presentation/video/build.py`) must regenerate the whole video, because three numbers change on Thursday and I want a re-render to cost 10 minutes, not an afternoon.

# The project, in ten lines (all numbers are measured and live in the repo)

1. Solo entry to the Alpaca AI Trading Agents Hackathon (lablab.ai), challenge "Options Alpha Agents". Prize pool $6,000. Judged on P&L Performance, Technology Implementation, Creativity & Originality, Presentation & Execution.
2. The agent sells the volatility risk premium on SPY with defined-risk iron condors, and refuses to trade when the premium is not measurably there. Refusals are logged with the same detail as fills.
3. Research was pre-registered before any backtest code existed (`research/PREREGISTRATION_R1.md`, provable from git history). 6.99 years of SPY out of sample: mean VRP +3.68 vol points over 1,741 observations, Newey-West t = +4.74 (the naive t of +18.16 is invalid because the windows overlap). 7 trials against a multiple-testing-corrected bar of 0.791.
4. The deployed tenor (21 to 45 days to expiry) was chosen from 8 days of live paper-market comparison, three candidates run in parallel: it traded on 2 of 5 days, the alternatives on 0 and 1. `research/DEPLOYMENT_DECISIONS.md`, section D3.
5. 11 numbered gates (0 to 10) plus a stagger rule run before any order. Gates 0, 2, 3 are circuit breakers. `agent/engine.py`, `agent/risk.py`.
6. Every runtime call goes through Alpaca's official MCP server (alpaca-mcp-server 2.3.0, 74 tools, JSON-RPC over stdio), every request and response recorded. `agent/mcp_client.py`.
7. Orders ladder from mid across up to 5 rungs; measured 1.5% of credit round trip on a real fill. A deadline mechanism flattens the whole book 90 minutes before submission so the result is realised, not marked.
8. Every decision is hashed into a SHA-256 Merkle tree with domain-separated leaves and nodes, sealed before outcomes are known. `make verify` recomputes it. 211 tests.
9. THE STORY BEAT: on the first live morning (31 Aug, 09:45 ET) a payload-parsing bug read the account as flat and the agent stacked four condors instead of one. The sealed log caught it: one artifact holds both the raw broker response with the legs and the reconciliation that ignored them. Bug, fix, regression test, and the adopted positions are all in the record. `RISK_REGISTER.md` sections 4.7 and 4.8 name the exact artifact.
10. Live state as of Tue 1 Sep close: 4 condors, 28 contracts, $3,108 credit collected, worst case capped at $10,840, equity $100,036.93 on a $100,000 paper account. 85 of 85 cycles ran unattended, 344 exit checks, 550+ sealed artifacts. The VIX tail hedge is designed and coded but has NEVER engaged live: Alpaca served zero VIX contracts all week, and the agent logs that refusal every cycle (`RISK_REGISTER.md` 4.9).

# Read these first, in this order, before planning anything

1. `presentation/VIDEO_BRIEF.md`: the approved script with timestamps and shot list. Use it as written; tighten wording only where the read-aloud pace needs it.
2. `presentation/WRITEUP.md` and `presentation/SUBMISSION_FORM.md`: the exact claims we are making. The video may not claim anything these do not.
3. `README.md`, `RISK_REGISTER.md` (4.6 to 4.9), `research/DEPLOYMENT_DECISIONS.md` (D1, D3).
4. `presentation/slides_draft.pdf` (14 slides; the architecture slide and the comparison slide are usable as full-frame visuals).
5. `artifacts/decisions.jsonl`: find the 31 Aug incident artifact that 4.7 names, and the newest cycle.

# Hard rules, no exceptions

- Do not modify anything outside `presentation/video/`. Do not touch `agent/`, `artifacts/`, `research/`, `.env`, `.env.live`. Do not run `agent/watchdog.py` or `agent/agent.py`. Do not place, cancel or inspect orders. The live agent runs on a Windows scheduled task at 18:50 IST tonight; a second process on the account is the one way this video costs us the competition.
- Never show, print, or open `.env` or `.env.live`. Never show the dev account `PA308NOY3X36` anywhere on screen. The submission account is `PA37R35A5ZGW`.
- No em-dashes in any on-screen text or captions. Use commas, periods, or colons.
- Do not say "Track 2". The challenge is "Options Alpha Agents".
- Do not claim the hedge protects the book. It never engaged live. Say so, it is a credibility point.
- Do not invent a number. Every number spoken or shown must trace to one of the files above or to the live dashboard. If you cannot trace it, cut it.
- Author every git commit as Nilay Toshniwal, no AI attribution lines in commit messages.

# Machine and toolchain

Windows 11, PowerShell. Python via `uv` (use `uv run --with <pkg>` for anything not installed). No Homebrew. Verify every tool by RUNNING it before you plan around it; if `ffmpeg` is missing, install it with `winget install Gyan.FFmpeg` and re-open the shell, and tell me you did.

Preferred pipeline, adjust only if a tool fails when run:
- Dashboard captures: Playwright (`uv run --with playwright python -m playwright install chromium`), full-page screenshots at 1920x1080. The public app is `https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app`. Its real content renders inside an iframe; capture `https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/~/+/` directly. If it shows a sleep page, click "Yes, get this app back up!" and wait 60 seconds.
- Terminal beats (`make verify`, `make summary`): run them for real in the repo (they are read-only) and render the actual output as a typed-text animation, not a screen recording.
- Slide frames: render PDF pages with PyMuPDF (`uv run --with pymupdf`).
- Narration: if `presentation/video/voiceover.wav` exists, use it and align cuts to it. If it does not exist, generate narration with `edge-tts` (`uv run --with edge-tts`), voice `en-US-AndrewNeural` or `en-GB-RyanNeural`, and do not ask me which. Normalise audio to -16 LUFS.
- Assembly: ffmpeg concat with crossfades of 0.3 s, captions burned in from the `.srt` (white text, dark band, bottom), plus the separate `.srt` file.
- Music: none. Silence between sentences is fine.

# Structured plan, with checkpoints

Phase 0, toolchain (30 min): run ffmpeg, Playwright, PyMuPDF, edge-tts. Report which worked as numbers ("4 of 4 tools run").
Phase 1, facts (30 min): read the files above. Produce `presentation/video/facts.md`: every number the script uses, each with its source file and line or dashboard field. Anything untraceable gets cut from the script.
Phase 2, storyboard (30 min): a beat table in `presentation/video/storyboard.md`: beat, start time, duration, on-screen asset, spoken line, caption text. Total must land between 2:30 and 3:00 at 150 words per minute. STOP and show me the storyboard before capturing anything. I will answer once.
Phase 3, assets (1.5 h): capture every frame into `presentation/video/assets/`. Name files by beat number.
Phase 4, narration (30 min): generate or import, one file per beat, so a single beat can be re-recorded without touching the rest.
Phase 5, build script (1.5 h): `build.py` takes `facts.md` values as parameters and produces `final.mp4` and `final.srt`. Run it end to end.
Phase 6, QA (30 min): report as numbers: duration, resolution, file size, loudness, number of beats, number of captions. Then grep every caption for em-dashes and for `PA308NOY3X36` (both must be 0). Watch the whole thing once at 1x and list every place a number on screen disagrees with `facts.md`.
Phase 7, handoff: give me the path, the QA numbers, and the exact command plus the three values I will change Thursday night (`LIVE_N`, `LIVE_PCT`, `LIVE_PNL`) before the final re-render.

# Quality bar

Judges watch dozens of these. The first 15 seconds carry the counter-intuitive claim ("built to refuse"), on screen over the live dashboard. Show evidence, do not describe it: the pre-registration file's git history on screen while the narration says "before any backtest code existed", the real `make verify` output while it says "one command". One number per beat, large, and the same number the narration says. The incident beat is the emotional centre of the video; give it the most screen time and the plainest words. End on "you do not have to trust me", over the repo README.

# Reporting rules

Numbers, not adjectives. State execution status only in these words: inspected / changed locally / verified locally / committed / pushed / blocked. Ask me exactly one thing, at the storyboard checkpoint, using a popup with options; otherwise decide and proceed. If something blocks you, say what you tried and the exact error, in one message.
