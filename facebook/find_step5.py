with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find the dialog text section
idx = content.find('# Step 5: Get')
if idx < 0:
    idx = content.find('Get full text via JS')
print(f'Step 5 at: {idx}')
print(repr(content[idx:idx+200]))