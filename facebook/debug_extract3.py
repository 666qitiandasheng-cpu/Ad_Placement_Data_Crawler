import re
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114846.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    page_source = f.read()

# Test multiple ads
test_ids = ['918858044256446', '1265526875532879', '1199758375584524']

for ad_id in test_ids:
    pattern = f'ad_archive_id[":\\s]+{ad_id}'
    match = re.search(pattern, page_source)
    if not match:
        print(f"Ad {ad_id}: NOT FOUND")
        continue
    
    pos = match.start()
    start = max(0, pos - 3000)
    end = min(len(page_source), pos + 5000)
    context = page_source[start:end]
    
    print(f"\nAd {ad_id}:")
    
    # 找 video_hd_url
    video_match = re.search(r'"video_hd_url":"([^"]+)"', context)
    if video_match:
        print(f"  video: {video_match.group(1)[:60]}...")
    else:
        print(f"  video: null or not found")
    
    # 找 start_date
    start_date_match = re.search(r'start_date[":\\s]+(\d+)', context)
    if start_date_match:
        ts = int(start_date_match.group(1))
        try:
            start_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            print(f"  start_date: {start_date}")
        except:
            print(f"  start_date: ts={start_date_match.group(1)} (invalid)")
    else:
        print(f"  start_date: not found")
