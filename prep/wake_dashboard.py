"""
Keep the public dashboard awake through judging.

Streamlit Community Cloud puts an app to sleep after roughly 12 hours
without a real browser session, and a plain HTTP GET does not count as one.
A judge who opens the URL and meets "this app has gone to sleep" plus a
60 second boot has already formed an opinion. This script opens the app in
a headless Chromium, presses the wake button if the sleep page is showing,
waits for the real page, and confirms the Merkle badge rendered.

Scheduled every 6 hours as AlpacaHackathon-DashWake (Windows Task
Scheduler). Exit code 0 means the dashboard is up and verified; 1 means it
is not, which the log makes visible the next morning.

    uv run --with playwright python prep/wake_dashboard.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = "https://alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app"
INNER = APP + "/~/+/"          # the iframe that holds the actual app
LOG = Path(__file__).resolve().parent / "wake.log"


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # Outer page first: this is where the sleep prompt lives.
        page.goto(APP, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(6_000)
        button = page.get_by_text("get this app back up", exact=False)
        if button.count():
            button.first.click()
            log("sleep page found, wake button pressed, waiting 75s for boot")
            page.wait_for_timeout(75_000)

        # Inner frame: the only place the app's own text is readable.
        page.goto(INNER, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(20_000)
        text = page.inner_text("body")
        browser.close()

    verified = "MERKLE ROOT VERIFIED" in text
    equity = ""
    if "Equity" in text:
        after = text.split("Equity", 1)[1].strip().splitlines()
        equity = next((s.strip() for s in after if s.strip()), "")
    log(f"{'awake, verified' if verified else 'NOT VERIFIED'} equity={equity!r} "
        f"chars={len(text)}")
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
