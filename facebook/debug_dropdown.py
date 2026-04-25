"""Debug: Find and interact with the country selector dropdown"""
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
    
    # Look for the country selector - it's near the disclosure section header
    # Look for combobox, listbox, or dropdown elements
    selector_search = driver.execute_script("""
        // Look for any element with role='combobox', 'listbox', 'option', or 'menu'
        var selectorRoles = ['combobox', 'listbox', 'option', 'menu', 'menuitem', 'tab', 'treeitem'];
        var found = [];
        for (var role of selectorRoles) {
            var els = document.querySelectorAll('[role=\"' + role + '\"]');
            for (var el of els) {
                var text = (el.textContent || '').trim();
                var al = (el.getAttribute('aria-label') || '').trim();
                var inDialog = !!el.closest(\"[role='dialog'], [role='presentation']\");
                if (text.length > 0 && text.length < 100) {
                    found.push({
                        role: role,
                        text: text.substring(0, 40),
                        al: al,
                        inDialog: inDialog,
                        tag: el.tagName
                    });
                }
            }
        }
        return JSON.stringify(found.slice(0, 20));
    """)
    log(f'Selector elements: {selector_search}')
    
    # Look specifically for the dropdown arrow near "广告信息公示（按地区）"
    dropdown_near_header = driver.execute_script("""
        // Find the element containing the disclosure section header text
        var header = null;
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text === '\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') {
                header = el;
                break;
            }
        }
        if (!header) return 'header not found';
        
        // Get the parent and look for dropdown elements
        var container = header.parentElement;
        for (var i = 0; i < 5; i++) {
            if (!container) break;
            // Look for combobox, button with aria-haspopup, or aria-expanded
            var dropdowns = container.querySelectorAll('[role=\"combobox\"], [role=\"listbox\"], [aria-haspopup=\"listbox\"], [aria-expanded]');
            if (dropdowns.length > 0) {
                var results = [];
                for (var d of dropdowns) {
                    results.push({
                        tag: d.tagName,
                        role: d.getAttribute('role'),
                        text: (d.textContent || '').trim().substring(0, 40),
                        al: (d.getAttribute('aria-label') || '').trim(),
                        ariaExpanded: d.getAttribute('aria-expanded'),
                        ariaHaspopup: d.getAttribute('aria-haspopup'),
                        inDialog: !!d.closest(\"[role='dialog']\")
                    });
                }
                return JSON.stringify({containerLevel: i, dropdowns: results});
            }
            container = container.parentElement;
        }
        return 'no dropdown found in parent chain';
    """)
    log(f'Dropdown near header: {dropdown_near_header}')
    
    # Try to find ANY combobox on the page
    comboboxes = driver.execute_script("""
        var cb = document.querySelectorAll('[role=\"combobox\"]');
        var results = [];
        for (var el of cb) {
            var text = (el.textContent || '').trim();
            results.push({
                tag: el.tagName,
                text: text.substring(0, 50),
                al: (el.getAttribute('aria-label') || '').trim(),
                ariaExpanded: el.getAttribute('aria-expanded'),
                inDialog: !!el.closest(\"[role='dialog']\")
            });
        }
        return JSON.stringify(results);
    """)
    log(f'Comboboxes: {comboboxes}')
    
    # Try to find and click the dropdown in the modal by looking for 
    # elements containing "打开下拉菜单" and finding their clickable parent
    find_dropdown = driver.execute_script("""
        // Find the span/element with "打开下拉菜单" text
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text === '\\u6253\\u5f00\\u4e0b\\u62c9\\u83dc\\u5355') {
                // This is the label - find the clickable parent
                var parent = el;
                for (var i = 0; i < 5; i++) {
                    if (!parent || !parent.parentElement) break;
                    parent = parent.parentElement;
                    var role = parent.getAttribute('role');
                    var tabindex = parent.getAttribute('tabindex');
                    var cursor = window.getComputedStyle(parent).cursor;
                    if (role === 'button' || role === 'combobox' || tabindex === '0' || cursor === 'pointer') {
                        return JSON.stringify({
                            clickableTag: parent.tagName,
                            clickableRole: role,
                            clickableText: (parent.textContent || '').trim().substring(0, 40),
                            clickableAl: (parent.getAttribute('aria-label') || '').trim(),
                            inDialog: !!parent.closest(\"[role='dialog']\")
                        });
                    }
                }
                return 'found label but no clickable parent';
            }
        }
        return 'label not found';
    """)
    log(f'Dropdown clickable parent: {find_dropdown}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
