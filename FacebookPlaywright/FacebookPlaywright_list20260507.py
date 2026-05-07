"""
Facebook Ad Library Scraper - Part 1: List Page
================================================
抓列表页，提取 library_id + 基础字段（标题/开始日期/平台/广告文本/ advertiser_name 等）。
输出: output/<keyword>/ads_<keyword>_<date>.json

纯 Playwright 实现（不依赖 Selenium 或外部 Chrome）。

Usage:
  python FacebookPlaywright_list.py
  python FacebookPlaywright_list.py --keyword "Block Blast" --days 7
"""

import sys
import os

# Fix stdout encoding on Windows (GBK console can't handle emoji)
# 同时强制无缓冲输出，避免 exec 看不到日志
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

import json
import time
import re
import shutil
import urllib.request
import urllib.parse
import warnings
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====== 代理配置（根据你的梯子端口修改）====================
PROXY_SERVER = "http://127.0.0.1:7890"   # ← 改成你的代理端口，7890 是 Clash 默认

# ====== 浏览器配置文件（保留登录状态）====================
# 设置一个专用的 Chrome 配置目录（建议用脚本目录下的 facebook_profile）
# 首次使用前，先运行 python setup_chrome_profile.py，它会打开浏览器让你登录 Facebook
# 登录后关闭浏览器，之后主程序会自动复用这个配置的登录状态
#
# 如果设为空或 ANONYMOUS_MODE=True，则使用匿名模式（可能无法看到广告内容）
CHROME_USER_DATA_DIR = r"C:\Users\Ivy\.openclaw\workspace\facebook_chrome_profile"
ANONYMOUS_MODE = False

# ====== CONFIG ======
# 搜索关键词，支持多个
KEYWORDS = [
    "Block Blast",
    "Block Journey - Puzzle Games",
    "WOODUKU",#手动搜索是这个无广告素材
    "Woodoku Blast",#手动搜索是这个无广告素材
    "Wood Block - Puzzle Games",
    "Block Rush - Block Puzzle Game",
    "Block Sudoku Woody Puzzle Game",#手动搜索了这个无广告素材
    "Vita Block for Seniors",#很多赞助广告
    "Block Puzzle: Block Smash Game",#全是赞助广告
    "Woody Block Puzzle",#全是赞助广告
    "Block Puzzle",
    "Block Puzzle Gem: Jewel Blast",#手动搜索是这个无广告素材
    "Blockudoku®: Block Puzzle Game",
    "Woodoku - Wood Block Puzzle",#手动搜索是这个无广告素材
    "My Block",
    "Block Puzzle Jewel",
    "Block Puzzle：Bloom Journey",#手动搜索是这个无广告素材
    "Block Puzzle Wood",
    "Block Sudoku - Wood Puzzle"
    "Puzzle Game",
    "Wood Block Puzzle",
    "Blockanza: Block Puzzle",#手动搜索是这个无广告素材
    "Block Puzzle - Gem Block",
    "Woody Block Puzzle Classic",
    "Playdoku: Block Puzzle Games",#手动搜索是这个无广告素材
    "Block Puzzle - Sudoku Mode",#手动搜索是这个无广告素材
    "Block Puzzle Jewel: Blast Game",#手动搜索是这个无广告素材
    "Block Crush: Block Puzzle Game",
    "Block Puzzle: Wood Sudoku Game",#手动搜索是这个无广告素材
    "BT Block Puzzle: Block Blast",#手动搜索是这个无广告素材
    "Block Puzzle: Block Smash Game",#全是赞助广告
    "Block Crush: Wood Block Puzzle",
    "Block Puzzle - Jewel Blast"#手动搜索是这个无广告素材
    "Block Puzzle Sudoku",
    "Cube Block - Woody Puzzle Game",
    "Emoji Blast: Block Puzzle",
    "Block Journey - Puzzle Games",
    "Wood Block Puzzle-SudokuJigsaw",#手动搜索是这个无广告素材
    "Jewel Block Puzzle: Gem Crush",#手动搜索是这个无广告素材
    "Block Puzzle Legend",
    "Wood Block Puzzle 3D",#手动搜索是这个无广告素材
    "Block Puzzle Legend:Jewel Game",#手动搜索是这个无广告素材
    "Block Blitz - Wooden Puzzle",
    "Wooden 100 Block Puzzle Game",#手动搜索是这个无广告素材
    "Block Mania - Block Puzzle",
    "Block Puzzle: Diamond Star",#手动搜索是这个无广告素材
    "Block Sudoku Woody Puzzle Game",#手动搜索是这个无广告素材
    "Block Rush - Block Puzzle Game",
    "Wood Block - Puzzle Games",
    "Tetris®",
    "Tetris® Block Puzzle",
    "Block Puzzle 99: Gem Sudoku Go",#手动搜索是这个无广告素材
    "Blocky Quest - Classic Puzzle",#手动搜索是这个无广告素材
    "Block Puzzle - Blast Game",
    "Block Travel",
    "Color Block : Puzzle Games",
    "Block Puzzle:Adventure Master",
    "Block Puzzle: Jewel Quest",
    "Woodoku Blast",
    "Jewel Blast: Block Puzzle Z",#手动搜索是这个无广告素材
    "Block Buster : Block Puzzle",
    "Block Puzzle Wood Blast",
    "Block Master - Puzzle Game",
    "Blockudoku - Block Puzzle",
    "Woodoku - Wood Block Puzzles",
    "Wood Block Puzzle",
    "Block Puzzle Blast",
    "Wood Block 99 - Sudoku Puzzle",
    "Blocky Quest - Classic Blocks",
    "Block Puzzle: Jewel Blast",
    "Block Travel : Puzzle Block",
    "Block Puzzle: Diamond Star",
    "Block Puzzle: Jewel Blast!",
    "Block Puzzle - Fun Games",
    "Block Puzzle Jewel :Gem Legend",
    "Block Puzzle - Brain Games",
    "Block Puzzle-Wood Sudoku Game",
    "Block Puzzle - Brain Test Game",
    "Block Puzzle: Puzzle Games",
    "Block Puzzle Jewel Legend",
    "Block Puzzle: Star Gem",
    "Woody Block Puzzle Brain Game",
    "Block Puzzle - Wood Games",
    "Block Blast - Top Puzzle Games",
    "Block Blast Master:Puzzle Game",
    "Color Blast:Block Puzzle",
    "Block Puzzle Jewel World",
    "Block Puzzle Gem",
    "Block Puzzle - Jewel Quest",
    "Jewel Blitz: Block Puzzle",
    "Wood Block Puzzle Classic",
    "Block Puzzle: Wood Brain Games",
    "Wood Cube Puzzle",
    "Fill Wooden Block Puzzle 8x8"
]

MAX_SCROLLS = 999               # 【核心配置】列表页最大滚动次数
#   = 1      : 只滚一次（默认，测试用，速度快）
#   = N      : 最多滚 N 次后停止
#   = 999    : 滚动很多次，配合 CHECK_BOTTOM=True 可近似"滚动到到底部"
#
#   ⚠️ 注意：Facebook Ad Library 是无限滚动页面，不会自然终止。
#     想抓全部 → 设一个大数（如 999），同时开启 CHECK_BOTTOM=True
#     CHECK_BOTTOM 会检测页面高度不再变化，视为已到底部并提前停止
#     这样即使 MAX_SCROLLS 设得很大，也不会真的滚 999 次白费功夫

WAIT_SEC = 5                  # 每次滚动后等待秒数（给页面加载内容的时间）
#   = 1~2   : 网速快/广告少，可设短一点加快速度
#   = 3~5   : 默认推荐，网速一般时足够加载
#   = 8~10  : 网速慢或广告多，给更多缓冲避免漏抓
#   ⚠️ 设太短可能导致新内容还没加载完就被当成"已到底部"

CHECK_BOTTOM = True           # 是否检测滚动到底部（智能停止开关）
#   = True  : 开启。连续两次滚动页面高度不变 → 判定已到底部，强制停止
#             配合大数值 MAX_SCROLLS 使用，实现"滚动到到底部"
#   = False : 关闭。无论页面高度是否变化，都严格按 MAX_SCROLLS 次数滚动
#             可能会滚很多次但页面内容不再增加，浪费时间内
#
# 【推荐组合】
#   抓全部广告：MAX_SCROLLS=999 + WAIT_SEC=3~5 + CHECK_BOTTOM=True
#   快速测试：   MAX_SCROLLS=1  + WAIT_SEC=2  + CHECK_BOTTOM=False

HEADLESS = False              # Playwright 是否无头模式
MAX_ADS_LIMIT = 0           # 最大收集广告数，0=无限制
# ====================

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
# 总表文件：记录所有已抓过的 library_id（去重用）
ADS_MASTER_FILE = OUTPUT_DIR / "ads_master.json"
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
    log_file = log_dir / f"playwright_list_{today}.log"
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


def keyword_to_folder(keyword):
    """把关键词转成安全的文件夹名（去空格/特殊字符）。"""
    return re.sub(r'[^\w]', '_', keyword.strip())

def get_output_paths(keyword, date_str):
    """根据关键词和日期生成输出路径：output/<keyword>/ads_<keyword>_<date>.json"""
    folder_name = keyword_to_folder(keyword)
    folder = OUTPUT_DIR / folder_name
    daily_file = folder / f"ads_{folder_name}_{date_str}.json"
    return folder, daily_file

# ---- Playwright 浏览器启动 ----
def make_browser(headless=False):
    """创建 Playwright 实例（start 模式，不自动启动浏览器）。"""
    from playwright.sync_api import sync_playwright
    return sync_playwright().start()

def launch_browser(p, headless=False):
    """启动 Chromium 浏览器实例，返回 browser 对象。"""
    from playwright.sync_api import Browser
    args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-gpu",
        "--window-size=1920,1080",
    ]
    browser = p.chromium.launch(headless=headless, args=args)
    return browser

# ---- 广告数据解析 ----

def find_ad_data_in_json(obj, ad_id, depth=0):
    """递归在 JSON 对象树中查找指定 ad_archive_id 的广告数据节点。"""
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

def extract_all_fields_from_html(html, ad_id):
    """
    从页面 HTML 的 <script type="application/json"> 标签中解析广告字段。
    支持字段：video_url, age_range, gender, reach_count, spend, impressions,
             ad_disclosure_regions, advertiser_name, advertiser_description,
             payer_name, about_sponsor, body_text, title
    """
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
    # 提取广告主名称（page_name）
    m = re.search(r'"page_name":"((?:[^"\\]|\\.)*)"', html)
    if m:
        try:
            result['advertiser_name'] = m.group(1).encode().decode("unicode_escape")
        except Exception:
            result['advertiser_name'] = m.group(1)
    # 提取付费方名称（payer_name）
    m = re.search(r'"payer_name":"((?:[^"\\]|\\.)*)"', html)
    if m:
        try:
            result['payer_name'] = m.group(1).encode().decode("unicode_escape")
        except Exception:
            result['payer_name'] = m.group(1)
    # 遍历所有 JSON 脚本块，找广告数据
    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for sc in scripts:
        if 'ad_archive_id' not in sc:
            continue
        try:
            data = json.loads(sc)
        except Exception:
            continue
        ad_data = find_ad_data_in_json(data, ad_id)
        if not ad_data:
            continue
        # 地区披露标签
        disp = ad_data.get("disclaimer_label") or ad_data.get("disclosure_label")
        if disp:
            result['ad_disclosure_regions'] = [disp]
        # 覆盖人数
        imp = ad_data.get("impressions_with_index") or {}
        if isinstance(imp, dict):
            reach = imp.get("reach") or imp.get("impressions") or ""
            if isinstance(reach, int):
                result['reach_count'] = str(reach)
        # 关于广告赞助方
        about = ad_data.get("about_advertiser") or ad_data.get("page_info", {}).get("page_description") or ""
        if about:
            result['about_sponsor'] = about
        # 广告正文
        body = ad_data.get("body") or {}
        if isinstance(body, dict):
            result['body_text'] = body.get("text", "")
        elif isinstance(body, str):
            result['body_text'] = body
    # 如果 JSON 里没有，从 HTML 全局搜索 disclaimer_label
    if not result['ad_disclosure_regions']:
        m = re.search(r'"disclaimer_label":"([^"]+)"', html)
        if m:
            result['ad_disclosure_regions'] = [m.group(1)]
    # 花费区间
    m = re.search(r'"spend":\s*\{[^}]*?"min":\s*(\d+)[^}]*?"max":\s*(\d+)', html)
    if m:
        result['spend'] = f"{m.group(1)}-{m.group(2)}"
    # 展示次数区间
    m = re.search(r'"impressions":\s*\{[^}]*?"min":\s*(\d+)[^}]*?"max":\s*(\d+)', html)
    if m:
        result['impressions'] = f"{m.group(1)}-{m.group(2)}"
    return result

def _extract_all_video_urls(html):
    """
    从页面 HTML 的 JSON 块中提取所有广告的 video_hd_url。
    结构（从 Block 31 解析）：
      edges[n].node.collated_results[0] 是字典，
      其中 "ad_archive_id": 数字（广告ID），
      video_hd_url 在 collated_results[0].snapshot.videos[0].video_hd_url
    返回：dict{library_id: video_url}
    """
    video_map = {}
    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for sc in scripts:
        if 'ad_archive_id' not in sc or 'video_hd_url' not in sc:
            continue
        try:
            data = json.loads(sc)
        except Exception:
            continue

        # 找到 edges 数组，逐个处理
        edges = None
        def find_key(obj, key, depth=0):
            if depth > 30:
                return None
            if isinstance(obj, dict):
                if key in obj:
                    return obj[key]
                for v in obj.values():
                    r = find_key(v, key, depth+1)
                    if r is not None:
                        return r
            elif isinstance(obj, list):
                for item in obj:
                    r = find_key(item, key, depth+1)
                    if r is not None:
                        return r
            return None

        edges = find_key(data, 'edges')
        if not isinstance(edges, list):
            continue

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            node = edge.get('node', {})
            if not isinstance(node, dict):
                continue
            collated = node.get('collated_results', [])
            if not isinstance(collated, list) or not collated:
                continue
            cr0 = collated[0]
            if not isinstance(cr0, dict):
                continue

            ad_id = str(cr0.get('ad_archive_id', ''))
            if not ad_id.isdigit():
                continue

            snapshot = cr0.get('snapshot', {})
            if not isinstance(snapshot, dict):
                continue
            videos = snapshot.get('videos', [])
            if not isinstance(videos, list) or not videos:
                continue
            v0 = videos[0]
            if not isinstance(v0, dict):
                continue

            vurl = v0.get('video_hd_url', '')
            if vurl:
                video_map[ad_id] = vurl

    return video_map


def parse_ads_from_page(page):
    """
    从当前页面解析所有广告数据。
    流程：
      1. 获取页面 HTML
      2. 用正则提取所有 ad_archive_id（去重）
      3. 一次性提取所有广告的 video_url（从 JSON 块）
      4. 对每个 ID 在 HTML JSON 块中提取其他字段
    返回广告列表，每条包含 library_id / detail_url 及提取到的字段。
    """
    ads = []
    html = page.content()

    # 一次性提取所有广告的视频 URL
    video_map = _extract_all_video_urls(html)

    # 从 HTML 中提取所有 library_id（ad_archive_id）
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
        # video_url
        if lid in video_map:
            ad['video_url'] = video_map[lid]
        # 从 HTML JSON 块中提取更多字段
        try:
            fields = extract_all_fields_from_html(html, lid)
            for k, v in fields.items():
                if v and v != []:
                    ad[k] = v
        except Exception:
            pass
        if ad.get("library_id"):
            ads.append(ad)
    return ads

# ---- 滚动收集 ----
def scroll_and_collect(page, url, keyword, max_scrolls, wait_sec, max_ads=0):
    """
    打开基础页，执行搜索筛选，滚动收集所有广告数据。

    参数：
      page          - Playwright Page 对象
      url           - 基础页 URL（固定值 https://www.facebook.com/ads/library）
      keyword       - 搜索关键词
      max_scrolls   - 最大滚动次数
      wait_sec      - 每次滚动后等待秒数
      max_ads       - 最大收集广告数，0=不限

    完整流程：
      1. 打开基础页 https://www.facebook.com/ads/library
      2. 处理 cookies 弹窗
      3. 选择国家为"美国（United States）"
      4. 广告类型选择"所有广告"
      5. 在搜索框输入关键词，回车
      6. 等待2秒，复制地址栏URL，粘贴并回车（Facebook 重定向修复，必做）
      7. 循环滚动：
         - 执行 window.scrollTo 到底部
         - 等待页面加载
         - 解析页面广告
         - 检测是否已到底部（高度不再变化）
         - 提前停止（max_ads 达到）
    返回广告列表。
    """
    # ---- 步骤1：打开基础页 ----
    # 加重试 + 用 domcontentloaded 加速；Facebook 重定向时直接访问可能超时
    log_print(f"[Browser] 打开页面: {url}")
    for attempt in range(3):
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            log_print("[Browser] 页面导航完成")
            break
        except Exception as e:
            log_print(f"[Browser] 第{attempt+1}次导航失败: {e}")
            if attempt == 2:
                raise
            time.sleep(5)
    time.sleep(3)

    # 等待页面完全加载（Facebook React app 需要更多时间初始化）
    try:
        page.wait_for_load_state('networkidle', timeout=15000)
        log_print("[Browser] 页面网络请求已完成")
    except Exception:
        pass
    time.sleep(2)

    # ---- 处理 cookies 弹窗（微软隐私弹窗） ----
    try:
        # 微软 Edge 的隐私弹窗："我接受" 或 "全部拒绝"
        accept_btn = page.locator('button:has-text("我接受"), button:has-text("全部拒绝")').first
        if accept_btn.is_visible(timeout=3000):
            accept_btn.click(timeout=3000)
            time.sleep(1)
            log_print("[Setup] 已处理隐私弹窗")
    except Exception:
        pass

    # ---- 处理 Facebook cookies 弹窗 ----
    for text in ['Accept Cookies', 'Accept All Cookies', '同意', 'Accept']:
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if btn.is_visible(timeout=2000):
                btn.click(timeout=2000)
                time.sleep(1)
                break
        except Exception:
            pass

    # ---- 步骤2：选择国家 = 美国 ----
    # Facebook Ad Library 的国家下拉框使用 React，标准 click 不触发 state 更新
    # 正确流程：打开下拉 → 在搜索框输入 "United States" → 键盘 ArrowDown + Enter
    log_print("[Setup] 选择国家: 美国 (US)")
    try:
        combobox = page.locator('div[role="combobox"]').first
        if combobox.is_visible(timeout=3000):
            combobox.click(timeout=5000)
            time.sleep(1)
            log_print("[Setup] 国家下拉已打开")

            # 在国家搜索框中输入 "United States" 过滤列表
            search_in_dropdown = page.locator('input[placeholder="Search for country"]').first
            if search_in_dropdown.is_visible(timeout=2000):
                search_in_dropdown.click(timeout=2000)
                time.sleep(0.3)
                search_in_dropdown.fill("United States")
                time.sleep(1.5)
                log_print("[Setup] 已在国家搜索框输入 'United States'")

                # 键盘 ArrowDown 移动到第一项（United States），再按 Enter 确认
                page.keyboard.press("ArrowDown")
                time.sleep(0.3)
                page.keyboard.press("Enter")
                time.sleep(1)
                log_print("[Setup] 键盘选择完成")
            else:
                log_print("[Setup] 未找到国家搜索框，关闭下拉")
                page.keyboard.press("Escape")
        else:
            log_print("[Setup] 未找到国家下拉框，跳过")
    except Exception as e:
        log_print(f"[Setup] 国家选择异常: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    # ---- 步骤3：广告类型 = 所有广告 ----
    # 广告类型默认就是"全部"，此处仅记录日志确认即可
    # （后续步骤5会统一修正 URL 参数，确保 country=US 和 ad_type=all）
    log_print("[Setup] 广告类型: 默认全部（步骤5统一修正URL参数）")

    # ---- 步骤4：在搜索框输入关键词并回车 ----
    log_print(f"[Setup] 输入关键词: {keyword}")
    try:
        search_box_selectors = [
            # Facebook 广告库搜索框：顶部居中的大搜索框
            page.locator('input[placeholder*="搜索" i], input[placeholder*="Search" i]').first,
            # 搜索框在页面内容区
            page.locator('div[role="search"] input').first,
            page.locator('input[type="search"]').first,
        ]
        search_filled = False
        for i, sel in enumerate(search_box_selectors):
            try:
                if sel.is_visible(timeout=2000):
                    sel.click(timeout=3000)
                    time.sleep(0.5)
                    sel.fill(keyword)
                    time.sleep(0.3)
                    sel.press('Enter')
                    log_print(f"[Setup] 搜索框已输入「{keyword}」并回车（第{i+1}个选择器）")
                    search_filled = True
                    break
            except Exception:
                pass

        if not search_filled:
            log_print("[Setup] 未找到搜索框，跳过")
    except Exception as e:
        log_print(f"[Setup] 搜索框输入异常（继续）: {e}")

    # ---- 步骤5：等待2秒，复制地址栏URL ----
    # 关键步骤：Facebook UI 操作后，URL 已经包含了所有搜索参数
    # 把这个 URL 复制下来，作为最终的工作 URL
    # 不再重新 goto（已经在正确页面），直接记录日志
    log_print("[Setup] 等待2秒后复制地址栏URL...")
    time.sleep(2)
    final_url = page.url
    log_print(f"[Setup] 地址栏URL: {final_url}")

    # 确认 URL 参数正确（country 应为 US，ad_type 应为 all）
    import urllib.parse
    parsed = urllib.parse.urlparse(final_url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    log_print(f"[Setup] URL参数: country={params.get('country', 'N/A')}, ad_type={params.get('ad_type', 'N/A')}, q={params.get('q', 'N/A')}")

    # 如果参数不对（Facebook 重定向覆盖了），强制修正并重新加载
    need_fix = (
        params.get('country') != 'US'
        or params.get('ad_type') != 'all'
        or params.get('q') != keyword
    )
    if need_fix:
        log_print("[Setup] URL参数被覆盖，强制修正 country=US, ad_type=all 后重新加载...")
        params['country'] = 'US'
        params['ad_type'] = 'all'
        params['q'] = keyword
        fixed_url = urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            '', urllib.parse.urlencode(params), ''
        ))
        log_print(f"[Setup] 修正后URL: {fixed_url}")
        page.goto(fixed_url, timeout=30000)
        time.sleep(5)
        final_url = page.url
        log_print(f"[Setup] 修正后重新加载完成: {final_url}")
    else:
        log_print("[Setup] URL参数正确，直接使用当前页面继续")

    # ---- 步骤6：处理可能再次出现的 cookies/隐私弹窗 ----
    try:
        accept_btn = page.locator('button:has-text("我接受"), button:has-text("全部拒绝")').first
        if accept_btn.is_visible(timeout=2000):
            accept_btn.click(timeout=2000)
            time.sleep(1)
    except Exception:
        pass
    for text in ['Accept Cookies', 'Accept All Cookies', '同意', 'Accept']:
        try:
            btn = page.locator(f"button:has-text('{text}')").first
            if btn.is_visible(timeout=2000):
                btn.click(timeout=2000)
                time.sleep(1)
                break
        except Exception:
            pass

    # ---- 开始滚动收集 ----
    all_ads = []
    last_height = 0
    prev_ad_count = 0

    log_print(f"[Scroll] 开始滚动 | 最大次数={max_scrolls} | 等待={wait_sec}秒 | 最大广告数={max_ads if max_ads else '不限'}")

    for scroll in range(max_scrolls):
        # 滚动到页面底部
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)

        # 解析当前页面广告
        ads = parse_ads_from_page(page)
        for ad in ads:
            if ad not in all_ads:
                all_ads.append(ad)

        # 提前停止条件：广告数连续 3 次不增长，视为已到底
        if len(all_ads) > 0 and len(all_ads) == prev_ad_count:
            no_new_count += 1
            if no_new_count >= 3:
                log_print(f"  [Bottom] 广告数连续3次不变（{len(all_ads)}条），停止滚动")
                break
        else:
            no_new_count = 0
        prev_ad_count = len(all_ads)

        if max_ads > 0 and len(all_ads) >= max_ads:
            log_print(f"  Reached max_ads={max_ads}, stopping early")
            break

        # 检测滚动到底部：广告数连续3次不变，视为已全部加载
        # 同时保留页面高度检测作为备用
        if CHECK_BOTTOM:
            height_changed = page.evaluate("() => document.body.scrollHeight") != last_height
            if len(all_ads) == prev_ad_count and not height_changed:
                time.sleep(2)
                # 再次确认
                if page.evaluate("() => document.body.scrollHeight") == last_height:
                    log_print(f"  [Bottom] 广告数连续不变且页面高度稳定，停止滚动（第 {scroll+1} 次）")
                    break
            last_height = page.evaluate("() => document.body.scrollHeight")

        log_print(f"  Scroll {scroll+1}/{max_scrolls}: {len(all_ads)} ads collected")

    log_print(f"[Scroll] 滚动结束，共收集到 {len(all_ads)} 条广告")
    return all_ads

# ---- 视频下载 ----
def download_videos(ads, video_dir, keyword):
    """
    批量下载广告视频（多线程并发，最多 3 个同时下载）。
    
    参数：
      ads       - 广告列表（含 video_url 字段）
      video_dir - 视频保存目录
      keyword   - 关键词（用于日志）
    
    跳过条件：
      - 视频已存在（以 library_id.mp4 为文件名）
      - video_url 为空或不以 http 开头
    """
    video_dir.mkdir(parents=True, exist_ok=True)
    # 跳过已下载的
    existing = {f.stem for f in video_dir.glob("*.mp4")}
    to_download = [a for a in ads if a['library_id'] not in existing
                   and str(a.get('video_url', '')).startswith('http')]
    if not to_download:
        log_print(f"[Video] 没有新视频要下载 ({video_dir.name})")
        return
    log_print(f"[Video] 开始下载 {len(to_download)} 个视频到 {video_dir}")

    def download_one(ad):
        """下载单个视频，返回是否成功。"""
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

    # 最多 3 个线程并发下载
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(download_one, ad): ad for ad in to_download}
        for future in as_completed(futures):
            future.result()  # raise any exceptions

# ---- 工具函数 ----
def load_json_file(path):
    """读取 JSON 文件，返回内容（失败返回空结构）。"""
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

# ---- 主逻辑 ----
def scrape_keyword(keyword):
    """
    抓取单个关键词的完整流程：
    
    1. 计算日期范围，构建搜索 URL
    2. 加载总表，去重今日文件里已有的广告
    3. 启动 Playwright 浏览器，滚动收集广告
    4. 与今日文件合并，保存
    5. 追加新 library_id 到总表
    6. 下载新广告的视频
    
    返回本次新增的广告列表（去重后）。
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    folder, daily_file = get_output_paths(keyword, end_date)
    folder.mkdir(parents=True, exist_ok=True)

    log_print(f"========== 开始抓取: {keyword} | 日期: {end_date} ==========")

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

    # ---- 启动 Playwright，滚动收集 ----
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        if ANONYMOUS_MODE or not CHROME_USER_DATA_DIR:
            # 匿名模式：新建空白 context
            browser = p.chromium.launch(
                headless=HEADLESS,
                proxy={"server": PROXY_SERVER} if PROXY_SERVER else None,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()
        else:
            # 复用 Chrome 用户数据（保留登录状态）
            # 需要用 launch_persistent_context 而非 launch + user-data-dir 参数
            log_print(f"[Browser] 使用 Chrome 用户数据: {CHROME_USER_DATA_DIR}")
            context = p.chromium.launch_persistent_context(
                CHROME_USER_DATA_DIR,
                headless=HEADLESS,
                proxy={"server": PROXY_SERVER} if PROXY_SERVER else None,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.pages[0] if context.pages else context.new_page()
        ads = scroll_and_collect(page, "https://www.facebook.com/ads/library", keyword, MAX_SCROLLS, WAIT_SEC, MAX_ADS_LIMIT)
        log_print(f"[List] 本次滚动抓到 {len(ads)} 条（未去重）")
        # 关闭浏览器（launch_persistent_context 和 launch 都用 .close()）
        if 'browser' in dir():
            browser.close()
        elif 'context' in dir():
            context.close()

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
        "date_range": end_date,
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

    # ---- 下载视频 ----
    video_dir = folder / "videos"
    log_print(f"[Video] Checking videos for {keyword}...")
    download_videos(new_ads, video_dir, keyword)

    return new_ads

def main():
    """主入口：遍历所有关键词执行抓取。"""
    for i, keyword in enumerate(KEYWORDS, 1):
        log_print(f"========== 处理关键词 {i}/{len(KEYWORDS)}: {keyword} ==========")
        scrape_keyword(keyword)
    log_print("所有关键词处理完毕")

def _main():
    """主入口（含参数解析），避免 global 声明与模块级代码混淆。"""
    import argparse
    global KEYWORDS, MAX_ADS_LIMIT
    parser = argparse.ArgumentParser(description="Facebook Ad Library - List Scraper (Playwright)")
    parser.add_argument("--keyword", default=None, help="搜索关键词（多个用逗号分隔）")
    parser.add_argument("--max-ads", type=int, default=0, help="最大收集广告数，0=无限制")
    args = parser.parse_args()

    # 支持逗号分隔的多个关键词
    if args.keyword:
        keywords_from_arg = [k.strip() for k in args.keyword.split(",") if k.strip()]
        if keywords_from_arg:
            KEYWORDS.clear()
            KEYWORDS.extend(keywords_from_arg)

    if args.max_ads:
        MAX_ADS_LIMIT = args.max_ads

    main()


if __name__ == "__main__":
    _main()
