import sys
import os

os.chdir(r'C:\Users\Ivy\.openclaw\workspace\tiktok')

log_file = open(r'C:\Users\Ivy\.openclaw\workspace\tiktok\output\debug_tiktok_detail.txt', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

print('Debug TikTok detail page structure...', flush=True)

try:
    from run import make_driver
    
    driver = make_driver(headless=False)
    
    # Visit one detail page
    ad_id = '1862488689350913'
    detail_url = f'https://library.tiktok.com/ads/detail/?ad_id={ad_id}'
    
    print(f'Visiting: {detail_url}', flush=True)
    driver.get(detail_url)
    import time
    time.sleep(8)
    
    # Get HTML
    html = driver.page_source
    
    # Save HTML for analysis
    with open(r'C:\Users\Ivy\.openclaw\workspace\tiktok\output\detail_page_html.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('HTML saved', flush=True)
    
    # Get text
    from selenium.webdriver.common.by import By
    body = driver.find_element(By.TAG_NAME, 'body')
    text = body.text
    
    # Save text
    with open(r'C:\Users\Ivy\.openclaw\workspace\tiktok\output\detail_page_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Text saved', flush=True)
    
    print(f'Text length: {len(text)}', flush=True)
    print(f'Text preview:', flush=True)
    print(text[:5000], flush=True)
    
    # Try to find Gender and Age sections in HTML
    import re
    
    # Check for checkmarks pattern in HTML
    print('\n=== Looking for Gender section ===', flush=True)
    gender_match = re.search(r'Gender\s+<', html)
    if gender_match:
        start = gender_match.start() - 200
        end = gender_match.start() + 2000
        print(f'Gender context: {html[start:end]}', flush=True)
    
    print('\n=== Looking for Age section ===', flush=True)
    age_match = re.search(r'Age\s+<', html)
    if age_match:
        start = age_match.start() - 200
        end = age_match.start() + 2000
        print(f'Age context: {html[start:end]}', flush=True)
    
    # Check for svg paths that might be checkmarks
    print('\n=== Looking for SVG checkmark patterns ===', flush=True)
    # Common checkmark SVG path patterns
    svg_patterns = [
        r'<path[^>]*d="M[^"]*"[^>]*>',  # generic SVG path
        r'd="M\d',  # SVG path starting with M (drawing)
    ]
    for pattern in svg_patterns:
        matches = re.findall(pattern, html[:50000])
        print(f'Pattern {pattern}: found {len(matches)} matches', flush=True)
        if matches:
            print(f'Sample: {matches[:3]}', flush=True)
    
    driver.quit()
    print('\nDone!', flush=True)
    
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}', flush=True)
    import traceback
    traceback.print_exc()

log_file.close()