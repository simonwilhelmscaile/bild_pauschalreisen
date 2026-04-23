#!/usr/bin/env python3
"""Bisect the big script to find the exact line that breaks."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

DEMO = Path(__file__).parent.parent.parent / "bild_pauschalreisen_demo.html"
html = DEMO.read_text()

# Extract the script body
m = re.search(r'<script>([\s\S]*?)</script>', html)
script = m.group(1)
lines = script.splitlines()
print(f'{len(lines):,} lines')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    def test(up_to_line):
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        partial = "\n".join(lines[:up_to_line])
        wrapped = f"""<!DOCTYPE html><html><body><script>{partial}</script></body></html>"""
        tmp = DEMO.parent / "_tmp_bisect.html"
        tmp.write_text(wrapped)
        try:
            page.goto(f"file://{tmp}", wait_until="domcontentloaded", timeout=10_000)
            page.wait_for_timeout(150)
        finally:
            tmp.unlink(missing_ok=True)
        return errors

    # Binary search
    lo, hi = 0, len(lines)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        errors = test(mid)
        print(f"  test 0..{mid}: {'OK' if not errors else errors[0][:80]}")
        if errors and 'missing' in errors[0]:
            hi = mid
        else:
            lo = mid
    print(f'Breaking line: {hi}')
    print(f'Context:')
    for i in range(max(0, hi - 3), min(len(lines), hi + 2)):
        print(f'  {i+1}: {lines[i][:200]}')
    browser.close()
