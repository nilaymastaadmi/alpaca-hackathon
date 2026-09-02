# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Build the submission video from facts, captured assets and narration.

    uv run presentation/video/build.py              # silent build (captions only)
    uv run presentation/video/build.py --voice      # generate missing narration with Sarvam, then build
    uv run presentation/video/build.py --capture    # re-capture the dashboard and GitHub frames first
    uv run presentation/video/build.py --no-render  # write timeline.json and final.srt only

Outputs: presentation/video/final.mp4 and presentation/video/final.srt.

The script is the edit. Change a number in facts.md (PARAMS block), re-run, and the
narration for the beats whose text changed is regenerated (the rest is cached by text
hash), the terminal beats re-run `make verify` and `make summary` for real, and Remotion
re-renders the whole thing. Nothing here writes outside presentation/video/.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REMOTION = HERE / "remotion"
PUBLIC = REMOTION / "public"
ASSETS = HERE / "assets"
NARR = HERE / "narration"
FINAL = HERE / "final.mp4"
FINAL_RAW = HERE / "final_raw.mp4"
SRT = HERE / "final.srt"
TIMELINE = PUBLIC / "timeline.json"

FPS = 30
W, H = 1920, 1080
TRANSITION = 9      # 0.3 s crossfade
LEAD = 9            # frames of silence before speech in each beat
GAP = 15            # 0.5 s of silence after speech
WPM_SILENT = 150    # pacing used when no narration file exists
DEV_ACCOUNT = "PA308NOY3X36"
EM_DASH = "\u2014"
SARVAM_URL = "https://api.sarvam.ai/text-to-speech"

ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str], cwd: Path = REPO, check: bool = True) -> str:
    exe = shutil.which(cmd[0])
    if exe is None:
        sys.exit(f"missing tool: {cmd[0]}")
    p = subprocess.run([exe, *cmd[1:]], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    if check and p.returncode != 0:
        sys.exit(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p.stdout


# ------------------------------------------------------------------ facts
def parse_params() -> dict[str, str]:
    text = (HERE / "facts.md").read_text(encoding="utf-8")
    m = re.search(r"## PARAMS.*?```\n(.*?)```", text, re.S)
    if not m:
        sys.exit("facts.md has no PARAMS block")
    params: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            params[k.strip()] = v.strip()
    for k in ("LIVE_N", "LIVE_PCT", "LIVE_PNL", "VOICE", "PACE"):
        if k not in params:
            sys.exit(f"facts.md PARAMS is missing {k}")
    return params


def pnl_words(v: float) -> str:
    sign = "plus" if v >= 0 else "minus"
    dollars = int(abs(v))
    cents = int(round((abs(v) - dollars) * 100))
    s = f"{sign} {dollars:,} dollar{'s' if dollars != 1 else ''}"
    if cents:
        s += f" and {cents} cents"
    return s


def pnl_text(v: float) -> str:
    return f"{'+' if v >= 0 else '-'}${abs(v):,.2f}"


# ------------------------------------------------------------------ live evidence (read-only)
def verify_output() -> tuple[str, str]:
    out = run(["uv", "run", "--with", "requests", "python", "agent/artifacts.py", "verify"]).strip().splitlines()
    line = out[-1] if out else ""
    if not line.startswith("VERIFIED"):
        sys.exit(f"make verify did not say VERIFIED:\n{line}")
    m = re.search(r"VERIFIED: (\d+) artifacts", line)
    return line, (m.group(1) if m else "?")


def summary_output() -> dict[str, int]:
    out = run(["uv", "run", "--with", "requests", "python", "agent/artifacts.py", "summary"])
    res: dict[str, int] = {}
    m = re.search(r"decision opportunities \(market open, in window\): (\d+)", out)
    if m:
        res["opportunities"] = int(m.group(1))
    m = re.search(r"refusals by blocking gate \((\d+) of (\d+) opportunities\)", out)
    if m:
        res["refused"] = int(m.group(1))
    m = re.search(r"hedge:no_candidate\s+(\d+)", out)
    if m:
        res["hedge_refusals"] = int(m.group(1))
    return res


def gitlog() -> list[dict]:
    out = run(["git", "log", "--diff-filter=A", "--reverse", "--date=format:%Y-%m-%d %H:%M:%S", "--format=%h|%ad|%s", "--", "research/PREREGISTRATION_R1.md", "backtest/"])
    lines = []
    for raw in out.strip().splitlines()[:4]:
        h, t, s = raw.split("|", 2)
        lines.append({"hash": h, "time": t, "subject": s, "highlight": len(lines) < 2})
    if len(lines) < 2 or "Pre-register" not in lines[0]["subject"]:
        sys.exit(f"git history does not start with the pre-registration commit: {lines[:2]}")
    return lines


def seq30_excerpt() -> dict:
    path = REPO / "artifacts" / "decisions.jsonl"
    rec = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            if '"seq": 30,' in line or '"seq":30,' in line:
                r = json.loads(line)
                if r.get("seq") == 30:
                    rec = r
                    break
    if rec is None:
        sys.exit("artifact seq 30 not found in artifacts/decisions.jsonl")
    ts = rec["timestamp"]
    gate5 = next(g for g in rec["gates"] if g.get("number") == 5)
    call = next(c for c in rec["mcp_calls"] if c.get("tool") == "get_all_positions")
    summary = call.get("result_summary", "")
    i = summary.find('"data"')
    j = summary.find("SPY261002C00792000")
    if i < 0 or j < 0:
        sys.exit("seq 30 get_all_positions response does not contain the expected legs")
    tail = summary[j + len("SPY261002C00792000") + 1:]
    m = re.search(r'"asset_class": "[^"]+"', tail)
    symbol_line = '    "symbol": "SPY261002C00792000"' + (", " + m.group(0) if m else "") + ' ..."}'
    recon = rec["reconciliation"][0]
    return {
        "header": f"artifacts/decisions.jsonl    seq 30    {ts[:10]} {ts[11:19]} ET    action: {rec['action']}",
        "gate5": [
            '{"gate": "capacity", "number": 5, "passed": true,',
            f' "reason": "{gate5["reason"]}"}}',
        ],
        "positions": [
            '{"tool": "get_all_positions", "ok": true,',
            ' "result_summary": "{... "data": {"result": [{...',
            symbol_line,
        ],
        "reconcile": [
            f'{{"position": "{recon["position"]}", "severity": "{recon["severity"]}",',
            f' "issue": "{recon["issue"]}",',
            f' "expected_legs": ["{recon["expected_legs"][0]}", ...]}}',
        ],
    }


# ------------------------------------------------------------------ script
def script(p: dict[str, str]) -> list[dict]:
    live_n = int(p["LIVE_N"])
    live_pct = int(p["LIVE_PCT"])
    live_pnl = float(p["LIVE_PNL"])
    return [
        {
            "id": "b01", "kicker": "01  built to refuse",
            "text": f"Most trading agents are built to trade. This one is built to refuse. Over the live week it evaluated {live_n} real opportunities and declined {live_pct} percent of them, and every refusal is a signed artifact you can verify yourself. Let me show you why that is the point, not a bug.",
            "anchors": {"n81": f"evaluated {live_n}", "declined": "declined"},
        },
        {
            "id": "b02", "kicker": "02  pre-registered",
            "text": "The thesis is the volatility risk premium: SPY options are priced richer than the movement that follows. Before a single line of backtest code, I pre-registered the hypotheses, the trial count, and a multiple-testing bar. The git history proves the order.",
            "anchors": {"pre": "Before a single line", "git": "The git history"},
        },
        {
            "id": "b03", "kicker": "03  the edge is real",
            "text": "Nearly seven years of SPY, out of sample: mean premium 3.68 vol points over 1,741 observations, Newey-West t of 4.74. The naive t of 18 is invalid, because the windows overlap. The edge is real, and the number is honest.",
            "anchors": {"vrp": "3.68", "obs": "1,741", "t": "Newey-West", "naive": "The naive"},
        },
        {
            "id": "b04", "kicker": "04  eleven gates",
            "text": "The agent sells that premium with defined-risk iron condors, only after eleven numbered gates pass: position integrity, timing, circuit breakers, a contango filter, the premium threshold at the exact strikes it would sell, event proximity, cost, sizing, and a stagger rule. Every call goes through Alpaca's official MCP server, request and response recorded.",
            "anchors": {"eleven": "eleven numbered", "listStart": "position integrity", "listEnd": "sizing", "stagger": "stagger rule", "mcp": "Every call"},
        },
        {
            "id": "b05", "kicker": "05  raced live, not ranked",
            "text": "The deployed tenor was not picked from the backtest ranking. Three candidates raced live in parallel for eight days on real market data, risking nothing. The one that actually traded won: two days of five, against zero and one.",
            "anchors": {"three": "Three candidates", "eight": "eight days", "won": "won"},
        },
        {
            "id": "b06", "kicker": "06  one command",
            "text": "Every decision, fill and refusal is hashed into a Merkle tree, sealed before outcomes are known. One command recomputes the root. If anything had been edited after the fact, this line would not say verified.",
            "anchors": {"sealed": "sealed before", "command": "One command"},
        },
        {
            "id": "b07", "kicker": "07  the record caught its author",
            "text": "Here is the strongest evidence that this works. On the first live morning, a payload-parsing bug read the account as flat, and the agent stacked four condors instead of one. The sealed log caught it: one artifact holds both the raw broker response with the legs, and the reconciliation that ignored them. Bug, fix, regression tests and the adopted positions are all in the record. I did not hide it. The record would not let me.",
            "anchors": {"morning": "On the first live morning", "flat": "read the account", "four": "stacked four", "raw": "the raw broker", "recon": "the reconciliation", "record": "Bug, fix"},
        },
        {
            "id": "b08", "kicker": "08  live, so far",
            "text": f"Live P&L so far: {pnl_words(live_pnl)} on a hundred thousand dollar paper account. On Friday a deadline flatten closes every position ninety minutes before submission. Realised, not marked. One week of options P&L is mostly noise, and the write-up says so. The tail hedge is coded and never engaged: Alpaca served no VIX data all week. That refusal is logged every cycle too.",
            "anchors": {"friday": "On Friday", "noise": "One week", "hedge": "The tail hedge"},
        },
        {
            "id": "b09", "kicker": "09  verify it yourself",
            "text": "Clone it. Run make test, make verify, make summary. You do not have to trust me. That is the whole design.",
            "anchors": {"trust": "You do not"},
            "tail": 45,
        },
    ]


# ------------------------------------------------------------------ narration
def sarvam_key() -> str:
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        f = HERE / ".env.sarvam"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("SARVAM_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("no Sarvam key: set SARVAM_API_KEY or create presentation/video/.env.sarvam")
    return key


def sarvam_tts(text: str, voice: str, pace: float, out: Path) -> None:
    import requests

    body = {
        "text": text,
        "target_language_code": "en-IN",
        "speaker": voice,
        "model": "bulbul:v3",
        "pace": pace,
        "speech_sample_rate": 24000,
        "output_audio_codec": "wav",
    }
    hdr = {"api-subscription-key": sarvam_key(), "Content-Type": "application/json"}
    for attempt in range(4):
        r = requests.post(SARVAM_URL, headers=hdr, json=body, timeout=120)
        if r.status_code == 200:
            audio = base64.b64decode(r.json()["audios"][0])
            out.write_bytes(audio)
            return
        log(f"sarvam HTTP {r.status_code} on attempt {attempt + 1}: {r.text[:120]}")
        time.sleep(3 * (attempt + 1))
    sys.exit("Sarvam TTS failed 4 times")


def ffprobe_duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


def loudnorm(src: Path, dst: Path) -> None:
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", str(dst)])


def narration(beats: list[dict], p: dict[str, str], want_voice: bool) -> None:
    """Fill beat['audio'] (public-relative path or None) and beat['speechSec']."""
    NARR.mkdir(exist_ok=True)
    (PUBLIC / "narration").mkdir(parents=True, exist_ok=True)
    voice, pace = p["VOICE"], float(p["PACE"])
    for b in beats:
        key = hashlib.sha1(f"{b['text']}|{voice}|{pace}|bulbul:v3".encode()).hexdigest()[:12]
        wav = NARR / f"{b['id']}.wav"
        side = NARR / f"{b['id']}.json"
        fresh = wav.exists() and side.exists() and json.loads(side.read_text()).get("key") == key
        if not fresh and want_voice:
            log(f"narration {b['id']}: generating with Sarvam ({voice}, pace {pace})")
            sarvam_tts(b["text"], voice, pace, wav)
            side.write_text(json.dumps({"key": key, "voice": voice, "pace": pace, "text": b["text"]}, indent=1))
            fresh = True
        if fresh:
            norm = PUBLIC / "narration" / f"{b['id']}.wav"
            loudnorm(wav, norm)
            b["audio"] = f"narration/{b['id']}.wav"
            b["speechSec"] = ffprobe_duration(norm)
        else:
            if wav.exists() and not fresh:
                log(f"narration {b['id']}: text changed since it was recorded, run with --voice to regenerate (using silent timing)")
            b["audio"] = None
            b["speechSec"] = len(b["text"].split()) / WPM_SILENT * 60


# ------------------------------------------------------------------ timeline
def _pack(parts: list[str], max_len: int) -> list[str]:
    out: list[str] = []
    cur = ""
    for part in parts:
        if cur and len(cur) + len(part) + 1 > max_len:
            out.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_captions(text: str, max_len: int = 86) -> list[str]:
    """Sentences first; a long sentence breaks at clause boundaries, then at words."""
    sentences = re.split(r"(?<=[.?!])\s+", text.strip())
    chunks: list[str] = []
    for s in sentences:
        if len(s) <= max_len:
            chunks.append(s)
            continue
        clauses = [c.strip() for c in re.split(r"(?<=[,:;])\s+", s) if c.strip()]
        for piece in _pack(clauses, max_len):
            if len(piece) <= max_len:
                chunks.append(piece)
            else:
                chunks.extend(_pack(piece.split(), max_len))
    # merge very short fragments into the previous chunk
    merged: list[str] = []
    for c in chunks:
        if merged and len(c) < 24 and len(merged[-1]) + len(c) + 1 <= max_len:
            merged[-1] = f"{merged[-1]} {c}"
        else:
            merged.append(c)
    return merged


def frames(sec: float) -> int:
    return int(round(sec * FPS))


def build_beats(beats: list[dict]) -> list[dict]:
    out = []
    for b in beats:
        speech = frames(b["speechSec"])
        tail = b.get("tail", GAP)
        duration = LEAD + speech + tail
        text = b["text"]
        n = len(text)
        anchors = {}
        for name, needle in b["anchors"].items():
            i = text.find(needle)
            if i < 0:
                sys.exit(f"anchor {name!r} ({needle!r}) not found in beat {b['id']}")
            anchors[name] = LEAD + int(round(speech * i / n))
        caps = []
        chunks = chunk_captions(text)
        pos = 0
        for k, c in enumerate(chunks):
            i = text.find(c, pos)
            i = i if i >= 0 else pos
            start = LEAD + int(round(speech * i / n))
            pos = i + len(c)
            caps.append({"start": start, "text": c})
        for k, c in enumerate(caps):
            c["end"] = caps[k + 1]["start"] if k + 1 < len(caps) else duration - TRANSITION
        out.append({
            "id": b["id"], "kicker": b["kicker"], "durationInFrames": duration, "lead": LEAD, "speech": speech,
            "audio": b["audio"], "captions": caps, "anchors": anchors, "text": text,
        })
    return out


def build_timeline(p: dict[str, str], beats: list[dict], verify: tuple[str, str], summ: dict[str, int]) -> dict:
    live_pnl = float(p["LIVE_PNL"])
    gates = [
        (0, "position integrity", True), (1, "session window", False), (2, "drawdown breaker", True),
        (3, "daily loss limit", True), (4, "consecutive-loss pause", False), (5, "capacity", False),
        (6, "regime: contango required", False), (7, "VRP threshold at the traded strikes", False),
        (8, "macro-event proximity", False), (9, "cost ceiling", False), (10, "sizing", False),
    ]
    return {
        "fps": FPS, "width": W, "height": H, "transition": TRANSITION,
        "beats": build_beats(beats),
        "facts": {
            "LIVE_N": int(p["LIVE_N"]), "LIVE_PCT": int(p["LIVE_PCT"]), "LIVE_PNL": live_pnl,
            "LIVE_PNL_TEXT": pnl_text(live_pnl), "ARTIFACTS": verify[1], "TESTS": 211,
        },
        "verify": {"command": "make verify", "output": verify[0], "count": verify[1]},
        "gitlog": gitlog(),
        "seq30": seq30_excerpt(),
        "fills": ["09:45 ET   condor 1 filled", "09:55 ET   condor 2 filled", "10:05 ET   condor 3 filled", "10:21 ET   condor 4 filled"],
        "record": [
            "the bug, pinned by artifact seq 30",
            "the fix: an unknown payload shape now raises, never reads as flat",
            "9 regression tests in tests/test_position_sync.py",
            "3 orphan condors adopted into the ledger; all 4 managed by every gate since",
            "the watchdog now restarts itself if it is killed",
        ],
        "race": {
            "title": "22 to 29 Aug: three tenors ran live in parallel, 21 cycles over 5 trading days, no orders sent",
            "tenors": [
                {"id": "T4", "dte": "7 to 14 DTE", "cycles": "0 / 21", "days": "0 / 5", "deployed": False},
                {"id": "T6", "dte": "21 to 45 DTE", "cycles": "10 / 21", "days": "2 / 5", "deployed": True},
                {"id": "T7", "dte": "5 to 10 DTE", "cycles": "1 / 21", "days": "1 / 5", "deployed": False},
            ],
        },
        "gates": [{"n": n, "name": name, "breaker": br} for n, name, br in gates],
        "live": {
            "pnl": f"{pnl_text(live_pnl)} so far",
            "pnlSub": "on a $100,000 paper account, Alpaca paper trading",
            "book": "4 condors, 28 contracts, $3,108 credit collected, worst case capped at $10,840",
            "flatten": "Friday: a deadline flatten closes every position 90 minutes before submission. Realised, not marked.",
            "noise": "One week of options P&L is mostly noise. The write-up says so.",
            "hedge": "VIX tail hedge: designed and coded, never engaged.",
            "hedgeSub": f"Alpaca served 0 VIX contracts all week. {summ.get('hedge_refusals', '?')} refusals to hedge, logged one per cycle.",
        },
        "close": {
            "line": "You do not have to trust me.",
            "commands": "make test, make verify, make summary",
            "url": "github.com/nilaymastaadmi/alpaca-hackathon",
            "tests": "211 tests. Paper trading only. MIT.",
        },
    }


def safety_check(tl: dict) -> None:
    blob = json.dumps(tl, ensure_ascii=False)
    if EM_DASH in blob:
        sys.exit("ABORT: an em-dash reached the timeline")
    if DEV_ACCOUNT in blob:
        sys.exit("ABORT: the dev account string reached the timeline")


def write_srt(tl: dict) -> int:
    def ts(frame: int) -> str:
        ms = int(round(frame * 1000 / FPS))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    n = 0
    start = 0
    for i, b in enumerate(tl["beats"]):
        for c in b["captions"]:
            n += 1
            lines.append(f"{n}\n{ts(start + c['start'])} --> {ts(start + c['end'])}\n{c['text']}\n")
        start += b["durationInFrames"] - TRANSITION
    SRT.write_text("\n".join(lines), encoding="utf-8")
    return n


# ------------------------------------------------------------------ render
def sync_assets() -> None:
    dst = PUBLIC / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    needed = ["b01_dashboard.png", "b02_prereg.png", "slide05.png", "b08_positions.png", "b09_readme.png"]
    for name in needed:
        src = ASSETS / name
        if not src.exists():
            sys.exit(f"missing asset {src}; run with --capture (it also renders slide05.png from the deck)")
        shutil.copy2(src, dst / name)


def render(silent: bool) -> None:
    cmd = ["npx", "remotion", "render", "src/index.ts", "Final", str(FINAL_RAW), f"--props={TIMELINE}", "--crf=20", "--log=error"]
    log("rendering with Remotion (this is the slow step)")
    t0 = time.time()
    run(cmd, cwd=REMOTION)
    log(f"remotion render finished in {time.time() - t0:.0f} s")
    if silent:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(FINAL_RAW), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(FINAL)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(FINAL_RAW), "-c:v", "copy",
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(FINAL)])


def qa(tl: dict, n_captions: int) -> None:
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height:format=duration,size", "-of", "json", str(FINAL)])
    info = json.loads(out)
    streams = {s["codec_name"]: s for s in info["streams"]}
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    loud = subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-nostats", "-i", str(FINAL), "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", loud)
    srt = SRT.read_text(encoding="utf-8")
    print()
    print("QA")
    print(f"  duration     {int(dur // 60)}:{dur % 60:05.2f}  ({dur:.2f} s)")
    print(f"  resolution   {streams.get('h264', {}).get('width')}x{streams.get('h264', {}).get('height')}  video {'h264' if 'h264' in streams else 'MISSING'}, audio {'aac' if 'aac' in streams else 'MISSING'}")
    print(f"  size         {size_mb:.1f} MB")
    print(f"  loudness     {m.group(1) if m else 'n/a'} LUFS integrated")
    print(f"  beats        {len(tl['beats'])}")
    print(f"  captions     {n_captions}")
    print(f"  em-dashes    {srt.count(EM_DASH)} in final.srt")
    print(f"  dev account  {srt.count(DEV_ACCOUNT)} in final.srt")
    print(f"  output       {FINAL}")
    print(f"  captions     {SRT}")
    ok = 150 <= dur <= 180 and size_mb < 150 and srt.count(EM_DASH) == 0 and srt.count(DEV_ACCOUNT) == 0
    print(f"  verdict      {'PASS' if ok else 'CHECK'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true", help="re-capture the dashboard and GitHub frames first")
    ap.add_argument("--voice", action="store_true", help="generate missing or stale narration with Sarvam")
    ap.add_argument("--no-render", action="store_true", help="write timeline.json and final.srt only")
    args = ap.parse_args()

    for tool in ("uv", "ffmpeg", "ffprobe", "npx", "git"):
        if shutil.which(tool) is None:
            sys.exit(f"missing tool on PATH: {tool}")
    p = parse_params()
    log(f"params: LIVE_N={p['LIVE_N']} LIVE_PCT={p['LIVE_PCT']} LIVE_PNL={p['LIVE_PNL']} VOICE={p['VOICE']} PACE={p['PACE']}")

    if args.capture:
        log("capturing dashboard and GitHub frames")
        run(["uv", "run", "--with", "playwright", "--with", "pymupdf", "python", str(HERE / "capture.py")])
    sync_assets()

    verify = verify_output()
    log(f"make verify: {verify[0][:90]}")
    summ = summary_output()
    log(f"make summary: {summ}")
    if summ.get("opportunities") and summ["opportunities"] != int(p["LIVE_N"]):
        log(f"WARNING: facts.md LIVE_N={p['LIVE_N']} but make summary reports {summ['opportunities']} opportunities")
    if summ.get("opportunities") and summ.get("refused") is not None:
        pct = round(100 * summ["refused"] / summ["opportunities"])
        if pct != int(p["LIVE_PCT"]):
            log(f"WARNING: facts.md LIVE_PCT={p['LIVE_PCT']} but make summary implies {pct}%")

    beats = script(p)
    narration(beats, p, args.voice)
    silent = all(b["audio"] is None for b in beats)
    if silent:
        log("no narration files: building a silent cut timed at 150 words per minute")
    elif any(b["audio"] is None for b in beats):
        sys.exit("some beats have narration and some do not; run with --voice to fill the gaps")

    tl = build_timeline(p, beats, verify, summ)
    safety_check(tl)
    PUBLIC.mkdir(exist_ok=True)
    TIMELINE.write_text(json.dumps(tl, indent=1, ensure_ascii=False), encoding="utf-8")
    n_caps = write_srt(tl)
    total = sum(b["durationInFrames"] for b in tl["beats"]) - (len(tl["beats"]) - 1) * TRANSITION
    log(f"timeline: {len(tl['beats'])} beats, {n_caps} captions, {total / FPS:.1f} s planned")
    for b in tl["beats"]:
        log(f"  {b['id']}  {b['durationInFrames'] / FPS:5.1f} s  {'voiced' if b['audio'] else 'silent'}")
    if args.no_render:
        return
    render(silent)
    FINAL_RAW.unlink(missing_ok=True)
    qa(tl, n_caps)


if __name__ == "__main__":
    main()
