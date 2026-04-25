"""Debug: Inspect what happens after clicking 查看广告详情 button"""
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
    
    # BEFORE clicking: check if 欧盟 is in the page
    before_eu = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var count = 0;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6b27\\u7f9f')) count++;
        }
        return count;
    """)
    log(f'Before click - elements with 欧盟: {before_eu}')
    
    # Click the detail button
    try:
        btn = driver.execute_script("""
            var buttons = document.querySelectorAll(\"div[role='button']\");
            for (var b of buttons) {
                var text = (b.textContent || '').trim();
                if (text.includes('\\u67e5\\u770b\\u5e7f\\u544a\\u8be6\\u60c5')) {
                    return text.substring(0, 50);
                }
            }
            return 'NOT_FOUND';
        """)
        log(f'Button text: {btn}')
        
        # Find and click it
        clicked = driver.execute_script("""
            var buttons = document.querySelectorAll(\"div[role='button']\");
            for (var b of buttons) {
                var text = (b.textContent || '').trim();
                if (text.includes('\\u67e5\\u770b\\u5e7f\\u544a\\u8be6\\u60c5')) {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        """)
        log(f'Click result: {clicked}')
        time.sleep(5)
    except Exception as e:
        log(f'Error: {e}')
    
    # AFTER clicking: check if 欧盟 is in the page
    after_eu = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var count = 0;
        var examples = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6b27\\u7f9f') && examples.length < 3) {
                examples.push({
                    tag: el.tagName,
                    text: text.substring(0, 60),
                    role: el.getAttribute('role'),
                    visible: el.offsetWidth > 0
                });
            }
            if (text.includes('\\u6b27\\u7f9f')) count++;
        }
        return JSON.stringify({count: count, examples: examples});
    """)
    log(f'After click - elements with 欧盟: {after_eu}')
    
    # Look for all visible text containing relevant keywords
    targeting_text = driver.execute_script("""
        var body = document.body.innerText;
        var lines = body.split('\\n');
        var relevant = [];
        for (var line of lines) {
            if (line.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a') ||
                line.includes('\\u6b27\\u7f9f') ||
                line.includes('\\u82f1\\u56fd') ||
                line.includes('\\u8986\\u76d6') ||
                line.includes('\\u5e74\\u9f84') ||
                line.includes('\\u6027\\u522b')) {
                relevant.push(line.trim().substring(0, 80));
            }
        }
        return JSON.stringify(relevant.slice(0, 20));
    """)
    log(f'Targeting text lines: {targeting_text}')
    
    # Find all elements with role that might be tabs or buttons
    interactive = driver.execute_script("""
        var all = document.querySelectorAll('[role]');
        var results = [];
        for (var el of all) {
            var r = el.getAttribute('role');
            if (['button', 'tab', 'link', 'menuitem', 'option', 'radio', 'checkbox'].includes(r)) {
                var text = (el.textContent || '').trim();
                if (text.length > 0 && text.length < 100) {
                    results.push({
                        role: r,
                        text: text.substring(0, 40),
                        al: el.getAttribute('aria-label') || ''
                    });
                }
            }
        }
        return JSON.stringify(results.slice(0, 20));
    """)
    log(f'Interactive elements: {interactive}')
    
    # Look at what was clicked - check if a modal appeared
    modal_check = driver.execute_script("""
        // Check for any overlay/modal
        var overlays = document.querySelectorAll(\"[role='dialog'], [role='presentation'], [aria-modal='true'], .x1n2okr2\");
        var result = [];
        for (var o of overlays) {
            var text = (o.textContent || '').trim();
            if (text.length > 0) {
                result.push({
                    role: o.getAttribute('role'),
                    tag: o.tagName,
                    text: text.substring(0, 80),
                    visible: o.offsetWidth > 0
                });
            }
        }
        return JSON.stringify(result.slice(0, 5));
    """)
    log(f'Modal/overlay elements: {modal_check}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
