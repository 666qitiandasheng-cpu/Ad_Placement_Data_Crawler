"""Debug: Inspect actual DOM structure of the disclosure section for ad 1242102094427110"""
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
    
    driver = uc.Chrome(options=options, version_main=147)
    log('Chrome started')
    
    driver.set_page_load_timeout(15)
    driver.get('https://www.facebook.com/ads/library/?id=1242102094427110')
    log('Page loaded')
    time.sleep(8)
    
    # Get the page source to understand structure
    page_source_len = driver.execute_script("return document.body.innerHTML.length")
    log(f'Page source length: {page_source_len}')
    
    # Find ALL clickable elements that might be the detail button
    all_buttons = driver.execute_script('''
        var buttons = document.querySelectorAll("div[role='button'], span[role='button'], a[role='button'], [clickable], div[tabindex='0']");
        var result = [];
        for (var b of buttons) {
            var text = (b.textContent || '').trim();
            if (text.length > 0 && text.length < 100 && text.includes('\u67e5\u770b')) {
                result.push({
                    text: text.substring(0, 50),
                    tag: b.tagName,
                    role: b.getAttribute('role'),
                    id: b.id,
                    classes: b.className.substring(0, 80)
                });
            }
        }
        return JSON.stringify(result.slice(0, 10));
    ''')
    log(f'Buttons with 查看: {all_buttons}')
    
    # Find the disclosure section
    disc = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        var keywords = ['\u5e7f\u544a\u4fe1\u606f\u516c\u793a', '\u516c\u793a', 'Ad Disclosure', 'disclosure', '\u5e7f\u544a'];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            for (var kw of keywords) {
                if (text.includes(kw) && text.length < 200) {
                    results.push({
                        tag: el.tagName,
                        text: text.substring(0, 80),
                        role: el.getAttribute('role'),
                        id: el.id,
                        classes: el.className.substring(0, 60)
                    });
                    break;
                }
            }
        }
        return JSON.stringify(results.slice(0, 5));
    """)
    log(f'Disclosure section: {disc}')
    
    # Try to find the detail modal/dialog after clicking
    # First, let's see what happens when we search for elements containing '欧盟'
    eu_search = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\u6b27\u7f9f') && text.length < 100) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 60),
                    role: el.getAttribute('role'),
                    classes: el.className.substring(0, 60)
                });
            }
        }
        return JSON.stringify(results.slice(0, 10));
    """)
    log(f'Elements containing 欧盟: {eu_search}')
    
    # Try to find the ACTUAL detail modal by looking for dialogs
    dialogs = driver.execute_script('''
        var ds = document.querySelectorAll("[role='dialog'], [role='presentation'], [role='tooltip']");
        var result = [];
        for (var d of ds) {
            var text = (d.textContent || '').trim();
            result.push({
                role: d.getAttribute('role'),
                text: text.substring(0, 80),
                visible: d.offsetWidth > 0,
                id: d.id,
                classes: d.className.substring(0, 60)
            });
        }
        return JSON.stringify(result.slice(0, 5));
    ''')
    log(f'Dialogs/presentations: {dialogs}')
    
    # Find all divs that contain "2,258" or "2258" (the EU reach)
    reach_search = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '');
            if (text.includes('2,258') || text.includes('2258')) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 80).replace(/\\n/g, '|'),
                    role: el.getAttribute('role'),
                    visible: el.offsetWidth > 0
                });
            }
        }
        return JSON.stringify(results.slice(0, 5));
    """)
    log(f'Elements with 2,258: {reach_search}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
