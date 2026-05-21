"""
TikTok Ad Library 抓取 + 去重合并 + 视频下载
============================================ TiktokPlaywright.py

【功能说明】
  1. 抓取列表页广告（通过点击"View more"翻页加载）
  2. 逐个访问详情页，提取视频 URL（<video currentSrc>）
  3. 去重后合并到汇总文件
  4. 下载视频（支持断点续传，已下载跳过）

【Playwright 版说明】
  - 使用 Playwright 替代 Selenium/undetected-chromedriver
  - 异步并发抓取，提升稳定性
  - 翻页方式：点击 "View more" 按钮
  - 页面到底标志：出现 "End of results" 或按钮消失
  - 广告ID：从 URL 参数 ad_id= 提取
  - 视频 URL：从详情页 <video currentSrc> 获取

【配置区】保持与 run.py 一致，修改这里即可运行不同任务
"""

import asyncio
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

# ============================================================
#                    【配置区】
#                   （修改这里即可）
# ============================================================

# ----- 搜索条件（支持多个关键字）-----
KEYWORDS = [
    "Block Blast",
    "Easybrain Ltd",
    "Tripledot Studios",
    "Block Puzzle Wood Blast",
    "Block Puzzles"
    # "Block Puzzle: Diamond Star",
    # "Blockanza: Block Puzzle",
    # "Block Puzzle - Fun Games",
    # "Block Puzzle Jewel :Gem Legend",
    # "Block Puzzle - Brain Games",
    # "Block Puzzle - Brain Test Game",
    # "Block Puzzle Jewel Legend",
    # "Woody Block Puzzle Brain Game",
    # "Block Puzzle",
    # "Block Puzzle - Woody 99 2024",
    # "Block Puzzle - Wood Games",
    # "Block Blast Master:Puzzle Game",
    # "Block Puzzle Wood",
    # "Block Puzzle Jewel World",
    # "Block Puzzle Gem",
    # "Block Puzzle - Jewel Quest",
    # "Block Puzzle Blast",
    # "Jewel Blitz: Block Puzzle",
    # "Block Puzzle: Wood Brain Games",
    # "Wood Cube Puzzle"
    ]  # 搜索关键词列表，支持多个

# ----- 日期设置 -----
# AUTO_DATE = True  -> 自动模式：抓最近7天（END_DATE=今日，START_DATE=今日-6天）
# AUTO_DATE = False -> 手动模式：使用下方指定的 START_DATE 和 END_DATE
AUTO_DATE = True

START_DATE = "2026-04-16"    # 手动模式时的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-04-22"      # 手动模式时的结束日期，留空 "" 表示今天；和开始日期相同则只抓当天

# ----- 抓取模式 -----
#   MODE = "fixed"  -> 只抓固定数量（由 MAX_ADS 控制）
#   MODE = "all"    -> 抓取全部数据（直到页面底部才停止）
MODE = "all"                  # ★ 重要：选 "fixed" 或 "all"
MAX_ADS = 10                  # MODE="fixed" 时生效，表示最多抓多少条

# ----- 浏览器模式 -----
#   True  = 无头模式（不弹窗，后台运行，更稳定，推荐）
#   False = 可见浏览器（弹出 Chrome 窗口）
HEADLESS = False

# ----- 等待时间（秒）-----
# 每次点击 View more 后等待（给页面加载时间）
# 数据多或网速慢 → 可以调大，如 5 或 8
WAIT_SEC = 7

# ----- 断点续抓 -----
# True = 开启断点续抓（中断后可从上次进度恢复）
RESUME_ENABLED = True

# ----- 反爬增强 -----
# 连续 0 结果次数达到此值时触发指数退避（避免被封）
ZERO_RESULT_THRESHOLD = 3
# 指数退避初始等待秒数（会逐次加倍）
BACKOFF_BASE_SEC = 30

# ----- 并发数 -----
MAX_DOWNLOAD_WORKERS = 1       # 视频下载的并发线程数（降低避免被限流）
MAX_DETAIL_WORKERS = 2        # 详情页视频提取的并发浏览器实例数
DETAIL_BATCH = 5             # 每处理多少个详情页后保存一次（防止内存累积）

# ----- 视频提取 -----
# 每个详情页打开后等待秒数（给视频元素加载时间）
DETAIL_WAIT = 5

# ============================================================


# 忽略依赖警告（不影响程序运行）
warnings.filterwarnings('ignore', category=DeprecationWarning)

# 全局禁用 SSL 验证（解决 SSL 连接错误问题）
ssl._create_default_https_context = ssl._create_unverified_context

# 修复 urllib 的 SSL 问题
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36')]
urllib.request.install_opener(opener)


# ========== Playwright 依赖 ==========
from playwright.sync_api import sync_playwright


# ============================================================
# 【固定路径】
# （一般不需要改）
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# HTTP 请求头（下载视频时模拟浏览器）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
    'Referer': 'https://www.tiktok.com/',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Encoding': 'identity',
}


# ============================================================
# 【工具函数】
# ============================================================

def date_to_timestamp_ms(date_str):
    """
    把日期字符串转成毫秒时间戳（北京时间 00:00:00）

    例如：2026-04-14 -> 1776096000000
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    # 北京时区 +8
    tz = timezone(timedelta(hours=8))
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    return int(dt.timestamp() * 1000)


def build_url(keyword, start_date, end_date):
    """
    构建 TikTok Ad Library 搜索 URL

    参数:
        keyword:    搜索关键词（如 "Block Blast"）
        start_date: 开始日期字符串（如 "2026-04-14"）
        end_date:   结束日期字符串（留空表示今天）

    返回:
        完整 URL 字符串
    """
    # 关键词转 URL 编码（全大写，空格变 %20）
    kw = keyword.upper().replace(" ", "%20")

    # 开始时间戳（北京时间 00:00:00）
    start_ts = date_to_timestamp_ms(start_date)

    # 结束时间戳（北京时间 23:59:59）
    if end_date:
        tz = timezone(timedelta(hours=8))
        dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=tz)
        end_ts = int(dt.timestamp() * 1000)
    else:
        end_ts = date_to_timestamp_ms(datetime.now().strftime("%Y-%m-%d"))

    # URL 参数说明：
    #   adv_name=    关键词（URL编码）
    #   start_time=  开始时间戳（毫秒）
    #   end_time=    结束时间戳（毫秒）
    #   sort_type=   排序：按最近投放时间倒序
    return (
        "https://library.tiktok.com/ads?"
        f"region=all&start_time={start_ts}&end_time={end_ts}"
        f"&adv_name={kw}&adv_biz_ids=&query_type=1"
        "&sort_type=last_shown_date,desc"
    )


def keyword_to_name(keyword):
    """把关键词转成文件名（全小写无空格）"""
    return keyword.lower().replace(" ", "").replace("!", "").replace("*", "")


def resolve_dates():
    """根据 AUTO_DATE 设置决定实际抓取日期范围，返回 (start_date, end_date)"""
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
    """获取当日日期字符串（用于文件命名）"""
    return datetime.now().strftime('%Y-%m-%d')


def get_file_paths(keyword, date_str):
    """
    根据关键词和日期生成各类文件路径

    返回:
        (汇总文件路径, 每日文件路径, 视频目录路径, 日期字符串)
    """
    name = keyword_to_name(keyword)
    agg_file = OUTPUT_DIR / f"ads_{name}.json"               # 汇总文件
    daily_file = OUTPUT_DIR / f"ads_{name}_{date_str}.json" # 每日文件
    video_dir = OUTPUT_DIR / f"videos_{name}"                 # 视频目录
    return agg_file, daily_file, video_dir, date_str


# ============================================================
# 【浏览器实例管理】
# ============================================================

def make_browser_context(headless=True):
    """
    创建 Playwright 浏览器实例和上下文

    反爬措施（分层防御）:
      1. 禁用 webdriver 特征（navigator.webdriver）
      2. 注入 JS 去除常见自动化检测信号
         （webdriver 属性 / plugins / languages / permissions / chrome.runtime）
      3. 模拟真实窗口尺寸 + 随机化 viewport
      4. 设置真实的 User-Agent
      5. 禁用通知/弹窗/扩展/GPU 等非必要功能
      6. 每次新建 context 时注入 fresh fingerprint（避免复用）

    参数:
        headless: 是否使用无头模式

    返回:
        (playwright_instance, browser, context, page)
    """
    import random

    p = sync_playwright().start()

    # 随机化窗口尺寸（模拟不同设备，减少固定指纹）
    width = random.choice([1920, 1366, 1536, 1600, 1440])
    height = random.choice([1080, 768, 864, 900, 810])

    # 启动 Chromium
    browser = p.chromium.launch(
        headless=headless,
        args=[
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-notifications',
            '--disable-popup-blocking',
            f'--window-size={width},{height}',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
            '--ssl-protocol=TLSv1.2',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
            '--disable-blink-features=AutomationControlled',
            '--disable-blink-features=IsRunningOnGpuBridge',
            '--disable-ipc-flooding-protection',
        ]
    )

    # 创建浏览器上下文
    context = browser.new_context(
        viewport={'width': width, 'height': height},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
        locale='en-US',
        timezone_id='Asia/Shanghai',
        ignore_https_errors=True,
        # 不自动下载图片（加速加载 + 减少暴露）
        # offline=True 让 context 处于离线状态（后续按需启用）
    )

    # 注入 JS：去除自动化特征（多层防御）
    context.add_init_script("""
        // ---- 基础反检测 ----
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

        // ---- 去除 Chrome runtime 特征 ----
        window.chrome = window.chrome || {};
        try {
            Object.defineProperty(window.chrome, 'runtime', {
                get: () => ({ onInstalled: {}, onConnect: {}, loaded: true }),
            });
        } catch(e) {}

        // ---- 模拟真实 plugins（常见浏览器插件列表）----
        const fakePlugins = [
            { name: 'Chrome PDF Plugin',     filename: 'internal-pdf-viewer',  description: 'Portable Document Format',  version: '1.0' },
            { name: 'Chrome PDF Viewer',      filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format', version: '1.0' },
            { name: 'Native Client',          filename: 'internal-nacl-plugin', description: '', version: '1.0' },
        ];
        Object.defineProperty(navigator, 'plugins', {
            get: () => fakePlugins,
        });

        // ---- 模拟 languages ----
        const realLanguages = navigator.languages;
        if (!realLanguages || realLanguages.length === 0) {
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'zh-CN', 'zh'],
            });
        }

        // ---- 去除 permissions API 检测 ----
        const originalQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
        if (originalQuery) {
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ||
                parameters.name === 'push' ||
                parameters.name === 'midi'
            ) ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters)
            ;
        }

        // ---- 去除 automation 相关变量 ----
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.selenuim;
        delete window.webdriver;
        delete window.__webdriver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__webdriver_script_function;
        delete window.__webdriver_script_func;
        delete window.__webdriver_script_fn;
        delete window.__fxdriver_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__driver_evaluate;
        delete window.__selenium_unwrapped;
        delete window.__fxdriver_unwrapped;

        // ---- 模拟 hardware concurrency / deviceMemory ----
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        try { Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 }); } catch(e) {}

        // ---- canvas 反指纹：劫持 toDataURL ----
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        if (originalToDataURL) {
            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                // 绕过基于 canvas 的 WebGL 检测
                try {
                    const ctx = this.getContext('webgl') || this.getContext('experimental-webgl');
                    if (ctx) {
                        const ext = ctx.getExtension('WEBGL_debug_renderer_info');
                        if (ext) {
                            ctx.disable(ext.UNMASKED_VENDOR_WEBGL);
                            ctx.disable(ext.UNMASKED_RENDERER_WEBGL);
                        }
                    }
                } catch(e) {}
                return originalToDataURL.apply(this, args);
            };
        }

        // ---- 去除常见的 automation 检测事件 ----
        document.addEventListener && document.addEventListener('visibilitychange', () => {}, false);
    """)

    page = context.new_page()

    # 额外注入：运行时再补一刀（有些网站在用户交互后才检测）
    page.add_init_script("""
        try {
            const el = document.createElement('meta');
            el.name = 'robots'; el.content = 'noindex, nofollow';
            document.head.appendChild(el);
        } catch(e) {}
    """)

    print(f"[浏览器] Playwright Chromium 已启动 ({width}x{height})", flush=True)
    return p, browser, context, page


def close_browser(p, browser):
    """安全关闭浏览器实例"""
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
    """
    接受 Cookie 弹窗（如果出现）

    TikTok 有时会弹出 Cookie 同意框，需要点击接受
    """
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
    """
    点击 "View more" 按钮加载更多广告

    返回:
        True  = 成功点击，页面有新内容
        False = 按钮不存在或已消失（页面到底了）
    """
    try:
        # View more 按钮是 span.loading_more_text
        btn = page.locator("span.loading_more_text").first

        if not btn.is_visible():
            return False

        # 滚动到按钮位置，再点击
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
    """
    判断列表页是否已经加载到底

    两种情况都算到底:
      1. HTML 中出现 "End of results" 文字
      2. View more 按钮消失（找不到元素）
    """
    html = page.content()

    if "End of results" in html or "No more results" in html:
        print("[抓取] 检测到 'End of results'，列表已到底", flush=True)
        return True

    try:
        btn = page.locator("span.loading_more_text").first
        if btn.is_visible():
            return False  # 按钮还在，没到底
    except Exception:
        pass

    # 按钮消失，也视为到底
    print("[抓取] View more 按钮消失，列表已到底", flush=True)
    return True


# ============================================================
# 【广告解析（列表页）】
# ============================================================

def parse_ads_from_page(page):
    """
    从当前列表页解析所有广告

    TikTok 广告库页面结构：
      每个广告是一个 <a href="/ads/detail/?ad_id=xxx"> 链接
      链接文字包含：Ad | [文案] | [公司名] | First shown | Last shown | ...

    返回:
        广告字典列表，每条包含 library_id / platforms / ad_text 等字段
    """
    ads = []
    seen_ids = set()

    # 找所有广告详情链接
    links = page.locator("a[href*='/ads/detail/?ad_id=']").all()

    for link in links:
        href = link.get_attribute("href") or ""

        # 提取广告 ID（URL 中的 ad_id 参数值）
        m = re.search(r'ad_id=(\d+)', href)
        if not m:
            continue
        ad_id = m.group(1)
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        # 解析链接文字
        text = link.text_content() or ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        ad = {
            "library_id": ad_id,
            "index": len(ads) + 1,
            "platforms": ["TikTok"],              # TikTok 广告库固定是 TikTok 平台
            "video_urls": [],                    # 视频 URL 后续在详情页提取
            # 拼接完整详情页 URL
            "detail_url": href if href.startswith('http')
                           else f"https://library.tiktok.com{href}",
        }

        # 从文字行中提取各字段
        for line in lines:
            if line.startswith('First shown:'):
                ad["first_shown"] = line.replace('First shown:', '').strip()
            elif line.startswith('Last shown:'):
                ad["last_shown"] = line.replace('Last shown:', '').strip()
            elif line.startswith('Unique users seen:'):
                ad["unique_users"] = line.replace('Unique users seen:', '').strip()
            # 广告文案（过滤掉系统关键字）
            elif line not in ['Ad', 'Details', 'View details'] and len(line) > 3:
                if 'shown' not in line and 'users' not in line:
                    ad["ad_text"] = line[:500]

        ads.append(ad)

    return ads


# ============================================================
# 【视频提取（详情页）】
# ============================================================

def extract_video_from_detail(page, ad_id, wait_sec):
    """
    访问广告详情页，提取视频 URL

    原理：
      详情页 HTML 中有 <video> 标签，
      其 currentSrc 属性就是可直接下载的视频 URL

    参数:
        page:      Playwright Page 实例
        ad_id:     广告 ID
        wait_sec:  打开详情页后等待秒数（给视频元素加载时间）

    返回:
        视频 URL 字符串，或 None（无视频或提取失败）
    """
    try:
        detail_url = f"https://library.tiktok.com/ads/detail/?ad_id={ad_id}"
        page.goto(detail_url)
        page.wait_for_timeout(wait_sec * 1000)

        # 找 video 标签
        video_el = page.locator("video").first
        if not video_el:
            return None

        # currentSrc 是真正的视频地址（src 可能为空）
        # 如果 currentSrc 为空或 null，使用 src 兜底
        url = video_el.get_attribute('currentSrc') or video_el.get_attribute('src') or ''
        if not url or url == 'null' or len(url) < 20:
            return None

        return url

    except Exception:
        return None


def mine_videos_from_details(lib_ids, wait_sec, batch_size):
    """
    批量提取广告详情页视频（分批处理，定期保存）

    策略：
      - 每处理 batch_size 个详情页后，保存一次 JSON（防止内存崩溃丢数据）
      - 使用多浏览器实例并行提取
      - 进度实时打印

    参数:
        lib_ids:    广告 ID 列表
        wait_sec:   每个详情页等待秒数
        batch_size: 每多少个保存一次

    返回:
        字典 { library_id: 视频URL, ... }
    """
    results = {}  # 最终结果
    total = len(lib_ids)

    print(f"[视频] 开始提取 {total} 个详情页视频（每批{batch_size}个，每批后保存）...", flush=True)

    # 分批
    all_batches = [lib_ids[i:i+batch_size] for i in range(0, len(lib_ids), batch_size)]

    for batch_idx, batch_ids in enumerate(all_batches, 1):
        batch_num = len(all_batches)
        print(f"\n[视频] 批次 {batch_idx}/{batch_num}（{len(batch_ids)} 个详情页）...", flush=True)

        # 本批并发处理（每个线程一个浏览器实例）
        chunk_size = max(1, len(batch_ids) // MAX_DETAIL_WORKERS)
        chunks = [batch_ids[i:i+chunk_size] for i in range(0, len(batch_ids), chunk_size)]

        def process_chunk(chunk):
            """单浏览器处理一组详情页"""
            pw, browser, context, page = make_browser_context(headless=HEADLESS)
            chunk_result = {}
            try:
                for lid in chunk:
                    url = extract_video_from_detail(page, lid, wait_sec)
                    chunk_result[lid] = url
            finally:
                close_browser(pw, browser)
            return chunk_result

        chunk_all = []
        with ThreadPoolExecutor(max_workers=MAX_DETAIL_WORKERS) as ex:
            futures = [ex.submit(process_chunk, chunk) for chunk in chunks]
            for future in as_completed(futures):
                chunk_all.append(future.result())

        # 合并本批结果
        for chunk_result in chunk_all:
            results.update(chunk_result)

        found_so_far = sum(1 for v in results.values() if v)
        done = min(batch_idx * batch_size, total)
        print(f"[视频] 进度: {done}/{total}，当前共 {found_so_far} 个视频", flush=True)

    found = sum(1 for v in results.values() if v)
    print(f"[视频] 提取完成，共 {found}/{total} 个视频 URL", flush=True)
    return results


# ============================================================
# 【详情页抓取（完整数据）】
# ============================================================

def scrape_tiktok_detail_page(page, ad_id, wait_sec):
    """
    访问 TikTok 广告详情页（https://library.tiktok.com/ads/detail/?ad_id=xxx）
    提取页面上的详细信息（公司信息、投放数据、受众覆盖等）

    参数:
        page:      Playwright Page 实例
        ad_id:     广告 ID
        wait_sec:  打开详情页后等待秒数

    返回:
        详情页抓取的字典数据，包含所有字段；提取失败返回空字典
    """
    from bs4 import BeautifulSoup
    import random

    detail_url = f"https://library.tiktok.com/ads/detail/?ad_id={ad_id}"
    data = {
        "ad_id": ad_id,
        "detail_url": detail_url,
        "scrape_time": datetime.now().isoformat(),
        # 基本信息
        "advertiser_name": "",
        "advertiser_description": "",
        "ad_text": "",
        # 投放信息
        "first_seen": "",
        "last_seen": "",
        "delivery_status": "",
        "active_ad_delivery": "",
        # 受众
        "target_audience_size": "",
        "gender_summary": "",
        "age_summary": "",
        "gender_detail": {},
        "age_detail": {},
        "locations": [],
        "locations_detail": {},
        "language": "",
        # 覆盖
        "unique_users": "",
        "impressions": "",
        # 创意
        "video_url": "",
        "thumbnail_url": "",
        # 原始文本
        "raw_text": "",
    }

    try:
        time.sleep(random.uniform(2, 8))  # 随机延迟2-8秒，模拟真人操作
        page.goto(detail_url)
        page.wait_for_timeout(wait_sec * 1000)

        # 获取页面源码
        html = page.content()

        # 获取页面文本
        full_text = page.locator("body").text_content() or ""
        data["raw_text"] = full_text

        # 解析 HTML
        soup = BeautifulSoup(html, "html.parser")

        # ==================== 提取基本信息 ====================

        # ---- 广告文本（赞助内容）----
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

        # ---- 公司名（Advertiser）----
        # 格式：Advertiser北京阿瑞斯蒂科技有限公司See all ads
        # 注意：中文字符前无空格，公司名与 See all ads 之间也无空格
        # 使用 `Advertiser` 后面捕获所有非 'S' 字符（到 "See all" 前的 S）
        advertiser_m = re.search(r'Advertiser([^S]+?)\s*See all', full_text)
        if advertiser_m:
            data["advertiser_name"] = advertiser_m.group(1).strip()
        else:
            # 兜底：找 "Ad paid for by" 之后的那个公司名
            advertiser_m2 = re.search(r'Ad paid for by\s+([A-Z][^\n]+?)\s+Advertiser', full_text)
            if advertiser_m2:
                data["advertiser_name"] = advertiser_m2.group(1).strip()

        # ---- 付费方（Ad paid for by）----
        # 格式：Ad paid for byBLUEVISION INTERACTIVE LIMITEDAdvertiser（公司名与 Advertiser 之间无空格）
        # 捕获 "Ad paid for by" 之后，到 "Advertiser" 之前的公司名
        payer_m = re.search(r'Ad paid for by(.+?)\s*Advertiser', full_text)
        if payer_m:
            data["payer_name"] = payer_m.group(1).strip()
        else:
            # 兜底：直接搜索 "Ad paid for by" 后的文字
            payer_m2 = re.search(r'Ad paid for by([^\n]+)', full_text)
            if payer_m2:
                data["payer_name"] = payer_m2.group(1).strip()[:200]

        # ---- 广告主注册地 ----
        # ---- 广告主注册地 ----
        # 格式：Advertiser's registered locationChinablock.blast（国家名后紧跟广告主账号，无分隔）
        # 以 "registered location" 开头，捕获直到下一个以字母开头+小写字母的词（如 block.blast）
        loc_m = re.search(r"registered location\s*([A-Za-z]+)", full_text)
        if loc_m:
            data["advertiser_registered_location"] = loc_m.group(1).strip()

        # ---- 首次/最后投放时间 ----
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

        # ---- 目标观众人数 ----
        # 注意：Facebook/TikTok 页面有时值紧跟标签无空格，如 "Target audience size289.4M-353.7M"
        audience_m = re.search(r'Target audience size\s*([\d\.,]+[MBK]?-?[\d\.,]+[MBK]?)', full_text, re.IGNORECASE)
        if audience_m:
            data["target_audience_size"] = audience_m.group(1).strip()
        else:
            # 兜底：找 "Target audience size" 后的第一行非空内容
            audience_m2 = re.search(r'Target audience size\s*([^\n]+)', full_text)
            if audience_m2:
                val = audience_m2.group(1).strip().split('\n')[0]
                # 过滤掉纯数字序号（表格行号）
                if val and not re.match(r'^\d+$', val):
                    data["target_audience_size"] = val

        # ---- Gender / Age / Location 表格解析（HTML）----
        # 查找所有 targeting 表格
        targeting_tables = soup.find_all("table", role="table")

        # 打勾颜色常量
        CHECK_COLOR = "#FE2C55"   # 粉色 = 勾选
        UNCHECK_COLOR = "rgba(22, 24, 35, 0.34)"  # 灰色 = 未勾选

        def is_checked(svg_tag):
            """检查 SVG 是否表示勾选状态"""
            if not svg_tag or not svg_tag.get("fill"):
                return False
            color = svg_tag.get("fill", "")
            if color.lower() == "currentcolor":
                color = svg_tag.get("color", "") or ""
            return CHECK_COLOR.lower() in color.lower()

        def parse_targeting_table(table, col_headers):
            """
            解析 targeting 表格，返回 (country_rows, global_flags)
            country_rows: [(country_name, {col_name: checked_bool}), ...]
            global_flags: {col_name: checked_bool} 如果是第一行是全局勾选框
            """
            rows = table.find_all("tr", role="row")
            if not rows:
                return [], {}

            results = []
            global_flags = {}

            # 解析表头
            header_row = rows[0]
            header_cols = header_row.find_all(["th", "td"])
            col_cols = header_row.find_all("th", scope="col")
            col_count = len(col_cols) if col_cols else len(header_cols)

            # 检查第一行是否是全局勾选（没有国家名列）
            first_data_row = rows[1] if len(rows) > 1 else None
            if first_data_row:
                cells = first_data_row.find_all("td", role="cell")
                if cells and cells[0].get("aria-colindex") == "1":
                    first_cell_text = cells[0].get_text(strip=True)
                    if not first_cell_text.isdigit():
                        # 第一行是全局勾选行，不是国家
                        for cell in cells:
                            col_idx = int(cell.get("aria-colindex", 0)) - 1
                            if col_idx < len(col_headers):
                                svg = cell.find("svg")
                                global_flags[col_headers[col_idx]] = is_checked(svg)

            # 解析每个国家的数据行
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

        # 遍历所有 targeting 表格，找到 Gender / Age / Location
        for table in targeting_tables:
            header_row = table.find("thead")
            if not header_row:
                continue
            header_cells = header_row.find_all("th", scope="col")
            header_titles = [th.get_text(strip=True) for th in header_cells]

            # Gender 表格检测
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

            # Age 表格检测
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
                        if max_age >= 65:
                            data["age_summary"] = f"{min_age}-65+"
                        else:
                            data["age_summary"] = f"{min_age}-{max_age}"
                else:
                    data["age_summary"] = "不限"

        # ---- Location 国家列表 ----
        location_sections = soup.find_all("h2", class_="ad_details_targeting_title")
        for section in location_sections:
            if section.get_text(strip=True) == "Location":
                next_table = section.find_next_sibling("div")
                if next_table:
                    table = next_table.find("table", role="table")
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
        # 注意：TikTok 详情页 currentSrc 为空，视频 URL 在 src 属性
        try:
            video_el = page.locator("video").first
            # src 优先（TikTok 详情页 video 标签的 URL 在 src，不在 currentSrc）
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
        import traceback
        traceback.print_exc()

    return data


def mine_details_batch(lib_ids, wait_sec, batch_size, detail_callback=None):
    """
    批量抓取详情页（分批处理，定期保存）
    每批处理完立即回调保存，防止内存累积

    反爬机制：
      - 检测连续 n 批 0 有效数据，触发指数退避等待
      - 退避等待后仍无效则警告并继续（不中断流程）

    参数:
        lib_ids:         广告 ID 列表
        wait_sec:        每页等待秒数
        batch_size:      每批处理数量
        detail_callback: 每批完成后的回调函数，参数为 (batch_idx, batch_results)
    """
    import random

    total = len(lib_ids)
    print(f"[详情] 开始批量抓取 {total} 个详情页（每批 {batch_size} 个）...", flush=True)

    all_batches = [lib_ids[i:i+batch_size] for i in range(0, len(lib_ids), batch_size)]

    zero_streak = 0   # 连续 0 有效数据的批次数

    for batch_idx, batch_ids in enumerate(all_batches, 1):
        batch_num = len(all_batches)

        # ---- 反爬：连续 0 结果 → 指数退避 ----
        if zero_streak >= ZERO_RESULT_THRESHOLD:
            backoff_sec = BACKOFF_BASE_SEC * (2 ** (zero_streak - ZERO_RESULT_THRESHOLD))
            backoff_cap = min(backoff_sec, 300)  # 最多等 5 分钟
            print(f"\n[⚠️ 反爬] 连续 {zero_streak} 批 0 有效数据，指数退避等待 {backoff_cap:.0f}s...", flush=True)
            print(f"[⚠️ 反爬] 建议：降低并发、开启 RESUME_ENABLED=true 中断后恢复，或切换 IP", flush=True)
            time.sleep(backoff_cap)

        print(f"\n[详情] 批次 {batch_idx}/{batch_num}（{len(batch_ids)} 个）...", flush=True)

        results = {}
        pw, browser, context, page = make_browser_context(headless=HEADLESS)
        try:
            for i, lid in enumerate(batch_ids):
                detail_data = scrape_tiktok_detail_page(page, lid, wait_sec)
                results[lid] = detail_data
                time.sleep(1)
                # 每处理5个广告后额外休息5-10秒
                if i % 5 == 4:
                    print(f"[详情] 休息一下...", flush=True)
                    time.sleep(random.uniform(5, 10))
        finally:
            close_browser(pw, browser)

        found = sum(1 for v in results.values() if v and v.get("advertiser_name"))
        print(f"[详情] 批次 {batch_idx} 完成，有效数据 {found}/{len(batch_ids)}", flush=True)

        # 更新连续 0 结果计数
        if found == 0:
            zero_streak += 1
        else:
            zero_streak = 0  # 重置计数

        # 回调保存（防止内存累积）
        if detail_callback:
            detail_callback(batch_idx, results)

    print(f"[详情] 批量抓取完成，共 {total} 个详情页", flush=True)
    return results


# ============================================================
# 【列表页滚动抓取】
# ============================================================

def scroll_and_collect(page, target_url, wait_sec, mode, max_ads, batch_save_size=20, batch_callback=None):
    """
    打开列表页，循环点击 View more 抓取广告

    抓取逻辑：
      1. 打开 URL，等待初始加载
      2. 解析当前页面所有广告
      3. 点击 View more，加载更多
      4. 重复直到停止条件

    停止条件（MODE="fixed"）:
      - 达到 MAX_ADS 条时停止

    停止条件（MODE="all"）:
      - 出现 "End of results"
      - View more 按钮消失
      - 连续 2 次无法点击

    参数:
        page:       Playwright Page 实例
        target_url: 列表页 URL
        wait_sec:   每次点击后等待秒数
        mode:       "fixed" 或 "all"
        max_ads:    MODE="fixed" 时的上限

    返回:
        广告字典列表
    """
    print(f"[抓取] 访问: {target_url}", flush=True)
    page.goto(target_url)
    page.wait_for_timeout(8000)  # 等待页面初始加载
    print(f"[抓取] 页面标题: {page.title()}", flush=True)

    # 处理 Cookie 弹窗
    accept_cookies_if_present(page)

    ads = []
    seen_ids = set()
    click_count = 0       # 已点击次数
    empty_clicks = 0      # 连续点击无新广告的次数
    zero_streak = 0       # 连续 0 新广告的点击次数

    # ---- 第1次解析（初始页面，不点击）----
    for ad in parse_ads_from_page(page):
        if ad["library_id"] not in seen_ids:
            seen_ids.add(ad["library_id"])
            ads.append(ad)
    print(f"[抓取] 初始广告: {len(ads)} 条", flush=True)

    # ---- 循环点击 View more ----
    while True:
        # ---- 停止条件检查 ----
        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止收集", flush=True)
            break

        if mode == "all" and is_page_exhausted(page):
            print("[抓取] 页面已到底，停止收集", flush=True)
            break

        # ---- 反爬：连续多批 0 新广告 → 指数退避 ----
        if zero_streak >= ZERO_RESULT_THRESHOLD:
            backoff_sec = BACKOFF_BASE_SEC * (2 ** (zero_streak - ZERO_RESULT_THRESHOLD))
            backoff_cap = min(backoff_sec, 300)
            print(f"\n[⚠️ 反爬] 连续 {zero_streak} 次无新广告，指数退避等待 {backoff_cap:.0f}s...", flush=True)
            print(f"[⚠️ 反爬] 建议：降低并发、开启 RESUME_ENABLED=true 中断后恢复，或切换 IP", flush=True)
            time.sleep(backoff_cap)

        # ---- 点击 View more ----
        print(f"[抓取] 等待页面加载（点击 #{click_count + 1}）...", flush=True)
        clicked = click_view_more(page, wait_sec)

        if clicked:
            click_count += 1
            empty_clicks = 0
        else:
            empty_clicks += 1
            print(f"[抓取] 连续第 {empty_clicks} 次无法点击 View more", flush=True)
            if empty_clicks >= 2:
                print("[抓取] 连续2次无法点击，停止", flush=True)
                break

        # ---- 解析当前页面所有广告 ----
        new_count = 0
        for ad in parse_ads_from_page(page):
            if ad["library_id"] not in seen_ids:
                if mode == "fixed" and len(ads) >= max_ads:
                    break
                seen_ids.add(ad["library_id"])
                ads.append(ad)
                new_count += 1

        print(f"  已收集 {len(ads)} 条 (+{new_count} 本轮，点击#{click_count})", flush=True)

        # 更新 zero_streak（用于反爬指数退避）
        if new_count == 0:
            zero_streak += 1
        else:
            zero_streak = 0

        # ---- MODE=fixed 二次检查 ----
        if mode == "fixed" and len(ads) >= max_ads:
            print(f"[抓取] 已达固定上限 {max_ads} 条，停止", flush=True)
            break

    print(f"[抓取] 列表页抓取完成，共 {len(ads)} 条广告", flush=True)
    return ads


# ============================================================
# 【文件处理：去重 + 合并】
# ============================================================

def load_json(filepath):
    """安全加载 JSON（文件不存在或损坏时返回 None）"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_json(filepath, data):
    """安全保存 JSON（缩进2字节）"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_deduplicate(new_ads, agg_ads):
    """
    去除重复：用 library_id 对比，返回新增记录

    返回:
        (去重后的广告列表, 被剔除的重复数量)
    """
    agg_ids = {ad["library_id"] for ad in agg_ads if ad.get("library_id")}
    unique = [ad for ad in new_ads
               if ad.get("library_id") and ad["library_id"] not in agg_ids]
    dup_count = len(new_ads) - len(unique)
    return unique, dup_count


def process_files(keyword, ads, scrape_url, date_str):
    """
    处理每日文件和汇总文件

    每日文件：直接覆盖（同一日期只保留一份）
    汇总文件：读取已有 → 对比去重 → 追加新记录

    参数:
        keyword:    关键词
        ads:        本次抓取的所有广告
        scrape_url: 抓取时用的 URL（记录到元数据）
        date_str:   日期字符串

    返回:
        (daily_file, agg_file, video_dir, unique_new)
    """
    agg_file, daily_file, video_dir, _ = get_file_paths(keyword, date_str)

    print(f"\n{'='*50}", flush=True)
    print(f"[文件] 每日文件: {daily_file.name}", flush=True)
    print(f"[文件] 汇总文件: {agg_file.name}", flush=True)
    print(f"[文件] 视频目录: {video_dir.name}", flush=True)

    # ---- 1. 保存每日文件（覆盖）----
    daily_data = {
        "scrape_time": datetime.now().isoformat(),
        "url": scrape_url,
        "keyword": keyword,
        "start_date": date_str,
        "ads_count": len(ads),
        "ads_with_videos": sum(1 for a in ads if a.get("video_urls")),
        "ads": ads,
    }
    save_json(daily_file, daily_data)
    print(f"[文件] 已保存每日文件（{len(ads)} 条广告）", flush=True)

    # ---- 2. 处理汇总文件 ----
    agg_data = load_json(agg_file)

    # 不存在则创建新结构
    if agg_data is None:
        agg_data = {
            "keyword": keyword,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_ads": 0,
            "total_with_videos": 0,
            "ads": [],
        }
        print(f"[文件] 汇总文件不存在，创建新文件", flush=True)
    else:
        print(f"[文件] 汇总已有 {len(agg_data.get('ads', []))} 条记录", flush=True)

    # ---- 3. 去重对比 ----
    existing_ads = agg_data.get("ads", [])
    unique_new, dup_count = merge_deduplicate(ads, existing_ads)
    print(f"[去重] 本次 {len(ads)} 条，去重 {dup_count} 条，新增 {len(unique_new)} 条", flush=True)

    # ---- 4. 追加到汇总文件 ----
    if unique_new:
        agg_data["ads"] = agg_data.get("ads", []) + unique_new
        agg_data["updated_at"] = datetime.now().isoformat()
        agg_data["total_ads"] = len(agg_data["ads"])
        agg_data["total_with_videos"] = sum(1 for a in agg_data["ads"] if a.get("video_urls"))
        save_json(agg_file, agg_data)
        print(f"[汇总] 已追加，汇总共 {len(agg_data['ads'])} 条", flush=True)
    else:
        print(f"[汇总] 无新增记录", flush=True)

    return daily_file, agg_file, video_dir, unique_new


# ============================================================
# 【视频下载】
# ============================================================

def download_single_video(args):
    """
    下载单个视频（供线程池调用）

    已有文件则跳过（断点续传）
    支持重试机制，应对 SSL 错误和连接中断
    """
    import ssl
    import random

    url, filepath, lib_id = args

    if filepath.exists():
        print(f"  [跳过] {filepath.name} 已存在", flush=True)
        return {"lib_id": lib_id, "status": "skipped", "path": str(filepath)}

    # 创建 SSL 上下文（处理 SSL 错误）
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    max_retries = 3
    retry_delay = 5  # 初始等待秒数

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120, context=ssl_context) as resp:
                size = 0
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = resp.read(1024 * 512)   # 每次读 512KB
                        if not chunk:
                            break
                        f.write(chunk)
                        size += len(chunk)

            print(f"  [完成] {filepath.name} ({size/1024/1024:.1f}MB)", flush=True)
            return {"lib_id": lib_id, "status": "success", "path": str(filepath), "size_mb": size/1024/1024}

        except (ssl.SSLError, urllib.error.URLError) as e:
            err_str = str(e)
            if attempt < max_retries - 1:
                wait_time = retry_delay + random.uniform(1, 5)
                print(f"  [重试] lib={lib_id} (尝试 {attempt+1}/{max_retries}) 等待 {wait_time:.1f}s: {err_str[:80]}", flush=True)
                time.sleep(wait_time)
                retry_delay *= 2  # 指数退避
            else:
                print(f"  [失败] lib={lib_id}: {err_str}", flush=True)
                return {"lib_id": lib_id, "status": "error", "error": err_str}

        except Exception as e:
            print(f"  [失败] lib={lib_id}: {e}", flush=True)
            return {"lib_id": lib_id, "status": "error", "error": str(e)}

    return {"lib_id": lib_id, "status": "error", "error": "max retries exceeded"}


def download_videos(daily_file, video_dir, keyword):
    """
    从每日 JSON 文件读取广告，下载其中视频

    逻辑：
      1. 读取每日 JSON
      2. 找出有视频 URL 的广告
      3. 扫描已下载目录，跳过已有文件
      4. 并发下载剩余视频
    """
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(daily_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ads = data.get('ads', [])
    ads_video = [a for a in ads if a.get('video_urls')]

    print(f"\n{'='*50}", flush=True)
    print(f"[下载] 视频目录: {video_dir}", flush=True)
    print(f"[下载] 待下载广告: {len(ads_video)} 个", flush=True)

    if not ads_video:
        print("[下载] 没有带视频的广告")
        return

    # 准备任务
    tasks = []
    for ad in ads_video:
        lib_id = ad['library_id']
        url = ad['video_urls'][0]
        filepath = video_dir / f"{lib_id}.mp4"
        tasks.append((url, filepath, lib_id))

    # 过滤已下载
    existing = {f.stem for f in video_dir.glob("*") if f.is_file()}
    to_dl = [t for t in tasks if t[1].stem not in existing]
    done = len(tasks) - len(to_dl)

    print(f"[下载] 已有视频: {done} 个，待下载: {len(to_dl)} 个", flush=True)
    if not to_dl:
        print("[下载] 全部视频已下载完毕")
        return

    # 并发下载
    success, skipped, failed = 0, done, 0
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

    print(f"[完成] 成功: {success} | 跳过: {skipped} | 失败: {failed} | 大小: {total_size:.1f}MB", flush=True)


# ============================================================
# 【主流程】
# ============================================================

def main():
    """
    程序入口，按顺序执行：

      第1步：对每个关键字分别抓取列表页广告（View more 翻页）
      第2步：逐个访问详情页提取视频 URL 和详细信息
      第3步：所有关键字合并去重 → 统一汇总文件 + 每日文件
      第4步：下载视频（每个关键字单独子目录）
    """
    # ---- 确定日期 ----
    start_date, end_date = resolve_dates()
    today_str = get_today_date_str()

    # 日期用于文件名（单日或范围）
    if start_date == end_date:
        date_str = start_date
    else:
        date_str = f"{start_date}_to_{end_date}"

    # 模式描述
    if MODE == "fixed":
        mode_desc = f"固定数量模式（上限 {MAX_ADS} 条）"
    else:
        mode_desc = "全量模式（抓取全部数据）"

    # ---- 文件路径（统一命名，不含关键字）----
    agg_file = OUTPUT_DIR / "ads_all.json"
    daily_file = OUTPUT_DIR / f"ads_{today_str}.json"
    video_dir = OUTPUT_DIR / "videos"

    print("=" * 60, flush=True)
    print(f"TikTok Ad Library 抓取 + 合并 + 视频下载 (Playwright版)", flush=True)
    print(f"关键词: {KEYWORDS}", flush=True)
    print(f"日期范围: {start_date} ~ {end_date}", flush=True)
    print(f"当日日期（文件命名）: {today_str}", flush=True)
    print(f"汇总文件: {agg_file.name}", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"模式: {mode_desc}", flush=True)
    print(f"浏览器: {'无头模式' if HEADLESS else '可见浏览器'}", flush=True)
    print("=" * 60, flush=True)

    # ---- 逐个关键字抓取 ----
    all_keyword_ads = []   # 每个元素 (keyword, [ads列表])

    for kw in KEYWORDS:
        print(f"\n{'='*50}", flush=True)
        print(f"[关键词] 开始抓取: {kw}", flush=True)

        scrape_url = build_url(kw, start_date, end_date)
        print(f"[URL] {scrape_url}", flush=True)

        pw, browser, context, page = None, None, None, None
        kw_ads = []
        try:
            print(f"\n>>> 第1步：抓取 [{kw}] 列表页广告 >>>", flush=True)
            print("[启动] Playwright Chromium...", flush=True)
            pw, browser, context, page = make_browser_context(headless=HEADLESS)
            kw_ads = scroll_and_collect(page, scrape_url, WAIT_SEC, MODE, MAX_ADS,
                                        batch_save_size=20, batch_callback=None)
            print(f"\n[第1步完成] [{kw}] 共收集 {len(kw_ads)} 条广告", flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[错误] [{kw}] 抓取失败: {e}", flush=True)
        finally:
            if browser:
                close_browser(pw, browser)

        # ---- 第2步：抓取详情页（断点续抓）----
        if kw_ads:
            # 断点续抓：加载已收集的详情页数据，跳过已有
            existing_detail_ids = set()
            if RESUME_ENABLED:
                existing_daily = load_json(daily_file)
                if existing_daily and existing_daily.get('ads'):
                    for existing_ad in existing_daily['ads']:
                        if existing_ad.get('library_id') and existing_ad.get('tiktok_detail'):
                            existing_detail_ids.add(existing_ad['library_id'])
                    print(f"[续抓] 检测到每日文件已有 {len(existing_detail_ids)} 条详情数据，将跳过", flush=True)

            lib_ids = [a["library_id"] for a in kw_ads if a.get("library_id")]
            lib_ids_to_scrape = [lid for lid in lib_ids if lid not in existing_detail_ids]
            print(f"[详情] 待抓详情: {len(lib_ids_to_scrape)} 个（跳过 {len(lib_ids) - len(lib_ids_to_scrape)} 个已有）", flush=True)

            if not lib_ids_to_scrape:
                print(f"[详情] 所有详情已抓完，跳过第2步", flush=True)
                # 将已有详情的广告也补回 kw_details
                for ad in kw_ads:
                    lid = ad["library_id"]
                    if lid in existing_detail_ids:
                        for existing_ad in existing_daily.get('ads', []):
                            if existing_ad.get('library_id') == lid and existing_ad.get('tiktok_detail'):
                                ad["tiktok_detail"] = existing_ad["tiktok_detail"]
                                if existing_ad["tiktok_detail"].get("video_url"):
                                    ad["video_urls"] = [existing_ad["tiktok_detail"]["video_url"]]
                                break
            else:
                kw_details = {}

                def detail_cb(batch_idx, batch_results):
                    nonlocal kw_details
                    kw_details.update(batch_results)
                    print(f"[详情保存] [{kw}] 批次 {batch_idx} 完成，已累计 {len(kw_details)} 条", flush=True)

                mine_details_batch(lib_ids_to_scrape, wait_sec=DETAIL_WAIT, batch_size=DETAIL_BATCH,
                                  detail_callback=detail_cb)

                # 将新抓到的详情写入对应广告
                for ad in kw_ads:
                    lid = ad["library_id"]
                    if lid in kw_details:
                        detail = kw_details[lid]
                        ad["tiktok_detail"] = detail
                        if detail.get("video_url"):
                            ad["video_urls"] = [detail["video_url"]]
                    elif lid in existing_detail_ids:
                        # 补回已有关切（从 daily 文件中查找）
                        for existing_ad in existing_daily.get('ads', []):
                            if existing_ad.get('library_id') == lid and existing_ad.get('tiktok_detail'):
                                ad["tiktok_detail"] = existing_ad["tiktok_detail"]
                                if existing_ad["tiktok_detail"].get("video_url"):
                                    ad["video_urls"] = [existing_ad["tiktok_detail"]["video_url"]]
                                break

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

    # ==================== 第3步：文件处理（去重 + 合并）====================
    print(f"\n>>> 第3步：去重并更新汇总文件 >>>", flush=True)

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
    existing_ids = {ad.get("library_id") for ad in existing_ads if ad.get("library_id")}

    unique_new = []
    for ad in ads_pool:
        if ad.get("library_id") and ad["library_id"] not in existing_ids:
            unique_new.append(ad)
            existing_ids.add(ad["library_id"])

    print(f"[去重] 本次 {len(ads_pool)} 条，新增 {len(unique_new)} 条（不重复）", flush=True)

    # 保存每日文件（all-in-one，不区分关键字）
    daily_data = {
        "scrape_time": datetime.now().isoformat(),
        "url": f"multi-keyword: {KEYWORDS}",
        "keywords": KEYWORDS,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
        "ads_count": len(ads_pool),
        "new_ads_count": len(unique_new),
        "total_in_summary": len(existing_ads) + len(unique_new),
        "ads": ads_pool,
    }
    save_json(daily_file, daily_data)
    print(f"[文件] 已保存每日文件: {daily_file.name}（{len(ads_pool)} 条）", flush=True)

    # 追加到汇总
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

    # ==================== 第4步：下载视频（每个关键字单独子目录）====================
    print(f"\n>>> 第4步：下载视频 >>>", flush=True)

    for kw, kw_ads in all_keyword_ads:
        kw_video_dir = video_dir / keyword_to_name(kw) if len(KEYWORDS) > 1 else video_dir
        kw_video_dir.mkdir(parents=True, exist_ok=True)
        kw_ids = [a["library_id"] for a in kw_ads if a.get("library_id")]
        kw_ads_in_pool = [a for a in ads_pool if a["library_id"] in kw_ids]
        if kw_ads_in_pool:
            kw_daily_data = {
                "scrape_time": datetime.now().isoformat(),
                "keyword": kw,
                "ads": [{k: v for k, v in a.items()} for a in kw_ads_in_pool],
            }
            tmp_path = OUTPUT_DIR / f"_tmp_dl_{keyword_to_name(kw)}_{today_str}.json"
            save_json(tmp_path, kw_daily_data)
            print(f"[下载] [{kw}] 视频目录: {kw_video_dir.name}", flush=True)
            download_videos(tmp_path, kw_video_dir, kw)
            tmp_path.unlink()
        else:
            print(f"[下载] [{kw}] 无广告，跳过", flush=True)

    # ---- 完成摘要 ----
    total_ads_all = len(agg_data.get("ads", []))
    print(f"\n{'='*60}", flush=True)
    print(f"全部完成！", flush=True)
    for kw, kw_ads in all_keyword_ads:
        print(f"  [{kw}] 抓取 {len(kw_ads)} 条", flush=True)
    print(f"本次新增: {len(unique_new)} 条", flush=True)
    print(f"汇总文件: {agg_file.name}（共 {total_ads_all} 条）", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
