"""
TikTok Ad Library 列表页抓取（仅 ID）
================================ TiktokPlaywright_list.py

【功能】
  1. 多关键词搜索，抓取列表页广告 ID（View More 翻页）
  2. 不进详情页，不下载视频
  3. 结果写入 ads_<date>.json

【断点续抓】
  运行时检查 ads_<date>.json，已有的广告 ID 直接跳过

【用法】
  python TiktokPlaywright_list.py
"""

import sys
import json
import time
import re
import ssl
import warnings
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ============================================================
#                    【配置区】
# ============================================================

KEYWORDS = [
    "Block Blast",
    "Easybrain Ltd",
    "Tripledot Studios",
    "Block Puzzle Wood Blast",
    "Block Puzzles",
    "Block Puzzle: Diamond Star",
    "Blockanza: Block Puzzle"
    # "Block Puzzle - Fun Games",
    # "Block Puzzle Jewel :Gem Legend",
    # "Block Puzzle - Brain Games",
    # "Block Puzzle - Brain Test Game",
    # "Block Puzzle Jewel Legend",
    # "Woody Block Puzzle Brain Game",
    # "Block Puzzle",
    # "Block Puzzle - Woody 99 2024",
    # "Block Puzzle - Wood Games",
    # "Block Blast Master:Puzzle Game"
    # "Block Puzzle Wood"
    # "Block Puzzle Jewel World",
    # "Block Puzzle Gem",
    # "Block Puzzle - Jewel Quest",
    # "Block Puzzle Blast",
    # "Jewel Blitz: Block Puzzle",
    # "Block Puzzle: Wood Brain Games",
    # "Wood Cube Puzzle"
    ]

AUTO_DATE = True
START_DATE = "2026-04-16"
END_DATE = "2026-04-22"

MODE = "all"
MAX_ADS = 10

HEADLESS = False
WAIT_SEC = 7

RESUME_ENABLED = True
ZERO_RESULT_THRESHOLD = 3
BACKOFF_BASE_SEC = 30

# ============================================================

warnings.filterwarnings('ignore', category=DeprecationWarning)
ssl._create_default_https_context = ssl._create_unverified_context

from playwright.sync_api import sync_playwright

# ============================================================
# 【固定路径】
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 【工具函数】
# ============================================================

def date_to_timestamp_ms(date_str):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    tz = timezone(timedelta(hours=8))
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    return int(dt.timestamp() * 1000)


def build_url(keyword, start_date, end_date):
    kw = keyword.upper().replace(" ", "%20")
    start_ts = date_to_timestamp_ms(start_date)
    if end_date:
        tz = timezone(timedelta(hours=8))
        dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=tz)
        end_ts = int(dt.timestamp() * 1000)
    else:
        end_ts = date_to_timestamp_ms(datetime.now().strftime("%Y-%m-%d"))
    return (
        "https://library.tiktok.com/ads?"
        f"region=all&start_time={start_ts}&end_time={end_ts}"
        f"&adv_name={kw}&adv_biz_ids=&query_type=1"
        "&sort_type=last_shown_date,desc"
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
# 【页面交互】
# ============================================================

def accept_cookies_if_present(page):
    cookie_texts = ['Accept', 'Accept all', 'Allow', 'I accept', '同意', '接受']
    for text in cookie_texts:
        try:
            btn = page.locator(f"button", has_text=text).first
            if btn.is_visible(timeout=2000):
                btn.click()
                print(f"[弹窗] 已点击 Cookie 按钮: {text}", flush=True)
                time.sleep(2)
                return
        except Exception:
            continue


def click_view_more(page, wait_sec):
    try:
        btn = page.locator("span.loading_more_text").first
        if not btn.is_visible():
            return False
        btn.scroll_into_view_if_needed()
        time.sleep(1)
        btn.click()
        print(f"[加载] 点击 View more，等待 {wait_sec}s...", flush=True)
        time.sleep(wait_sec)
        return True
    except Exception as e:
        print(f"[加载] View more 点击异常: {e}", flush=True)
        return False


def is_page_exhausted(page):
    html = page.content()
    if "End of results" in html or "No more results" in html:
        print("[抓取] 检测到 'End of results'，列表已到底", flush=True)
        return True
    try:
        btn = page.locator("span.loading_more_text").first
        if btn.is_visible():
            return False
    except Exception:
        pass
    print("[抓取] View more 按钮消失，列表已到底", flush=True)
    return True


# ============================================================
# 【广告解析（列表页）】
# ============================================================

def parse_ads_from_page(page):
    ads = []
    seen_ids = set()
    links = page.locator("a[href*='/ads/detail/?ad_id=']").all()

    for link in links:
        href = link.get_attribute("href") or ""
        m = re.search(r'ad_id=(\d+)', href)
        if not m:
            continue
        ad_id = m.group(1)
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        text = link.text_content() or ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        ad = {
            "library_id": ad_id,
            "index": len(ads) + 1,
            "platforms": ["TikTok"],
            "video_urls": [],
            "detail_url": href if href.startswith('http')
                           else f"https://library.tiktok.com{href}",
        }

        for line in lines:
            if line.startswith('First shown:'):
                ad["first_shown"] = line.replace('First shown:', '').strip()
            elif line.startswith('Last shown:'):
                ad["last_shown"] = line.replace('Last shown:', '').strip()
            elif line.startswith('Unique users seen:'):
                ad["unique_users"] = line.replace('Unique users seen:', '').strip()
            elif line not in ['Ad', 'Details', 'View details'] and len(line) > 3:
                if 'shown' not in line and 'users' not in line:
                    ad["ad_text"] = line[:500]

        ads.append(ad)

    return ads


# ============================================================
# 【列表页滚动抓取】
# ============================================================

def scroll_and_collect(page, target_url, wait_sec, mode, max_ads, existing_ids):
    print(f"[抓取] 访问: {target_url}", flush=True)
    page.goto(target_url)
    page.wait_for_timeout(8000)
    print(f"[抓取] 页面标题: {page.title()}", flush=True)
    accept_cookies_if_present(page)

    ads = []
    seen_ids = set()
    click_count = 0
    empty_clicks = 0
    zero_streak = 0
    new_count_total = 0

    # 初始加载，跳过已有 ID
    for ad in parse_ads_from_page(page):
        if ad["library_id"] in existing_ids:
            continue
        if ad["library_id"] not in seen_ids:
            seen_ids.add(ad["library_id"])
            ads.append(ad)
            new_count_total += 1

    print(f"[抓取] 初始广告: {len(ads)} 条（跳过已有: {sum(1 for a in parse_ads_from_page(page) if a['library_id'] in existing_ids)} 条）", flush=True)

    while True:
        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止收集", flush=True)
            break
        if mode == "all" and is_page_exhausted(page):
            print("[抓取] 页面已到底，停止收集", flush=True)
            break
        if zero_streak >= ZERO_RESULT_THRESHOLD:
            backoff_sec = min(BACKOFF_BASE_SEC * (2 ** (zero_streak - ZERO_RESULT_THRESHOLD)), 300)
            print(f"\n[⚠️ 反爬] 连续 {zero_streak} 次无新广告，指数退避等待 {backoff_sec:.0f}s...", flush=True)
            time.sleep(backoff_sec)

        print(f"[抓取] 等待页面加载（点击 #{click_count + 1}）...", flush=True)
        clicked = click_view_more(page, wait_sec)

        if clicked:
            click_count += 1
            empty_clicks = 0
        else:
            empty_clicks += 1
            if empty_clicks >= 2:
                print("[抓取] 连续2次无法点击，停止", flush=True)
                break

        new_count = 0
        for ad in parse_ads_from_page(page):
            if ad["library_id"] in existing_ids:
                continue
            if ad["library_id"] not in seen_ids:
                if mode == "fixed" and len(ads) >= max_ads:
                    break
                seen_ids.add(ad["library_id"])
                ads.append(ad)
                new_count += 1
                new_count_total += 1

        print(f"  已收集 {len(ads)} 条（+{new_count} 本轮，点击#{click_count}，本次新增{new_count_total}）", flush=True)

        if new_count == 0:
            zero_streak += 1
        else:
            zero_streak = 0

        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止", flush=True)
            break

    print(f"[抓取] 列表页抓取完成，共 {len(ads)} 条广告（本次新增 {new_count_total} 条）", flush=True)
    return ads


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

    mode_desc = f"固定数量模式（上限 {MAX_ADS} 条）" if MODE == "fixed" else "全量模式（抓取全部数据）"

    agg_file = OUTPUT_DIR / "ads_all.json"
    daily_file = OUTPUT_DIR / f"ads_{today_str}.json"

    print("=" * 60, flush=True)
    print(f"TikTok Ad Library 列表页抓取（仅 ID）", flush=True)
    print(f"关键词: {KEYWORDS}", flush=True)
    print(f"日期范围: {start_date} ~ {end_date}", flush=True)
    print(f"当日日期（文件命名）: {today_str}", flush=True)
    print(f"汇总文件: {agg_file.name}", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"模式: {mode_desc}", flush=True)
    print(f"断点续抓: {'开启' if RESUME_ENABLED else '关闭'}", flush=True)
    print(f"浏览器: {'无头模式' if HEADLESS else '可见浏览器'}", flush=True)
    print("=" * 60, flush=True)

    # ---- 读取已有数据（断点续抓）----
    existing_ids = set()
    if RESUME_ENABLED and daily_file.exists():
        daily_data = load_json(daily_file)
        if daily_data and daily_data.get("ads"):
            for ad in daily_data["ads"]:
                lid = ad.get("library_id") or ad.get("ad_id")
                if lid:
                    existing_ids.add(str(lid))
            print(f"[续抓] 已有 {len(existing_ids)} 条广告 ID，跳过已有记录", flush=True)

    # ---- 逐个关键字抓取 ----
    all_keyword_ads = []

    for kw in KEYWORDS:
        print(f"\n{'='*50}", flush=True)
        print(f"[关键词] 开始抓取: {kw}", flush=True)

        scrape_url = build_url(kw, start_date, end_date)
        print(f"[URL] {scrape_url}", flush=True)

        pw, browser, context, page = None, None, None, None
        kw_ads = []
        try:
            print(f"\n>>> 开始抓取 [{kw}] 列表页广告 >>>", flush=True)
            print("[启动] Playwright Chromium...", flush=True)
            pw, browser, context, page = make_browser_context(headless=HEADLESS)
            kw_ads = scroll_and_collect(page, scrape_url, WAIT_SEC, MODE, MAX_ADS, existing_ids)
            print(f"\n[完成] [{kw}] 共收集 {len(kw_ads)} 条广告（跳过已有: {len(existing_ids)} 条）", flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[错误] [{kw}] 抓取失败: {e}", flush=True)
        finally:
            if browser:
                close_browser(pw, browser)

        all_keyword_ads.append((kw, kw_ads))
        print(f"[关键词] [{kw}] 完成，收集 {len(kw_ads)} 条广告", flush=True)

    # ---- 合并所有关键字的广告 ----
    print(f"\n{'='*50}", flush=True)
    print(f"[合并] 共抓取 {len(all_keyword_ads)} 个关键字，合并去重...", flush=True)

    ads_pool = []
    for kw, kw_ads in all_keyword_ads:
        ads_pool.extend(kw_ads)
        print(f"  [{kw}] +{len(kw_ads)} 条", flush=True)
    print(f"[合并] 合计 {len(ads_pool)} 条（未去重）", flush=True)

    # ---- 已有汇总数据处理 ----
    agg_data = load_json(agg_file)
    if agg_data is None:
        agg_data = {
            "keywords": KEYWORDS,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_ads": 0,
            "total_with_videos": 0,
            "ads": [],
        }

    existing_ads = agg_data.get("ads", [])
    agg_existing_ids = {ad.get("library_id") for ad in existing_ads if ad.get("library_id")}

    # ---- 合并去重 ----
    unique_new = []
    for ad in ads_pool:
        if ad.get("library_id") and ad["library_id"] not in agg_existing_ids:
            unique_new.append(ad)
            agg_existing_ids.add(ad["library_id"])

    print(f"[去重] 本次 {len(ads_pool)} 条，新增 {len(unique_new)} 条（不重复）", flush=True)
    print(f"[汇总] 已有 {len(existing_ads)} 条，新增 {len(unique_new)} 条", flush=True)

    # ---- 保存每日文件（追加新广告，不覆盖已有）----
    daily_data = load_json(daily_file) or {}
    existing_daily_ids = {str(ad.get("library_id") or ad.get("ad_id") or "") for ad in daily_data.get("ads", [])}

    new_ads_to_add = []
    for ad in ads_pool:
        if str(ad.get("library_id") or "") not in existing_daily_ids:
            new_ads_to_add.append(ad)

    all_daily_ads = daily_data.get("ads", []) + new_ads_to_add

    # 更新已有广告的字段（如果新抓到的有更多信息）
    for existing_ad in all_daily_ads:
        for new_ad in ads_pool:
            if existing_ad.get("library_id") == new_ad.get("library_id"):
                # 用新数据补充空字段
                for k, v in new_ad.items():
                    if k not in existing_ad or not existing_ad[k]:
                        existing_ad[k] = v
                break

    daily_data.update({
        "scrape_time": datetime.now().isoformat(),
        "url": f"multi-keyword: {KEYWORDS}",
        "keywords": KEYWORDS,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
        "ads_count": len(all_daily_ads),
        "new_ads_count": len(new_ads_to_add),
        "total_in_summary": len(existing_ads) + len(unique_new),
        "ads": all_daily_ads,
    })
    save_json(daily_file, daily_data)
    print(f"[文件] 已保存每日文件: {daily_file.name}（{len(all_daily_ads)} 条，含新增 {len(new_ads_to_add)} 条）", flush=True)

    # ---- 追加到汇总 ----
    if unique_new:
        agg_data["ads"] = agg_data.get("ads", []) + unique_new
        agg_data["updated_at"] = datetime.now().isoformat()
        agg_data["total_ads"] = len(agg_data["ads"])
        agg_data["total_with_videos"] = sum(1 for a in agg_data["ads"] if a.get("video_urls"))
        if "keywords" not in agg_data:
            agg_data["keywords"] = KEYWORDS
        save_json(agg_file, agg_data)
        print(f"[汇总] 已更新汇总文件: {agg_file.name}（共 {len(agg_data['ads'])} 条）", flush=True)
    else:
        print(f"[汇总] 无新增记录", flush=True)

    # ---- 完成摘要 ----
    total_ads_all = len(agg_data.get("ads", []))
    print(f"\n{'='*60}", flush=True)
    print(f"列表页抓取完成！", flush=True)
    for kw, kw_ads in all_keyword_ads:
        print(f"  [{kw}] 抓取 {len(kw_ads)} 条", flush=True)
    print(f"本次新增: {len(unique_new)} 条", flush=True)
    print(f"汇总文件: {agg_file.name}（共 {total_ads_all} 条）", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"  └─ 下一步: 运行 TiktokPlaywright_detail.py 抓详情+视频", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()