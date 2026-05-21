import json
f = 'output/detail_ads_2026-05-11.json'
d = json.load(open(f, encoding='utf-8'))
keys = list(d.keys())
print(keys)
if '857760736582462' in d:
    del d['857760736582462']
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('deleted 857760736582462')
else:
    print('not found')
