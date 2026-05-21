"""
TikTok Ad Library 详情页抓取 + 视频下载
==================================== TiktokPlaywright_detail.py

【功能】
  读取 TiktokPlaywright_list.py 输出的 ads_<date>.json，
  逐个广告访问详情页，提取：
    - 视频 URL（通过 Playwright 浏览器 session 下载，规避 403）
    - 全部详细信息（20+ 字段）
  结果写入每日 JSON（断点续抓，已抓跳过）

【输入】
  - output/ads_<date>.json   <- TiktokPlaywright_list.py 产出

【输出】
  - ads_<date>.json           <- 更新后（含 tiktok_detail + video_urls）
  - ads_all.json              <- 同步更新汇总文件
  - output/videos/            <- 视频文件

【断点续抓】
  - 已有的 library_id 直接跳过
  - 已下载的视频跳过

【每日 JSON 字段对照】（与原始 TiktokPlaywright.py 一致）
  ad_id / detail_url / scrape_time
  advertiser_name / advertiser_description / ad_text
  first_seen / last_seen / delivery_status / active_ad_delivery
  target_audience_size / gender_summary / age_summary
  gender_detail / age_detail / locations / locations_detail
  language / unique_users / impressions
  video_url / thumbnail_url / raw_text
  advertiser_registered_location / payer_name

【用法】
  python TiktokPlaywright_detail.py
  python TiktokPlaywright_detail.py --date 2026-05-14
"""

import sys
import os
import json
import time
import re
import ssl
import warnings
import random
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ============================================================
#                    【配置区】
# ============================================================

TARGET_DATE = ""
HEADLESS = False
DETAIL_WAIT = 5
RESUME_ENABLED = True
ZERO_RESULT_THRESHOLD = 3
BACKOFF_BASE_SEC = 30
MAX_DETAIL_WORKERS = 2
DETAIL_BATCH = 5

# ============================================================

warnings.filterwarnings('ignore', category=DeprecationWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# ============================================================
# 【固定路径】
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR = OUTPUT_DIR / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 【工具函数】
# ============================================================

def get_today_date_str():
    return datetime.now().strftime('%Y-%m-%d')


def load_json(filepath):
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_ads_detail(ads_list, new_details):
    """将详情数据合并到广告列表，依据 library_id 匹配"""
    detail_map = {}
    for detail in new_details:
        lid = detail.get("ad_id") or detail.get("library_id")
        if lid:
            detail_map[str(lid)] = detail

    updated = 0
    for ad in ads_list:
        lid = str(ad.get("library_id") or ad.get("ad_id") or "")
        if lid in detail_map:
            # 已有 tiktok_detail 且 video_url 非空，认为已完成，跳过更新（保留原数据）
            existing = ad.get("tiktok_detail", {})
            if existing and existing.get("video_url"):
                continue
            ad["tiktok_detail"] = detail_map[lid]
            # 同步 video_url 到顶层（兼容下载判断）
            dv = detail_map[lid].get("video_url", "")
            if dv:
                ad["video_urls"] = [dv]
            updated += 1

    return updated


# ============================================================
# 【浏览器实例管理】
# ============================================================

def make_browser_context(headless=True):
    p = sync_playwright().start()
    width = random.choice([1920, 1366, 1536, 1600, 1440])
    height = random.choice([1080, 768, 864, 900, 810])

    browser = p.chromium.launch(
        headless=headless,
        args=[
            '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
            '--disable-extensions', '--disable-notifications', '--disable-popup-blocking',
            f'--window-size={width},{height}',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
            '--ssl-protocol=TLSv1.2', '--ignore-certificate-errors',
            '--allow-running-insecure-content',
            '--disable-blink-features=AutomationControlled',
            '--disable-blink-features=IsRunningOnGpuBridge',
            '--disable-ipc-flooding-protection',
        ]
    )

    context = browser.new_context(
        viewport={'width': width, 'height': height},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
        locale='en-US',
        timezone_id='Asia/Shanghai',
        ignore_https_errors=True,
    )

    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = window.chrome || {};
        try { Object.defineProperty(window.chrome, 'runtime', { get: () => ({ onInstalled: {}, onConnect: {}, loaded: true }) }); } catch(e) {}
        const fakePlugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', version: '1.0' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format', version: '1.0' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', version: '1.0' },
        ];
        Object.defineProperty(navigator, 'plugins', { get: () => fakePlugins });
        const realLangs = navigator.languages;
        if (!realLangs || realLangs.length === 0) { Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'zh-CN', 'zh'] }); }
        const originalQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
        if (originalQuery) {
            window.navigator.permissions.query = (parameters) =>
                (parameters.name === 'notifications' || parameters.name === 'push' || parameters.name === 'midi')
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
        }
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.selenuim;
        delete window.webdriver;
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        try { Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 }); } catch(e) {}
    """)

    page = context.new_page()
    page.add_init_script("""
        try { const el = document.createElement('meta'); el.name = 'robots'; el.content = 'noindex, nofollow'; document.head.appendChild(el); } catch(e) {}
    """)

    print(f"[浏览器] Playwright Chromium 已启动 ({width}x{height})", flush=True)
    return p, browser, context, page


def close_browser(p, browser):
    try:
        browser.close()
    except Exception:
        pass
    try:
        p.stop()
    except Exception:
        pass


# ============================================================
# 【详情页抓取 + 视频下载】
# ============================================================

def scrape_detail_page(page, ad_id, wait_sec):
    """
    访问 TikTok 广告详情页，提取完整字段。
    同时从 <video> 标签提取视频 URL。
    """
    detail_url = f"https://library.tiktok.com/ads/detail/?ad_id={ad_id}"
    data = {
        "ad_id": ad_id,
        "detail_url": detail_url,
        "scrape_time": datetime.now().isoformat(),
        "advertiser_name": "",
        "advertiser_description": "",
        "ad_text": "",
        "payer_name": "",
        "advertiser_registered_location": "",
        "first_seen": "",
        "last_seen": "",
        "delivery_status": "",
        "active_ad_delivery": "",
        "target_audience_size": "",
        "gender_summary": "",
        "age_summary": "",
        "gender_detail": {},
        "age_detail": {},
        "locations": [],
        "locations_detail": {},
        "language": "",
        "unique_users": "",
        "impressions": "",
        "video_url": "",
        "thumbnail_url": "",
        "raw_text": "",
    }

    try:
        time.sleep(random.uniform(2, 8))
        page.goto(detail_url)
        page.wait_for_timeout(wait_sec * 1000)

        html = page.content()
        full_text = page.locator("body").text_content() or ""
        data["raw_text"] = full_text
        soup = BeautifulSoup(html, "html.parser")

        # ---- 广告文本 ----
        lines = full_text.split('\n')
        in_sponsored = False
        sponsored_parts = []
        skip_keys = {'advertiser', 'active', 'delivery', 'status', 'seen', 'gender',
                     'age', 'location', 'language', 'unique', 'impression', 'first',
                     'last', 'meta', 'tiktok', 'learn more', 'see more', 'additional',
                     'audience', 'number', 'country', 'target'}
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 3:
                continue
            if 'sponsor' in stripped.lower():
                in_sponsored = True
                continue
            if in_sponsored:
                if stripped.lower() in skip_keys or any(k in stripped.lower() for k in skip_keys):
                    continue
                if len(stripped) > 5:
                    sponsored_parts.append(stripped)
        if sponsored_parts:
            data["ad_text"] = ' '.join(sponsored_parts)[:800]

        # ---- 公司名 ----
        advertiser_m = re.search(r'Advertiser([^S]+?)\s*See all', full_text)
        if advertiser_m:
            data["advertiser_name"] = advertiser_m.group(1).strip()
        else:
            advertiser_m2 = re.search(r'Ad paid for by\s+([A-Z][^\n]+?)\s+Advertiser', full_text)
            if advertiser_m2:
                data["advertiser_name"] = advertiser_m2.group(1).strip()

        # ---- 付费方 ----
        payer_m = re.search(r'Ad paid for by(.+?)\s*Advertiser', full_text)
        if payer_m:
            data["payer_name"] = payer_m.group(1).strip()
        else:
            payer_m2 = re.search(r'Ad paid for by([^\n]+)', full_text)
            if payer_m2:
                data["payer_name"] = payer_m2.group(1).strip()[:200]

        # ---- 注册地 ----
        loc_m = re.search(r"registered location\s*([A-Za-z]+)", full_text)
        if loc_m:
            data["advertiser_registered_location"] = loc_m.group(1).strip()

        # ---- 投放时间 ----
        first_m = re.search(r'First shown:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if first_m:
            data["first_seen"] = first_m.group(1)
        last_m = re.search(r'Last shown:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if last_m:
            data["last_seen"] = last_m.group(1)

        # ---- 投放状态 ----
        status_m = re.search(r'Delivery status\s+(\w+)', full_text)
        if status_m:
            data["delivery_status"] = status_m.group(1)
        if 'Active ad' in full_text or 'active ad' in full_text.lower():
            data["active_ad_delivery"] = "Yes"
        elif 'Not active' in full_text:
            data["active_ad_delivery"] = "No"

        # ---- 目标受众人数 ----
        audience_m = re.search(r'Target audience size\s*([\d\.,]+[MBK]?-?[\d\.,]+[MBK]?)', full_text, re.IGNORECASE)
        if audience_m:
            data["target_audience_size"] = audience_m.group(1).strip()
        else:
            audience_m2 = re.search(r'Target audience size\s*([^\n]+)', full_text)
            if audience_m2:
                val = audience_m2.group(1).strip().split('\n')[0]
                if val and not re.match(r'^\d+$', val):
                    data["target_audience_size"] = val

        # ---- Gender / Age / Location 表格解析 ----
        targeting_tables = soup.find_all("table", role="table")
        CHECK_COLOR = "#FE2C55"

        def is_checked(svg_tag):
            if not svg_tag or not svg_tag.get("fill"):
                return False
            color = svg_tag.get("fill", "")
            if color.lower() == "currentcolor":
                color = svg_tag.get("color", "") or ""
            return CHECK_COLOR.lower() in color.lower()

        def parse_targeting_table(table, col_headers):
            rows = table.find_all("tr", role="row")
            if not rows:
                return [], {}
            results = []
            global_flags = {}
            header_row = rows[0]
            header_cols = header_row.find_all(["th", "td"])
            first_data_row = rows[1] if len(rows) > 1 else None
            if first_data_row:
                cells = first_data_row.find_all("td", role="cell")
                if cells and cells[0].get("aria-colindex") == "1":
                    first_cell_text = cells[0].get_text(strip=True)
                    if not first_cell_text.isdigit():
                        for cell in cells:
                            col_idx = int(cell.get("aria-colindex", 0)) - 1
                            if col_idx < len(col_headers):
                                svg = cell.find("svg")
                                global_flags[col_headers[col_idx]] = is_checked(svg)
            for row in rows[1:]:
                cells = row.find_all("td", role="cell")
                if not cells:
                    continue
                country_name = ""
                row_data = {}
                for cell in cells:
                    col_idx = int(cell.get("aria-colindex", 0)) - 1
                    if col_idx == 1:
                        country_name = cell.get_text(strip=True)
                    elif col_idx >= 2 and col_idx - 2 < len(col_headers):
                        svg = cell.find("svg")
                        row_data[col_headers[col_idx - 2]] = is_checked(svg)
                    elif col_idx < len(col_headers):
                        svg = cell.find("svg")
                        row_data[col_headers[col_idx]] = is_checked(svg)
                if country_name:
                    results.append((country_name, row_data))
            return results, global_flags

        for table in targeting_tables:
            header_row = table.find("thead")
            if not header_row:
                continue
            header_cells = header_row.find_all("th", scope="col")
            header_titles = [th.get_text(strip=True) for th in header_cells]

            gender_cols = [h for h in header_titles if h in ("Male", "Female", "Unknown gender")]
            if gender_cols and len(gender_cols) >= 2:
                country_rows, global_flags = parse_targeting_table(table, gender_cols)
                has_male = global_flags.get("Male", False)
                has_female = global_flags.get("Female", False)
                has_unknown = global_flags.get("Unknown gender", False)
                if not global_flags:
                    for country, row_data in country_rows:
                        has_male = has_male or row_data.get("Male", False)
                        has_female = has_female or row_data.get("Female", False)
                        has_unknown = has_unknown or row_data.get("Unknown gender", False)
                        data["gender_detail"][country] = row_data

                all_checked = has_male and has_female and has_unknown
                if all_checked:
                    data["gender_summary"] = "不限"
                elif has_male and has_female:
                    data["gender_summary"] = "Male, Female"
                elif has_male and has_unknown:
                    data["gender_summary"] = "Male, Unknown gender"
                elif has_female and has_unknown:
                    data["gender_summary"] = "Female, Unknown gender"
                elif has_male:
                    data["gender_summary"] = "Male only"
                elif has_female:
                    data["gender_summary"] = "Female only"
                elif has_unknown:
                    data["gender_summary"] = "Unknown gender only"
                else:
                    data["gender_summary"] = "不限"

            age_range_cols = [h for h in header_titles if re.match(r'\d+-\d+\+?', h)]
            if age_range_cols and len(age_range_cols) >= 2:
                country_rows, global_flags = parse_targeting_table(table, age_range_cols)
                checked_ages = set()
                age_detail = {}
                for country, row_data in country_rows:
                    age_detail[country] = row_data
                    for age_range, checked in row_data.items():
                        if checked:
                            checked_ages.add(age_range)
                data["age_detail"] = age_detail
                if checked_ages:
                    all_mins = []
                    all_maxs = []
                    for age_range in checked_ages:
                        m = re.match(r'(\d+)-(\d+\+?)', age_range)
                        if m:
                            all_mins.append(int(m.group(1)))
                            if '+' in m.group(2):
                                all_maxs.append(65)
                            else:
                                all_maxs.append(int(m.group(2)))
                    if all_mins and all_maxs:
                        min_age = min(all_mins)
                        max_age = max(all_maxs)
                        data["age_summary"] = f"{min_age}-65+" if max_age >= 65 else f"{min_age}-{max_age}"
                else:
                    data["age_summary"] = "不限"

        # ---- Location ----
        location_sections = soup.find_all("h2", class_="ad_details_targeting_title")
        for section in location_sections:
            if section.get_text(strip=True) == "Location":
                next_div = section.find_next_sibling("div")
                if next_div:
                    table = next_div.find("table", role="table")
                    if table:
                        rows = table.find_all("tr", role="row")
                        for row in rows[1:]:
                            cells = row.find_all("td", role="cell")
                            if len(cells) >= 3:
                                num = cells[0].get_text(strip=True)
                                country = cells[1].get_text(strip=True)
                                users = cells[2].get_text(strip=True)
                                if country and num.isdigit():
                                    data["locations"].append(country)
                                    data["locations_detail"][country] = users

        if not data["locations"]:
            location_m = re.search(r'Location\s+This ad was shown to [^\n]+?\s+Number\s+Country\s+Unique users seen\s+(.+?)(?=Ad\s+Advertiser|$)', full_text, re.DOTALL | re.IGNORECASE)
            if location_m:
                loc_text = location_m.group(1)
                user_blocks = re.findall(r'(\d+)\s+([A-Za-z\s]+?)\s+(0-1K|1K-10K|10K-100K|100K-1M|1M-10M|10M-100M)', loc_text)
                for num, country, users in user_blocks:
                    country = country.strip()
                    if country and len(country) > 1:
                        data["locations"].append(country)
                        data["locations_detail"][country] = users

        # ---- 覆盖 ----
        unique_m = re.search(r'Unique users seen:\s*([^T]+)', full_text)
        if unique_m:
            data["unique_users"] = unique_m.group(1).strip()

        # ---- 视频 URL ----
        try:
            video_el = page.locator("video").first
            v_url = video_el.get_attribute('src') or video_el.get_attribute('currentSrc') or ''
            if v_url and v_url != 'null' and len(v_url) > 20:
                data["video_url"] = v_url
                poster = video_el.get_attribute('poster')
                if poster:
                    data["thumbnail_url"] = poster
        except Exception:
            pass

        # ---- 广告描述 ----
        desc_m = re.search(r'Advertiser[\\\'\"]?\s+([^\n]{10,300})', full_text)
        if desc_m:
            data["advertiser_description"] = desc_m.group(1).strip()[:500]

    except Exception as e:
        print(f"[详情] 抓取失败 {ad_id}: {e}", flush=True)
        import traceback; traceback.print_exc()

    return data


# ============================================================
# 【视频下载（通过 yt-dlp）】
# ============================================================

def download_video_ytdlp(video_url, ad_id, video_dir):
    """
    通过 yt-dlp 下载 TikTok 广告视频。
    yt-dlp 自动处理签名 URL、重试和 CDN 路由问题。
    """
    filepath = video_dir / f"{ad_id}.mp4"
    if filepath.exists():
        return {"ad_id": ad_id, "status": "skipped", "path": str(filepath)}

    try:
        # yt-dlp 参数说明：
        # --no-playlist        不下载播放列表
        # -o                   输出路径模板
        # --user-agent         模拟浏览器 UA
        # --socket-timeout     超时时间
        # --retries            重试次数
        # -q                   静默模式（只显示错误）
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist",
            "-o", str(filepath),
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36",
            "--socket-timeout", "60",
            "--retries", "3",
            "-q",
            video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if filepath.exists():
            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f"  [完成] {ad_id}.mp4 ({size_mb:.1f}MB)", flush=True)
            return {"ad_id": ad_id, "status": "success", "size_mb": size_mb}
        else:
            err = result.stderr.strip() if result.stderr else "文件未生成"
            print(f"  [失败] lib={ad_id}: {err[:120]}", flush=True)
            return {"ad_id": ad_id, "status": "error", "error": err[:120]}

    except subprocess.TimeoutExpired:
        print(f"  [超时] lib={ad_id}: 下载超时 120s", flush=True)
        return {"ad_id": ad_id, "status": "error", "error": "timeout 120s"}
    except Exception as e:
        print(f"  [失败] lib={ad_id}: {str(e)[:100]}", flush=True)
        return {"ad_id": ad_id, "status": "error", "error": str(e)[:100]}


def download_videos_batch(lib_ids_with_urls):
    """
    批量下载视频，传入 [(ad_id, video_url), ...]
    通过 yt-dlp 下载（无需 Playwright 浏览器）。
    """
    success, skipped, failed = 0, 0, 0

    for ad_id, video_url in lib_ids_with_urls:
        if not video_url or str(video_url) == 'null' or len(str(video_url)) < 20:
            failed += 1
            continue

        result = download_video_ytdlp(video_url, ad_id, VIDEO_DIR)
        if result["status"] == "success":
            success += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1

    print(f"[下载] 完成: 成功 {success} | 跳过 {skipped} | 失败 {failed}", flush=True)
    return success, skipped, failed


# ============================================================
# 【批量抓取详情页】
# ============================================================

def mine_details_batch(lib_ids, wait_sec, batch_size, detail_callback=None, video_callback=None):
    total = len(lib_ids)
    print(f"[详情] 开始批量抓取 {total} 个详情页（每批 {batch_size} 个）...", flush=True)

    all_batches = [lib_ids[i:i+batch_size] for i in range(0, len(lib_ids), batch_size)]
    zero_streak = 0

    for batch_idx, batch_ids in enumerate(all_batches, 1):
        batch_num = len(all_batches)

        if zero_streak >= ZERO_RESULT_THRESHOLD:
            backoff_sec = min(BACKOFF_BASE_SEC * (2 ** (zero_streak - ZERO_RESULT_THRESHOLD)), 300)
            print(f"\n[⚠️ 反爬] 连续 {zero_streak} 批 0 有效数据，指数退避等待 {backoff_sec:.0f}s...", flush=True)
            print(f"[⚠️ 反爬] 建议：降低并发或切换 IP", flush=True)
            time.sleep(backoff_sec)

        print(f"\n[详情] 批次 {batch_idx}/{batch_num}（{len(batch_ids)} 个）...", flush=True)

        results = {}
        pw, browser, context, page = make_browser_context(headless=HEADLESS)
        try:
            for i, lid in enumerate(batch_ids):
                detail_data = scrape_detail_page(page, lid, wait_sec)
                results[lid] = detail_data

                # 实时进度
                if detail_data.get("advertiser_name"):
                    print(f"  [OK] lib={lid}: {detail_data['advertiser_name'][:30]}", flush=True)
                elif detail_data.get("video_url"):
                    print(f"  [OK] lib={lid}: 视频 {detail_data['video_url'][:60]}", flush=True)
                else:
                    print(f"  [空] lib={lid}", flush=True)

                time.sleep(1)
                if i % 5 == 4:
                    print(f"[详情] 休息一下...", flush=True)
                    time.sleep(random.uniform(5, 10))
        finally:
            close_browser(pw, browser)

        found = sum(1 for v in results.values() if v and v.get("advertiser_name"))
        vid_count = sum(1 for v in results.values() if v and v.get("video_url"))
        print(f"[详情] 批次 {batch_idx} 完成，广告主 {found}/{len(batch_ids)}，视频URL {vid_count} 个", flush=True)

        if found == 0:
            zero_streak += 1
        else:
            zero_streak = 0

        if detail_callback:
            detail_callback(batch_idx, results)

        # 每批次完成后尝试下载视频
        if video_callback:
            pending_videos = [(lid, results[lid].get("video_url", "")) for lid in batch_ids if results.get(lid, {}).get("video_url")]
            if pending_videos:
                video_callback(batch_idx, pending_videos)

    print(f"[详情] 批量抓取完成，共 {total} 个详情页", flush=True)
    return results


# ============================================================
# 【主流程】
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='TikTok Ad Library 详情页抓取 + 视频下载')
    parser.add_argument('--date', type=str, default='', help='目标日期，如 2026-05-14（默认当天）')
    args = parser.parse_args()

    target_date = args.date.strip() if args.date.strip() else get_today_date_str()

    daily_file = OUTPUT_DIR / f"ads_{target_date}.json"
    agg_file = OUTPUT_DIR / "ads_all.json"

    print("=" * 60, flush=True)
    print(f"TikTok Ad Library 详情页抓取 + 视频下载", flush=True)
    print(f"日期: {target_date}", flush=True)
    print(f"输入: {daily_file.name}", flush=True)
    print(f"视频目录: {VIDEO_DIR}", flush=True)
    print(f"断点续抓: {'开启' if RESUME_ENABLED else '关闭'}", flush=True)
    print(f"浏览器: {'无头模式' if HEADLESS else '可见浏览器'}", flush=True)
    print("=" * 60, flush=True)

    # ---- 读取每日文件 ----
    daily_data = load_json(daily_file)
    if daily_data is None:
        print(f"[错误] 找不到每日文件: {daily_file}")
        print(f"[提示] 请先运行 TiktokPlaywright_list.py 抓取 ID")
        return

    ads = daily_data.get("ads", [])
    if not ads:
        print("[错误] 每日文件中没有广告记录")
        return

    print(f"[加载] 每日文件共 {len(ads)} 条广告")

    # ---- 统计已有详情的广告（断点续抓）----
    existing_detail_ids = set()
    pending_ads = []
    for ad in ads:
        lid = str(ad.get("library_id") or ad.get("ad_id") or "")
        if not lid:
            continue
        # 已有的 tiktok_detail 且包含 advertiser_name 或 video_url，认为已完成
        existing_detail = ad.get("tiktok_detail", {})
        if existing_detail and (existing_detail.get("advertiser_name") or existing_detail.get("video_url")):
            existing_detail_ids.add(lid)
        else:
            pending_ads.append(ad)

    print(f"[续抓] 已有详情: {len(existing_detail_ids)} 条，待抓: {len(pending_ads)} 条")

    if not pending_ads:
        print("[完成] 所有广告详情已抓取完毕，跳过详情页抓取")
    else:
        lib_ids = [str(ad.get("library_id") or ad.get("ad_id")) for ad in pending_ads]
        kw_details = {}

        def detail_cb(batch_idx, batch_results):
            nonlocal kw_details
            kw_details.update(batch_results)
            print(f"[保存] 批次 {batch_idx} 完成，已累计 {len(kw_details)} 条", flush=True)

            # 每批次保存一次（断点续抓）
            current_data = load_json(daily_file)
            if current_data and current_data.get("ads"):
                merge_ads_detail(current_data["ads"], list(batch_results.values()))
                save_json(daily_file, current_data)
                print(f"[保存] 已写入 {daily_file.name}", flush=True)

        def video_cb(batch_idx, pending_videos):
            print(f"[视频] 批次 {batch_idx} 开始下载 {len(pending_videos)} 个视频...", flush=True)
            success, skipped, failed = download_videos_batch(pending_videos)
            print(f"[视频] 批次 {batch_idx} 下载完成: 成{success} 跳{skipped} 失{failed}", flush=True)

        mine_details_batch(
            lib_ids,
            wait_sec=DETAIL_WAIT,
            batch_size=DETAIL_BATCH,
            detail_callback=detail_cb,
            video_callback=video_cb
        )

        # ---- 最终合并保存 ----
        final_data = load_json(daily_file)
        if final_data and final_data.get("ads") and kw_details:
            updated = merge_ads_detail(final_data["ads"], list(kw_details.values()))
            save_json(daily_file, final_data)
            print(f"[完成] 详情合并完成，更新 {updated} 条广告")

            agg_data = load_json(agg_file)
            if agg_data and agg_data.get("ads"):
                agg_updated = merge_ads_detail(agg_data["ads"], list(kw_details.values()))
                save_json(agg_file, agg_data)
                print(f"[汇总] 已同步更新 ads_all.json（更新 {agg_updated} 条）")
        elif final_data:
            save_json(daily_file, final_data)

    # ---- 统计 ----
    final_data = load_json(daily_file)
    if final_data:
        total_ads = len(final_data.get("ads", []))
        with_detail = sum(1 for a in final_data.get("ads", []) if a.get("tiktok_detail", {}).get("advertiser_name"))
        with_video_url = sum(1 for a in final_data.get("ads", []) if a.get("tiktok_detail", {}).get("video_url") or a.get("video_urls"))
        downloaded_videos = len([f for f in VIDEO_DIR.glob("*.mp4")])
        print(f"\n{'='*60}", flush=True)
        print(f"详情页抓取完成！", flush=True)
        print(f"每日文件: {daily_file.name}（{total_ads} 条广告）", flush=True)
        print(f"已有详情: {with_detail} 条", flush=True)
        print(f"已有视频URL: {with_video_url} 条", flush=True)
        print(f"已下载视频: {downloaded_videos} 个", flush=True)
        print(f"汇总文件: ads_all.json", flush=True)
        print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()