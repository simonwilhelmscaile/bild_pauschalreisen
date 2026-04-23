#!/usr/bin/env python3
"""Screenshot the demo dashboard for visual QA."""
from pathlib import Path
from playwright.sync_api import sync_playwright

DEMO = Path(__file__).parent.parent.parent / "bild_pauschalreisen_demo.html"
OUT_DIR = Path(__file__).parent.parent.parent / "previews"
OUT_DIR.mkdir(exist_ok=True)

TABS = ["overview", "journey", "insights", "competitors", "alerts", "media",
        "content", "qa", "news", "seo", "kundendienst"]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1560, "height": 1050}, device_scale_factor=2)
        page = ctx.new_page()
        url = f"file://{DEMO}"
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: console_msgs.append(f"[ERROR] {e}"))
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT_DIR / "00_overview.png"), full_page=True)
        print("wrote", OUT_DIR / "00_overview.png")
        for i, tab in enumerate(TABS, start=1):
            try:
                page.evaluate(f"typeof activateSidebarTab === 'function' && activateSidebarTab('{tab}')")
                page.wait_for_timeout(1500)
                page.screenshot(path=str(OUT_DIR / f"{i:02d}_{tab}.png"), full_page=True)
                print("wrote", tab)
            except Exception as e:
                print(f"[fail] {tab}: {e}")
        for msg in console_msgs[:25]:
            print(msg)
        browser.close()


if __name__ == "__main__":
    main()
