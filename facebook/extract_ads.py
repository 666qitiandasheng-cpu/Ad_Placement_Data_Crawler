#!/usr/bin/env python3
"""
从 Facebook Ad Library 页面源码提取完整广告数据
"""
import re
import json
from datetime import datetime

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_112541.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 <script type="application/json" data-content-len="..."> 标签
script_match = re.search(r'<script type="application/json"[^>]*data-content-len="\d+"[^>]*>(.*?)</script>', content, re.DOTALL)
if not script_match:
    print("未找到 JSON script 标签")
    exit(1)

json_str = script_match.group(1)
print(f"JSON 字符串长度: {len(json_str)}")

# 解析 JSON
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"JSON 解析失败: {e}")
    exit(1)

# 导航到广告数据
# require[0][1] -> __bbox -> require[0][1] -> result -> data -> ad_library_main -> search_results_connection
try:
    bbox = data['require'][0][1]['__bbox']
    result = bbox['result']
    ad_data = result['data']['ad_library_main']['search_results_connection']
    count = ad_data['count']
    edges = ad_data['edges']
    print(f"总广告数: {count}, 边数: {len(edges)}")
    
    ads = []
    for edge in edges:
        nodes = edge['node']['collated_results']
        for node in nodes:
            ad_archive_id = node.get('ad_archive_id', '')
            snapshot = node.get('snapshot', {})
            
            # 提取基本信息
            page_name = snapshot.get('page_name', '')
            page_like_count = snapshot.get('page_like_count', '')
            body_text = snapshot.get('body', {}).get('text', '')
            title = snapshot.get('title', '')
            caption = snapshot.get('caption', '')
            cta_text = snapshot.get('cta_text', '')
            display_format = snapshot.get('display_format', '')
            link_url = snapshot.get('link_url', '')
            page_profile_uri = snapshot.get('page_profile_uri', '')
            
            # 时间（Unix 时间戳）
            start_date_ts = snapshot.get('start_date', 0)
            end_date_ts = snapshot.get('end_date', 0)
            start_date = datetime.fromtimestamp(start_date_ts).strftime('%Y-%m-%d') if start_date_ts else ''
            end_date = datetime.fromtimestamp(end_date_ts).strftime('%Y-%m-%d') if end_date_ts else ''
            
            # 视频
            videos = snapshot.get('videos', [])
            video_url = videos[0].get('video_hd_url', '') if videos else ''
            
            # 平台
            publisher_platforms = snapshot.get('publisher_platform', [])
            
            ad_info = {
                'library_id': ad_archive_id,
                'page_name': page_name,
                'page_like_count': page_like_count,
                'body_text': body_text,
                'title': title,
                'caption': caption,
                'cta_text': cta_text,
                'display_format': display_format,
                'link_url': link_url,
                'page_profile_uri': page_profile_uri,
                'start_date': start_date,
                'end_date': end_date,
                'video_url': video_url,
                'publisher_platforms': publisher_platforms,
            }
            ads.append(ad_info)
            
            print(f"\n广告 ID: {ad_archive_id}")
            print(f"  页面: {page_name}")
            print(f"  标题: {title[:50] if title else 'N/A'}...")
            print(f"  正文: {body_text[:50] if body_text else 'N/A'}...")
            print(f"  格式: {display_format}")
            print(f"  链接: {link_url[:80] if link_url else 'N/A'}...")
            print(f"  投放开始: {start_date}")
            print(f"  投放结束: {end_date}")
            print(f"  视频: {video_url[:80] if video_url else 'N/A'}...")
            print(f"  平台: {publisher_platforms}")
            
    print(f"\n\n共提取 {len(ads)} 条广告")
    
    # 保存到文件
    output_file = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\output\block_blast\extracted_ads.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'ads': ads, 'total': len(ads)}, f, ensure_ascii=False, indent=2)
    print(f"已保存到: {output_file}")
    
except Exception as e:
    print(f"提取数据时出错: {e}")
    import traceback
    traceback.print_exc()
