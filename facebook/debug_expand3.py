"""Debug: Take screenshot and find the disclosure expand control"""
import sys
import time
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')

from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

OUT = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_out.txt'
SCREENSHOT = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_screen.png'

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
    
    # Take screenshot
    try:
        driver.save_screenshot(SCREENSHOT)
        log(f'Screenshot saved to {SCREENSHOT}')
    except Exception as e:
        log(f'Screenshot error: {e}')
    
    # Get the text content of the dialog to understand structure
    # Find the "广告信息公示（按地区）" section
    section_info = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var result = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09')) {
                // Get the full subtree text
                var subtreeText = '';
                var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
                while (walker.nextNode()) {
                    subtreeText += walker.currentNode.textContent + '|';
                }
                result.push({
                    tag: el.tagName,
                    fullText: subtreeText.substring(0, 200),
                    parent: el.parentElement ? el.parentElement.tagName : null,
                    nextText: el.nextElementSibling ? el.nextElementSibling.textContent.trim().substring(0, 50) : null
                });
            }
        }
        return JSON.stringify(result);
    """)
    log(f'Section info: {section_info}')
    
    # Try to find the expand element near the disclosure header
    # by finding the specific element containing "广告信息公示" and looking for its expand control
    expand_by_header = driver.execute_script("""
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            // Find element that has both disclosure text AND is a heading or label
            if (text.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') ||
                (text.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a') && text.length < 30)) {
                // This is the disclosure header - now look for its container/parent
                // which should have the expand control
                var container = el.closest('div[class*=\"expand\"], div[class*=\"section\"], div[class*=\"collapse\"], div[aria-expanded]');
                if (!container) container = el.parentElement;
                if (!container) continue;
                
                // Find all clickable children
                var clickables = [];
                var children = container.querySelectorAll('[role=\"button\"], [aria-expanded], [aria-controls], span, div');
                for (var c of children) {
                    var ct = (c.textContent || '').trim();
                    if (ct.length > 0 && ct.length < 50) {
                        clickables.push({
                            tag: c.tagName,
                            text: ct.substring(0, 30),
                            role: c.getAttribute('role'),
                            al: (c.getAttribute('aria-label') || '').trim(),
                            ariaExpanded: c.getAttribute('aria-expanded'),
                            ariaControls: c.getAttribute('aria-controls')
                        });
                    }
                }
                return JSON.stringify({
                    headerTag: el.tagName,
                    headerText: text.substring(0, 60),
                    containerTag: container.tagName,
                    containerClass: container.className.substring(0, 60),
                    clickables: clickables
                });
            }
        }
        return 'header not found';
    """)
    log(f'Expand by header: {expand_by_header}')
    
    # Try a completely different approach - look for the section by its accessible name
    # and find elements with aria-expanded that control it
    aria_controls = driver.execute_script("""
        var expanded = document.querySelectorAll('[aria-expanded]');
        var result = [];
        for (var el of expanded) {
            var al = (el.getAttribute('aria-label') || '').trim();
            var text = (el.textContent || '').trim();
            if (text.length < 100 || al.length < 100) {
                result.push({
                    tag: el.tagName,
                    text: text.substring(0, 30),
                    al: al,
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    ariaControls: el.getAttribute('aria-controls')
                });
            }
        }
        return JSON.stringify(result.slice(0, 10));
    """)
    log(f'Elements with aria-expanded: {aria_controls}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
