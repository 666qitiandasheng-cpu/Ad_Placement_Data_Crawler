with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find the payer block section
idx = src.find('pblock.find')
print('pblock.find idx:', idx)
if idx >= 0:
    print('Context:', repr(src[idx-50:idx+300]))