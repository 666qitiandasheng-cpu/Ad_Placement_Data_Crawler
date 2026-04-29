import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("[1] Starting script", flush=True)
sys.stdout.flush()

try:
    import json, time, re
    from pathlib import Path
    from datetime import datetime

    print("[2] Imports done", flush=True)

    BASE_DIR = Path(__file__).parent
    OUTPUT_DIR = BASE_DIR / "output"

    # Load ads
    input_file = BASE_DIR / "output" / "block_blast" / "ads_Block_Blast_2026-04-29.json"
    print(f"[3] Input: {input_file}", flush=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ads = data.get('ads', [])
    print(f"[4] Loaded {len(ads)} ads", flush=True)

    if not ads:
        print("[X] No ads")
        sys.exit(0)

    # Setup Selenium
    print("[5] Setting up Selenium", flush=True)
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException
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
    print("[6] Chrome launched", flush=True)

    lid = ads[0]['library_id']
    detail_url = "https://www.facebook.com/ads/library/?id=" + lid
    print(f"[7] Navigating to {detail_url}", flush=True)
    driver.get(detail_url)
    print(f"[8] Page title: {driver.title}", flush=True)
    time.sleep(5)

    # Click "查看广告详情"
    print("[9] Looking for '查看广告详情' button", flush=True)
    clicked = False
    for btn_text in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View Ad Details']:
        try:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(),'" + btn_text + "')]")
            print(f"   Found {len(btns)} buttons for '{btn_text}'", flush=True)
            for btn in btns:
                if btn.is_displayed():
                    print(f"   Clicking button: {btn_text}", flush=True)
                    driver.execute_script("arguments[0].click({force:true})", btn)
                    clicked = True
                    break
        except Exception as e:
            print(f"   Error finding button: {e}", flush=True)
        if clicked:
            break

    if not clicked:
        print("[10] No button found!", flush=True)
    else:
        print("[10] Button clicked", flush=True)
        time.sleep(3)

        # Wait for modal
        print("[11] Waiting for modal dialog", flush=True)
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
            )
            print("[12] Modal appeared", flush=True)
        except TimeoutException:
            print("[12] No modal appeared", flush=True)

    driver.quit()
    print("[DONE] Test complete", flush=True)

except Exception as e:
    print(f"[ERROR] {e}", flush=True)
    import traceback
    traceback.print_exc()