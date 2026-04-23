import re
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114613.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    page_source = f.read()

# Test with ad that has video (from earlier extract_ads_v2.py output)
ad_id = '1265526875532879'

pattern = f'ad_archive_id[":\\s]+{ad_id}'
match = re.search(pattern, page_source)
if not match:
    print(f"Ad {ad_id} not found")
    exit(1)

pos = match.start()
start = max(0, pos - 3000)
end = min(len(page_source), pos + 5000)
context = page_source[start:end]

print(f"Context length: {len(context)}")

# 找 video_hd_url - 尝试不同的模式
patterns = [
    r'video_hd_url[":\\s]+([^"\\s,}]+)',
    r'"video_hd_url":"([^"]+)"',
    r'video_hd_url[^:]*:"([^"]+)"',
]

for i, p in enumerate(patterns):
    m = re.search(p, context)
    print(f"Pattern {i+1}: {p[:40]}...")
    if m:
        print(f"  Match: {m.group(1)[:60]}...")
    else:
        print(f"  No match")

# 也检查一下原始 JSON 中的格式
# 看看 video_hd_url 附近的内容
idx = context.find('video_hd_url')
if idx > 0:
    print(f"\nAround video_hd_url:")
    print(context[idx:idx+100])
