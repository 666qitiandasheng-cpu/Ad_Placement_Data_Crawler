import sys, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

import json as _json
input_file = OUTPUT_DIR / "block_blast" / "ads_Block_Blast_2026-04-29.json"
with open(input_file, 'r', encoding='utf-8') as f:
    ads = _json.load(f).get('ads', [])
print(f"[Load] {len(ads)} ads", flush=True)

# ---- Launch Chrome ----
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-blink-features=AutomationControlled')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)
driver.set_page_load_timeout(30)
driver.implicitly_wait(5)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})
print("[Chrome] Ready", flush=True)

detail_file = OUTPUT_DIR / "block_blast" / "detail_fulltext.json"

for i, ad in enumerate(ads, 1):
    lid = ad['library_id']
    print(f"\n[Detail] {i}/{len(ads)}: {lid}", flush=True)
    driver.get(f"https://www.facebook.com/ads/library/?id={lid}")
    print(f"  Title: {driver.title}", flush=True)
    time.sleep(8)

    # Click button
    clicked = False
    for btn_text in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View Ad Details']:
        try:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(),'" + btn_text + "')]")
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click({force:true})", btn)
                    clicked = True
                    print(f"  Clicked: {btn_text}", flush=True)
                    break
        except Exception as e:
            print(f"  Error: {e}", flush=True)
        if clicked:
            break

    time.sleep(3)

    # Wait for modal
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
        )
        print(f"  Modal OK", flush=True)
    except TimeoutException:
        print(f"  No modal!", flush=True)
        continue

    time.sleep(2)

    # Click 4 tabs
    tab_labels = [
        '\u5e7f\u544a\u4fe1\u606f\u516c\u793a\uff08\u6309\u5730\u533a\uff09',
        '\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9',
        '\u5173\u4e8e\u5e7f\u544a\u4e3b',
        '\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9',
    ]
    for tab in tab_labels:
        try:
            els = driver.find_elements(By.XPATH, f".//*[contains(text(),'{tab}')]")
            for el in els:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click({force:true})", el)
                    print(f"  Tab: {tab[:15]}...", flush=True)
                    time.sleep(1)
                    break
        except Exception as e:
            print(f"  Tab err: {e}", flush=True)

    time.sleep(2)

    # Get full text
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    if dialogs:
        full_text = driver.execute_script("return arguments[0].innerText", dialogs[-1])
        print(f"  Text: {len(full_text)} chars", flush=True)

        existing = {}
        if detail_file.exists():
            try:
                existing = _json.load(open(detail_file, 'r', encoding='utf-8'))
            except:
                pass
        existing[lid] = {"library_id": lid, "full_text": full_text}
        with open(detail_file, 'w', encoding='utf-8') as fp:
            _json.dump(existing, fp, ensure_ascii=False, indent=2)
        print(f"  Saved {detail_file.name}", flush=True)

driver.quit()
print("\n[DONE]", flush=True)
