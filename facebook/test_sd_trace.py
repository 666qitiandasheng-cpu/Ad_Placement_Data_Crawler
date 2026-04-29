import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Redirect to file immediately
import builtins
original_print = builtins.print

def log(msg):
    original_print(msg, flush=True)
    with open(r"C:\Users\Ivy\.openclaw\workspace\sd_trace.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

builtins.print = log

log("[START] scrape_detail.py")

# Clear trace file
open(r"C:\Users\Ivy\.openclaw\workspace\sd_trace.txt", "w", encoding="utf-8").close()

try:
    import json
    from pathlib import Path
    from datetime import datetime

    BASE_DIR = Path(__file__).parent
    OUTPUT_DIR = BASE_DIR / "output"

    CDP_URLS = [
        "http://127.0.0.1:18800",
        "http://127.0.0.1:9222",
    ]

    import urllib.request

    def detect_cdp_url():
        log("[CDP] Starting detection")
        for url in CDP_URLS:
            try:
                resp = urllib.request.urlopen(url + "/json/version", timeout=3)
                log(f"[CDP] Connected to {url}")
                return url
            except Exception as e:
                log(f"[CDP] {url} failed: {e}")
        log("[CDP] No CDP available")
        return None

    log("[1] Imports done")

    # Find input file
    input_file = OUTPUT_DIR / "block_blast" / "ads_Block_Blast_2026-04-29.json"
    log(f"[2] Input: {input_file}")

    if not input_file.exists():
        log("[ERROR] Input file not found!")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ads = data.get('ads', [])
    log(f"[3] Loaded {len(ads)} ads")

    detail_file = input_file.parent / f"detail_{input_file.stem}.json"
    log(f"[4] Detail file: {detail_file}")

    done_ids = set()
    if detail_file.exists():
        try:
            done = json.load(open(detail_file, 'r', encoding='utf-8'))
            done_ids = set(done.keys())
            log(f"[5] Already scraped: {len(done_ids)}")
        except:
            pass

    to_scrape = [a for a in ads if a['library_id'] not in done_ids]
    log(f"[6] To scrape: {len(to_scrape)}")

    if not to_scrape:
        log("[X] Nothing to scrape")
        sys.exit(0)

    # Detect CDP
    cdp_url = detect_cdp_url()
    use_cdp = (cdp_url is not None)
    log(f"[7] use_cdp={use_cdp}")

    driver = None
    if not use_cdp:
        log("[8] Launching Selenium")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        import time

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
        log("[9] Chrome ready")

    # Scrape loop
    success_count = 0
    for i, ad in enumerate(to_scrape, 1):
        lid = ad['library_id']
        log(f"[SCRAPE] {i}/{len(to_scrape)}: {lid}")

        if use_cdp:
            log("[SELENIUM] CDP mode not implemented in this test")
        else:
            log(f"[SELENIUM] Navigating to {lid}")
            detail_url = "https://www.facebook.com/ads/library/?id=" + lid
            driver.get(detail_url)
            log(f"[SELENIUM] Title: {driver.title}")
            time.sleep(8)

            # Click 查看广告详情
            log("[SELENIUM] Clicking button")
            clicked = False
            for btn_text in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View Ad Details']:
                try:
                    btns = driver.find_elements(By.XPATH, "//*[contains(text(),'" + btn_text + "')]")
                    log(f"  Found {len(btns)} buttons for '{btn_text}'")
                    for btn in btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click({force:true})", btn)
                            clicked = True
                            log("  Clicked!")
                            break
                except Exception as e:
                    log(f"  Error: {e}")
                if clicked:
                    break

            time.sleep(3)

            # Wait for modal
            log("[SELENIUM] Waiting for modal")
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
                )
                log("[SELENIUM] Modal appeared!")
            except TimeoutException:
                log("[SELENIUM] No modal!")
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
                            log(f"[TAB] {tab}")
                            time.sleep(1)
                            break
                except Exception as e:
                    log(f"[TAB] Error: {e}")

            time.sleep(2)

            # Get text
            log("[TEXT] Getting dialog text")
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            log(f"  Found {len(dialogs)} dialogs")
            if dialogs:
                full_text = driver.execute_script("return arguments[0].innerText", dialogs[-1])
                log(f"  Text length: {len(full_text)}")

                # Save
                from pathlib import Path
                detail_file = Path(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_ads_Block_Blast_2026-04-29.json")
                existing = {}
                if detail_file.exists():
                    try:
                        existing = json.load(open(detail_file, 'r', encoding='utf-8'))
                    except:
                        pass
                existing[lid] = {"library_id": lid, "text_length": len(full_text), "text_preview": full_text[:500]}
                with open(detail_file, 'w', encoding='utf-8') as fp:
                    json.dump(existing, fp, ensure_ascii=False, indent=2)
                log(f"[SAVED] {detail_file}")
                success_count += 1
            else:
                log("  No dialogs!")

        log(f"[DONE] {lid} done. Total: {success_count}")

    if driver:
        driver.quit()
    log(f"[FINAL] Success: {success_count}/{len(to_scrape)}")

except Exception as e:
    log(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

log("[END]")