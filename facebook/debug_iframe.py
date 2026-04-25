"""Debug: Check if countries are in an iframe inside the dialog"""
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
    
    # Check for iframes inside the dialog
    iframe_info = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        var result = [];
        for (var d of dialogs) {
            var iframes = d.querySelectorAll('iframe');
            if (iframes.length > 0) {
                for (var iframe of iframes) {
                    result.push({
                        src: iframe.src || 'about:blank',
                        id: iframe.id || '',
                        width: iframe.width,
                        height: iframe.height
                    });
                }
            }
        }
        return JSON.stringify(result);
    """)
    log(f'Iframes in dialogs: {iframe_info}')
    
    # Check ALL iframes on the page
    all_iframes = driver.execute_script("""
        var iframes = document.querySelectorAll('iframe');
        var result = [];
        for (var iframe of iframes) {
            result.push({
                src: iframe.src || 'about:blank',
                id: iframe.id || '',
                name: iframe.name || '',
                width: iframe.width,
                height: iframe.height
            });
        }
        return JSON.stringify(result);
    """)
    log(f'All iframes on page: {all_iframes}')
    
    # Check dialog structure - look for all divs/containers inside dialog
    dialog_structure = driver.execute_script("""
        var dialogs = document.querySelectorAll(\"[role='dialog']\");
        var result = [];
        for (var d of dialogs) {
            var text = (d.textContent || '').trim();
            if (text.includes('\\u675f\\u5165') || text.includes('Block Blast')) {
                // Get the direct children of this dialog
                var children = [];
                for (var c of d.children) {
                    children.push({
                        tag: c.tagName,
                        class: c.className.substring(0, 50),
                        id: c.id || ''
                    });
                }
                result.push({
                    text: text.substring(0, 100),
                    children: children
                });
            }
        }
        return JSON.stringify(result);
    """)
    log(f'Dialog structure: {dialog_structure}')
    
    # Try switching to any iframe with the detail modal content
    # First check if the detail modal is in an iframe
    driver.switch_to.default_content()
    iframe_switch = driver.execute_script("""
        // Check if there's an iframe that might contain the ad detail content
        var iframes = document.querySelectorAll('iframe');
        var result = [];
        for (var iframe of iframes) {
            try {
                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                var iframeText = iframeDoc.body.innerText || '';
                result.push({
                    src: iframe.src || 'about:blank',
                    textPreview: iframeText.substring(0, 100)
                });
            } catch(e) {
                result.push({
                    src: iframe.src || 'about:blank',
                    error: 'cannot access: ' + e.message.substring(0, 50)
                });
            }
        }
        return JSON.stringify(result);
    """)
    log(f'Iframe content check: {iframe_switch}')
    
    # Try clicking the country/region in the disclosure section
    # The countries are in a grid - let's look for the grid cell with cursor:pointer
    click_grid = driver.execute_script("""
        // Find grid cells with cursor:pointer that contain country names
        var gridcells = document.querySelectorAll('[role=\"gridcell\"], [role=\"grid\"]');
        var results = [];
        for (var gc of gridcells) {
            var text = (gc.textContent || '').trim();
            if (text === '\\u5965\\u5730\\u5229' || text === '\\u610f\\u5927\\u5229' || 
                text === '\\u6bd4\\u5229\\u65f6' || text === '\\u6b27\\u7f9f' || text === '\\u82f1\\u56fd') {
                var cursor = window.getComputedStyle(gc).cursor;
                var inDialog = !!gc.closest(\"[role='dialog']\");
                gc.scrollIntoView({block: 'center'});
                gc.click();
                results.push({clicked: text, cursor: cursor, inDialog: inDialog});
            }
        }
        return JSON.stringify(results);
    """)
    log(f'Grid cell click: {click_grid}')
    time.sleep(2)
    
    # After clicking, check for targeting data
    after_click = driver.execute_script("""
        var body = document.body.innerText;
        var lines = body.split('\\n');
        var relevant = [];
        for (var l of lines) {
            if ((l.includes('\\u8986\\u76d6') || l.includes('Reach') || l.includes('Impression')) && relevant.length < 5) {
                relevant.push(l.trim().substring(0, 80));
            }
        }
        return relevant.join(' | ');
    """)
    log(f'After grid click targeting: {after_click}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
