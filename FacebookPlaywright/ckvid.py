import json
from pathlib import Path

base = Path(__file__).parent
master = json.load(open(base / 'output' / 'ads_master.json', encoding='utf-8'))
print(f"Master total: {master.get('total_count')}")
print(f"Sample IDs: {list(master.get('library_ids', []))[:5]}")

d = json.load(open(base / 'output' / 'ads_2026-05-08.json', encoding='utf-8'))
ads = d.get('ads', [])
with_vid = [a for a in ads if a.get('video_url')]
print(f"\nDaily file ads: {len(ads)}")
print(f"With video_url: {len(with_vid)}")
print(f"Without video_url: {len(ads) - len(with_vid)}")
print(f"\nAll ad keys: {list(ads[0].keys())}")
