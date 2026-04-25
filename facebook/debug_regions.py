"""
Debug script: inspect the modal DOM for ad 1242102094427110
to understand the region selector structure. Writes output to debug_output.txt
"""
import sys
import os
import time
import re
import json
sys.path.insert(0, os.path.dirname(__file__))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "debug_output.txt")

def log(msg):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

def debug_ad_detail(driver, library_id, wait_sec=8):
    try:
        detail_url = "https://www.facebook.com/ads/library/?id=" + library_id
        driver.get(detail_url)
        time.sleep(3)
        
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        time.sleep(wait_sec)

        # Click "View ad details"
        btn_clicked = False
        for btn_text in ["\u67e5\u770b\u5e7f\u544a\u8be6\u60c5", "View Ad Details", "view ad details"]:
            try:
                for btn in driver.find_elements(By.XPATH, "//*[contains(text(),'" + btn_text + "')]"):
                    if btn.is_displayed():
                        btn.click()
                        btn_clicked = True
                        log(f"[Modal] Clicked: {btn_text}")
                        break
            except Exception as e:
                pass
            if btn_clicked:
                break

        if not btn_clicked:
            try:
                for btn in driver.find_elements(By.XPATH, "//*[@aria-label='View ad details']"):
                    if btn.is_displayed():
                        btn.click()
                        btn_clicked = True
                        log("[Modal] Clicked via aria-label")
                        break
            except Exception:
                pass

        if not btn_clicked:
            log(f"[Modal] Button not found: {library_id}")
            return

        time.sleep(3)

        # Find modal
        try:
            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, '[role="dialog"]')) >= 3
            )
        except Exception:
            pass
        
        dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
        dialog = dialogs[-1]
        log(f"[Modal] Opened: {library_id}")
        
        # Scroll to bottom
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
        time.sleep(1)

        # Expand sections
        section_labels = [
            "\u5e7f\u544a\u4fe1\u606f\u516c\u793a",
            "\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9",
            "\u5173\u4e8e\u5e7f\u544a\u4e3b",
            "\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9",
            "Ad Disclosure",
            "About the Sponsor",
            "About the Advertiser",
            "Advertiser & Payer",
        ]

        for _ in range(3):
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            dialog = dialogs[-1]
            for label in section_labels:
                try:
                    matching = dialog.find_elements(By.XPATH, ".//*[contains(text(),'" + label + "')]")
                    for el in matching:
                        if el.is_displayed():
                            try:
                                el.click()
                            except Exception:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
                                time.sleep(0.3)
                                try:
                                    el.click()
                                except Exception:
                                    pass
                            time.sleep(0.8)
                            log(f"[Expanded] {label}")
                            break
                except Exception:
                    pass
            time.sleep(1.5)

        # Scroll back up
        driver.execute_script("arguments[0].scrollTop = 0", dialog)
        time.sleep(2)

        # Get full text
        full_text = driver.execute_script("return arguments[0].innerText", dialog)
        log(f"\n[FULL TEXT] ({len(full_text)} chars):\n")
        log(full_text[:5000])

        # Find disclosure header
        disc_header = None
        for lbl in ["\u5e7f\u544a\u4fe1\u606f\u516c\u793a", "Ad Disclosure"]:
            try:
                headers = dialog.find_elements(By.XPATH, ".//*[contains(text(),'" + lbl + "')]")
                for h in headers:
                    if h.is_displayed():
                        disc_header = h
                        break
            except Exception:
                pass

        if disc_header:
            # Get disclosure section parent HTML - go up to find the section container
            for depth in range(1, 6):
                try:
                    parent = disc_header
                    for _ in range(depth):
                        parent = parent.find_element(By.XPATH, "..")
                    disc_html = driver.execute_script("return arguments[0].innerHTML", parent)
                    log(f"\n[DISCLOSURE HTML] depth={depth} ({len(disc_html)} chars):\n")
                    log(disc_html[:3000])
                    break
                except Exception as e:
                    log(f"[depth {depth}] error: {e}")
        
        # JS-based comprehensive search for ALL region-like text in the dialog
        region_names = [
            "\u6b27\u7f9f", "\u6b27\u6d32", "\u82f1\u56fd", "\u5fb7\u56fd",
            "\u6cd5\u56fd", "\u610f\u5927\u5229", "EU", "United Kingdom", "Germany",
        ]
        
        js_script = """
        var dialog = arguments[0];
        var regionNames = arguments[1];
        var results = [];
        var allEls = dialog.querySelectorAll('*');
        for (var el of allEls) {
            var text = (el.textContent || '').trim();
            for (var rn of regionNames) {
                if (text === rn) {
                    var style = window.getComputedStyle(el);
                    var rect = el.getBoundingClientRect();
                    var parentText = (el.parentElement ? el.parentElement.textContent || '' : '').trim().substring(0, 50);
                    if (style.display !== 'none' && rect.width > 0 && rect.height > 0) {
                        results.push({
                            tagName: el.tagName,
                            text: text.substring(0, 30),
                            className: (el.className || '').substring(0, 60),
                            role: el.getAttribute('role') || 'none',
                            ariaLabel: (el.getAttribute('aria-label') || '').substring(0, 60),
                            parentTag: el.parentElement ? el.parentElement.tagName : '',
                            parentClass: (el.parentElement ? el.parentElement.className || '' : '').substring(0, 60),
                            isClickable: !!(el.onclick || el.click || el.href || style.cursor === 'pointer')
                        });
                    }
                }
            }
        }
        return JSON.stringify(results.slice(0, 30));
        """
        js_results = driver.execute_script(js_script, dialog, region_names)
        try:
            parsed = json.loads(js_results)
            log(f"\n[JAVASCRIPT REGION SEARCH] Found {len(parsed)} elements:")
            for r in parsed[:15]:
                log(f"  {json.dumps(r, ensure_ascii=False)}")
        except Exception as e:
            log(f"JS parse error: {e}: {js_results[:500] if js_results else 'empty'}")

        # Also search for elements with EU-related aria-labels
        log("\n[ARIA-LABEL SEARCH for EU-related]")
        eu_aria_script = """
        var dialog = arguments[0];
        var results = [];
        var allEls = dialog.querySelectorAll('[aria-label*="EU"], [aria-label*="eU"], [aria-label*="EU"], [aria-label*="\u6b27"], [aria-label*="\u82f1"], [aria-label*="United"]');
        for (var el of allEls) {
            var style = window.getComputedStyle(el);
            var rect = el.getBoundingClientRect();
            if (style.display !== 'none' && rect.width > 0 && rect.height > 0) {
                results.push({
                    tagName: el.tagName,
                    text: (el.textContent || '').trim().substring(0, 40),
                    ariaLabel: (el.getAttribute('aria-label') || '').substring(0, 80),
                    role: el.getAttribute('role') || 'none',
                    className: (el.className || '').substring(0, 60),
                });
            }
        }
        return JSON.stringify(results.slice(0, 20));
        """
        eu_aria = driver.execute_script(eu_aria_script, dialog)
        try:
            eu_parsed = json.loads(eu_aria)
            log(f"Found {len(eu_parsed)} aria-label matches:")
            for r in eu_parsed[:10]:
                log(f"  {json.dumps(r, ensure_ascii=False)}")
        except Exception as e:
            log(f"EU aria parse error: {e}")

        # Search for any element that has EU as substring
        log("\n[ALL EU CONTAINING TEXT]")
        eu_text_script = """
        var dialog = arguments[0];
        var results = [];
        var allEls = dialog.querySelectorAll('*');
        for (var el of allEls) {
            var text = (el.textContent || '').trim();
            if (text.indexOf('EU') !== -1 || text.indexOf('\\u6b27\\u7f9f') !== -1 || text.indexOf('\\u82f1\\u56fd') !== -1) {
                var style = window.getComputedStyle(el);
                var rect = el.getBoundingClientRect();
                if (style.display !== 'none' && rect.width > 0 && rect.height > 0 && text.length < 100) {
                    results.push({
                        tagName: el.tagName,
                        text: text.substring(0, 60),
                        className: (el.className || '').substring(0, 60),
                        role: el.getAttribute('role') || 'none',
                        isClickable: !!(el.onclick || el.click || el.href || style.cursor === 'pointer')
                    });
                }
            }
        }
        return JSON.stringify(results.slice(0, 20));
        """
        eu_text = driver.execute_script(eu_text_script, dialog)
        try:
            eu_parsed = json.loads(eu_text)
            log(f"Found {len(eu_parsed)} EU text matches:")
            for r in eu_parsed[:10]:
                log(f"  {json.dumps(r, ensure_ascii=False)}")
        except Exception as e:
            log(f"EU text parse error: {e}")

        log("\n[DEBUG COMPLETE]")

    except Exception as e:
        import traceback
        log(f"Error: {e}")
        traceback.print_exc()
        log(traceback.format_exc())


if __name__ == "__main__":
    import undetected_chromedriver as uc
    
    CHROMEDRIVER_PATH = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"
    
    # Clear output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Debug output for ad 1242102094427110\n\n")
    
    options = uc.ChromeOptions()
    for arg in [
        '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
        '--disable-extensions', '--disable-notifications',
        '--disable-popup-blocking', '--window-size=1920,1080',
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    ]:
        options.add_argument(arg)
    options.add_argument('--headless=new')
    
    log("[Browser] Starting Chrome...")
    driver = uc.Chrome(options=options, use_subprocess=True,
                       driver_executable_path=CHROMEDRIVER_PATH)
    driver.set_page_load_timeout(60)
    
    try:
        debug_ad_detail(driver, "1242102094427110", wait_sec=10)
    finally:
        driver.quit()
        log("[Done]")
