with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    src = f.read()

idx = src.find('pblock.find')
lines = src.split('\n')
for i, line in enumerate(lines):
    if 'pblock.find' in line:
        for j in range(max(0,i-5), min(len(lines), i+5)):
            print(f'{j+1}: {repr(lines[j])}')
        break