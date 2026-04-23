#!/usr/bin/env python3
"""
从 Facebook Ad Library 页面源码提取广告数据（正则版）
"""
import re
import json
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有 ad_archive_id
ad_ids = re.findall(r'ad_archive_id[\\":\\s]+(\d+)', content)
ad_ids = list(set(ad_ids))
print(f"找到 {len(ad_ids)} 个广告ID")

# 为每个 ad_id，提取其附近的视频URL和start_date
ads_data = []
for ad_id in ad_ids:
    # 找到该 ad_id 在源码中的位置
    pattern = f'ad_archive_id[\\":\\s]+{ad_id}'
    match = re.search(pattern, content)
    if not match:
        continue
    
    pos = match.start()
    start = max(0, pos - 4000)
    end = min(len(content), pos + 4000)
    context = content[start:end]
    
    # 在上下文中找 video_hd_url
    video_match = re.search(r'video_hd_url[\\":\\s]+([^"\\s]+)', context)
    video_url = video_match.group(1).replace('\\/', '/') if video_match else ''
    
    # 在上下文中找 start_date
    start_date_match = re.search(r'start_date[\\":\\s]+(\d+)', context)
    start_date_ts = int(start_date_match.group(1)) if start_date_match else 0
    start_date = datetime.fromtimestamp(start_date_ts).strftime('%Y-%m-%d') if start_date_ts else ''
    
    # page_name（在前面找）
    page_name_match = re.search(r'page_name[\\":\\s]+([^"\\s]+)', context[:2000])
    page_name = page_name_match.group(1).replace('\\/', '/') if page_name_match else ''
    
    # title
    title_match = re.search(r'title[\\":\\s]+([^"\\s]+)', context)
    title = title_match.group(1).replace('\\/', '/') if title_match else ''
    
    # body text - 用原始字符串
    body_match = re.search(r'"text":"([^"\\]+)', context)
    body_text = body_match.group(1).replace('\\/', '/') if body_match else ''
    
    print(f"\n广告 ID: {ad_id}")
    print(f"  page_name: {page_name}")
    print(f"  title: {title[:50] if title else 'N/A'}")
    print(f"  body: {body_text[:50] if body_text else 'N/A'}")
    print(f"  start_date: {start_date}")
    print(f"  video: {video_url[:80] if video_url else 'N/A'}...")
    
    ads_data.append({
        'library_id': ad_id,
        'page_name': page_name,
        'title': title,
        'body_text': body_text,
        'start_date': start_date,
        'video_url': video_url,
    })

print(f"\n\n共提取 {len(ads_data)} 条广告的详细信息")

# 保存
output_file = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\ads_with_video.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({'ads': ads_data, 'total': len(ads_data)}, f, ensure_ascii=False, indent=2)
print(f"已保存到: {output_file}")
