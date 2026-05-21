import json
from pathlib import Path

output = Path(__file__).parent / 'output'

# Check what's in the old 05-07 file for comparison
old = output / 'ads_2026-05-07.json'
if old.exists():
    d = json.load(open(old, encoding='utf-8'))
    ads = d.get('ads', [])
    v = sum(1 for a in ads if a.get('video_url'))
    print(f"ads_2026-05-07: {len(ads)} ads, {v} with video_url")
    if ads:
        print(f"  Keys: {list(ads[0].keys())}")
        print(f"  Sample: {ads[0].get('library_id')} video={bool(ads[0].get('video_url'))}")
else:
    print("ads_2026-05-07.json not found")
