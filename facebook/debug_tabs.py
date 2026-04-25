"""Minimal debug script to find why tabs can't be found in full scraper"""
import sys
import time
import json
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

def run():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-data-dir=C:\\Users\\Ivy\\AppData\\Local\\Google\\Chrome\\User Data\\Default')
    options.add_argument('--profile-email=automatictest2024@gmail.com')
    
    driver = uc.Chrome(options=options, version_main=147)
    driver.get('https://www.facebook.com/ads/library/?id=1242102094427110')
    time.sleep(8)
    
    # Click detail button
    try:
        btns = driver.find_elements(By.XPATH, '//span[contains(text(),"查看")] | //span[contains(text(),"Detail")]')
        for btn in btns:
            if btn.is_displayed():
                btn.click()
                break
        time.sleep(5)
    except Exception as e:
        print(f"Button click error: {e}")
        driver.quit()
        return
    
    # Re-find dialog
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    print(f"Dialogs found: {len(dialogs)}")
    if dialogs:
        dialog = dialogs[-1]
        print(f"Dialog tag: {dialog.tag_name}")
        
        # Check dialog innerHTML length
        inner_len = driver.execute_script("return arguments[0].innerHTML.length", dialog)
        print(f"Dialog innerHTML length: {inner_len}")
        
        # Find tabs via Selenium
        tabs = dialog.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        print(f"Selenium tabs in dialog: {len(tabs)}")
        for t in tabs[:5]:
            print(f"  Tab: aria-label='{t.get_attribute('aria-label')}', text='{t.text[:30]}'")
        
        # Find tabs via document-level JS
        all_tabs = driver.execute_script("""
            var tabs = document.querySelectorAll('[role="tab"]');
            var result = [];
            for (var t of tabs) {
                result.push({ariaLabel: t.getAttribute('aria-label'), text: t.textContent.substring(0, 50)});
            }
            return result;
        """)
        print(f"JS tabs via document.querySelectorAll: {len(all_tabs)}")
        for t in all_tabs[:5]:
            print(f"  Tab: aria-label='{t['ariaLabel']}', text='{t['text']}'")
    
    # Check all dialogs
    all_dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    print(f"\nAll dialogs: {len(all_dialogs)}")
    for i, d in enumerate(all_dialogs):
        try:
            al = d.get_attribute('aria-label') or ''
            print(f"  Dialog {i}: aria-label='{al}', displayed={d.is_displayed()}")
        except:
            print(f"  Dialog {i}: stale or error")
    
    driver.quit()

if __name__ == '__main__':
    run()
