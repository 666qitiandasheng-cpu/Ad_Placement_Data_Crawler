"""
Test region tab extraction for ad 1242102094427110
Focused test of the fixed region tab detection using aria-label.
"""
import sys, os, time, json, re
sys.path.insert(0, os.path.dirname(__file__))

from selenium.webdriver.common.by import By

OUTPUT = os.path.join(os.path.dirname(__file__), "test_region_output.txt")

def log(msg):
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

def test_region_tabs(driver, lib_id):
    log(f"\n{'='*60}")
    log(f"TESTING REGION TABS FOR: {lib_id}")
    log(f"{'='*60}")
    
    driver.get("https://www.facebook.com/ads/library/?id=" + lib_id)
    time.sleep(4)
    
    # Click
    for txt in ["查看广告详情", "View Ad Details"]:
        try:
            for b in driver.find_elements(By.XPATH, f"//*[contains(text(),'{txt}')]"):
                if b.is_displayed():
                    b.click()
                    log(f"[OK] Clicked: {txt}")
                    break
        except:
            pass
        time.sleep(1)
    
    time.sleep(4)
    
    # Find dialogs
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    if not dialogs:
        log("[FAIL] No dialogs")
        return
    dialog = max(dialogs, key=lambda d: d.size.get('width', 0) * d.size.get('height', 0))
    log(f"[OK] Dialog: {dialog.size}")
    
    # Expand sections
    for _ in range(3):
        for lbl in ["广告信息公示", "关于广告赞助方", "关于广告主", "广告主和付费方"]:
            try:
                els = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{lbl}')]")
                for el in els:
                    if el.is_displayed():
                        try:
                            el.click()
                        except:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
                            time.sleep(0.3)
                            el.click()
                        time.sleep(0.5)
                        break
            except:
                pass
        time.sleep(1.5)
    
    time.sleep(2)
    
    # Find disclosure header
    disc_header = None
    for lbl in ["广告信息公示", "广告信息公示（按地区）"]:
        try:
            headers = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{lbl}')]")
            for h in headers:
                if h.is_displayed():
                    disc_header = h
                    log(f"[OK] Found header: '{lbl}'")
                    break
        except:
            pass
    
    if not disc_header:
        log("[FAIL] No disclosure header")
        return
    
    region_labels = [
        "欧盟", "英国", "德国", "法国", "意大利", "西班牙",
        "荷兰", "波兰", "瑞典", "奥地利", "比利时",
        "EU", "United Kingdom", "Germany", "France", "Italy",
    ]
    
    region_tabs = []
    
    # Strategy 2: parent + aria-label
    try:
        parent = disc_header.find_element(By.XPATH, "..")
        for rlbl in region_labels:
            # text match
            try:
                els = parent.find_elements(By.XPATH, f".//*[contains(text(),'{rlbl}')]")
                for el in els:
                    if el.is_displayed() and el not in region_tabs:
                        region_tabs.append(el)
            except:
                pass
            # aria-label match
            try:
                aria_els = parent.find_elements(By.XPATH, f".//*[@aria-label='{rlbl}']")
                for el in aria_els:
                    if el.is_displayed() and el not in region_tabs:
                        region_tabs.append(el)
            except:
                pass
    except Exception as e:
        log(f"Strategy 2 error: {e}")
    
    log(f"\n[Strategy 2] region_tabs found: {len(region_tabs)}")
    
    # Strategy 3: role=tablist + role=tab + aria-label search
    try:
        tab_containers = dialog.find_elements(By.CSS_SELECTOR, '[role="tablist"]')
        tab_containers += dialog.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        log(f"[Strategy 3] Found {len(tab_containers)} tab containers")
        
        for tc in tab_containers:
            for rlbl in region_labels:
                try:
                    tab_matches = tc.find_elements(By.XPATH, f".//*[@aria-label='{rlbl}']")
                    for el in tab_matches:
                        if el.is_displayed() and el not in region_tabs:
                            region_tabs.append(el)
                    text_matches = tc.find_elements(By.XPATH, f".//*[contains(text(),'{rlbl}')]")
                    for el in text_matches:
                        if el.is_displayed() and el not in region_tabs:
                            region_tabs.append(el)
                except:
                    pass
        
        all_tabs = dialog.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        log(f"[Strategy 3] Total role=tab elements: {len(all_tabs)}")
        for tab in all_tabs:
            try:
                aria_lbl = tab.get_attribute('aria-label') or ''
                log(f"  tab aria-label: {repr(aria_lbl)}")
                for rlbl in region_labels:
                    if aria_lbl == rlbl or (aria_lbl and aria_lbl.startswith(rlbl + ' ')):
                        log(f"  -> MATCH: '{rlbl}' with aria-label='{aria_lbl}'")
                        if tab.is_displayed() and tab not in region_tabs:
                            region_tabs.append(tab)
            except:
                pass
    except Exception as e:
        log(f"Strategy 3 error: {e}")
    
    # Deduplicate
    seen = set()
    unique = []
    for t in region_tabs:
        try:
            txt = (t.get_attribute('aria-label') or '').strip() or (t.text or '').strip()
            if txt and txt not in seen and len(txt) < 50:
                seen.add(txt)
                unique.append(t)
        except:
            pass
    region_tabs = unique
    
    log(f"\n[FINAL] Unique region tabs: {len(region_tabs)}")
    for t in region_tabs:
        try:
            log(f"  aria-label={repr(t.get_attribute('aria-label'))} text={repr(t.text[:30])}")
        except:
            pass
    
    # If we have tabs, click each and extract data
    if region_tabs:
        log(f"\n[EXTRACTING DATA FROM {len(region_tabs)} REGIONS]")
        for tab in region_tabs:
            try:
                region_name = (tab.get_attribute('aria-label') or '').strip() or (tab.text or '').strip()
                if not region_name or len(region_name) > 40:
                    continue
                
                log(f"\n  Clicking region: '{region_name}'")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
                time.sleep(0.3)
                try:
                    tab.click()
                except:
                    driver.execute_script("arguments[0].click();", tab)
                time.sleep(2)
                
                region_text = driver.execute_script("return arguments[0].innerText", dialog)
                
                # Parse age
                age_val = ''
                age_m = re.search(r"(\d{1,2})\s*[-~]\s*(\d+\+?)\s*\u5c81", region_text)
                if not age_m:
                    age_m = re.search(r"Age\s*:\s*(\d{1,2})\s*[-~]\s*(\d+\+?)", region_text, re.I)
                if age_m:
                    lo, hi = age_m.group(1), age_m.group(2)
                    age_val = f"{lo}-{hi}岁" if hi != "+" else f"{lo}岁+"
                
                # Parse gender
                gender_val = ''
                if re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u4e0d\u9650|Gender\s*:\s*All", region_text, re.I):
                    gender_val = "\u4e0d\u9650"
                elif re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u7537\u6027|Gender\s*:\s*Male", region_text, re.I):
                    gender_val = "\u7537\u6027"
                elif re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u5973\u6027|Gender\s*:\s*Female", region_text, re.I):
                    gender_val = "\u5973\u6027"
                
                # Parse reach
                reach_val = ''
                reach_m = re.search(r"\u8986\u76d6[^\n]{0,50}?([\d,]+)\s*(?:\u4eba|people|users|impressions)", region_text)
                if not reach_m:
                    reach_m = re.search(r"(?:Reach|Impressions)[^:]*:\s*([\d,]+)", region_text, re.I)
                if not reach_m:
                    reach_m = re.search(r"\u8986\u76d6\u4eba\u6570\s*[:\u3001]?\s*([\d,]+)", region_text)
                if reach_m:
                    raw = reach_m.group(1).replace(",", "").replace("\u3000", "").strip()
                    if raw.isdigit() and len(raw) >= 3:
                        reach_val = raw
                
                log(f"  -> age={age_val}, gender={gender_val}, reach={reach_val}")
                log(f"  -> text snippet: {region_text[:200]}")
                
                time.sleep(0.5)
            except Exception as e:
                log(f"  Error: {e}")
    else:
        log("[WARN] No region tabs found!")
        # Try aria-label search on full dialog
        log("\n[FALLBACK: Searching full dialog for aria-label matches]")
        for rlbl in region_labels:
            try:
                all_els = dialog.find_elements(By.XPATH, f".//*[@aria-label='{rlbl}']")
                log(f"  '{rlbl}': {len(all_els)} aria-label matches")
                for el in all_els[:3]:
                    try:
                        log(f"    tag={el.tag_name} display={el.is_displayed()} rect={el.rect}")
                    except:
                        pass
            except:
                pass
    
    log("\n[COMPLETE]")

if __name__ == "__main__":
    import undetected_chromedriver as uc
    
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"Region tab test {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    CHROMEDRIVER = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"
    opts = uc.ChromeOptions()
    for a in ['--disable-gpu','--no-sandbox','--disable-dev-shm-usage',
              '--disable-extensions','--disable-notifications','--disable-popup-blocking',
              '--window-size=1920,1080']:
        opts.add_argument(a)
    opts.add_argument('--headless=new')
    
    driver = uc.Chrome(options=opts, use_subprocess=True, driver_executable_path=CHROMEDRIVER)
    driver.set_page_load_timeout(60)
    
    try:
        test_region_tabs(driver, "1242102094427110")
    finally:
        driver.quit()