import re
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114613.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    page_source = f.read()

def extract_ad_details(page_source, ad_id):
    """从页面源码中提取指定广告的详细信息（视频URL、开始日期）"""
    
    # 找到该 ad_id 在源码中的位置
    pattern = f'ad_archive_id[":\\s]+{ad_id}'
    match = re.search(pattern, page_source)
    if not match:
        return '', ''
    
    pos = match.start()
    # 提取周围 5000 字符的上下文
    start = max(0, pos - 3000)
    end = min(len(page_source), pos + 5000)
    context = page_source[start:end]
    
    print(f"Context length for {ad_id}: {len(context)}")
    
    # 找 video_hd_url
    video_url = ''
    video_match = re.search(r'video_hd_url[":\\s]+([^"\\s,}]+)', context)
    if video_match:
        video_url = video_match.group(1).replace('\\/', '/')
        print(f"  Found video: {video_url[:60]}...")
    else:
        print(f"  No video found")
        # 尝试更宽的搜索
        video_match2 = re.search(r'video_hd_url[^"]*"([^"]+)"', context)
        if video_match2:
            print(f"  Found video (alt): {video_match2.group(1)[:60]}...")
    
    # 找 start_date（Unix 时间戳）
    start_date = ''
    start_date_match = re.search(r'start_date[":\\s]+(\d+)', context)
    if start_date_match:
        ts = int(start_date_match.group(1))
        try:
            start_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            print(f"  Found start_date: {start_date}")
        except:
            pass
    else:
        print(f"  No start_date found")
    
    return video_url, start_date

# Test with first ad
ad_id = '918858044256446'
video_url, start_date = extract_ad_details(page_source, ad_id)
print(f"\nResult: video={video_url[:40] if video_url else 'None'}, start_date={start_date}")
