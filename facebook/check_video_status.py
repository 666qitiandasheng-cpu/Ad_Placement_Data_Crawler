import json
import os

# Check daily file
daily_file = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\2026-04-23.json'
video_dir = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\videos_blockblast'

with open(daily_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

ads = data.get('ads', [])
print(f"每日文件中的广告数: {len(ads)}")

# Count ads with video_url
ads_with_video = [a for a in ads if a.get('creative_data', {}).get('video_url')]
print(f"有 video_url 的广告: {len(ads_with_video)}")

# Count downloaded videos
video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
print(f"已下载的视频数: {len(video_files)}")

# Show first 3 ads with video info
print("\n前3条广告详情:")
for ad in ads[:3]:
    lib_id = ad.get('library_id')
    video_url = ad.get('creative_data', {}).get('video_url', '')
    video_file = f"{lib_id}.mp4"
    downloaded = video_file in video_files
    print(f"  {lib_id}:")
    print(f"    video_url: {video_url[:60]}..." if video_url else f"    video_url: (empty)")
    print(f"    本地文件: {'✓' if downloaded else '✗'} {video_file}")
