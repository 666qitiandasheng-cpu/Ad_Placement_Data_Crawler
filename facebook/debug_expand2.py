"""Debug: Find the correct expand control for the EU disclosure section"""
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
    
    # Find the expand control near "欧盟境内广告信息公示"
    # Look for clickable elements near that text
    expand_controls = driver.execute_script("""
        // Find all elements that have "下拉菜单" or arrow-like content
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            // Check if element contains "下拉菜单" or arrow characters
            if (text.includes('\\u4e0b\\u62c9\\u83dc\\u5355') || 
                text.includes('>') || text.includes(' chevron') ||
                text === '' && el.querySelectorAll('*').length === 0) {
                var style = window.getComputedStyle(el);
                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    results.push({
                        tag: el.tagName,
                        text: text.substring(0, 20),
                        role: el.getAttribute('role'),
                        al: (el.getAttribute('aria-label') || '').trim(),
                        classes: el.className.substring(0, 50)
                    });
                }
            }
        }
        return JSON.stringify(results.slice(0, 15));
    """)
    log(f'Expand controls (下拉菜单/arrows): {expand_controls}')
    
    # Try to find the specific element that controls "欧盟境内广告信息公示" expand
    # by looking for the arrow icon element near that text
    eu_expand = driver.execute_script("""
        // Strategy: find element containing "欧盟境内广告信息公示" and then
        // look at its siblings/parent for a clickable expand control
        var all = document.querySelectorAll('*');
        var result = null;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6b27\\u7f9f\\u5883\\u5185\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a')) {
                result = {
                    tag: el.tagName,
                    text: text.substring(0, 60),
                    role: el.getAttribute('role'),
                    al: (el.getAttribute('aria-label') || '').trim(),
                    id: el.id,
                    classes: el.className.substring(0, 60),
                    hasClickHandler: !!(el.onclick || el.getAttribute('onclick') || el.getAttribute('aria-expanded'))
                };
                // Get parent
                if (el.parentElement) {
                    result.parent = {
                        tag: el.parentElement.tagName,
                        role: el.parentElement.getAttribute('role'),
                        classes: el.parentElement.className.substring(0, 40)
                    };
                }
                // Get next sibling
                if (el.nextElementSibling) {
                    result.nextSibling = {
                        tag: el.nextElementSibling.tagName,
                        text: el.nextElementSibling.textContent.trim().substring(0, 30),
                        role: el.nextElementSibling.getAttribute('role'),
                        al: (el.nextElementSibling.getAttribute('aria-label') || '').trim()
                    };
                }
            }
        }
        return JSON.stringify(result);
    """)
    log(f'EU disclosure element: {eu_expand}')
    
    # Try clicking the expand control - look for elements after "广告信息公示"
    expand_click = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var disclosureText = '';
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09')) {
                // Found the section header "广告信息公示（按地区）"
                // The expand control might be a sibling or child
                // Let's get the full parent structure
                var parent = el.parentElement;
                for (var i = 0; i < 5 && parent; i++) {
                    var siblings = [];
                    var children = [];
                    for (var c of parent.children) {
                        children.push({
                            tag: c.tagName,
                            text: (c.textContent || '').trim().substring(0, 30),
                            role: c.getAttribute('role'),
                            al: (c.getAttribute('aria-label') || '').trim()
                        });
                    }
                    siblings.push({
                        parent: parent.tagName,
                        children: children
                    });
                    parent = parent.parentElement;
                }
                return JSON.stringify(siblings.slice(0, 2));
            }
        }
        return 'section header not found';
    """)
    log(f'Expand click candidates: {expand_click}')
    
    # Find ALL clickable elements in the dialog and show their text
    dialog_buttons = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        var allBtns = [];
        for (var d of dialogs) {
            if (!d.textContent.includes('\\u675f\\u5165') && !d.textContent.includes('Block Blast')) continue;
            var btns = d.querySelectorAll(\"[role='button'], [role='tab'], [aria-expanded], .x1i10hfl\");
            for (var b of btns) {
                var text = (b.textContent || '').trim();
                if (text.length < 100) {
                    allBtns.push({
                        text: text.substring(0, 40),
                        role: b.getAttribute('role'),
                        al: (b.getAttribute('aria-label') || '').trim(),
                        ariaExpanded: b.getAttribute('aria-expanded'),
                        id: b.id,
                        classes: b.className.substring(0, 50)
                    });
                }
            }
        }
        return JSON.stringify(allBtns.slice(0, 20));
    """)
    log(f'Dialog buttons: {dialog_buttons}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
