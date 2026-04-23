"""
更新 run.py - 添加视频URL和开始日期提取，以及视频下载功能
"""
import re

# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替换 parse_ads_from_page 函数，添加视频URL和开始日期提取
old_parse = '''def parse_ads_from_page(driver):
    """从当前列表页解析所有广告（从页面嵌入的JSON数据提取）"""
    ads = []
    seen_ids = set()

    try:
        page_source = driver.page_source
        
        # Facebook 使用 ad_archive_id 作为广告ID
        ad_ids = re.findall(r'ad_archive_id[":\\s]+(\d+)', page_source)
        
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

new_parse = '''def parse_ads_from_page(driver):
    """从当前列表页解析所有广告（从页面嵌入的JSON数据提取）"""
    ads = []
    seen_ids = set()

    try:
        page_source = driver.page_source
        
        # Facebook 使用 ad_archive_id 作为广告ID
        ad_ids = re.findall(r'ad_archive_id[":\\s]+(\d+)', page_source)
        
        if ad_ids:
            ad_ids = list(set(ad_ids))  # 去重
            print(f"[JSON] 从页面找到 {len(ad_ids)} 个广告ID (ad_archive_id)", flush=True)
            
            for ad_id in ad_ids:
                if ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    
                    # 提取该广告的详细信息（视频URL、开始日期等）
                    video_url, start_date = extract_ad_details(page_source, ad_id)
                    
                    ad = {
                        "library_id": ad_id,
                        "keyword": "",
                        "index": len(ads) + 1,
                        "platforms": ["Facebook"],
                        "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                        "ad_text": "",
                        "start_date": start_date,
                        "delivery_status": "",
                        "ad_disclosure_regions": [],
                        "age_range": "",
                        "gender": "",
                        "reach_count": "",
                        "advertiser_name": "",
                        "advertiser_description": "",
                        "payer_name": "",
                        "creative_data": {"video_url": video_url},
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
                    video_url, start_date = extract_ad_details(page_source, ad_id)
                    ad = {
                        "library_id": ad_id,
                        "keyword": "",
                        "index": len(ads) + 1,
                        "platforms": ["Facebook"],
                        "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                        "ad_text": "",
                        "start_date": start_date,
                        "delivery_status": "",
                        "ad_disclosure_regions": [],
                        "age_range": "",
                        "gender": "",
                        "reach_count": "",
                        "advertiser_name": "",
                        "advertiser_description": "",
                        "payer_name": "",
                        "creative_data": {"video_url": video_url},
                        "raw_detail_text": "",
                    }
                    ads.append(ad)
                    
    except Exception as e:
        print(f"[JSON] 提取数据失败: {e}", flush=True)

    print(f"[解析] 共找到 {len(ads)} 条广告", flush=True)
    return ads


def extract_ad_details(page_source, ad_id):
    """从页面源码中提取指定广告的详细信息（视频URL、开始日期）"""
    from datetime import datetime
    
    # 找到该 ad_id 在源码中的位置
    pattern = f'ad_archive_id[\\":\\s]+{ad_id}'
    match = re.search(pattern, page_source)
    if not match:
        return '', ''
    
    pos = match.start()
    # 提取周围 5000 字符的上下文
    start = max(0, pos - 3000)
    end = min(len(page_source), pos + 5000)
    context = page_source[start:end]
    
    # 找 video_hd_url
    video_url = ''
    video_match = re.search(r'video_hd_url[\\":\\s]+([^"\\s,}]+)', context)
    if video_match:
        video_url = video_match.group(1).replace('\\/', '/')
    
    # 找 start_date（Unix 时间戳）
    start_date = ''
    start_date_match = re.search(r'start_date[\\":\\s]+(\d+)', context)
    if start_date_match:
        ts = int(start_date_match.group(1))
        try:
            start_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            pass
    
    return video_url, start_date'''

content = content.replace(old_parse, new_parse)

# 2. 添加视频下载函数（在 download_videos 函数之前）
old_download = '''def download_videos(ads, output_dir):
    """下载视频（仅针对 new_ads 中不重复的广告）"""
    video_dir = output_dir / "videos"
    video_dir.mkdir(exist_ok=True)

    # 已有视频
    existing = {f.stem for f in video_dir.glob("*.mp4")}
    new_ads = [a for a in ads if a["library_id"] not in existing]
    print(f"[视频] 已有 {len(existing)} 个视频，本次跳过 {len(ads) - len(new_ads)} 个")

    if not new_ads:
        return

    for ad in new_ads:
        video_url = ad.get("creative_data", {}).get("video_url", "")
        if not video_url:
            continue

        library_id = ad["library_id"]
        filepath = video_dir / f"{library_id}.mp4"

        try:
            req = urllib.request.Request(video_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(filepath, "wb") as f:
                    shutil.copyfileobj(response, f)
            print(f"[视频] 已下载: {library_id}.mp4")
        except Exception as e:
            print(f"[视频] 下载失败 [{library_id}]: {e}")

    print(f"[视频] 视频总数: {len(list(video_dir.glob('*.mp4')))}")'''

new_download = '''def download_videos(ads, output_dir):
    """下载视频（仅针对 new_ads 中不重复的广告）"""
    video_dir = output_dir / "videos"
    video_dir.mkdir(exist_ok=True)

    # 已有视频
    existing = {f.stem for f in video_dir.glob("*.mp4")}
    new_ads = [a for a in ads if a["library_id"] not in existing]
    print(f"[视频] 已有 {len(existing)} 个视频，本次跳过 {len(ads) - len(new_ads)} 个")

    if not new_ads:
        print(f"[视频] 没有新视频需要下载")
        return

    for ad in new_ads:
        video_url = ad.get("creative_data", {}).get("video_url", "")
        if not video_url:
            continue

        library_id = ad["library_id"]
        filepath = video_dir / f"{library_id}.mp4"

        try:
            print(f"[视频] 正在下载: {library_id}.mp4", flush=True)
            req = urllib.request.Request(video_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(filepath, "wb") as f:
                    shutil.copyfileobj(response, f)
            print(f"[视频] 已下载: {library_id}.mp4", flush=True)
        except Exception as e:
            print(f"[视频] 下载失败 [{library_id}]: {e}")

    print(f"[视频] 视频总数: {len(list(video_dir.glob('*.mp4')))}")'''

content = content.replace(old_download, new_download)

# 写回
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! run.py 已更新")
