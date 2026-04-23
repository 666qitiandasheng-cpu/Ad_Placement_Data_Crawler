import json
import os

daily_file = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\2026-04-23.json'

with open(daily_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

ads = data.get('ads', [])
print(f"每日文件广告数: {len(ads)}")

# Check first ad's structure
if ads:
    first = ads[0]
    print(f"\n第一条广告字段:")
    for k, v in first.items():
        if isinstance(v, dict):
            print(f"  {k}: dict with keys {list(v.keys())}")
        elif isinstance(v, list):
            print(f"  {k}: list with {len(v)} items")
        elif isinstance(v, str) and len(v) > 100:
            print(f"  {k}: '{v[:80]}...'")
        else:
            print(f"  {k}: {v}")

# Check downloaded videos
video_dir = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\videos_blockblast'
video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
print(f"\n已下载视频数: {len(video_files)}")
