"""Test: Look at raw page source for ad 1242102094427110 to find targeting data"""
import sys
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

out_file = open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\raw_test.txt', 'w', encoding='utf-8')

def log(msg):
    out_file.write(str(msg) + '\n')
    out_file.flush()

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
    log('Page loaded')
    time.sleep(8)
    
    # Click detail button
    try:
        btns = driver.find_elements(By.XPATH, '//span[contains(text(),"查看")]')
        for btn in btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                log(f'Clicked: {btn.text[:30]}')
                break
        time.sleep(5)
    except Exception as e:
        log(f'Button click error: {e}')
    
    # Get all tab aria-labels
    tabs = driver.execute_script("""
        return JSON.stringify(Array.from(document.querySelectorAll('[role="tab"]')).map(t => ({
            ariaLabel: t.getAttribute('aria-label'),
            text: t.textContent.trim().substring(0, 40),
            visible: t.offsetWidth > 0
        })));
    """)
    log(f'Tabs: {tabs}')
    
    # Get all script tag contents that might have targeting data
    scripts = driver.execute_script("""
        var scripts = document.querySelectorAll('script');
        var results = [];
        for (var s of scripts) {
            var text = s.textContent;
            if (text.includes('age') && text.includes('gender') && text.includes('reach')) {
                results.push(text.substring(0, 500));
            }
        }
        return JSON.stringify(results.slice(0, 3));
    """)
    log(f'Scripts with targeting: {scripts[:500] if scripts else "none"}')
    
    # Get the full body text after clicking each tab
    for region in ['欧盟', '英国']:
        # Click tab with this aria-label
        clicked = driver.execute_script("""
            var rn = arguments[0];
            var tabs = document.querySelectorAll('[role="tab"]');
            for (var t of tabs) {
                if (t.getAttribute('aria-label') === rn) {
                    t.scrollIntoView({block: 'center'});
                    t.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        """, region)
        log(f'Click {region}: {clicked}')
        time.sleep(2)
        
        # Get body text
        body = driver.execute_script("return document.body.innerText")
        # Find relevant section
        if '覆盖' in body or 'Age' in body or 'gender' in body.lower():
            lines = body.split('\n')
            for i, line in enumerate(lines):
                if any(k in line.lower() for k in ['覆盖', 'age', 'gender', 'reach', 'impression', '不限']):
                    context = lines[max(0,i-1):i+3]
                    log(f'  {region} context: {context}')
                    break
    
    driver.quit()
    log('Done')
    out_file.close()

if __name__ == '__main__':
    import time
    run()
