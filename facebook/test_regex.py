import re

with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Test different patterns
patterns = [
    r'ad_archive_id[":\s]+(\d+)',  # 当前代码使用的
    r'ad_archive_id[=:\s"]+(\d+)',  # 带=的版本
    r'ad_archive_id":"(\d+)',  # 简单精确匹配
]

for p in patterns:
    matches = re.findall(p, content)
    print(f'Pattern: {p!r}')
    print(f'  Found: {len(matches)} matches')
    if matches:
        print(f'  First 3: {matches[:3]}')
    print()
