import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("[START] Testing CDP modal text extraction", flush=True)

try:
    import json
    from pathlib import Path
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    import time

    # Load ads
    input_file = Path(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\ads_Block_Blast_2026-04-29.json")
    with open(input_file, 'r', encoding='utf-8') as f:
        ads = json.load(f).get('ads', [])
    print(f"[LOAD] {len(ads)} ads", flush=True)

    # Launch Chrome
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
    print("[CHROME] Launched", flush=True)

    lid = ads[0]['library_id']
    driver.get(f"https://www.facebook.com/ads/library/?id={lid}")
    print(f"[PAGE] Title: {driver.title}", flush=True)
    time.sleep(8)

    # Click 查看广告详情
    print("[CLICK] Looking for button", flush=True)
    btns = driver.find_elements(By.XPATH, "//*[contains(text(),'查看广告详情')]")
    print(f"  Found {len(btns)} buttons", flush=True)
    for btn in btns:
        if btn.is_displayed():
            driver.execute_script("arguments[0].click({force:true})", btn)
            print("  Clicked!", flush=True)
            break
    time.sleep(3)

    # Wait for modal
    print("[MODAL] Waiting...", flush=True)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
        )
        print("[MODAL] Modal appeared!", flush=True)
    except TimeoutException:
        print("[MODAL] No modal!", flush=True)
        driver.quit()
        sys.exit(1)

    # Click 4 tabs
    tab_labels = ['广告信息公示（按地区）', '关于广告赞助方', '关于广告主', '广告主和付费方']
    for tab in tab_labels:
        try:
            els = driver.find_elements(By.XPATH, f".//*[contains(text(),'{tab}')]")
            for el in els:
                if el.is_displayed():
                    driver.execute_script("arguments[0].click({force:true})", el)
                    print(f"[TAB] Clicked: {tab}", flush=True)
                    time.sleep(1)
                    break
        except Exception as e:
            print(f"[TAB] Error clicking {tab}: {e}", flush=True)

    time.sleep(2)

    # Get dialog text - THE CRITICAL STEP
    print("[TEXT] Getting dialog text...", flush=True)
    import time as t
    start = t.time()
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    print(f"  Found {len(dialogs)} dialogs", flush=True)
    if dialogs:
        full_text = driver.execute_script("return arguments[0].innerText", dialogs[-1])
        elapsed = t.time() - start
        print(f"  innerText length: {len(full_text)} in {elapsed:.1f}s", flush=True)
        print(f"  First 200 chars: {full_text[:200]}", flush=True)
    else:
        print("  No dialogs found!", flush=True)

    driver.quit()
    print("[DONE]", flush=True)

except Exception as e:
    print(f"[ERROR] {e}", flush=True)
    import traceback
    traceback.print_exc()