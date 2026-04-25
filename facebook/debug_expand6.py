"""Debug: Click the 广告信息公示 section directly and explore country dropdown"""
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
    options.add_argument(r'--user-data-dir=C:\Users\Ivy\AppData\Local\Google\Chrome\User Data\Default')
    options.add_argument('--profile-email=automatictest2024@gmail.com')
    
    driver = uc.Chrome(options=options, version_main=147)
    driver.set_page_load_timeout(15)
    driver.get('https://www.facebook.com/ads/library/?id=1242102094427110')
    time.sleep(8)
    
    # Click detail button
    driver.execute_script("""
        var buttons = document.querySelectorAll(\"div[role='button']\");
        for (var b of buttons) {
            var text = (b.textContent || '').trim();
            if (text.includes('\\u67e5\\u770b\\u5e7f\\u544a\\u8be6\\u60c5')) {
                b.scrollIntoView({block: 'center'});
                b.click();
                return;
            }
        }
    """)
    time.sleep(5)
    driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_screen2.png')
    log('Clicked detail button')
    
    # Try clicking directly on the "广告信息公示（按地区）" text element
    click_disc = driver.execute_script("""
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            // Find the heading "广告信息公示（按地区）"
            if (text === '\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') {
                el.scrollIntoView({block: 'center'});
                el.click();
                return 'clicked heading: ' + el.tagName + ', text: ' + text;
            }
        }
        return 'heading not found';
    """)
    log(f'Click disclosure heading: {click_disc}')
    time.sleep(2)
    driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_screen3.png')
    
    # Now look for clickable country names in the disclosure section
    # Look for elements containing "奥地利" or "意大利" or "欧盟" that are clickable
    country_elements = driver.execute_script("""
        var countries = ['\\u5965\\u5730\\u5229', '\\u610f\\u5927\\u5229', '\\u6bd4\\u5229\\u65f6', '\\u6b27\\u7f9f', '\\u6b27\\u6d32', '\\u82f1\\u56fd', '\\u5fb7\\u56fd', '\\u6cd5\\u56fd'];
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            for (var c of countries) {
                if (text === c) {
                    var role = el.getAttribute('role') || '';
                    var tabindex = el.getAttribute('tabindex') || '';
                    var cursor = window.getComputedStyle(el).cursor;
                    var isInDialog = !!el.closest(\"[role='dialog']\");
                    results.push({
                        tag: el.tagName,
                        text: text,
                        role: role,
                        tabindex: tabindex,
                        cursor: cursor,
                        inDialog: isInDialog,
                        parent: el.parentElement ? el.parentElement.tagName + '|' + el.parentElement.getAttribute('role') : 'none'
                    });
                }
            }
        }
        return JSON.stringify(results.slice(0, 15));
    """)
    log(f'Country elements: {country_elements}')
    
    # Click each country element and see if data changes
    for country in ['\\u5965\\u5730\\u5229', '\\u6b27\\u7f9f', '\\u82f1\\u56fd']:
        click_c = driver.execute_script("""
            var country = arguments[0];
            var all = document.querySelectorAll('*');
            for (var el of all) {
                var text = (el.textContent || '').trim();
                if (text === country) {
                    // Check if this element is in the dialog
                    var inDialog = !!el.closest(\"[role='dialog']\");
                    if (!inDialog) continue;
                    el.scrollIntoView({block: 'center'});
                    el.click();
                    return 'clicked';
                }
            }
            return 'not_found_in_dialog';
        """, country)
        log(f'Click {country}: {click_c}')
        time.sleep(2)
        
        if click_c == 'clicked':
            # Get the targeting data visible
            targeting = driver.execute_script("""
                var all = document.querySelectorAll('*');
                for (var el of all) {
                    var text = (el.textContent || '').trim();
                    if (text.includes('\\u8986\\u76d6') || text.includes('Reach') || text.includes('Impression')) {
                        var inDialog = !!el.closest(\"[role='dialog']\");
                        if (inDialog) {
                            return el.textContent.trim().substring(0, 100);
                        }
                    }
                }
                return 'no targeting found';
            """)
            log(f'  Targeting: {targeting}')
            
            # Get body text snippet
            body_snippet = driver.execute_script("""
                var body = document.body.innerText;
                var lines = body.split('\\n');
                var relevant = [];
                for (var l of lines) {
                    if (l.includes('\\u8986\\u76d6') || l.includes('\\u5e74\\u9f84') || l.includes('\\u6027\\u522b') || l.includes('\\u5965\\u5730') || l.includes('\\u82f1\\u56fd')) {
                        relevant.push(l.trim());
                    }
                }
                return relevant.slice(0, 5).join(' | ');
            """)
            log(f'  Relevant lines: {body_snippet}')
            driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\screen_' + country.replace('\\u', '') + '.png')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
