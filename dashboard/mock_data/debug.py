#!/usr/bin/env python3
"""Diagnose JS errors in the demo."""
from pathlib import Path
from playwright.sync_api import sync_playwright

DEMO = Path(__file__).parent.parent.parent / "bild_pauschalreisen_demo.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1560, "height": 1050})
    page = ctx.new_page()
    errors = []
    console = []
    page.on("console", lambda m: console.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"file://{DEMO}", wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(3000)
    print("=== ERRORS ===")
    for e in errors:
        print(e)
    print()
    print("=== CONSOLE ===")
    for c in console[:40]:
        print(c)
    # Try to detect where DASHBOARD_DATA went
    data_top = page.evaluate("typeof DASHBOARD_DATA")
    print("DASHBOARD_DATA typeof:", data_top)
    if data_top == "object":
        keys = page.evaluate("Object.keys(DASHBOARD_DATA).slice(0,10)")
        print("keys:", keys)
    browser.close()
