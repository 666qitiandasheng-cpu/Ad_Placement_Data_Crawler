#!/usr/bin/env python3
"""调试 JSON 结构 v2"""
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

# 检查 require[0] 结构
req = data['require'][0]
print(f"require[0] 元素类型: {[type(x) for x in req]}")

# 找到包含 __bbox 的元素
for i, item in enumerate(req):
    if isinstance(item, dict):
        if '__bbox' in item:
            print(f"__bbox 在 require[0][{i}]")
            bbox = item['__bbox']
            print(f"  __bbox keys: {list(bbox.keys())}")
            
            # 尝试导航
            result = bbox.get('result', {})
            print(f"  result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            
            data2 = result.get('data', {})
            print(f"  data keys: {list(data2.keys()) if isinstance(data2, dict) else type(data2)}")
            
            ad_lib = data2.get('ad_library_main', {})
            print(f"  ad_library_main keys: {list(ad_lib.keys()) if isinstance(ad_lib, dict) else type(ad_lib)}")
            
            src = ad_lib.get('search_results_connection', {})
            print(f"  search_results_connection keys: {list(src.keys()) if isinstance(src, dict) else type(src)}")
            
            count = src.get('count', 0)
            edges = src.get('edges', [])
            print(f"  count: {count}, edges: {len(edges)}")
            break
    elif isinstance(item, list):
        print(f"require[0][{i}] 是列表，长度: {len(item)}")
        for j, subitem in enumerate(item[:3]):
            if isinstance(subitem, dict):
                print(f"  [{j}] keys: {list(subitem.keys())[:5]}")
