import json
f = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\ads_block_blast_2026-04-25.json'
with open(f, encoding='utf-8') as fh:
    data = json.load(fh)
print(f'Total ads: {len(data)}')
for a in data:
    if a.get('ad_id') == '1242102094427110':
        print(json.dumps(a, ensure_ascii=False, indent=2))
        break
else:
    print('Ad not found in top 3, searching...')
    for a in data:
        if '1242102094427110' in str(a.get('ad_id', '')):
            print(json.dumps(a, ensure_ascii=False, indent=2))
            break
