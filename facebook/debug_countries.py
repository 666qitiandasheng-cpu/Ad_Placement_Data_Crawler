"""Debug: Click country grid cells and capture targeting data"""
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
    log('Clicked detail button')
    
    # Click each country grid cell and check targeting data
    for country in ['\\u5965\\u5730\\u5229', '\\u610f\\u5927\\u5229', '\\u6bd4\\u5229\\u65f6', '\\u6b27\\u7f9f', '\\u82f1\\u56fd']:
        clicked = driver.execute_script("""
            var country = arguments[0];
            var gridcells = document.querySelectorAll('[role=\"gridcell\"]');
            for (var gc of gridcells) {
                if ((gc.textContent || '').trim() === country) {
                    gc.scrollIntoView({block: 'center'});
                    gc.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        """, country)
        log(f'Click {country}: {clicked}')
        time.sleep(2)
        
        # Take screenshot
        try:
            fname = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\screen_' + country.replace('\\u', '') + '.png'
            driver.save_screenshot(fname)
        except:
            pass
        
        # Get targeting data from the page
        targeting = driver.execute_script("""
            var body = document.body.innerText;
            var reach = '';
            var reachM = body.match(/\\u8986\\u76d6[^\\n]{0,80}([\\d,]+)\\s*(?:\\u4eba|people|users|impressions)?/i);
            if (reachM) reach = reachM[1];
            var age = '';
            var ageM = body.match(/(\\d{1,2})\\s*[-~]\\s*(\\d+\\+?)\\s*[\\u5c81years?]/i);
            if (ageM) age = ageM[0];
            var gender = '';
            if (body.includes('\\u4e0d\\u9650')) gender = '\\u4e0d\\u9650';
            else if (body.includes('\\u7537\\u6027')) gender = '\\u7537\\u6027';
            else if (body.includes('\\u5973\\u6027')) gender = '\\u5973\\u6027';
            var country_shown = '';
            var lines = body.split('\\n');
            for (var l of lines) {
                if (l.trim() === '\\u5965\\u5730\\u5229' || l.trim() === '\\u610f\\u5927\\u5229' || 
                    l.trim() === '\\u6bd4\\u5229\\u65f6' || l.trim() === '\\u6b27\\u7f9f' || 
                    l.trim() === '\\u82f1\\u56fd') {
                    country_shown = l.trim();
                    break;
                }
            }
            return JSON.stringify({reach: reach, age: age, gender: gender, country: country_shown});
        """)
        log(f'  Targeting: {targeting}')
        
        # Check if modal is still open
        modal_open = driver.execute_script("""
            var dialogs = document.querySelectorAll(\"[role='dialog']\");
            for (var d of dialogs) {
                var text = (d.textContent || '').trim();
                if (text.includes('\\u675f\\u5165') || text.includes('Block Blast')) {
                    return 'modal open';
                }
            }
            return 'modal closed';
        """)
        log(f'  Modal: {modal_open}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
