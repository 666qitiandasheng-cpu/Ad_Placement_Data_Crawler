with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

idx = content.find('def _scrape_detail_page_cdp')
if idx < 0:
    idx = content.find('def _scrape_detail_page')

with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\func_start.txt', 'w', encoding='utf-8') as f:
    f.write(f'Function index: {idx}\n')
    if idx >= 0:
        f.write(content[idx:idx+80])
