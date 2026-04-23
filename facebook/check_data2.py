import json

with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\all_ads.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ads = data.get('ads', [])
print(f'Total ads: {len(ads)}')
if ads:
    first = ads[0]
    print(f'\nFirst ad:')
    print(f'  library_id: {first.get("library_id")}')
    print(f'  start_date: {first.get("start_date")}')
    print(f'  video_url: {first.get("creative_data", {}).get("video_url", "")[:80] if first.get("creative_data", {}).get("video_url") else "N/A"}...')
    
    # Count ads with video
    with_video = sum(1 for a in ads if a.get('creative_data', {}).get('video_url'))
    with_date = sum(1 for a in ads if a.get('start_date'))
    print(f'\nAds with video_url: {with_video}/{len(ads)}')
    print(f'Ads with start_date: {with_date}/{len(ads)}')
