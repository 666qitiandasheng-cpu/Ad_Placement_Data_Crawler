"""Focused debug to understand tab search in full scraper context"""
import sys
import time
import json
import re
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

CHROMEDRIVER_PATH = r'C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe'

def run():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-data-dir=C:\\Users\\Ivy\\AppData\\Local\\Google\\Chrome\\User Data\\Default')
    options.add_argument('--profile-email=automatictest2024@gmail.com')
    
    driver = uc.Chrome(options=options, version_main=147)
    
    # Navigate to list page
    url = 'https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&is_targeted_country=false&media_type=all&q=Block+Blast&search_type=keyword_unordered&sort_data%5Bdirection%5D=desc&sort_data%5Bmode%5D=total_impressions'
    driver.get(url)
    time.sleep(6)
    
    # Find ad link for 1242102094427110
    ad_link = None
    try:
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="1242102094427110"]')
        for l in links:
            if l.is_displayed():
                ad_link = l
                break
    except Exception as e:
        print(f"Link search error: {e}")
    
    if not ad_link:
        print("Could not find ad link")
        driver.quit()
        return
    
    # Click the ad link to open detail modal
    try:
        driver.execute_script("arguments[0].click();", ad_link)
        time.sleep(5)
    except Exception as e:
        print(f"Link click error: {e}")
    
    # Find and expand disclosure section
    dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
    print(f"Dialogs after modal open: {len(dialogs)}")
    if not dialogs:
        print("No dialogs found!")
        driver.quit()
        return
    
    dialog = dialogs[-1]
    print(f"Dialog tag: {dialog.tag_name}")
    
    # Check dialog content length
    content_len = driver.execute_script("return arguments[0].innerText.length", dialog)
    print(f"Dialog text length: {content_len}")
    
    # Search for disclosure header
    disc_texts = ["广告信息公示", "Ad Disclosure"]
    for dt in disc_texts:
        try:
            headers = dialog.find_elements(By.XPATH, f".//*[contains(text(),'{dt}')]")
            print(f"Header '{dt}' found: {len(headers)}")
        except Exception as e:
            print(f"Header search error for '{dt}': {e}")
    
    # Expand all sections (like the full scraper does)
    expanded = 0
    try:
        # Look for section headers
        section_headers = dialog.find_elements(By.XPATH, 
            ".//div[contains(@class,'collapse')] | .//div[contains(@class,'section')] | .//span[contains(text(),'查看')] | .//div[@role='button'][contains(text(),'查看')]")
        print(f"Section headers found: {len(section_headers)}")
        
        # Find the main toggle/section containing disclosure
        all_buttons = dialog.find_elements(By.XPATH, 
            ".//div[@role='button'] | .//span[@role='button'] | .//a[@role='button']")
        print(f"All buttons in dialog: {len(all_buttons)}")
        
        for btn in all_buttons[:10]:
            try:
                txt = btn.text.strip()
                if txt and len(txt) < 50:
                    print(f"  Button text: '{txt[:40]}'")
            except:
                pass
    except Exception as e:
        print(f"Section search error: {e}")
    
    # Now search for tabs via different methods
    print("\n--- Tab search methods ---")
    
    # Method 1: CSS selector in dialog
    try:
        tabs1 = dialog.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        print(f"Method 1 - dialog CSS [role='tab']: {len(tabs1)}")
    except Exception as e:
        print(f"Method 1 error: {e}")
    
    # Method 2: XPath in dialog
    try:
        tabs2 = dialog.find_elements(By.XPATH, ".//*[@role='tab']")
        print(f"Method 2 - dialog XPath @role='tab': {len(tabs2)}")
        for t in tabs2[:3]:
            print(f"  aria-label='{t.get_attribute('aria-label')}' text='{t.text[:30]}'")
    except Exception as e:
        print(f"Method 2 error: {e}")
    
    # Method 3: document.querySelectorAll via JS
    try:
        tabs3 = driver.execute_script("""
            var tabs = document.querySelectorAll('[role="tab"]');
            return Array.from(tabs).map(t => ({ariaLabel: t.getAttribute('aria-label'), text: t.textContent.substring(0, 50)}));
        """)
        print(f"Method 3 - JS document.querySelectorAll: {len(tabs3)}")
        for t in tabs3[:5]:
            print(f"  aria-label='{t['ariaLabel']}' text='{t['text']}'")
    except Exception as e:
        print(f"Method 3 error: {e}")
    
    # Method 4: Search for elements with "tab" in role attribute
    try:
        tabs4 = driver.execute_script("""
            var allWithRole = document.querySelectorAll('[role]');
            var tabs = [];
            for (var el of allWithRole) {
                var r = el.getAttribute('role');
                if (r && r.toLowerCase().includes('tab')) {
                    tabs.push({role: r, ariaLabel: el.getAttribute('aria-label'), text: el.textContent.substring(0, 50)});
                }
            }
            return tabs;
        """)
        print(f"Method 4 - All role values containing 'tab': {len(tabs4)}")
        for t in tabs4[:5]:
            print(f"  role='{t['role']}' aria-label='{t['ariaLabel']}' text='{t['text']}'")
    except Exception as e:
        print(f"Method 4 error: {e}")
    
    driver.quit()
    print("\nDone")

if __name__ == '__main__':
    run()
