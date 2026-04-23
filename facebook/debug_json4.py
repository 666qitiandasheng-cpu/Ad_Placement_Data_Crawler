#!/usr/bin/env python3
"""调试 JSON 结构 v4"""
import re
import json

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

script_match = re.search(r'<script type="application/json"[^>]*data-content-len="\d+"[^>]*>(.*?)</script>', content, re.DOTALL)
json_str = script_match.group(1)
data = json.loads(json_str)

data_list = data['require'][0][3]
print(f"data_list 长度: {len(data_list)}")
for i, item in enumerate(data_list):
    print(f"data_list[{i}] type: {type(item)}")
    if isinstance(item, str):
        print(f"  值: {item[:100]}...")
    elif isinstance(item, dict):
        print(f"  keys: {list(item.keys())[:5]}")
        for k, v in list(item.items())[:3]:
            print(f"    {k}: {str(v)[:100]}")
    elif isinstance(item, list):
        print(f"  列表长度: {len(item)}")
        for j, sub in enumerate(item[:2]):
            print(f"    [{j}]: {type(sub)} - {str(sub)[:80]}")
