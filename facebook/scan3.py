# Inspect the actual source
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Show the payer section
for i in range(469, 485):
    print(f'{i+1}: {repr(lines[i])}')