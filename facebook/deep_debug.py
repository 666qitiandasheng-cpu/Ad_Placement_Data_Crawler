"""
Deep debug for ad 1242102094427110 - inspect the full modal HTML
to understand the region selector structure.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

OUTPUT = os.path.join(os.path.dirname(__file__), "deep_debug.txt")

def log(msg):
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

def debug_deep(driver, lib_id):
    log(f"\n{'='*60}")
    log(f"DEEP DEBUG: {lib_id}")
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
    
    # Find all dialogs
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    if not dialogs:
        log("[FAIL] No dialogs")
        return
    
    dialog = max(dialogs, key=lambda d: d.size.get('width', 0) * d.size.get('height', 0))
    log(f"[OK] Dialog size: {dialog.size}")
    
    # Click all section headers to expand them
    section_labels = ["广告信息公示", "关于广告赞助方", "关于广告主", "广告主和付费方"]
    for _ in range(3):
        for lbl in section_labels:
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
        time.sleep(1)
    
    time.sleep(2)
    
    # Get the HTML of the entire dialog
    log("\n[DIALOG FULL HTML]")
    full_html = driver.execute_script("return arguments[0].innerHTML", dialog)
    log(f"Total HTML length: {len(full_html)}")
    
    # Search for "欧盟" in HTML
    if "欧盟" in full_html:
        idx = full_html.index("欧盟")
        log(f"\n[Found '欧盟' at index {idx}]")
        log("Context around '欧盟':")
        log(repr(full_html[max(0,idx-300):idx+400]))
    else:
        log("\n[WARNING] '欧盟' NOT found in dialog HTML")
        # Check for other region-related text
        for kw in ["EU", "英国", "德国", "法国", "欧元", "region"]:
            if kw in full_html:
                log(f"Found '{kw}' at index {full_html.index(kw)}")
    
    # Check if there's a nested content area
    log("\n[LOOKING FOR EXPANDABLE CONTENT]")
    expandables = dialog.find_elements(
        By.XPATH,
        ".//*[contains(@class,'collapse') or contains(@class,'expand') "
        "or contains(@aria-expanded,'true') or contains(@aria-expanded,'false')]"
    )
    log(f"Expandable elements: {len(expandables)}")
    for e in expandables[:10]:
        try:
            log(f"  tag={e.tag_name} class={e.get_attribute('class')[:60]} aria-expanded={e.get_attribute('aria-expanded')} text={e.text[:40]}")
        except:
            pass
    
    # Try clicking the disclosure section header and waiting for content to load
    log("\n[TRYING TO CLICK DISCLOSURE HEADER DIRECTLY]")
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
    
    if disc_header:
        # Get the parent container
        container = disc_header
        for _ in range(8):
            try:
                container = container.find_element(By.XPATH, "..")
            except:
                break
        
        log(f"[Container] tag={container.tag_name} size={container.rect}")
        
        # Check what's immediately after the header in the DOM
        try:
            following = container.find_elements(By.XPATH, "./following-sibling::*")
            log(f"[Following siblings]: {len(following)}")
            for f in following[:3]:
                log(f"  tag={f.tag_name} class={f.get_attribute('class')[:50] if f.get_attribute('class') else ''}")
        except Exception as e:
            log(f"Following siblings error: {e}")
        
        # Get inner HTML of the container at depth 3 up
        for depth in [1, 2, 3, 4]:
            try:
                el = disc_header
                for _ in range(depth):
                    el = el.find_element(By.XPATH, "..")
                html = driver.execute_script("return arguments[0].innerHTML", el)
                log(f"\n[DEPTH {depth}] ({len(html)} chars):")
                log(repr(html[:1500]))
            except Exception as e:
                log(f"depth {depth} error: {e}")
    
    # Use JS to find ALL elements in the dialog that have "欧盟" in their text
    log("\n[JAVASCRIPT DEEP SEARCH FOR '欧盟']")
    js_script = """
    var dialog = arguments[0];
    var target = "欧盟";
    var results = [];
    // Check every element
    var all = dialog.querySelectorAll('*');
    for (var el of all) {
        if (el.textContent && el.textContent.includes(target)) {
            var style = window.getComputedStyle(el);
            if (style.display !== 'none') {
                results.push({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 100),
                    class: (el.className || '').substring(0, 60),
                    id: el.id || '',
                    role: el.getAttribute('role') || '',
                    rect: JSON.stringify(el.getBoundingClientRect())
                });
            }
        }
    }
    return JSON.stringify(results.slice(0, 20));
    """
    js_result = driver.execute_script(js_script, dialog)
    try:
        parsed = json.loads(js_result)
        log(f"Found {len(parsed)} elements with '欧盟':")
        for r in parsed[:10]:
            log(f"  {r}")
    except Exception as e:
        log(f"JS error: {e} -> {js_result[:200]}")
    
    # Also try to find any element where the text is exactly "欧盟" or "英国"
    log("\n[EXACT TEXT SEARCH]")
    for region in ["欧盟", "英国", "EU"]:
        js_exact = f"""
        var dialog = arguments[0];
        var target = "{region}";
        var results = [];
        var all = dialog.querySelectorAll('*');
        for (var el of all) {{
            var txt = (el.textContent || '').trim();
            if (txt === target) {{
                var style = window.getComputedStyle(el);
                var rect = el.getBoundingClientRect();
                results.push({{
                    tag: el.tagName,
                    text: txt,
                    class: (el.className || '').substring(0, 60),
                    role: el.getAttribute('role') || '',
                    visible: style.display !== 'none' && rect.width > 0 && rect.height > 0,
                    rect: JSON.stringify(rect)
                }});
            }}
        }}
        return JSON.stringify(results);
        """
        r = driver.execute_script(js_exact, dialog)
        try:
            p = json.loads(r)
            log(f"Exact '{region}': {len(p)} found")
            for item in p[:5]:
                log(f"  {item}")
        except Exception as e:
            log(f"Error for '{region}': {e}")
    
    log("\n[COMPLETE]")

if __name__ == "__main__":
    import undetected_chromedriver as uc
    
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"Deep debug {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
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
        debug_deep(driver, "1242102094427110")
    finally:
        driver.quit()