"""Debug: Simple approach - click expand and then find and click EU/UK tabs"""
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
    
    # Take initial screenshot
    driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_screen1.png')
    log('Took initial screenshot')
    
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
    log('Clicked detail button, took screenshot')
    
    # Try to find and click the expand dropdown for disclosure section
    # Look for any element that when clicked, expands the disclosure section
    expand_result = driver.execute_script("""
        // Find the element containing "广告信息公示（按地区）"
        var all = document.querySelectorAll('*');
        var disclosureEl = null;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text === '\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') {
                disclosureEl = el;
                break;
            }
        }
        if (!disclosureEl) return 'disclosure header not found';
        
        // The header "广告信息公示（按地区）" is inside the disclosure section
        // The expand button "打开下拉菜单" is a sibling
        // Let's find the parent of the disclosureEl and look for the expand button
        var container = disclosureEl;
        for (var i = 0; i < 5; i++) {
            if (!container.parentElement) break;
            container = container.parentElement;
            // Look for clickable elements in this container
            var clickables = container.querySelectorAll('[role=\"button\"], [tabindex=\"0\"]');
            for (var c of clickables) {
                var ct = (c.textContent || '').trim();
                var cal = (c.getAttribute('aria-label') || '').trim();
                // Check if this is the expand button (not "关闭" or navigation)
                if ((ct.includes('\\u4e0b\\u62c9') || cal.includes('\\u4e0b\\u62c9') ||
                     ct.includes('\\u6253\\u5f00') || cal.includes('\\u6253\\u5f00')) &&
                    !ct.includes('\\u5173\\u95ed') && !ct.includes('\\u6e05\\u9664')) {
                    c.scrollIntoView({block: 'center'});
                    c.click();
                    return 'clicked: ' + ct + ' | ' + cal;
                }
            }
        }
        return 'expand button not found';
    """)
    log(f'Expand result: {expand_result}')
    time.sleep(3)
    driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_screen3.png')
    log('After expand, took screenshot')
    
    # Now look for EU/UK tabs
    tabs_result = driver.execute_script("""
        var RA = ["\\u6b27\\u7f9f","\\u6b27\\u6d32","\\u82f1\\u56fd","\\u5fb7\\u56fd","\\u6cd5\\u56fd","\\u5965\\u5730\\u5229","\\u6bd4\\u5229\\u65f6","EU","United Kingdom"];
        var all = document.querySelectorAll('*');
        var found = [];
        for (var el of all) {
            var al = (el.getAttribute('aria-label') || '').trim();
            for (var rn of RA) {
                if (al === rn) {
                    found.push({
                        tag: el.tagName,
                        ariaLabel: al,
                        text: el.textContent.trim().substring(0, 40),
                        visible: el.offsetWidth > 0,
                        inDialog: !!el.closest(\"[role='dialog']\")
                    });
                }
            }
        }
        return JSON.stringify(found);
    """)
    log(f'EU/UK tabs found: {tabs_result}')
    
    # Try clicking each tab and getting the data
    for rn in ['\\u6b27\\u7f9f', '\\u82f1\\u56fd']:
        click_result = driver.execute_script("""
            var rn = arguments[0];
            var all = document.querySelectorAll('*');
            for (var el of all) {
                var al = (el.getAttribute('aria-label') || '').trim();
                if (al === rn) {
                    el.scrollIntoView({block: 'center'});
                    el.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        """, rn)
        log(f'Click {rn}: {click_result}')
        time.sleep(2)
        
        # Get targeting data
        data_result = driver.execute_script("""
            var body = document.body.innerText;
            var reach = '';
            var reachM = body.match(/\\u8986\\u76d6[^\\n]{0,50}([\\d,]+)\\s*(?:\\u4eba|people|users|impressions)/i);
            if (reachM) reach = reachM[1];
            else {
                var reachM2 = body.match(/(?:Reach|Impressions)[^:]*:\\s*([\\d,]+)/i);
                if (reachM2) reach = reachM2[1];
            }
            var age = '';
            var ageM = body.match(/(\\d{1,2})\\s*[-~]\\s*(\\d+\\+?)\\s*[\\u5c81years?]/i);
            if (ageM) age = ageM[0].trim();
            return JSON.stringify({reach: reach, age: age, bodySnippet: body.substring(0, 300)});
        """)
        log(f'Data for {rn}: {data_result}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
