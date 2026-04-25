"""Debug: Check what disclosure section contains and find country/region selectors"""
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
    
    # Check what the disclosure section actually contains
    disc_content = driver.execute_script("""
        // Find the disclosure section "广告信息公示（按地区）"
        var all = document.querySelectorAll('*');
        var disclosureParent = null;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text === '\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') {
                disclosureParent = el.parentElement;
                break;
            }
        }
        if (!disclosureParent) return 'disclosure parent not found';
        
        // Walk up to find a good container
        for (var i = 0; i < 3; i++) {
            if (!disclosureParent.parentElement) break;
            disclosureParent = disclosureParent.parentElement;
        }
        
        // Get all text content in this container
        var fullText = '';
        var walker = document.createTreeWalker(disclosureParent, NodeFilter.SHOW_TEXT, null, false);
        while (walker.nextNode()) {
            var t = walker.currentNode.textContent.trim();
            if (t.length > 0 && t.length < 100) {
                fullText += t + ' | ';
            }
        }
        return JSON.stringify({
            containerTag: disclosureParent.tagName,
            containerClass: disclosureParent.className.substring(0, 60),
            fullText: fullText.substring(0, 500)
        });
    """)
    log(f'Disclosure container: {disc_content}')
    
    # Try to find the country dropdown in the disclosure section
    # Look for: button/div with aria-label or text that is a country name
    country_dropdown = driver.execute_script("""
        // Look for all elements that have country names as their EXACT text
        var countries = ['\\u5965\\u5730\\u5229', '\\u610f\\u5927\\u5229', '\\u6bd4\\u5229\\u65f6', '\\u6b27\\u7f9f', 
                         '\\u6b27\\u6d32', '\\u82f1\\u56fd', '\\u5fb7\\u56fd', '\\u6cd5\\u56fd'];
        var results = [];
        var allEls = document.querySelectorAll('*');
        for (var el of allEls) {
            var text = (el.textContent || '').trim();
            // Check if element's direct text (not children) contains country name
            // Use TreeWalker to get direct text children only
            var directText = '';
            for (var child of el.childNodes) {
                if (child.nodeType === Node.TEXT_NODE) {
                    directText += child.textContent;
                }
            }
            directText = directText.trim();
            for (var c of countries) {
                if (directText === c) {
                    var cursor = window.getComputedStyle(el).cursor;
                    var role = el.getAttribute('role') || '';
                    var al = (el.getAttribute('aria-label') || '').trim();
                    var inModal = !!el.closest(\"[role='dialog'], [role='presentation']\");
                    results.push({
                        tag: el.tagName,
                        directText: directText,
                        fullText: text.substring(0, 30),
                        role: role,
                        al: al,
                        cursor: cursor,
                        inModal: inModal,
                        parent: el.parentElement ? el.parentElement.tagName + '|' + el.parentElement.getAttribute('role') : 'none'
                    });
                }
            }
        }
        return JSON.stringify(results.slice(0, 10));
    """)
    log(f'Country dropdown candidates: {country_dropdown}')
    
    # Now try to find the dropdown arrow/expand next to "广告信息公示（按地区）"
    # by looking at siblings of the disclosure header
    header_siblings = driver.execute_script("""
        var all = document.querySelectorAll('*');
        var header = null;
        for (var el of all) {
            var text = (el.textContent || '').trim();
            if (text === '\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09') {
                header = el;
                break;
            }
        }
        if (!header) return 'header not found';
        
        var parent = header.parentElement;
        var siblings = [];
        if (parent) {
            for (var s of parent.children) {
                var stext = (s.textContent || '').trim();
                if (stext.length < 100) {
                    siblings.push({
                        tag: s.tagName,
                        text: stext.substring(0, 30),
                        role: s.getAttribute('role'),
                        al: (s.getAttribute('aria-label') || '').trim(),
                        ariaExpanded: s.getAttribute('aria-expanded'),
                        nextText: s.nextElementSibling ? (s.nextElementSibling.textContent || '').trim().substring(0, 30) : ''
                    });
                }
            }
        }
        return JSON.stringify(siblings);
    """)
    log(f'Header siblings: {header_siblings}')
    
    driver.quit()
    log('=== Done ===')

if __name__ == '__main__':
    run()
