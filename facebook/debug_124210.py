"""
Debug ad 1242102094427110 specifically - focus on understanding
the region selector UI in the disclosure section.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

OUTPUT = os.path.join(os.path.dirname(__file__), "region_debug.txt")

def log(msg):
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

def debug_specific_ad(driver, lib_id):
    log(f"\n{'='*60}")
    log(f"DEBUGGING AD: {lib_id}")
    log(f"{'='*60}")
    
    driver.get("https://www.facebook.com/ads/library/?id=" + lib_id)
    time.sleep(4)
    
    # Click "查看广告详情"
    clicked = False
    for txt in ["查看广告详情", "View Ad Details"]:
        try:
            btns = driver.find_elements(By.XPATH, f"//*[contains(text(),'{txt}')]")
            for b in btns:
                if b.is_displayed():
                    b.click()
                    clicked = True
                    log(f"[OK] Clicked: {txt}")
                    break
        except:
            pass
        if clicked:
            break
    
    if not clicked:
        log("[FAIL] Could not click View Details")
        return
    
    time.sleep(4)
    
    # Find dialog
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    if not dialogs:
        log("[FAIL] No dialog found")
        return
    
    # Find the largest dialog (main modal)
    dialog = max(dialogs, key=lambda d: d.size.get('width', 0) * d.size.get('height', 0))
    log(f"[OK] Dialog found: {dialog.size}")
    
    # Expand all sections by scrolling through the dialog
    section_labels = [
        "广告信息公示", "关于广告赞助方", "关于广告主",
        "广告主和付费方",
    ]
    
    for _ in range(4):
        for lbl in section_labels:
            try:
                els = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{lbl}')]")
                for el in els:
                    if el.is_displayed():
                        try:
                            el.click()
                            log(f"[OK] Clicked section: {lbl}")
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
    
    # Now look for the disclosure section specifically
    disc_header = None
    for lbl in ["广告信息公示", "Ad Disclosure"]:
        try:
            headers = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{lbl}')]")
            for h in headers:
                if h.is_displayed():
                    disc_header = h
                    log(f"[OK] Found disclosure header: {lbl}")
                    break
        except:
            pass
    
    if not disc_header:
        log("[WARN] No disclosure header found")
        return
    
    # Walk up to find the container
    container = disc_header
    for _ in range(6):
        try:
            container = container.find_element(By.XPATH, "..")
        except:
            break
    
    # Print tag/path info
    log(f"\n[DISCLOSURE CONTAINER] tag={container.tag_name}")
    
    # Get all clickable elements inside container
    all_els = container.find_elements(By.XPATH, ".//*")
    log(f"[CONTAINER] Total children: {len(all_els)}")
    
    # Find elements that are likely tab-like
    for el in all_els:
        try:
            if not el.is_displayed():
                continue
            text = (el.text or '').strip()
            role = el.get_attribute('role') or ''
            tag = el.tag_name
            cls = (el.get_attribute('class') or '').split()[0][:40]
            
            # Only log interesting elements
            if text and len(text) < 30:
                log(f"  [{tag}] role={role} class={cls} text={repr(text[:30])}")
        except:
            pass
    
    # Now search for elements matching "欧盟" and "英国" EXACTLY
    log(f"\n[EXACT SEARCH for region tabs]")
    for region in ["欧盟", "英国"]:
        log(f"\n--- Searching for '{region}' ---")
        # Try aria-label
        aria_matches = dialog.find_elements(By.XPATH, f".//*[@aria-label='{region}']")
        log(f"  aria-label exact matches: {len(aria_matches)}")
        
        # Try text content exactly
        text_matches = dialog.find_elements(By.XPATH, f".//*[text()='{region}']")
        log(f"  text() exact matches: {len(text_matches)}")
        for m in text_matches[:5]:
            try:
                log(f"    -> tag={m.tag_name} class={m.get_attribute('class').split()[0][:50] if m.get_attribute('class') else 'none'} display={m.is_displayed()} rect={m.rect}")
            except:
                pass
        
        # Try contains
        contains_matches = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{region}')]")
        log(f"  contains matches: {len(contains_matches)}")
        for m in contains_matches[:5]:
            try:
                log(f"    -> tag={m.tag_name} class={m.get_attribute('class').split()[0][:50] if m.get_attribute('class') else 'none'} display={m.is_displayed()}")
            except:
                pass
    
    # Look specifically inside the disclosure container
    log(f"\n[SEARCH INSIDE DISCLOSURE CONTAINER]")
    try:
        # Get inner HTML of the container up to 5000 chars
        container_html = driver.execute_script("return arguments[0].innerHTML", container)
        log(f"Container HTML length: {len(container_html)}")
        # Print section around "欧盟" if present
        if "欧盟" in container_html:
            idx = container_html.index("欧盟")
            log(f"Found '欧盟' at index {idx}")
            log("Context: " + repr(container_html[max(0,idx-100):idx+200]))
        elif "EU" in container_html:
            idx = container_html.index("EU")
            log(f"Found 'EU' at index {idx}")
            log("Context: " + repr(container_html[max(0,idx-100):idx+200]))
        else:
            log("'欧盟' NOT FOUND in container HTML")
            log("First 2000 chars: " + repr(container_html[:2000]))
    except Exception as e:
        log(f"Error getting container HTML: {e}")
    
    # Also check for iframes
    log(f"\n[IFRAME CHECK]")
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    log(f"Total iframes: {len(iframes)}")
    for iframe in iframes[:3]:
        try:
            log(f"  iframe: {iframe.get_attribute('src') or iframe.get_attribute('name') or 'unknown'}")
        except:
            pass

    log(f"\n[DEBUG COMPLETE]")

if __name__ == "__main__":
    import undetected_chromedriver as uc
    
    CHROMEDRIVER = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"
    
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"Region debug {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    opts = uc.ChromeOptions()
    for a in ['--disable-gpu','--no-sandbox','--disable-dev-shm-usage',
              '--disable-extensions','--disable-notifications','--disable-popup-blocking',
              '--window-size=1920,1080']:
        opts.add_argument(a)
    opts.add_argument('--headless=new')
    
    driver = uc.Chrome(options=opts, use_subprocess=True, driver_executable_path=CHROMEDRIVER)
    driver.set_page_load_timeout(60)
    
    try:
        debug_specific_ad(driver, "1242102094427110")
    finally:
        driver.quit()