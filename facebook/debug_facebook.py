"""Debug: Inspect the actual tabs and targeting data on Facebook page for ad 1242102094427110"""
import sys
import time
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

OUT = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_out.txt'

def log(msg):
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

def run():
    for f in [OUT]:
        open(f, 'w').close()
    
    log('=== Test Start ===')
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-data-dir=C:\\Users\\Ivy\\AppData\\Local\\Google\\Chrome\\User Data\\Default')
    options.add_argument('--profile-email=automatictest2024@gmail.com')
    
    log('Starting Chrome...')
    driver = uc.Chrome(options=options, version_main=147)
    log('Chrome started')
    
    driver.set_page_load_timeout(15)
    driver.get('https://www.facebook.com/ads/library/?id=1242102094427110')
    log('Page loaded')
    time.sleep(8)
    
    # Click detail button
    try:
        btns = driver.find_elements(By.XPATH, '//span[contains(text(),"查看")]')
        log(f'Found {len(btns)} detail buttons')
        for btn in btns:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    log(f'Clicked: {btn.text[:40]}')
                    break
            except Exception as e:
                log(f'Btn click error: {e}')
        time.sleep(5)
    except Exception as e:
        log(f'Button search error: {e}')
    
    # Step 1: Count ALL role=tab elements on the page
    all_tabs = driver.execute_script("""
        var tabs = document.querySelectorAll('[role="tab"]');
        return 'Total role=tab: ' + tabs.length + ', details: ' + 
            JSON.stringify(Array.from(tabs).slice(0,20).map(t => ({
            al: t.getAttribute('aria-label'),
            text: t.textContent.trim().substring(0,30),
            role: t.getAttribute('role'),
            displayed: t.offsetWidth > 0 && t.offsetHeight > 0
        })));
    """)
    log(f'All tabs: {all_tabs}')
    
    # Step 2: Check all elements with role containing 'tab'
    role_elements = driver.execute_script("""
        var all = document.querySelectorAll('[role]');
        var tabs = [];
        for (var el of all) {
            var r = (el.getAttribute('role') || '').toLowerCase();
            if (r.includes('tab')) {
                tabs.push({
                    role: el.getAttribute('role'),
                    al: el.getAttribute('aria-label'),
                    text: el.textContent.trim().substring(0, 30)
                });
            }
        }
        return JSON.stringify(tabs);
    """)
    log(f'Elements with role containing tab: {role_elements}')
    
    # Step 3: Look specifically for the region tab list - tablist container
    tablist = driver.execute_script("""
        var tl = document.querySelectorAll('[role="tablist"], [role="menubar"], [role="navigation"]');
        var result = [];
        for (var t of tl) {
            result.push({
                role: t.getAttribute('role'),
                al: t.getAttribute('aria-label'),
                childRoles: JSON.stringify(Array.from(t.querySelectorAll('[role]')).slice(0,10).map(c => c.getAttribute('role'))),
                childAls: JSON.stringify(Array.from(t.querySelectorAll('[aria-label]')).slice(0,10).map(c => c.getAttribute('aria-label')))
            });
        }
        return JSON.stringify(result);
    """)
    log(f'Tablist/nav elements: {tablist}')
    
    # Step 4: Try to find EU/UK tabs by exact aria-label
    euuk_check = driver.execute_script("""
        var RA = ["\u6b27\u7f9f","\u82f1\u56fd","\u5fb7\u56fd","\u6cd5\u56fd","\u5965\u5730\u5229","\u6bd4\u5229\u65f6","\u610f\u5927\u5229","EU","United Kingdom"];
        var found = {};
        // Search by aria-label on ALL elements
        var allEls = document.querySelectorAll('[aria-label]');
        for (var el of allEls) {
            var al = (el.getAttribute('aria-label') || '').trim();
            for (var rn of RA) {
                if (al === rn) {
                    if (!found[al]) {
                        found[al] = {
                            tag: el.tagName,
                            role: el.getAttribute('role'),
                            text: el.textContent.trim().substring(0, 30),
                            visible: el.offsetWidth > 0
                        };
                    }
                }
            }
        }
        return JSON.stringify(found);
    """)
    log(f'EU/UK by aria-label search: {euuk_check}')
    
    # Step 5: Click each found tab and check body text
    for rn in ['\u6b27\u7f9f', '\u82f1\u56fd']:
        clicked = driver.execute_script("""
            var rn = arguments[0];
            var tabs = document.querySelectorAll('[role="tab"]');
            for (var t of tabs) {
                if (t.getAttribute('aria-label') === rn) {
                    t.scrollIntoView({block: 'center'});
                    t.click();
                    return 'clicked:' + t.textContent.trim().substring(0, 20);
                }
            }
            return 'not_found';
        """, rn)
        log(f'Click {rn}: {clicked}')
        time.sleep(2)
        
        # Get body text snippet around targeting info
        snippet = driver.execute_script("""
            var text = document.body.innerText;
            var idx = text.indexOf('\u8986\u76d6');
            if (idx >= 0) {
                return text.substring(idx, idx + 100);
            }
            idx = text.indexOf('Age');
            if (idx >= 0) {
                return text.substring(idx, idx + 100);
            }
            return 'NO_TARGETING_FOUND in body text';
        """)
        log(f'  After click snippet: {snippet}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
