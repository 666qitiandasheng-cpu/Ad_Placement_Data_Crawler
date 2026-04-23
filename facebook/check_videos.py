import json
import re
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114846.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 找所有视频相关字段
video_fields = re.findall(r'"(video_[^"]+)":"([^"]+)"', content)
video_fields = list(set(video_fields))

print("所有视频相关字段:")
for field, value in sorted(video_fields):
    if 'video' in field.lower():
        print(f"  {field}: {value[:60]}...")

# 检查 ad_id 为 1265526875532879 的完整视频数据
print("\n\n检查单个广告的完整视频数据:")
ad_id = '1265526875532879'
pattern = f'ad_archive_id[":\\s]+{ad_id}'
match = re.search(pattern, content)
if match:
    pos = match.start()
    start = max(0, pos - 500)
    end = min(len(content), pos + 3000)
    context = content[start:end]
    
    # 找 videos 数组
    videos_match = re.search(r'"videos":\[(.*?)\]', context, re.DOTALL)
    if videos_match:
        print(f"videos 数组: {videos_match.group(0)[:500]}...")
    
    # 列出所有视频字段
    all_video_fields = re.findall(r'"(video_[^"]+)":', context)
    print(f"\n该广告的所有视频字段: {set(all_video_fields)}")
