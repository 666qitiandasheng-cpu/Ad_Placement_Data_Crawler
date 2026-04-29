import json, sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_ads_Block_Blast_2026-04-29.json','r',encoding='utf-8') as f:
    d = json.load(f)
print(f'Total ads: {len(d)}')
for lid, v in list(d.items())[:5]:
    adv = v.get('advertiser_name', '?')
    payer = v.get('payer_name', '?')
    print(f'  {lid}: advertiser={adv[:25]} payer={payer[:25]}')
