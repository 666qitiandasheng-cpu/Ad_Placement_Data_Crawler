"""Test the extract_js code in isolation"""
import sys
import time
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
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
    
    # Test the extract_js in isolation
    test_js = r"""
        var RA = ["\u6b27\u7f9f","\u6b27\u6d32","\u82f1\u56fd","\u5fb7\u56fd","\u6cd5\u56fd","\u610f\u5927\u5229","\u897f\u73b0\u4e16","\u8377\u5170","\u6ce2\u5170","\u745e\u5179","\u4e39\u9ea6","\u5965\u5730\u5229","\u6bd4\u5229\u65f6","EU","United Kingdom","Germany","France","Italy","Spain","Netherlands","Poland","Sweden","Austria","Belgium","United States","Brazil","India","Japan","Korea","Vietnam","\u7f8e\u56fd","\u65b0\u52a0\u5761"];
        
        // Step 1: Find dropdown button
        var dropdownBtn = null;
        var allButtons = document.querySelectorAll('[role="button"]');
        var btnCount = 0;
        for (var btn of allButtons) {
            btnCount++;
            if (btn.getAttribute('aria-haspopup') === 'menu') {
                var inDialog = !!btn.closest("[role='dialog']");
                if (inDialog) {
                    dropdownBtn = btn;
                    break;
                }
            }
        }
        
        if (!dropdownBtn) {
            return JSON.stringify({step: 'find_dropdown', found: false, btnCount: btnCount, error: 'dropdown not found'});
        }
        
        // Click to open menu
        dropdownBtn.scrollIntoView({block: 'center'});
        dropdownBtn.click();
        
        // Wait for menu
        var waitStart = Date.now();
        while (Date.now() - waitStart < 2000) {
            if (dropdownBtn.getAttribute('aria-expanded') === 'true') break;
        }
        
        // Find menu items
        var menuItems = document.querySelectorAll('[role="menuitem"]');
        var regionItems = [];
        for (var item of menuItems) {
            var al = (item.getAttribute('aria-label') || '').trim();
            var text = (item.textContent || '').trim();
            for (var rn of RA) {
                if (al === rn || text === rn) {
                    regionItems.push({name: rn, ariaLabel: al});
                    break;
                }
            }
        }
        
        return JSON.stringify({step: 'done', dropdownFound: true, btnCount: btnCount, menuItemCount: menuItems.length, regionItemsFound: regionItems.length, regions: regionItems.slice(0, 10)});
    """
    
    try:
        result = driver.execute_script(test_js)
        log(f'JS Result: {result}')
    except Exception as e:
        log(f'JS Error: {e}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
