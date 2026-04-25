"""Test region tabs on the actual Facebook page for ad 1242102094427110"""
import sys
import time
import json
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def log(msg):
    with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\ttabs_log.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

def run():
    log('Starting test')
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-data-dir=C:\\Users\\Ivy\\AppData\\Local\\Google\\Chrome\\User Data\\Default')
    options.add_argument('--profile-email=automatictest2024@gmail.com')
    
    driver = uc.Chrome(options=options, version_main=147)
    log('Chrome started')
    
    driver.get('https://www.facebook.com/ads/library/?id=1242102094427110')
    time.sleep(8)
    log('Page loaded')
    
    try:
        btns = driver.find_elements(By.XPATH, '//span[contains(text(),"查看")] | //span[contains(text(),"Details")]')
        for btn in btns:
            if btn.is_displayed():
                btn.click()
                log(f'Clicked: {btn.text[:30]}')
                break
        time.sleep(5)
    except Exception as e:
        log(f'Button click error: {e}')
    
    tabs_info = driver.execute_script("""
        var tabs = document.querySelectorAll('[role="tab"]');
        var result = [];
        for (var t of tabs) {
            result.push({
                ariaLabel: t.getAttribute('aria-label'),
                text: t.textContent.trim().substring(0, 40),
                visible: t.offsetWidth > 0
            });
        }
        return JSON.stringify(result);
    """)
    log(f'Tabs found: {tabs_info}')
    
    click_and_get = driver.execute_script(r"""
        var RA = ["\u6b27\u7f9f","\u82f1\u56fd","\u5fb7\u56fd","\u6cd5\u56fd","\u610f\u5927\u5229","\u5965\u5730\u5229","\u6bd4\u5229\u65f6","EU","United Kingdom"];
        var tabs = document.querySelectorAll('[role="tab"]');
        var results = {};
        for (var tab of tabs) {
            var al = (tab.getAttribute('aria-label') || '').trim();
            if (!al || al.length > 40) continue;
            var isRegion = false;
            for (var rn of RA) { if (al === rn) { isRegion = true; break; } }
            if (!isRegion) continue;
            tab.scrollIntoView({block: 'center'});
            tab.click();
            var start = Date.now();
            while (Date.now() - start < 1500) {}
            var bodyText = document.body.innerText;
            var age = '';
            var ageM = bodyText.match(/(\d{1,2})\s*[-~]\s*(\d+\+?)\s*[\u5c81years?]/i);
            if (ageM) age = ageM[0].trim();
            var reach = '';
            var reachM = bodyText.match(/\u8986\u76d6[^\n]{0,30}([\d,]+)\s*(?:\u4eba|people|users)/i);
            if (reachM) reach = reachM[1];
            else {
                var reachM2 = bodyText.match(/(?:Reach|Impressions)[^:]*:\s*([\d,]+)/i);
                if (reachM2) reach = reachM2[1];
            }
            results[al] = {age: age, reach: reach, snippet: bodyText.substring(0, 150).replace(/\n/g,'|')};
        }
        return JSON.stringify(results);
    """)
    log(f'Click results: {click_and_get}')
    
    driver.quit()
    log('Done')

if __name__ == '__main__':
    run()
