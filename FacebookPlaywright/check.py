import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('output/detail_ads_2026-05-11.json', encoding='utf-8'))
rec = d.get('857760736582462', {})
for k, v in rec.items():
    if k in ('reach_count', 'region_targeting', 'age_range', 'gender', 'advertiser_name'):
        print(f'{k}: {v}')
