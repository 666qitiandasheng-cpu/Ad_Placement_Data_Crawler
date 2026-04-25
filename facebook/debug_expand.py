"""Debug: Find the expandable disclosure section with EU/UK tabs"""
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
    
    # Find the ad detail dialog
    dialog_info = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        var result = [];
        for (var d of dialogs) {
            var text = (d.textContent || '').trim();
            if (text.includes('\\u675f\\u5165') || text.includes('\\u4e2d') || text.includes('Block Blast')) {
                result.push({
                    text: text.substring(0, 150).replace(/\\n/g, '|'),
                    visible: d.offsetWidth > 0
                });
            }
        }
        return JSON.stringify(result);
    """)
    log(f'Ad detail dialog: {dialog_info}')
    
    # Get full text of the ad detail dialog to find expand targets
    full_dialog_text = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        for (var d of dialogs) {
            var text = (d.textContent || '').trim();
            if (text.includes('\\u675f\\u5165') || text.includes('Block Blast')) {
                return d.innerHTML.substring(0, 2000).replace(/\\n/g, '|');
            }
        }
        return 'not_found';
    """)
    log(f'Full dialog HTML: {full_dialog_text}')
    
    # Look for elements with aria-label containing '打开' or '展开' or 'EU'
    expand_elements = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var al = (el.getAttribute('aria-label') || '').trim();
            var text = (el.textContent || '').trim();
            if (al.includes('\\u6253\\u5f00') || al.includes('\\u5c55\\u5f00') ||
                al.includes('EU') || al.includes('\\u6b27\\u7f9f') ||
                text.includes('\\u6253\\u5f00') || text.includes('\\u5c55\\u5f00')) {
                results.push({
                    tag: el.tagName,
                    al: al,
                    text: text.substring(0, 40),
                    role: el.getAttribute('role'),
                    visible: el.offsetWidth > 0
                });
            }
        }
        return JSON.stringify(results.slice(0, 10));
    """)
    log(f'Expand elements: {expand_elements}')
    
    # Find the disclosure section text in the dialog
    disc_section = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        for (var d of dialogs) {
            var text = (d.textContent || '').trim();
            if (text.includes('\\u675f\\u5165') || text.includes('Block Blast')) {
                // Find the disclosure section
                var idx = text.indexOf('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a');
                if (idx >= 0) {
                    return text.substring(idx, idx + 500);
                }
            }
        }
        return 'disclosure not found in dialog';
    """)
    log(f'Disclosure section: {disc_section}')
    
    # Click the "打开" / expand button for EU disclosure
    clicked_eu = driver.execute_script("""
        var all = document.querySelectorAll('*');
        for (var el of all) {
            var al = (el.getAttribute('aria-label') || '').trim();
            var text = (el.textContent || '').trim();
            if (al.includes('\\u6253\\u5f00') || text.includes('\\u6253\\u5f00')) {
                if (el.offsetWidth > 0) {
                    el.scrollIntoView({block: 'center'});
                    el.click();
                    return 'clicked: al=' + al + ', text=' + text.substring(0, 30);
                }
            }
        }
        return 'not_found';
    """)
    log(f'Click expand EU: {clicked_eu}')
    time.sleep(3)
    
    # Now check for EU/UK text
    after_expand = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var results = [];
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text.includes('\\u6b27\\u7f9f') || text.includes('\\u82f1\\u56fd')) {
                if (results.length < 5) {
                    results.push({
                        tag: el.tagName,
                        text: text.substring(0, 60),
                        role: el.getAttribute('role'),
                        visible: el.offsetWidth > 0,
                        al: (el.getAttribute('aria-label') || '').trim().substring(0, 30)
                    });
                }
            }
        }
        return JSON.stringify(results);
    """)
    log(f'After expand - EU/UK elements: {after_expand}')
    
    # Check the full dialog text now
    dialog_text_after = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        for (var d of dialogs) {
            var text = (d.textContent || '').trim();
            if (text.includes('\\u675f\\u5165') || text.includes('Block Blast')) {
                var idx = text.indexOf('\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a');
                if (idx >= 0) {
                    return text.substring(idx, idx + 800);
                }
            }
        }
        return 'not found';
    """)
    log(f'Dialog text after expand: {dialog_text_after}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
