import re

# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new function
new_function = '''def parse_ads_from_page(driver):
    """从当前列表页解析所有广告（从页面嵌入的JSON数据提取）"""
    ads = []
    seen_ids = set()

    try:
        page_source = driver.page_source
        
        # Facebook 使用 "ad_archive_id" 作为广告ID字段（不是 ad_id）
        ad_ids = re.findall(r'ad_archive_id[":\s]+(\d+)', page_source)
        
        if ad_ids:
            ad_ids = list(set(ad_ids))  # 去重
            print(f"[JSON] 从页面找到 {len(ad_ids)} 个广告ID (ad_archive_id)", flush=True)
            
            for ad_id in ad_ids:
                if ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    ad = {
                        "library_id": ad_id,
                        "keyword": "",
                        "index": len(ads) + 1,
                        "platforms": ["Facebook"],
                        "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                        "ad_text": "",
                        "start_date": "",
                        "delivery_status": "",
                        "ad_disclosure_regions": [],
                        "age_range": "",
                        "gender": "",
                        "reach_count": "",
                        "advertiser_name": "",
                        "advertiser_description": "",
                        "payer_name": "",
                        "creative_data": {},
                        "raw_detail_text": "",
                    }
                    ads.append(ad)
        else:
            print("[JSON] 未找到 ad_archive_id，尝试备选方案...", flush=True)
            
            # 备选：查找较长的纯数字字符串
            long_ids = re.findall(r'\b(\d{15,18})\b', page_source)
            for ad_id in long_ids[:100]:
                if ad_id not in seen_ids and not ad_id.startswith('0'):
                    seen_ids.add(ad_id)
                    ad = {
                        "library_id": ad_id,
                        "keyword": "",
                        "index": len(ads) + 1,
                        "platforms": ["Facebook"],
                        "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                        "ad_text": "",
                        "start_date": "",
                        "delivery_status": "",
                        "ad_disclosure_regions": [],
                        "age_range": "",
                        "gender": "",
                        "reach_count": "",
                        "advertiser_name": "",
                        "advertiser_description": "",
                        "payer_name": "",
                        "creative_data": {},
                        "raw_detail_text": "",
                    }
                    ads.append(ad)
                    
    except Exception as e:
        print(f"[JSON] 提取数据失败: {e}", flush=True)

    print(f"[解析] 共找到 {len(ads)} 条广告", flush=True)
    return ads'''

# Find the start and end of the old function
# Pattern to match the function definition
pattern = r'def parse_ads_from_page\(driver\):.*?return ads\n\n# =+=' + '='*10 + r'\n# 【滚动翻页】'

# Replace
replacement = new_function + '\n\n\n# ============================================================\n# 【滚动翻页】'

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done! Function replaced.")
