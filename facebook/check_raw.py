import json

# Read the daily file
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\2026-04-23.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ads = data.get('ads', [])
print(f'Total ads in daily file: {len(ads)}')

# Check first few ads
for i, ad in enumerate(ads[:3]):
    print(f"\nAd {i+1}: {ad.get('library_id')}")
    print(f"  start_date: '{ad.get('start_date')}'")
    print(f"  creative_data: {ad.get('creative_data')}")
