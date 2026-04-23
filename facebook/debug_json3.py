#!/usr/bin/env python3
"""调试 JSON 结构 v3"""
import re
import json

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

script_match = re.search(r'<script type="application/json"[^>]*data-content-len="\d+"[^>]*>(.*?)</script>', content, re.DOTALL)
if not script_match:
    print("未找到 JSON script 标签")
    exit(1)

json_str = script_match.group(1)
data = json.loads(json_str)

# require[0] = [name, null, null, data_list]
data_list = data['require'][0][3]
print(f"data_list 长度: {len(data_list)}")
print(f"data_list[0] type: {type(data_list[0])}")
print(f"data_list[0] keys: {list(data_list[0].keys()) if isinstance(data_list[0], dict) else 'N/A'}")

# 检查 data_list[0]
item0 = data_list[0]
if isinstance(item0, dict):
    # 找 __bbox
    for key, val in item0.items():
        if '__bbox' in str(key):
            print(f"Key containing __bbox: {key}")
        if isinstance(val, dict) and 'result' in val:
            print(f"Found result in: {key}")
            result = val['result']
            if isinstance(result, dict):
                print(f"  result keys: {list(result.keys())[:10]}")
                data2 = result.get('data', {})
                if isinstance(data2, dict):
                    print(f"  data keys: {list(data2.keys())}")
