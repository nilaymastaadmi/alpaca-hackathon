"""Record real dashboard footage with Playwright: a browser tab, a visible cursor, a scroll.

    uv run --with playwright presentation/video/record.py

Writes presentation/video/assets/dash_top.mp4 and dash_positions.mp4 (1920x1080, H.264).
Read-only against the world: it opens the public dashboard and moves a fake cursor.
The cursor is a yellow dot injected into the page so the recording shows intent, the
way a screen recording of a person using the app would.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TMP = HERE / "assets" / "_rec"
DASH = "https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/~/+/"
DEV_ACCOUNT = "PA308NOY3X36"
W, H = 1920, 1080

CURSOR_JS = """
(() => {
  const d = document.createElement('div');
  d.id = '__cursor';
  Object.assign(d.style, {position: 'fixed', left: '0px', top: '0px', width: '22px', height: '22px',
    borderRadius: '11px', background: '#f5d90a', boxShadow: '0 0 0 4px rgba(245,217,10,0.35), 0 4px 14px rgba(0,0,0,0.6)',
    pointerEvents: 'none', zIndex: 2147483647, transform: 'translate(-11px,-11px)', transition: 'transform 80ms'});
  document.body.appendChild(d);
  window.addEventListener('mousemove', e => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
  window.__pulse = () => { d.style.transform = 'translate(-11px,-11px) scale(0.6)'; setTimeout(() => d.style.transform = 'translate(-11px,-11px)', 140); };
})();
"""


def glide(page, x0, y0, x1, y1, steps=40, dt=0.016):
    for i in range(1, steps + 1):
        t = i / steps
        e = t * t * (3 - 2 * t)  # ease in-out
        page.mouse.move(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)
        time.sleep(dt)


def scroll_container(page):
    return "document.querySelector('[data-testid=\"stAppViewContainer\"] section, .stMain, section.main') || document.scrollingElement"


def smooth_scroll(page, dy, steps=45, dt=0.016):
    per = dy / steps
    for _ in range(steps):
        page.evaluate(f"({scroll_container(page)}).scrollBy(0, {per})")
        time.sleep(dt)


def wake(page):
    page.goto(DASH, wait_until="domcontentloaded", timeout=120_000)
    for _ in range(3):
        btn = page.get_by_text("Yes, get this app back up!", exact=False)
        if btn.count():
            btn.first.click()
            time.sleep(60)
            page.goto(DASH, wait_until="domcontentloaded", timeout=120_000)
        else:
            break
    page.wait_for_selector("text=What the agent decided", timeout=180_000)
    time.sleep(6)
    if DEV_ACCOUNT in page.inner_text("body"):
        sys.exit("ABORT: dev account string visible on the dashboard")


def record(name: str, drive, tail: float = 14.0) -> None:
    """Record, then trim the page-load seconds so the clip starts 0.8 s before the cursor moves.
    A long idle tail lets the composition hold on the final state; the last frame is also
    saved as a PNG so a beat longer than the clip can freeze on it."""
    TMP.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  color_scheme="dark", record_video_dir=str(TMP),
                                  record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        t0 = time.time()
        wake(page)
        page.evaluate(CURSOR_JS)
        page.mouse.move(1500, 900)
        time.sleep(1.5)
        start = time.time() - t0 - 0.8
        drive(page)
        time.sleep(tail)
        path = page.video.path()
        ctx.close()
        browser.close()
    out = ASSETS / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", path, "-vf", f"scale={W}:{H}", "-r", "30",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(out)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(out), "-frames:v", "1", "-update", "1",
                    str(ASSETS / f"{name}_last.png")], check=True)
    shutil.rmtree(TMP, ignore_errors=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                         capture_output=True, text=True).stdout.strip()
    print(f"wrote {out.name} {float(dur):.1f} s (trimmed {start:.1f} s of page load)")


def drive_top(page):
    # Rest on the title, glide to the equity metric, then down to the headline sentence and pulse on "81".
    glide(page, 1500, 900, 300, 270, steps=50)
    time.sleep(0.6)
    glide(page, 300, 270, 640, 420, steps=45)
    time.sleep(0.4)
    glide(page, 640, 420, 112, 418, steps=30)
    page.evaluate("window.__pulse()")
    time.sleep(1.2)
    glide(page, 112, 418, 860, 418, steps=60)
    time.sleep(1.4)


def drive_positions(page):
    heading = page.get_by_text("Open positions (", exact=False).first
    page.mouse.move(1500, 600)
    time.sleep(0.4)
    # scroll in steps until the heading sits near the top of the viewport
    for _ in range(40):
        box = heading.bounding_box()
        if box and 60 <= box["y"] <= 140:
            break
        target = (box["y"] - 100) if box else 600
        smooth_scroll(page, max(-600, min(600, target)), steps=18)
    time.sleep(0.6)
    glide(page, 1500, 600, 700, 250, steps=45)
    time.sleep(0.5)
    glide(page, 700, 250, 1120, 250, steps=40)
    page.evaluate("window.__pulse()")
    time.sleep(1.5)


def drive_explain(page):
    """Scroll to the latest decision so its plain-English explanation and the
    'explained after the fact' label are both in frame, then trace the label."""
    page.mouse.move(1500, 700)
    time.sleep(0.4)
    heading = page.get_by_text("Latest decision:", exact=False).first
    for _ in range(40):
        box = heading.bounding_box()
        if box and 70 <= box["y"] <= 150:
            break
        target = (box["y"] - 110) if box else 700
        smooth_scroll(page, max(-700, min(700, target)), steps=18)
    time.sleep(0.8)
    glide(page, 1500, 700, 300, 240, steps=45)   # the explanation paragraph
    time.sleep(1.0)
    glide(page, 300, 240, 300, 340, steps=30)    # down to the "explained after the fact" label
    page.evaluate("window.__pulse()")
    time.sleep(1.6)
    glide(page, 300, 340, 1180, 340, steps=55)   # along it to the accepted/rejected counts
    time.sleep(1.6)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "top"):
        record("dash_top", drive_top)
    if which in ("all", "explain"):
        record("dash_explain", drive_explain)
    if which in ("all", "positions"):
        record("dash_positions", drive_positions)
