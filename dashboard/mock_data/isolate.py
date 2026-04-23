#!/usr/bin/env python3
"""Isolate the JS parse error by extracting <script> blocks and testing them."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

DEMO = Path(__file__).parent.parent.parent / "bild_pauschalreisen_demo.html"
html = DEMO.read_text()

# Extract all <script>...</script> bodies (not src= ones)
scripts = re.findall(r'<script>([\s\S]*?)</script>', html)
print(f'Found {len(scripts)} inline scripts')
for i, s in enumerate(scripts):
    print(f'  [{i}] {len(s):,} chars (first line: {s.strip().splitlines()[0][:80] if s.strip() else "empty"})')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # Test each script in isolation in a minimal HTML
    for i, s in enumerate(scripts):
        errors.clear()
        wrapped = f"""<!DOCTYPE html><html><body><script>{s}</script></body></html>"""
        tmp = DEMO.parent / f"_tmp_script_{i}.html"
        tmp.write_text(wrapped)
        try:
            page.goto(f"file://{tmp}", wait_until="domcontentloaded", timeout=10_000)
            page.wait_for_timeout(200)
            if errors:
                print(f'[{i}] ERRORS: {errors}')
            else:
                print(f'[{i}] OK')
        except Exception as e:
            print(f'[{i}] goto failed: {e}')
        tmp.unlink()
    browser.close()
