"""
Facebook Ad Library Scraper - Part 1: List Page
================================================
抓列表页，提取 library_id + 基础字段（标题/开始日期/平台/广告文本/ advertiser_name 等）。
输出: output/<keyword>/ads_<keyword>_<date>.json

Usage:
  python scrape_list.py
  python scrape_list.py --keyword "Block Blast" --days 7
"""

import sys
import os
import json
import time
import re
import shutil
import urllib.request
import urllib.parse
import ssl
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====== CONFIG ======
# 国家代码（country 参数），对应 Facebook Ad Library 的筛选地区
# 常用代码：US=美国, GB=英国, DE=德国, FR=法国, ES=西班牙, IT=意大利, JP=日本, KR=韩国, TW=台湾, SG=新加坡
COUNTRY = "US"

KEYWORDS = ["Block Blast"]        # 搜索关键词，支持多个
AUTO_DATE = True               # 是否自动使用日期范围
DAYS_BACK = 7                  # 往前取几天，0=只限今天

MAX_SCROLLS = 1               # 列表页最大滚动次数（防止无限滚动）
WAIT_SEC = 2                   # 每次滚动后等待秒数（页面加载等待）
CHECK_BOTTOM = False            # 是否检测滚动到底部：True=滚动停滞时提前停止，False=严格按 MAX_SCROLLS 次数滚动

HEADLESS = False               # Selenium 是否无头模式（False=显示浏览器窗口）
MAX_DETAIL_SCRAPES = 0         # 最大抓详情页数量，0=不限
SCRAPE_DETAIL = False          # 是否在列表阶段直接抓详情
MAX_ADS_LIMIT = 20             # 最大收集广告数，0=无限制（达到后提前停止滚动）
# ====================

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
# 总表文件：记录所有已抓过的 library_id（去重用）
ADS_MASTER_FILE = OUTPUT_DIR / "ads_master.json"   # 每次抓取后把新id写入此文件
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}
warnings.filterwarnings('ignore')

# ---- 运行日志文件 ----
def get_log_file():
    """获取今日运行日志文件路径。"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = BASE_DIR / "logs"
    log_file = log_dir / f"scrape_list_{today}.log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_file

def log_print(msg):
    """同时打印到屏幕和写入当日日志文件。"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def get_date_range():
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    return start_date, end_date

def build_url(keyword, start_date, end_date):
    # country 参数指定广告库筛选的国家地区
    # 改国家需同步修改上方 COUNTRY 配置项
    params = {
        "active_status": "all",
        "ad_type": "all",
        "country": COUNTRY,   # ← 改国家改这里
        "is_targeted_country": "false",
        "media_type": "all",
        "q": keyword,
        "search_type": "keyword_unordered",
        "start_date": start_date,
        "end_date": end_date,
    }
    base = "https://www.facebook.com/ads/library/"
    return base + "?" + urllib.parse.urlencode(params)

def keyword_to_folder(keyword):
    return re.sub(r'[^\w]', '_', keyword.strip())

def get_output_paths(keyword, date_str):
    folder_name = keyword_to_folder(keyword)
    folder = OUTPUT_DIR / folder_name
    daily_file = folder / f"ads_{folder_name}_{date_str}.json"
    return folder, daily_file

def make_driver(headless=False, max_retries=3):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"--user-agent={HEADERS['User-Agent']}")

    for attempt in range(max_retries):
        opts = Options()  # fresh options each attempt
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"--user-agent={HEADERS['User-Agent']}")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            log_print(f"[Driver] Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                raise

def accept_cookies_if_present(driver):
    try:
        for text in ["Accept Cookies", "Accept All Cookies", "同意", "Accept"]:
            btns = driver.find_elements(By.XPATH, f"//button[contains(text(),'{text}')]")
            for btn in btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    return
    except Exception:
        pass

def find_ad_data_in_json(obj, ad_id, depth=0):
    if depth > 30:
        return None
    if isinstance(obj, dict):
        if obj.get("ad_archive_id") and str(obj.get("ad_archive_id")) == str(ad_id):
            return obj
        for v in obj.values():
            result = find_ad_data_in_json(v, ad_id, depth + 1)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_ad_data_in_json(item, ad_id, depth + 1)
            if result:
                return result
    return None

def extract_video_from_detail_html(html):
    m = re.search(r'"video_hd_url":"([^"]+)"', html)
    if m:
        return m.group(1).replace("\\/", "/")
    m = re.search(r'"video_url":"([^"]+)"', html)
    if m:
        return m.group(1).replace("\\/", "/")
    return ""

def extract_all_fields_from_html(html, ad_id):
    result = {
        'video_url': '',
        'age_range': '',
        'gender': '',
        'reach_count': '',
        'spend': '',
        'impressions': '',
        'ad_disclosure_regions': [],
        'advertiser_name': '',
        'advertiser_description': '',
        'payer_name': '',
        'about_sponsor': '',
        'body_text': '',
        'title': '',
    }
    m = re.search(r'"page_name":"((?:[^"\\]|\\.)*)"', html)
    if m:
        try:
            result['advertiser_name'] = m.group(1).encode().decode("unicode_escape")
        except:
            result['advertiser_name'] = m.group(1)
    m = re.search(r'"payer_name":"((?:[^"\\]|\\.)*)"', html)
    if m:
        try:
            result['payer_name'] = m.group(1).encode().decode("unicode_escape")
        except:
            result['payer_name'] = m.group(1)
    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for sc in scripts:
        if 'ad_archive_id' not in sc:
            continue
        try:
            data = json.loads(sc)
        except:
            continue
        ad_data = find_ad_data_in_json(data, ad_id)
        if not ad_data:
            continue
        disp = ad_data.get("disclaimer_label") or ad_data.get("disclosure_label")
        if disp:
            result['ad_disclosure_regions'] = [disp]
        imp = ad_data.get("impressions_with_index") or {}
        if isinstance(imp, dict):
            reach = imp.get("reach") or imp.get("impressions") or ""
            if isinstance(reach, int):
                result['reach_count'] = str(reach)
        about = ad_data.get("about_advertiser") or ad_data.get("page_info", {}).get("page_description") or ""
        if about:
            result['about_sponsor'] = about
        body = ad_data.get("body") or {}
        if isinstance(body, dict):
            result['body_text'] = body.get("text", "")
        elif isinstance(body, str):
            result['body_text'] = body
        m = re.search(r'<h2[^>]*>([^<]+)</h2>', html)
        if m:
            result['title'] = m.group(1).strip()
    if not result['ad_disclosure_regions']:
        m = re.search(r'"disclaimer_label":"([^"]+)"', html)
        if m:
            result['ad_disclosure_regions'] = [m.group(1)]
    m = re.search(r'"spend":\s*\{[^}]*?"min":\s*(\d+)[^}]*?"max":\s*(\d+)', html)
    if m:
        result['spend'] = f"{m.group(1)}-{m.group(2)}"
    m = re.search(r'"impressions":\s*\{[^}]*?"min":\s*(\d+)[^}]*?"max":\s*(\d+)', html)
    if m:
        result['impressions'] = f"{m.group(1)}-{m.group(2)}"
    return result

def parse_ads_from_page(driver):
    """Parse ads from the current page HTML."""
    ads = []
    try:
        html = driver.page_source.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except Exception:
        return ads
    library_ids = re.findall(r'"ad_archive_id"\s*:\s*"?(\d+)"?', html)
    seen = set()
    for lid in library_ids:
        if lid in seen:
            continue
        seen.add(lid)
        ad = {
            "library_id": lid,
            "detail_url": f"https://www.facebook.com/ads/library/?id={lid}",
        }
        # Try to extract fields from page HTML
        try:
            fields = extract_all_fields_from_html(html, lid)
            for k, v in fields.items():
                if v and v != []:
                    ad[k] = v
        except Exception:
            pass
        # Also try JSON-LD
        try:
            json_patterns = [
                rf'"ad_archive_id"\s*:\s*"?{lid}"[^{{]*({{[^}}]+}})',
            ]
        except Exception:
            pass
        if ad.get("library_id"):
            ads.append(ad)
    return ads

from selenium.webdriver.common.by import By

def download_videos(ads, video_dir, keyword):
    video_dir.mkdir(parents=True, exist_ok=True)
    existing = {f.stem for f in video_dir.glob("*.mp4")}
    # video_url 字段直接存在于 ad 对象中（parse_ads_from_page 提取的）
    to_download = [a for a in ads if a['library_id'] not in existing
                   and str(a.get('video_url', '')).startswith('http')]
    if not to_download:
        log_print(f"[Video] 没有新视频要下载 ({video_dir.name})")
        return
    log_print(f"[Video] 开始下载 {len(to_download)} 个视频到 {video_dir}")

    def download_one(ad):
        video_url = ad.get('video_url', '')
        if not video_url:
            return False
        fname = video_dir / (ad['library_id'] + ".mp4")
        try:
            req = urllib.request.Request(video_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(fname, 'wb') as f:
                    shutil.copyfileobj(resp, f, length=1024*1024)
            log_print(f"  [Video] 保存成功: {ad['library_id']}")
            return True
        except Exception as e:
            log_print(f"  [Video] 下载失败 {ad['library_id']}: {e}")
            return False

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(download_one, ad): ad for ad in to_download}
        for future in as_completed(futures):
            future.result()  # raise any exceptions

def scroll_and_collect(driver, url, keyword, max_scrolls, wait_sec, max_ads=0):
    from selenium.webdriver.common.by import By
    driver.get(url)
    log_print(f"[Browser] 打开页面: {url}")
    time.sleep(3)
    accept_cookies_if_present(driver)
    time.sleep(2)
    all_ads = []
    last_height = 0
    log_print(f"[Scroll] 开始滚动 | 最大次数={max_scrolls} | 等待={wait_sec}秒 | 最大广告数={max_ads if max_ads else '不限'}")
    for scroll in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)
        ads = parse_ads_from_page(driver)
        for ad in ads:
            if ad not in all_ads:
                all_ads.append(ad)
        if max_ads > 0 and len(all_ads) >= max_ads:
            log_print(f"  Reached max_ads={max_ads}, stopping early")
            break
        # 检测是否已滚动到底部（页面高度不再变化）
        if CHECK_BOTTOM:
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    log_print(f"  [Bottom] 页面已到底，停止滚动（第 {scroll+1} 次）")
                    break
            last_height = new_height
        log_print(f"  Scroll {scroll+1}/{max_scrolls}: {len(all_ads)} ads collected")
    log_print(f"[Scroll] 滚动结束，共收集到 {len(all_ads)} 条广告")
    return all_ads

def load_json_file(path):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"ads": []}


def load_master_ids():
    """加载总表，返回已知的 library_id 集合。"""
    if ADS_MASTER_FILE.exists():
        try:
            data = json.load(open(ADS_MASTER_FILE, 'r', encoding='utf-8'))
            return set(data.get('library_ids', []))
        except Exception:
            pass
    return set()


def save_master_ids(new_ids):
    """把新的 library_id 追加到总表。"""
    existing = load_master_ids()
    merged = existing | new_ids
    master_data = {
        "last_updated": datetime.now().isoformat(),
        "library_ids": sorted(list(merged)),
        "total_count": len(merged),
    }
    ADS_MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ADS_MASTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    return len(new_ids)


def scrape_keyword(keyword):
    start_date, end_date = get_date_range()
    folder, daily_file = get_output_paths(keyword, end_date)
    folder.mkdir(parents=True, exist_ok=True)

    log_print(f"========== 开始抓取: {keyword} | 日期: {start_date}~{end_date} | 地区: {COUNTRY} ==========")

    # ---- 加载总表 ----
    master_ids = load_master_ids()
    log_print(f"[Master] 已有 {len(master_ids)} 个 library_id")

    # ---- 读取今日文件，把已存在于总表的删掉 ----
    existing_data = load_json_file(daily_file)
    existing_ads = existing_data.get('ads', [])

    # 过滤：只保留 library_id 不在总表里的
    new_ads = [ad for ad in existing_ads if ad['library_id'] not in master_ids]
    removed_count = len(existing_ads) - len(new_ads)
    if removed_count > 0:
        log_print(f"[Dedup] 今日文件中已有 {removed_count} 条在总表，去掉这些")

    log_print(f"[Load] 今日文件原有 {len(existing_ads)} 条，去重后剩 {len(new_ads)} 条")

    scrape_url = build_url(keyword, start_date, end_date)
    log_print(f"[URL] {scrape_url}")

    driver = make_driver(headless=HEADLESS)
    try:
        ads = scroll_and_collect(driver, scrape_url, keyword, MAX_SCROLLS, WAIT_SEC, MAX_ADS_LIMIT)
        log_print(f"[List] 本次滚动抓到 {len(ads)} 条（未去重）")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # ---- 去重：去掉总表已有的 ----
    ads_to_save = [ad for ad in ads if ad['library_id'] not in master_ids]
    duplicate_count = len(ads) - len(ads_to_save)
    log_print(f"[Dedup] 去除重复 {duplicate_count} 条，剩 {len(ads_to_save)} 条新广告")

    # ---- 合并到今日文件（只加新的） ----
    existing_map = {ad['library_id']: ad for ad in new_ads}   # new_ads 里没有总表存在的id
    for ad in ads_to_save:
        existing_map[ad['library_id']] = ad

    all_ads = list(existing_map.values())
    result_data = {
        "keyword": keyword,
        "date_range": f"{start_date}~{end_date}",
        "last_updated": datetime.now().isoformat(),
        "ads": all_ads,
    }

    daily_file.parent.mkdir(parents=True, exist_ok=True)
    with open(daily_file, 'w', encoding='utf-8') as fp:
        json.dump(result_data, fp, ensure_ascii=False, indent=2)

    # ---- 追加到总表 ----
    new_ids = {ad['library_id'] for ad in ads_to_save}
    if new_ids:
        saved_count = save_master_ids(new_ids)
        log_print(f"[Master] 写入 {saved_count} 个新 library_id")
    else:
        log_print("[Master] 没有新增，不写入")

    log_print(f"[Saved] {daily_file} | 今日文件共 {len(all_ads)} 条 | 本次新增 {len(ads_to_save)} 条")

    video_dir = folder / "videos"
    log_print(f"[Video] Checking videos for {keyword}...")
    download_videos(new_ads, video_dir, keyword)

    return new_ads

def main():
    for i, keyword in enumerate(KEYWORDS, 1):
        log_print(f"========== 处理关键词 {i}/{len(KEYWORDS)}: {keyword} ==========")
        scrape_keyword(keyword)
    log_print("所有关键词处理完毕")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Ad Library - List Scraper")
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--days", type=int, default=DAYS_BACK)
    parser.add_argument("--max-ads", type=int, default=0, help="Stop after collecting N ads (0=no limit)")
    args = parser.parse_args()
    if args.keyword:
        KEYWORDS.clear()
        KEYWORDS.append(args.keyword)
    if args.days:
        DAYS_BACK = args.days
    if args.max_ads:
        MAX_ADS_LIMIT = args.max_ads
    main()
