"""
Facebook Ad Library 抓取 + 去重合并 + 视频下载
============================================ facebookPlaywrightRun.py

【功能说明】
  1. 抓取列表页广告（通过翻页加载）
  2. 逐个访问详情页，提取视频/图片 URL
  3. 去重后合并到汇总文件

【与 TikTok 版的差异】
  - 使用 Playwright 而非 Selenium
  - Facebook Ad Library URL 和页面结构不同
  - 翻页方式：点击 "See more" 或翻页按钮
  - 广告ID：从 URL 参数或页面元素提取
"""

import sys
import os
import json
import time
import re
import urllib.request
import ssl
import warnings
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 忽略 Playwright 警告
warnings.filterwarnings('ignore', category=DeprecationWarning)

# 全局禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36')]
urllib.request.install_opener(opener)

# ============================================================
#                    【配置区】
#          （运行前修改这里即可，无需碰其他代码）
# ============================================================

# ----- 搜索条件 -----
KEYWORD = "Block Blast"        # 【必改】搜索关键词，如 "Block Blast"、"Instagram" 等
                          # 注意：Facebook Ad Library 会自动转为大写处理

# ----- 日期设置 -----
# 【模式切换】
#   AUTO_DATE = True  -> 自动模式：抓最近7天（END_DATE=今日，START_DATE=今日-6天）
#   AUTO_DATE = False -> 手动模式：使用下方指定的 START_DATE 和 END_DATE
AUTO_DATE = True

START_DATE = "2026-04-16"    # 手动模式时的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-04-22"      # 手动模式时的结束日期（格式：YYYY-MM-DD）
                          # 留空 "" 表示今天；和开始日期相同则只抓当天

# ----- 抓取模式 -----
# 【重要】选一个模式：
#   MODE = "fixed"  -> 固定数量模式：只抓前 MAX_ADS 条广告（推荐测试用）
#   MODE = "all"    -> 全量模式：抓取全部广告（直到页面底部才停止）
MODE = "fixed"                  # ★ 建议先用 fixed 模式测试，确认正常后换 all
MAX_ADS = 10                  # MODE="fixed" 时生效，表示最多抓多少条广告

# ----- 浏览器模式 -----
#   True  = 无头模式（不弹窗，后台运行，更稳定，推荐生产环境使用）
#   False = 可见浏览器（弹出 Chrome 窗口，方便调试看页面情况）
HEADLESS = False               # ★ 调试时可设为 False 观察页面

# ----- 等待时间（秒）-----
# 【网速调整】每次点击 "See more" 翻页后等待的时间
# 数据多或网速慢 -> 调大，如 8 或 10
# 网速快且数据少 -> 可调小，如 5
WAIT_SEC = 7

# ----- 并发数 -----
# 视频/图片下载的并发线程数（降低可避免被限流）
MAX_DOWNLOAD_WORKERS = 1

# 详情页视频提取的并发浏览器实例数（数字越大越快，但容易被限流）
MAX_DETAIL_WORKERS = 2

# 每处理多少个详情页后保存一次进度（防止中途崩溃丢失数据）
DETAIL_BATCH = 5

# ----- 视频/图片提取 -----
# 打开详情页后等待秒数（给视频/图片元素加载时间）
# 网速慢或视频大 -> 调大，如 8 或 10
DETAIL_WAIT = 5

# ============================================================

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# ============================================================
# 【固定路径】
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
    'Referer': 'https://www.facebook.com/',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Encoding': 'identity',
}


# ============================================================
# 【工具函数】
# ============================================================

def date_to_timestamp(date_str):
    """把日期字符串转成时间戳（北京时间 00:00:00）"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    tz = timezone(timedelta(hours=8))
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    return int(dt.timestamp())


def build_url(keyword, start_date, end_date):
    """
    构建 Facebook Ad Library 搜索 URL

    Facebook Ad Library: https://www.facebook.com/ads/library/
    """
    kw = keyword.upper().replace(" ", "%20")

    start_ts = date_to_timestamp(start_date)
    if end_date:
        tz = timezone(timedelta(hours=8))
        dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=tz)
        end_ts = int(dt.timestamp())
    else:
        end_ts = date_to_timestamp(datetime.now().strftime("%Y-%m-%d"))

    return (
        f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all"
        f"&country=ALL&q={kw}&search_type=keyword_unordered"
    )


def keyword_to_name(keyword):
    return keyword.lower().replace(" ", "").replace("!", "").replace("*", "")


def resolve_dates():
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    if AUTO_DATE:
        end_date = today_str
        start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
    else:
        end_date = END_DATE if END_DATE else today_str
        start_date = START_DATE
    return start_date, end_date


def get_today_date_str():
    return datetime.now().strftime('%Y-%m-%d')


def get_file_paths(keyword, date_str):
    name = keyword_to_name(keyword)
    agg_file = OUTPUT_DIR / f"fb_ads_{name}.json"
    daily_file = OUTPUT_DIR / f"fb_ads_{name}_{date_str}.json"
    video_dir = OUTPUT_DIR / f"fb_videos_{name}"
    return agg_file, daily_file, video_dir, date_str


# ============================================================
# 【浏览器驱动 - Playwright】
# ============================================================

def make_playwright():
    """
    创建 Playwright 浏览器实例
    """
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=HEADLESS,
        args=[
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--window-size=1920,1080',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
        ]
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
    )
    page = context.new_page()
    return pw, browser, context, page


# ============================================================
# 【页面交互】
# ============================================================

def accept_cookies_if_present(page):
    """接受 Cookie 弹窗（如果出现）"""
    cookie_selectors = [
        "button[title='Accept All']",
        "button[aria-label='Accept']",
        "[data-testid='cookie-policy-dialog-accept']",
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
    ]
    for selector in cookie_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                print(f"[弹窗] 已点击 Cookie 按钮: {selector}", flush=True)
                time.sleep(2)
                return
        except Exception:
            continue


def click_see_more(page, wait_sec):
    """
    点击 "See more" 或翻页按钮加载更多广告

    返回:
        True  = 成功点击，页面有新内容
        False = 按钮不存在或已消失
    """
    try:
        # 尝试多种 See more 按钮选择器
        see_more_selectors = [
            "span:has-text('See more')",
            "div:has-text('See more')",
            "[role='button']:has-text('See more')",
            "a:has-text('See more')",
            "//span[contains(text(), 'See more')]",
        ]

        for selector in see_more_selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    page.evaluate("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    btn.click()
                    print(f"[加载] 点击 See more，等待 {wait_sec}s...", flush=True)
                    time.sleep(wait_sec)
                    return True
            except Exception:
                continue

        return False
    except Exception as e:
        print(f"[加载] See more 点击异常: {e}", flush=True)
        return False


def is_page_exhausted(page):
    """判断列表页是否已经加载到底"""
    html = page.content()
    if "End of results" in html or "No more results" in html:
        print("[抓取] 检测到 'End of results'，列表已到底", flush=True)
        return True

    # 检查是否还有 See more 按钮
    see_more_selectors = [
        "span:has-text('See more')",
        "div:has-text('See more')",
    ]
    for selector in see_more_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                return False
        except Exception:
            continue

    print("[抓取] See more 按钮消失，列表已到底", flush=True)
    return True


# ============================================================
# 【广告解析（列表页）】
# ============================================================

def parse_ads_from_page(page):
    """
    从当前列表页解析所有广告

    Facebook 广告库页面结构：
      广告卡片在 div 或 article 元素中
      包含广告ID、投放者、文案等信息

    返回:
        广告字典列表
    """
    ads = []
    seen_ids = set()

    # 尝试多种选择器定位广告卡片
    card_selectors = [
        "div[role='article']",
        "div[data-testid='ad-card']",
        "div:has(> div > a[href*='/ads/about/'])",
    ]

    cards = []
    for selector in card_selectors:
        try:
            cards = page.query_selector_all(selector)
            if cards:
                break
        except Exception:
            continue

    # 备选：直接搜索包含广告ID的链接
    if not cards:
        try:
            links = page.query_selector_all("a[href*='ads/about']")
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    m = re.search(r'/ads/about/(\d+)', href)
                    if m:
                        card = link.query_selector("xpath=ancestor::div[@role='article' or @data-testid='ad-card'][1]")
                        if card:
                            cards.append(card)
                except Exception:
                    continue
        except Exception:
            pass

    for card in cards:
        try:
            # 提取广告ID
            card_html = card.inner_html()
            id_m = re.search(r'id=(\d{10,})', card_html) or re.search(r'/ads/about/(\d+)', card_html)
            if not id_m:
                continue
            ad_id = id_m.group(1) if id_m.group(1) else id_m.group(0).split('/')[-1]

            if ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)

            # 提取文本内容
            text = card.inner_text() or ""

            ad = {
                "library_id": ad_id,
                "index": len(ads) + 1,
                "platforms": ["Facebook"],
                "video_urls": [],
                "ad_text": "",
                "advertiser_name": "",
                "raw_text": text[:500],
            }

            # 解析文本行
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for line in lines:
                if line.startswith('Active') or line.startswith('Inactive'):
                    ad["delivery_status"] = line
                elif 'sponsor' in line.lower() or 'paid for' in line.lower():
                    ad["ad_text"] = line[:500]
                elif len(line) > 3 and 'shown' not in line.lower():
                    if not ad.get("advertiser_name"):
                        ad["advertiser_name"] = line[:200]

            ads.append(ad)
        except Exception as e:
            continue

    return ads


# ============================================================
# 【详情页抓取】
# ============================================================

def scrape_facebook_detail_page(page, ad_id, wait_sec):
    """
    访问 Facebook 广告详情页，提取视频/图片 URL 和详细信息

    参数:
        page:     Playwright Page 实例
        ad_id:    广告 ID
        wait_sec: 等待秒数

    返回:
        详情页数据字典
    """
    data = {
        "ad_id": ad_id,
        "video_url": "",
        "image_url": "",
        "ad_text": "",
        "advertiser_name": "",
        "delivery_status": "",
        "raw_text": "",
    }

    try:
        detail_url = f"https://www.facebook.com/ads/about/?id={ad_id}"
        page.goto(detail_url, wait_until="networkidle", timeout=30000)
        time.sleep(wait_sec)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 提取视频 URL
        video_tags = soup.find_all("video")
        for video in video_tags:
            src = video.get("src") or video.get("currentSrc") or ""
            if src and "facebook.com" in src or src.startswith("http"):
                data["video_url"] = src
                break

        # 备选：从 page 对象获取视频
        if not data["video_url"]:
            try:
                video_el = page.query_selector("video")
                if video_el:
                    data["video_url"] = video_el.get_attribute("src") or video_el.get_attribute("currentSrc") or ""
            except Exception:
                pass

        # 提取图片 URL
        if not data["image_url"]:
            img_tags = soup.find_all("img")
            for img in img_tags:
                src = img.get("src") or ""
                if src and "scontent" in src:  # Facebook CDN 图片
                    data["image_url"] = src
                    break

        # 提取页面文本
        body = page.query_selector("body")
        if body:
            data["raw_text"] = body.inner_text()[:1000]

        # 解析关键信息
        text = data["raw_text"]
        if not data["advertiser_name"]:
            m = re.search(r'(?:Advertiser|Ad paid for by)\s+([^\n]{3,200})', text)
            if m:
                data["advertiser_name"] = m.group(1).strip()

        if not data["ad_text"]:
            m = re.search(r'(?:sponsor|Sponsored|Ad|Paid for by)\s+([^\n]{10,500})', text, re.IGNORECASE)
            if m:
                data["ad_text"] = m.group(1).strip()[:500]

    except PlaywrightTimeout:
        print(f"[详情] 页面加载超时 {ad_id}", flush=True)
    except Exception as e:
        print(f"[详情] 抓取失败 {ad_id}: {e}", flush=True)

    return data


def mine_details_batch(lib_ids, wait_sec, batch_size, progress_prefix=""):
    """
    批量抓取详情页（分批处理，定期保存）
    """
    results = {}
    total = len(lib_ids)

    print(f"[视频] 开始提取 {total} 个详情页...", flush=True)

    all_batches = [lib_ids[i:i+batch_size] for i in range(0, len(lib_ids), batch_size)]

    for batch_idx, batch_ids in enumerate(all_batches, 1):
        batch_num = len(all_batches)
        print(f"\n[详情] 批次 {batch_idx}/{batch_num}（{len(batch_ids)} 个）...", flush=True)

        pw, browser, context, page = make_playwright()
        try:
            for lid in batch_ids:
                detail_data = scrape_facebook_detail_page(page, lid, wait_sec)
                results[lid] = detail_data
                time.sleep(1)
        finally:
            browser.close()
            pw.stop()

        found = sum(1 for v in results.values() if v.get("video_url") or v.get("image_url"))
        done = min(batch_idx * batch_size, total)
        print(f"[详情] 进度: {done}/{total}，当前共 {found} 个有媒体", flush=True)

    found = sum(1 for v in results.values() if v.get("video_url") or v.get("image_url"))
    print(f"[详情] 提取完成，共 {found}/{total} 个详情页有媒体", flush=True)
    return results


# ============================================================
# 【列表页滚动抓取】
# ============================================================

def scroll_and_collect(page, target_url, wait_sec, mode, max_ads):
    """
    打开列表页，循环点击 See more 抓取广告
    """
    print(f"[抓取] 访问: {target_url}", flush=True)
    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    print(f"[抓取] 页面标题: {page.title()}", flush=True)

    accept_cookies_if_present(page)

    ads = []
    seen_ids = set()
    click_count = 0
    empty_clicks = 0

    # 初始解析
    for ad in parse_ads_from_page(page):
        if ad["library_id"] not in seen_ids:
            seen_ids.add(ad["library_id"])
            ads.append(ad)
    print(f"[抓取] 初始广告: {len(ads)} 条", flush=True)

    while True:
        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止收集", flush=True)
            break

        if mode == "all" and is_page_exhausted(page):
            print("[抓取] 页面已到底，停止收集", flush=True)
            break

        print(f"[抓取] 等待页面加载（点击 #{click_count + 1}）...", flush=True)
        clicked = click_see_more(page, wait_sec)

        if clicked:
            click_count += 1
            empty_clicks = 0
        else:
            empty_clicks += 1
            print(f"[抓取] 连续第 {empty_clicks} 次无法点击 See more", flush=True)
            if empty_clicks >= 2:
                print("[抓取] 连续2次无法点击，停止", flush=True)
                break

        new_count = 0
        for ad in parse_ads_from_page(page):
            if ad["library_id"] not in seen_ids:
                if mode == "fixed" and len(ads) >= max_ads:
                    break
                seen_ids.add(ad["library_id"])
                ads.append(ad)
                new_count += 1

        print(f"  已收集 {len(ads)} 条 (+{new_count} 本轮，点击#{click_count})", flush=True)

        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止", flush=True)
            break

    print(f"[抓取] 列表页抓取完成，共 {len(ads)} 条广告", flush=True)
    return ads


# ============================================================
# 【文件处理】
# ============================================================

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


def merge_deduplicate(new_ads, agg_ads):
    agg_ids = {ad["library_id"] for ad in agg_ads if ad.get("library_id")}
    unique = [ad for ad in new_ads
               if ad.get("library_id") and ad["library_id"] not in agg_ids]
    dup_count = len(new_ads) - len(unique)
    return unique, dup_count


# ============================================================
# 【视频下载】
# ============================================================

def download_single_video(args):
    url, filepath, lib_id = args

    if filepath.exists():
        print(f"  [跳过] {filepath.name} 已存在", flush=True)
        return {"lib_id": lib_id, "status": "skipped", "path": str(filepath)}

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120, context=ssl_context) as resp:
                size = 0
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = resp.read(1024 * 512)
                        if not chunk:
                            break
                        f.write(chunk)
                        size += len(chunk)
            print(f"  [完成] {filepath.name} ({size/1024/1024:.1f}MB)", flush=True)
            return {"lib_id": lib_id, "status": "success", "path": str(filepath), "size_mb": size/1024/1024}
        except (ssl.SSLError, urllib.error.URLError) as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay + 1
                print(f"  [重试] lib={lib_id} (尝试 {attempt+1}/{max_retries}): {str(e)[:80]}", flush=True)
                time.sleep(wait_time)
                retry_delay *= 2
            else:
                print(f"  [失败] lib={lib_id}: {e}", flush=True)
                return {"lib_id": lib_id, "status": "error", "error": str(e)}
        except Exception as e:
            print(f"  [失败] lib={lib_id}: {e}", flush=True)
            return {"lib_id": lib_id, "status": "error", "error": str(e)}

    return {"lib_id": lib_id, "status": "error", "error": "max retries exceeded"}


def download_videos(daily_file, video_dir, keyword):
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(daily_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ads = data.get('ads', [])
    ads_with_media = [a for a in ads if a.get('video_urls') or a.get('image_url')]

    print(f"\n{'='*50}", flush=True)
    print(f"[下载] 视频目录: {video_dir}", flush=True)
    print(f"[下载] 待下载广告: {len(ads_with_media)} 个", flush=True)

    if not ads_with_media:
        print("[下载] 没有带视频的广告")
        return

    tasks = []
    for ad in ads_with_media:
        lib_id = ad['library_id']
        url = (ad.get('video_urls') or [ad.get('image_url')])[0]
        ext = "mp4" if ad.get('video_urls') else "jpg"
        filepath = video_dir / f"{lib_id}.{ext}"
        tasks.append((url, filepath, lib_id))

    existing = {f.stem for f in video_dir.glob("*") if f.is_file()}
    to_dl = [t for t in tasks if t[1].stem not in existing]
    done = len(tasks) - len(to_dl)

    print(f"[下载] 已有: {done} 个，待下载: {len(to_dl)} 个", flush=True)
    if not to_dl:
        print("[下载] 全部已下载完毕")
        return

    success, failed = 0, 0
    total_size = 0.0

    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as ex:
        futures = {ex.submit(download_single_video, t): t for t in to_dl}
        for future in as_completed(futures):
            r = future.result()
            if r['status'] == 'success':
                success += 1
                total_size += r.get('size_mb', 0)
            else:
                failed += 1

    print(f"[完成] 成功: {success} | 跳过: {done} | 失败: {failed} | 大小: {total_size:.1f}MB", flush=True)


# ============================================================
# 【主流程】
# ============================================================

def main():
    start_date, end_date = resolve_dates()
    today_str = get_today_date_str()

    if start_date == end_date:
        date_str = start_date
    else:
        date_str = f"{start_date}_to_{end_date}"

    if MODE == "fixed":
        mode_desc = f"固定数量模式（上限 {MAX_ADS} 条）"
    else:
        mode_desc = "全量模式"

    name = keyword_to_name(KEYWORD)
    agg_file = OUTPUT_DIR / f"fb_ads_{name}.json"
    daily_file = OUTPUT_DIR / f"fb_ads_{name}_{today_str}.json"

    print("=" * 60, flush=True)
    print(f"Facebook Ad Library 抓取 + 合并 + 媒体下载", flush=True)
    print(f"关键词: {KEYWORD}", flush=True)
    print(f"日期范围: {start_date} ~ {end_date}", flush=True)
    print(f"汇总文件: {agg_file.name}", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"模式: {mode_desc}", flush=True)
    print(f"浏览器: {'无头模式' if HEADLESS else '可见浏览器'}", flush=True)
    print("=" * 60, flush=True)

    scrape_url = build_url(KEYWORD, start_date, end_date)
    print(f"[URL] {scrape_url}", flush=True)

    # 第1步：抓取列表页
    print("\n>>> 第1步：抓取列表页广告 >>>", flush=True)
    pw, browser, context, page = make_playwright()
    try:
        ads = scroll_and_collect(page, scrape_url, WAIT_SEC, MODE, MAX_ADS)
        print(f"\n[第1步完成] 共收集 {len(ads)} 条广告", flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[错误] 抓取失败: {e}", flush=True)
        return
    finally:
        browser.close()
        pw.stop()

    # 第2步：抓取详情页
    print(f"\n>>> 第2步：抓取详情页数据 >>>", flush=True)
    lib_ids = [a["library_id"] for a in ads if a.get("library_id")]
    if lib_ids:
        all_details = mine_details_batch(lib_ids, wait_sec=DETAIL_WAIT, batch_size=DETAIL_BATCH)
        for ad in ads:
            lib_id = ad["library_id"]
            if lib_id in all_details:
                detail = all_details[lib_id]
                ad["video_urls"] = [detail["video_url"]] if detail.get("video_url") else []
                ad["fb_detail"] = detail
    else:
        print("[第2步] 没有广告ID，跳过", flush=True)

    # 第3步：文件处理
    print("\n>>> 第3步：去重并更新汇总文件 >>>", flush=True)
    agg_data = load_json(agg_file) or {
        "keyword": KEYWORD,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "total_ads": 0,
        "total_with_videos": 0,
        "ads": [],
    }

    existing_ads = agg_data.get("ads", [])
    existing_ids = {ad.get("library_id") for ad in existing_ads if ad.get("library_id")}

    unique_new = []
    for ad in ads:
        if ad.get("library_id") and ad["library_id"] not in existing_ids:
            unique_new.append(ad)
            existing_ids.add(ad["library_id"])

    print(f"[去重] 本次 {len(ads)} 条，新增 {len(unique_new)} 条", flush=True)

    daily_data = {
        "scrape_time": datetime.now().isoformat(),
        "url": scrape_url,
        "keyword": KEYWORD,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
        "ads_count": len(ads),
        "new_ads_count": len(unique_new),
        "ads": ads,
    }
    save_json(daily_file, daily_data)
    print(f"[文件] 已保存每日文件: {daily_file.name}（{len(ads)} 条）", flush=True)

    if unique_new:
        agg_data["ads"] = agg_data.get("ads", []) + unique_new
        agg_data["updated_at"] = datetime.now().isoformat()
        agg_data["total_ads"] = len(agg_data["ads"])
        agg_data["total_with_videos"] = sum(1 for a in agg_data["ads"] if a.get("video_urls"))
        save_json(agg_file, agg_data)
        print(f"[汇总] 已更新: {agg_file.name}（共 {len(agg_data['ads'])} 条）", flush=True)

    # 第4步：下载视频
    print("\n>>> 第4步：下载视频/图片 >>>", flush=True)
    _, _, video_dir, _ = get_file_paths(KEYWORD, today_str)
    download_videos(daily_file, video_dir, KEYWORD)

    print(f"\n{'='*60}", flush=True)
    print(f"全部完成！", flush=True)
    print(f"本次抓取: {len(ads)} 条", flush=True)
    print(f"新增记录: {len(unique_new)} 条", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
