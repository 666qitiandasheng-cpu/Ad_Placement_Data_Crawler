"""Debug: Find the disclosure tabs and expand control after clicking detail"""
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
    options.add_argument('--user-data-dir=C:\\Users\Ivy\\AppData\\Local\\Google\\Chrome\\User Data\\Default')
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
    
    # Look for "打开下拉菜单" - find the element with this text
    # and find its clickable parent
    expand_info = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var result = null;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6253\\u5f00\\u4e0b\\u62c9\\u83dc\\u5355')) {
                // Found the expand trigger - get its computed style and parent
                var parent = el.parentElement;
                var clickableParent = parent;
                while (clickableParent && clickableParent.tagName !== 'BODY') {
                    var role = clickableParent.getAttribute('role');
                    var tabindex = clickableParent.getAttribute('tabindex');
                    if (role === 'button' || role === 'link' || tabindex === '0') {
                        break;
                    }
                    clickableParent = clickableParent.parentElement;
                }
                var style = window.getComputedStyle(el);
                var parentStyle = window.getComputedStyle(parent);
                return JSON.stringify({
                    tag: el.tagName,
                    text: text.substring(0, 50),
                    role: el.getAttribute('role'),
                    al: (el.getAttribute('aria-label') || '').trim(),
                    parentTag: parent.tagName,
                    parentRole: parent.getAttribute('role'),
                    parentClass: parent.className.substring(0, 60),
                    clickableParentTag: clickableParent ? clickableParent.tagName : null,
                    clickableParentRole: clickableParent ? clickableParent.getAttribute('role') : null,
                    clickableParentClass: clickableParent ? clickableParent.className.substring(0, 60) : null,
                    cursor: style.cursor,
                    parentCursor: parentStyle.cursor
                });
            }
        }
        return 'expand element not found';
    """)
    log(f'Expand element: {expand_info}')
    
    # Now find what happens when we click "打开下拉菜单"
    # The element with that text - click it
    click_result = driver.execute_script("""
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6253\\u5f00\\u4e0b\\u62c9\\u83dc\\u5355')) {
                // Try clicking the element itself
                el.scrollIntoView({block: 'center'});
                el.click();
                return 'clicked el';
            }
        }
        // Try clicking parent
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6253\\u5f00\\u4e0b\\u62c9\\u83dc\\u5355')) {
                var parent = el.parentElement;
                if (parent) {
                    parent.scrollIntoView({block: 'center'});
                    parent.click();
                    return 'clicked parent';
                }
            }
        }
        return 'not found';
    """)
    log(f'Click result: {click_result}')
    time.sleep(2)
    
    # Now check what changed
    after_click = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6b27\\u7f9f\\u5883\\u5185') || text.includes('\\u6b27\\u7f9f\\u6d32')) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 80),
                    role: el.getAttribute('role')
                });
            }
        }
        return JSON.stringify(results.slice(0, 5));
    """)
    log(f'After click - EU elements: {after_click}')
    
    # Check if disclosure section expanded
    expanded_text = driver.execute_script("""
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09')) {
                var parent = el.parentElement;
                // Get all text in parent container
                var containerText = parent ? parent.innerText : '';
                return containerText.substring(0, 300);
            }
        }
        return 'section not found';
    """)
    log(f'Expanded section text: {expanded_text}')
    
    # Find any elements that appeared with EU/UK targeting data
    targeting_data = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            // Look for elements containing EU targeting info (age, gender, reach)
            if ((text.includes('21-65') || text.includes('21\\u5c81')) && 
                (text.includes('\\u4e0d\\u9650') || text.includes('\\u7537\\u6027') || text.includes('\\u5973\\u6027')) &&
                (text.includes('\\u8986\\u76d6') || text.includes('Reach'))) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 100),
                    role: el.getAttribute('role')
                });
            }
        }
        return JSON.stringify(results.slice(0, 5));
    """)
    log(f'Targeting data elements: {targeting_data}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
