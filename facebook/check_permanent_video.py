#!/usr/bin/env python3
"""
检查 Facebook Ad JSON 中的视频字段，找出是否有永久URL
"""
import re
import json

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114846.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 JSON script 标签
script_match = re.search(r'<script type="application/json"[^>]*data-content-len="\d+"[^>]*>(.*?)</script>', content, re.DOTALL)
if script_match:
    json_str = script_match.group(1)
    try:
        data = json.loads(json_str)
        
        # 遍历所有 keys 找视频相关字段
        def find_video_fields(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if 'video' in k.lower() or 'media' in k.lower():
                        print(f"{path}.{k}: {str(v)[:80]}...")
                    find_video_fields(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:2]):  # 只看前2个
                    find_video_fields(item, f"{path}[{i}]")
        
        find_video_fields(data)
        
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
else:
    print("未找到 JSON script")
