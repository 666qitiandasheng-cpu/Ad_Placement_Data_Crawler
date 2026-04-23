import json

with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\all_ads.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ads_list = data.get('ads', data) if isinstance(data, dict) else data
print(f'Total ads: {len(ads_list)}')
if ads_list:
    first = ads_list[0]
    print(f'First ad keys: {list(first.keys())}')
    print(f'First ad library_id: {first.get("library_id", "N/A")}')
