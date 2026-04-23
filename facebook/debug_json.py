#!/usr/bin/env python3
"""调试 JSON 结构"""
import re
import json

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 <script> 标签
script_match = re.search(r'<script type="application/json"[^>]*data-content-len="\d+"[^>]*>(.*?)</script>', content, re.DOTALL)
if not script_match:
    print("未找到 JSON script 标签")
    exit(1)

json_str = script_match.group(1)
print(f"JSON 长度: {len(json_str)}")

try:
    data = json.loads(json_str)
    print(f"顶层 keys: {list(data.keys())}")
    print(f"require type: {type(data.get('require'))}")
    if data.get('require'):
        print(f"require 长度: {len(data['require'])}")
        if data['require']:
            print(f"require[0] type: {type(data['require'][0])}")
            if isinstance(data['require'][0], list):
                print(f"require[0] 长度: {len(data['require'][0])}")
except Exception as e:
    print(f"解析失败: {e}")
