"""Capture the screen assets for the video with Playwright.

Run on its own (`uv run --with playwright --with pymupdf presentation/video/capture.py`)
or via `build.py --capture`. Writes PNGs into presentation/video/assets/, named by beat,
and renders slide 5 of presentation/slides_draft.pdf at 1920x1080.
Read-only against the world: it opens public pages and takes screenshots.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
DASH = "https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app/~/+/"
REPO = "https://github.com/nilaymastaadmi/alpaca-hackathon"
PREREG = REPO + "/blob/main/research/PREREGISTRATION_R1.md"
DEV_ACCOUNT = "PA308NOY3X36"
W, H = 1920, 1080


def wake_streamlit(page) -> None:
    """Click the sleep-page button if present, then wait for the app to render."""
    page.goto(DASH, wait_until="domcontentloaded", timeout=120_000)
    for _ in range(3):
        btn = page.get_by_text("Yes, get this app back up!", exact=False)
        if btn.count():
            print("dashboard asleep, waking it and waiting 60 s")
            btn.first.click()
            time.sleep(60)
            page.goto(DASH, wait_until="domcontentloaded", timeout=120_000)
        else:
            break
    page.wait_for_selector("text=What the agent decided", timeout=180_000)
    time.sleep(6)  # let the metrics and charts finish drawing


def capture_dashboard(ctx) -> None:
    page = ctx.new_page()
    wake_streamlit(page)
    text = page.inner_text("body")
    if DEV_ACCOUNT in text:
        sys.exit("ABORT: dev account string visible on the dashboard")
    # Beat 1: top of the dashboard, headline sentence in view.
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)
    page.screenshot(path=str(ASSETS / "b01_dashboard.png"), full_page=False)
    # Beat 8: the open positions section.
    heading = page.get_by_text(re.compile(r"^Open positions \(\d+\)")).first
    heading.scroll_into_view_if_needed()
    page.evaluate("document.querySelector('[data-testid=\"stAppViewContainer\"] section, .stMain, section.main')?.scrollBy(0, -60)")
    time.sleep(1)
    page.screenshot(path=str(ASSETS / "b08_positions.png"), full_page=False)
    # The headline sentence itself, for the facts check.
    line = page.get_by_text("real decision opportunities", exact=False).first.inner_text()
    (ASSETS / "b01_headline.txt").write_text(line, encoding="utf-8")
    print("dashboard headline:", line[:160])
    page.close()


def capture_github(browser) -> None:
    # 1280x720 at 1.5x gives a 1920x1080 PNG with text large enough to read at video size.
    ctx = browser.new_context(viewport={"width": 1280, "height": 720},
                              device_scale_factor=1.5, color_scheme="dark")
    page = ctx.new_page()
    shots = (
        (REPO, "b09_readme.png", "article.markdown-body h1"),
        (PREREG, "b02_prereg.png", None),  # top of the file view: header, title, "Committed 2026-08-19" line
    )
    for url, name, anchor in shots:
        if page.url != url:
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_selector("article.markdown-body", timeout=120_000)
            time.sleep(3)
        if anchor:
            # GitHub restores scroll position asynchronously after load, which can undo a
            # single scrollIntoView. Compute the absolute Y and scroll to it until it sticks.
            for _ in range(5):
                y = page.evaluate(f"document.querySelector('{anchor}').getBoundingClientRect().top + window.scrollY")
                page.evaluate(f"window.scrollTo(0, {max(0, y - 72)})")
                time.sleep(0.8)
                if abs(page.evaluate("window.scrollY") - max(0, y - 72)) < 4:
                    break
        else:
            page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        print(name, "scrollY", page.evaluate("window.scrollY"))
        if DEV_ACCOUNT in page.inner_text("body"):
            sys.exit(f"ABORT: dev account string visible on {url}")
        page.screenshot(path=str(ASSETS / name), full_page=False)
    ctx.close()


def render_slide(page_number: int = 5) -> None:
    """Slide 5 (the H1 numbers) is current and used full frame; 960x540 pt at 2x = 1920x1080."""
    import pymupdf

    doc = pymupdf.open(str(HERE.parent / "slides_draft.pdf"))
    pix = doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    pix.save(str(ASSETS / f"slide{page_number:02d}.png"))


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "slides"):
        render_slide(5)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
            color_scheme="dark",
        )
        if which in ("all", "dashboard"):
            capture_dashboard(ctx)
        if which in ("all", "github"):
            capture_github(browser)
        browser.close()
    for f in sorted(ASSETS.glob("*.png")):
        print("wrote", f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
