import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time, json
from pathlib import Path
from datetime import datetime

print(f"[START] {datetime.now().strftime('%H:%M:%S')}", flush=True)

# Test 1: Can we connect to OpenClaw browser at all?
import urllib.request
CDP_URL = "http://127.0.0.1:18800"
try:
    resp = urllib.request.urlopen(CDP_URL + "/json/version", timeout=3)
    print(f"[CDP] OpenClaw 18800 OK: {resp.read().decode()[:100]}", flush=True)
except Exception as e:
    print(f"[CDP] OpenClaw 18800 failed: {e}", flush=True)

# Test 2: Can Playwright connect?
try:
    from playwright.sync_api import sync_playwright
    print("[PLAYWRIGHT] Trying to connect...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = browser.new_page()
        page.goto("https://www.google.com", timeout=15000)
        print(f"[PLAYWRIGHT] Connected! Title: {page.title()}", flush=True)
        browser.close()
    print("[PLAYWRIGHT] Done!", flush=True)
except Exception as e:
    print(f"[PLAYWRIGHT] Failed: {e}", flush=True)

print(f"[END] {datetime.now().strftime('%H:%M:%S')}", flush=True)
