"""
Facebook Ad Library 抓取 + 去重合并 + 视频下载
============================================

【功能说明】
  1. 抓取列表页广告（通过滚动页面加载）
  2. 从页面 HTML JSON 数据中提取广告信息（ad_archive_id、video_url、start_date）
  3. 去重后合并到每日文件和汇总文件
  4. 下载视频（支持断点续传，已下载跳过，命名：library_id.mp4）
  5. 可选：抓取详情页4个展开块信息（耗时长，默认关闭）

【与 TikTok 版的差异】
  - URL 参数用日期字符串（不是毫秒时间戳）
  - 翻页方式：滚动页面（不是点击 View more）
  - 广告ID：从 ad_archive_id 字段提取（不是从 URL 参数提取）
  - 视频 URL：从页面 HTML JSON 正则提取（不是 <video currentSrc>）

【使用方法】
  python run.py
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
from playwright.sync_api import sync_playwright

# 忽略 undetected_chromedriver 析构器警告
warnings.filterwarnings('ignore', category=DeprecationWarning, module='undetected_chromedriver')

# 全局禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36')]
urllib.request.install_opener(opener)

# ============================================================
#                    【配置区】
#                   （修改这里即可）
# ============================================================

# ----- 搜索条件 -----
KEYWORDS = [
    "Block Blast",
    # 添加更多关键词，如：
    # "Coin Master",
    # "Royal Match",
]

# ----- 国家设置 -----
# Facebook Ad Library 国家筛选
# 可选：US, CN, GB, JP, KR, DE, FR, TW, HK, SG 等
COUNTRY = "US"

# ----- 日期设置 -----
# AUTO_DATE = True  -> 自动模式：抓最近7天（END_DATE=今日，START_DATE=今日-6天）
# AUTO_DATE = False -> 手动模式：使用下方指定的 START_DATE 和 END_DATE
AUTO_DATE = True

START_DATE = "2026-04-17"    # 手动模式时的开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-04-23"      # 手动模式时的结束日期，留空 "" 表示今天

# ----- 抓取模式 -----
#   MODE = "fixed"  -> 只抓固定数量（由 MAX_ADS 控制）
#   MODE = "all"   -> 抓取全部数据（直到页面底部才停止）
MODE = "fixed"                # ★ 重要：选 "fixed" 或 "all"
MAX_ADS = 10                  # MODE="fixed" 时生效，表示最多抓多少条

# ----- 浏览器模式 -----
#   True  = 无头模式（不弹窗，后台运行，更稳定，推荐）
#   False = 可见浏览器（弹出 Chrome 窗口）
HEADLESS = False

# ----- 等待时间（秒）-----
# 每次滚动页面后等待（给页面加载时间）
# 数据多或网速慢 → 可以调大，如 5 或 8
WAIT_SEC = 5

# ----- 最大滚动次数 -----
# MODE="all" 时生效，控制最多滚动多少次
# MODE="fixed" 时，通过 MAX_ADS 控制，滚动次数作用不大
MAX_SCROLLS = 50

# ----- 详情页抓取 -----
#   True  = 启用（Playwright CDP 获取详情页 HTML，正则提取完整视频 URL）
#   False = 跳过（只抓取列表页信息，速度快）
SCRAPE_DETAIL = True

MAX_DETAIL_SCRAPES = 10

CDP_URL = "http://127.0.0.1:18800"

DETAIL_WAIT = 5

# ----- 并发数 -----
MAX_DOWNLOAD_WORKERS = 3       # 视频下载的并发线程数

# ----- 视频提取 -----
# 每个详情页打开后等待秒数（给视频元素加载时间）
DETAIL_WAIT = 5

# ============================================================


# ========== Selenium 依赖 ==========
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

# ========== 固定路径 ==========
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROMEDRIVER_PATH = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
    'Referer': 'https://www.facebook.com/',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Encoding': 'identity',
}


# ============================================================
# 【工具函数】
# ============================================================

def get_date_range():
    """获取日期范围
    - AUTO_DATE=True: 自动计算（START_DATE=今天-6天，END_DATE=今天）
    - AUTO_DATE=False: 使用配置中的 START_DATE 和 END_DATE
    """
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    
    if AUTO_DATE:
        start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = today_str
    else:
        start_date = START_DATE if START_DATE else (today - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = END_DATE if END_DATE else today_str
    
    return start_date, end_date


def build_url(keyword, start_date, end_date):
    """
    构建 Facebook Ad Library 搜索 URL
    使用用户指定的 URL 格式
    """
    base = "https://www.facebook.com/ads/library/"
    params = {
        'active_status': 'active',
        'ad_type': 'all',
        'country': COUNTRY,
        'is_targeted_country': 'false',
        'media_type': 'all',
        'q': keyword,
        'search_type': 'keyword_unordered',
        'sort_data[direction]': 'desc',
        'sort_data[mode]': 'total_impressions',
        'start_date[min]': start_date,
        'start_date[max]': end_date,
    }
    return base + "?" + urllib.parse.urlencode(params)


def keyword_to_folder(keyword):
    """关键词转文件夹名"""
    return keyword.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")


def get_output_paths(keyword, date_str):
    """获取某个关键词在某天的所有文件路径"""
    folder_name = keyword_to_folder(keyword)
    folder = OUTPUT_DIR / folder_name
    # 每日文件: ads_blockblast_2026-04-23.json
    daily_file = folder / f"ads_{folder_name}_{date_str}.json"
    # 汇总文件: ads_blockblast.json
    agg_file = folder / f"ads_{folder_name}.json"
    video_dir = folder / "videos"
    return folder, daily_file, agg_file, video_dir


# ============================================================
# 【浏览器驱动】
# ============================================================

def make_driver(headless, max_retries=3):
    """创建 Chrome 浏览器实例"""
    for attempt in range(max_retries):
        try:
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
            
            for arg in [
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
                '--ssl-protocol=TLSv1.2',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content',
            ]:
                options.add_argument(arg)

            if headless:
                options.add_argument('--headless=new')

            driver = uc.Chrome(
                options=options, 
                use_subprocess=True,
                driver_executable_path=CHROMEDRIVER_PATH
            )
            print("[浏览器] 使用 undetected-chromedriver", flush=True)
            return driver
        except ImportError:
            print("[浏览器] 使用普通 selenium", flush=True)
            options = Options()
            options.binary_location = CHROME_PATH

            for arg in [
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
            ]:
                options.add_argument(arg)

            if headless:
                options.add_argument('--headless=new')

            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            service = Service(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)

            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
            })
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "plugins", {get: () => [1, 2, 3, 4, 5]});'
            })
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "languages", {get: () => ["zh-CN", "zh", "en"]});'
            })
            return driver
        except Exception as e:
            print(f"[浏览器] 第 {attempt+1} 次初始化失败: {e}", flush=True)
            if attempt < max_retries - 1:
                print("[浏览器] 5秒后重试...", flush=True)
                time.sleep(5)
            else:
                raise
    
    raise Exception("浏览器驱动初始化失败")


# ============================================================
# 【页面交互】
# ============================================================

def accept_cookies_if_present(driver):
    """接受 Cookie 弹窗"""
    for text in ['Accept', 'Accept all', 'Allow', 'I accept', '同意', '接受', 'Allow all cookies']:
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), '" + text + "')]")
            if btn.is_displayed():
                btn.click()
                print(f"[弹窗] 已点击: {text}", flush=True)
                time.sleep(2)
                return
        except NoSuchElementException:
            continue


def safe_click(driver, element, timeout=5):
    """安全点击元素"""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(element))
        element.click()
        return True
    except Exception:
        pass
    
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        pass
    
    return False


# ============================================================
# 【提取广告详情】
# ============================================================

def extract_ad_details(page_source, ad_id):
    """从页面源码中提取指定广告的详细信息（视频URL、开始日期）"""
    from datetime import datetime
    
    # 找到该 ad_id 在源码中的位置
    pattern = f'ad_archive_id[":\\s]+{ad_id}'
    match = re.search(pattern, page_source)
    if not match:
        return '', ''
    
    pos = match.start()
    start = max(0, pos - 3000)
    end = min(len(page_source), pos + 5000)
    context = page_source[start:end]
    
    # 找 video_hd_url（处理 null 和带引号URL两种格式）
    video_url = ''
    video_match = re.search(r'"video_hd_url":"([^"]+)"', context)
    if video_match:
        video_url = video_match.group(1).replace('\\/', '/')
    else:
        # 尝试非引号格式（如果是 null）
        video_match2 = re.search(r'video_hd_url[\":\\s]+null', context)
        if not video_match2:
            video_url = ''  # 确实没有视频
    
    # 找 start_date（Unix 时间戳）
    start_date = ''
    start_date_match = re.search(r'start_date[":\\s]+(\d+)', context)
    if start_date_match:
        ts = int(start_date_match.group(1))
        try:
            start_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            pass
    
    return video_url, start_date


def extract_video_from_detail_html(html):
    pattern = r'"videos":\[\{"video_hd_url":"([^"]+)"'
    m = re.search(pattern, html)
    if m:
        return m.group(1).replace('\\/', '/')
    return ''


def extract_video_from_detail_html(html):
    pattern = r'"videos":\[\{"video_hd_url":"([^"]+)"'
    m = re.search(pattern, html)
    if m:
        return m.group(1).replace('\\/', '/')
    return ''


def find_ad_data_in_json(obj, ad_id, depth=0):
    """在 JSON 对象树中递归查找指定 ad_archive_id 的广告数据"""
    if depth > 30:
        return None
    if isinstance(obj, dict):
        if obj.get('ad_archive_id') and str(obj.get('ad_archive_id')) == str(ad_id):
            return obj
        for v in obj.values():
            r = find_ad_data_in_json(v, ad_id, depth+1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = find_ad_data_in_json(item, ad_id, depth+1)
            if r:
                return r
    return None


def extract_all_fields_from_html(html, ad_id):
    """
    从 Facebook 详情页 HTML 中提取所有广告字段。
    返回完整 dict，包含所有需求字段。
    """
    result = {
        'library_id': ad_id,
        'page_name': '',
        'title': '',
        'body_text': '',
        'start_date': '',
        'end_date': '',
        'video_url': '',
        'video_sd_url': '',
        'video_preview_image_url': '',
        'link_url': '',
        'cta_type': '',
        'display_format': '',
        'publisher_platform': [],
        'ad_disclosure_regions': [],
        'reach_count': '',
        'spend': '',
        'currency': '',
        'age_range': '',
        'gender': '',
        'advertiser_name': '',
        'advertiser_description': '',
        'payer_name': '',
    }

    # 1. 视频 URL
    m = re.search(r'"videos":\[\{"video_hd_url":"([^"]+)"', html)
    if m:
        result['video_url'] = m.group(1).replace('\/', '/')

    # 2. 在所有 JSON script 标签中找这个广告的数据
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

        snapshot = ad_data.get('snapshot', {})
        result['page_name'] = snapshot.get('page_name', '')
        result['title'] = snapshot.get('title', '')

        body = snapshot.get('body', {})
        if isinstance(body, dict):
            result['body_text'] = body.get('text', '')
        elif body:
            result['body_text'] = str(body)

        result['link_url'] = snapshot.get('link_url', '')
        result['cta_type'] = snapshot.get('cta_type', '')
        result['display_format'] = snapshot.get('display_format', '')
        result['publisher_platform'] = snapshot.get('publisher_platform', [])

        # 日期
        sd = snapshot.get('start_date')
        if sd:
            try:
                result['start_date'] = datetime.fromtimestamp(int(sd)).strftime('%Y-%m-%d')
            except:
                pass
        ed = snapshot.get('end_date')
        if ed:
            try:
                result['end_date'] = datetime.fromtimestamp(int(ed)).strftime('%Y-%m-%d')
            except:
                pass

        # 地区披露（免责声明标签）
        disp = snapshot.get('disclaimer_label')
        if disp:
            result['ad_disclosure_regions'] = [disp]

        # 覆盖人数
        imp = snapshot.get('impressions_with_index') or {}
        if isinstance(imp, dict):
            result['reach_count'] = imp.get('impressions_text', '')

        # spend
        result['spend'] = snapshot.get('spend', '')
        result['currency'] = snapshot.get('currency', '')

        # 年龄
        gated = snapshot.get('gated_type', '')
        if gated == 'ALL_AGES':
            result['age_range'] = 'All ages'
        elif gated == 'MULTI_AGE_RANGE':
            result['age_range'] = 'Multi-age'
        elif gated:
            result['age_range'] = gated

        # 性别
        gender = snapshot.get('gender', '')
        if gender == 'ALL':
            result['gender'] = '不限'
        elif gender:
            result['gender'] = gender

        # 广告主名称
        result['advertiser_name'] = result['page_name']

        # 付费方
        payer = snapshot.get('payer_name', '')
        if payer:
            result['payer_name'] = payer

        break

    # 3. 全局搜索补充（JSON script 中没有的情况）
    if not result['advertiser_name']:
        m = re.search(r'"page_name":"((?:[^"\]|\.)*)"', html)
        if m:
            try:
                result['advertiser_name'] = m.group(1).encode().decode('unicode_escape')
            except:
                result['advertiser_name'] = m.group(1)

    if not result['body_text']:
        m = re.search(r'"body":\{"text":"((?:[^"\]|\.)*)"\}', html)
        if m:
            try:
                result['body_text'] = m.group(1).encode().decode('unicode_escape')
            except:
                result['body_text'] = m.group(1)

    if not result['reach_count']:
        m = re.search(r'"impressions_text":"([^"]+)"', html)
        if m:
            result['reach_count'] = m.group(1)

    if not result['age_range']:
        m = re.search(r'"gated_type":"([^"]+)"', html)
        if m:
            gt = m.group(1)
            if gt == 'ALL_AGES':
                result['age_range'] = 'All ages'
            elif gt == 'MULTI_AGE_RANGE':
                result['age_range'] = 'Multi-age'
            else:
                result['age_range'] = gt

    if not result['gender']:
        m = re.search(r'"gender":"([^"]+)"', html)
        if m:
            g = m.group(1)
            result['gender'] = '不限' if g == 'ALL' else g

    if not result['ad_disclosure_regions']:
        m = re.search(r'"disclaimer_label":"([^"]+)"', html)
        if m:
            result['ad_disclosure_regions'] = [m.group(1)]

    if not result['payer_name']:
        m = re.search(r'"payer_name":"((?:[^"\]|\.)*)"', html)
        if m:
            try:
                result['payer_name'] = m.group(1).encode().decode('unicode_escape')
            except:
                result['payer_name'] = m.group(1)

    return result



def fetch_detail_page_via_cdp(library_id, cdp_url, wait_sec=5):
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            contexts = browser.contexts
            if not contexts:
                browser.close()
                return '', ''
            ctx = contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            url = "https://www.facebook.com/ads/library/?id=" + library_id + "&active_status=active&ad_type=all&country=US&is_targeted_country=false&media_type=all&search_type=page"
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(wait_sec)
            html = page.content()
            video_url = extract_video_from_detail_html(html)
            browser.close()
            return html, video_url
    except Exception as e:
        print("[CDP] 抓取失败 " + library_id + ": " + str(e))
        return '', '' 


# ============================================================
# 【广告解析】
# ============================================================

def parse_ads_from_page(driver):
    """从当前列表页解析所有广告（优先从页面JSON数据提取）"""
    ads = []
    seen_ids = set()

    # 方法1: 尝试从页面源码的 JSON 数据中提取（Facebook 广告库会把数据嵌入在页面中）
    try:
        page_source = driver.page_source
        
        # 查找嵌入的 JSON 数据（通常在 <script> 标签中以 JSON 形式存储）
        # Facebook 经常把数据存在 "require(\"__曝光数据__\")" 类似的格式中
        json_patterns = [
            r'"ads":\s*(\[.*?\])',
            r'"browseID":\s*"(\d+)"',
            r'href="/ads/library/\?id=(\d+)"',
            r'ad_archive_id[":\s]+(\d+)',
        ]
        
        # 直接查找 ad_archive_id 数字（Facebook 的广告ID字段名）
        ad_ids = re.findall(r'ad_archive_id[\":\s]+(\d+)', page_source)
        if ad_ids:
            ad_ids = list(set(ad_ids))
            print(f"[JSON] 从页面找到 {len(ad_ids)} 个广告ID", flush=True)
            for ad_id in ad_ids:
                if ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    # 提取该广告的详细信息（视频URL、开始日期等）
                    video_url, start_date = extract_ad_details(page_source, ad_id)
                    if video_url or start_date:
                        print(f"  [详情] {ad_id}: video={bool(video_url)}, date={start_date}", flush=True)
                    
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
        
        # 方法1b: 查找 JSON 序列化的大字符串
        if not ads:
            # 尝试找所有 JSON 对象
            json_strings = re.findall(r'\{[^{}]*"id\"[^{}]*\}', page_source)
            for json_str in json_strings[:100]:  # 限制数量
                try:
                    # 尝试解析为 JSON
                    import re as re_module
                    # 查找 id 字段
                    id_matches = re.findall(r'"id"\s*:\s*"?(\d+)"?', json_str)
                    for ad_id in id_matches:
                        if ad_id not in seen_ids and len(ad_id) > 5:  # 广告ID通常较长
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
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"[JSON] 提取JSON数据失败: {e}", flush=True)

    # 方法2: 直接找广告链接（备选）
    if not ads:
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ads/library/?id=')]")
        print(f"[DOM] 从DOM找到 {len(links)} 个链接", flush=True)

        for link in links:
            href = link.get_attribute("href") or ""
            m = re.search(r'[?&]id=(\d+)', href)
            if not m:
                continue
            ad_id = m.group(1)
            if ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)

            text = link.text or ""
            video_url, start_date = extract_ad_details(page_source, ad_id)

            ad = {
                "library_id": ad_id,
                "keyword": "",
                "index": len(ads) + 1,
                "platforms": ["Facebook"],
                "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                "ad_text": text[:500] if text else "",
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

    # 方法3: 从页面源码字符串直接提取（兜底）
    if not ads:
        print("[兜底] 尝试从页面源码直接提取...", flush=True)
        all_ids = re.findall(r'ad_archive_id[_\":\s=]+(\d{10,})', page_source)
        all_ids = list(set(all_ids))
        for ad_id in all_ids[:100]:
            if ad_id not in seen_ids:
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

    print(f"[解析] 共找到 {len(ads)} 条广告", flush=True)
    return ads


# ============================================================
# 【滚动翻页】
# ============================================================

def scroll_and_collect(driver, url, keyword, max_scrolls, wait_sec):
    """滚动列表页并收集广告"""
    driver.get(url)
    time.sleep(wait_sec)
    
    accept_cookies_if_present(driver)
    time.sleep(3)
    
    # 等待页面加载
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("[页面] 已加载", flush=True)
    except Exception:
        print("[页面] 加载超时", flush=True)
    
    time.sleep(5)
    
    # 保存页面源码用于调试
    try:
        debug_dir = SCRIPT_DIR / "debug"
        debug_dir.mkdir(exist_ok=True)
        debug_file = debug_dir / f"page_source_{datetime.now().strftime('%H%M%S')}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"[调试] 页面源码已保存: {debug_file.name} ({len(driver.page_source)} 字符)", flush=True)
    except Exception as e:
        print(f"[调试] 保存页面源码失败: {e}", flush=True)
    
    # 检查页面状态
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "没有结果" in page_text or "no results" in page_text:
            print("[警告] 页面显示没有搜索结果", flush=True)
        # 检查是否有广告数据相关的内容
        if "ad" in page_text and len(page_text) > 1000:
            print(f"[调试] 页面包含内容: {len(page_text)} 字符", flush=True)
    except Exception:
        pass

    ads = []
    scroll_count = 0
    prev_count = 0
    no_new_count = 0

    while True:
        page_ads = parse_ads_from_page(driver)
        
        # 为每个广告填充关键词
        for ad in page_ads:
            ad['keyword'] = keyword
        
        # 去重合并
        new_count = 0
        for a in page_ads:
            if a['library_id'] not in [existing['library_id'] for existing in ads]:
                ads.append(a)
                new_count += 1

        print(f"  滚动 {scroll_count} 次，已抓 {len(ads)} 条 (新增 {new_count})", flush=True)
        
        # 检查是否到底
        if len(ads) == prev_count:
            no_new_count += 1
            if no_new_count >= 3:
                print("[完成] 连续3次无新广告，列表已到底", flush=True)
                break
        else:
            no_new_count = 0

        prev_count = len(ads)
        
        # 达到目标数量则提前停止
        if MAX_ADS and len(ads) >= MAX_ADS:
            print(f"[完成] 已达目标数量 {MAX_ADS}", flush=True)
            break

        # 检查滚动次数
        if scroll_count >= max_scrolls:
            print(f"[完成] 已达最大滚动次数 {max_scrolls}", flush=True)
            break

        # 分阶段滚动
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        scroll_count += 1
        
        time.sleep(wait_sec)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    driver.execute_script("window.scrollTo(0, 0);")
    return ads


# ============================================================
# ============================================================
# 【详情页抓取】
# ============================================================

def _click_element(driver, element):
    """使用原生 Selenium click 点击元素，失败时降级到 JS click"""
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False

def _wait_and_get_expanded_content(driver, block_name, block_xpath):
    """点击展开块并等待内容加载，然后提取"""
    try:
        el = driver.find_element(By.XPATH, block_xpath)
        # 滚动到可视区
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.5)
        # 点击
        _click_element(driver, el)
        # 等待展开（aria-expanded 变为 true，或内容区域出现）
        try:
            WebDriverWait(driver, 5).until(
                lambda d: el.get_attribute("aria-expanded") == "true"
            )
        except Exception:
            pass
        time.sleep(1.5)
        # 提取内容 - 找展开后的内容区
        # 常见结构：内容在 block 的下一个兄弟元素中
        content_xpaths = [
            # 找 block 最近的 expanded=true 的容器
            "./ancestor::div[contains(@class,'x1n2onr6')]//div[@aria-expanded='true']",
            # 找 x1dr75xp（Facebook 详情卡常用类名）
            "./following-sibling::div[contains(@class,'x1dr75xp')]",
            "./following-sibling::div[contains(@class,'x78zum5')]",
            # 找展开后的 section
            "./ancestor::section/following-sibling::div",
        ]
        for cx in content_xpaths:
            try:
                contents = driver.find_elements(By.XPATH, cx)
                for c in contents:
                    txt = c.text.strip()
                    if txt and len(txt) > 10:
                        return txt
            except Exception:
                pass
        # 降权：直接取 el 的父容器文本
        try:
            parent = el.find_element(By.XPATH, "./..")
            txt = parent.text.strip()
            if len(txt) > 10:
                return txt
        except Exception:
            pass
        return el.text.strip()
    except Exception as e:
        return f"[点击失败: {e}]"

def _click_block_isTrusted(driver, heading_text):
    """
    通过 isTrusted:true 触发 block 点击，展开 XHR 动态内容。
    Facebook 事件监听器检查 isTrusted 标志，必须用完整事件序列。
    """
    script = f"""
        var dialogs = document.querySelectorAll('[role="dialog"]');
        for (var d of dialogs) {{
            if (d.getAttribute('aria-labelledby') === 'js_104') {{
                var headings = d.querySelectorAll('[role="heading"]');
                for (var h of headings) {{
                    if (h.textContent.trim() === '{heading_text}') {{
                        var link = h.parentElement;
                        var rect = link.getBoundingClientRect();
                        var clientX = Math.floor(rect.left + rect.width / 2);
                        var clientY = Math.floor(rect.top + rect.height / 2);
                        ['mousedown', 'mouseup', 'click'].forEach(function(type) {{
                            link.dispatchEvent(new MouseEvent(type, {{
                                view: window, bubbles: true, cancelable: true,
                                clientX: clientX, clientY: clientY, isTrusted: true
                            }}));
                        }});
                        return 'OK: ' + clientX + ',' + clientY;
                    }}
                }}
            }}
        }}
        return 'NOT_FOUND';
    """
    return driver.execute_script(script)


def scrape_ad_detail(driver, library_id, wait_sec=8):
    # 优先用 CDP 获取详情页完整 HTML 和视频 URL
    html, video_url = fetch_detail_page_via_cdp(library_id, CDP_URL, wait_sec=wait_sec)
    if html:
        fields = extract_all_fields_from_html(html, library_id)
        if fields.get('video_url'):
            print("[CDP] " + library_id + " 完整字段提取成功 | video=" + fields['video_url'][:50] + "...")
            return {
                "library_id": library_id,
                "detail_url": "https://www.facebook.com/ads/library/?id=" + library_id,
                "video_url": fields['video_url'],
                "video_sd_url": fields['video_sd_url'],
                "video_preview_image_url": fields['video_preview_image_url'],
                "start_date": fields['start_date'],
                "end_date": fields['end_date'],
                "delivery_status": "",
                "ad_disclosure_regions": fields['ad_disclosure_regions'],
                "age_range": fields['age_range'],
                "gender": fields['gender'],
                "reach_count": fields['reach_count'],
                "advertiser_name": fields['advertiser_name'],
                "advertiser_description": fields['advertiser_description'],
                "payer_name": fields['payer_name'],
                "creative_data": {
                    "video_url": fields['video_url'],
                    "video_sd_url": fields['video_sd_url'],
                    "video_preview_image_url": fields['video_preview_image_url'],
                    "display_format": fields['display_format'],
                    "cta_type": fields['cta_type'],
                    "link_url": fields['link_url'],
                },
                "raw_detail_text": "",
                "ad_text": fields['body_text'],
                "title": fields['title'],
                "block_ad_disclosure": "", "block_about_sponsor": "",
                "block_about_advertiser": "", "block_advertiser_payer": "",
            }
        else:
            print("[CDP] " + library_id + " 页面已加载，但无视频")


    if html:
        print("[CDP] " + library_id + " 无视频（页面已加载）")
    else:
        print("[CDP] " + library_id + " CDP失败，降级到 Selenium")
    """
    访问 Facebook Ad Library 详情页（Selenium 降级模式）。
    
    关键技术：Facebook 用 isTrusted 标志过滤事件，必须传入 isTrusted:true 才能触发 XHR 加载。
    
    页面结构：
      - Dialog 0：左侧导航栏（无关）
      - Dialog 1：主模态框（600px，含广告基础信息）
      - Dialog 2：右侧信息栏（1873px，含4个可展开块）
      - 4个块在 Dialog 2 内，点击标题触发 XHR，展开内容追加到 innerText
    """
    detail_url = f"https://www.facebook.com/ads/library/?id={library_id}"
    detail_data = {
        "library_id": library_id,
        "detail_url": detail_url,
        "ad_text": "",
        "start_date": "",
        "end_date": "",
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
        "block_ad_disclosure": "",
        "block_about_sponsor": "",
        "block_about_advertiser": "",
        "block_advertiser_payer": "",
    }

    def get_dialog2_text():
        """获取 Dialog 2（右侧信息栏）的完整 innerText"""
        return driver.execute_script("""
            var dialogs = document.querySelectorAll('[role="dialog"]');
            for (var d of dialogs) {
                if (d.getAttribute('aria-labelledby') === 'js_104') {
                    return d.innerText;
                }
            }
            return '';
        """)

    def get_main_dialog_text():
        """获取 Dialog 1（主模态框）的完整文本（TreeWalker）"""
        return driver.execute_script("""
            var dialogs = document.querySelectorAll('[role="dialog"]');
            var mainDlg = null;
            for (var d of dialogs) {
                if (d.getAttribute('aria-labelledby') === 'js_zu') {
                    mainDlg = d; break;
                }
            }
            if (!mainDlg) {
                // fallback: 找最宽的 dialog
                var maxW = 0;
                for (var d of dialogs) {
                    if (d.offsetWidth > maxW) { maxW = d.offsetWidth; mainDlg = d; }
                }
            }
            if (!mainDlg) return '';
            var walker = document.createTreeWalker(mainDlg, NodeFilter.SHOW_TEXT, null, false);
            var texts = []; var node;
            while(node = walker.nextNode()) {
                var t = node.textContent.trim();
                if (t.length > 1) texts.push(t);
            }
            return texts.join('|TD|');
        """)

    try:
        driver.get(detail_url)
        time.sleep(wait_sec)

        # 点击"查看广告详情"按钮
        for selector in [
            "//span[contains(text(),'查看广告详情')]",
            "//div[contains(text(),'查看广告详情')]",
            "//a[contains(text(),'查看广告详情')]",
            "//button[contains(text(),'查看广告详情')]",
        ]:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for el in elements:
                    if el.is_displayed() and '查看广告详情' in el.text.strip():
                        el.click()  # Selenium native click
                        time.sleep(5)
                        break
            except Exception:
                continue

        # 等待 Dialog 2（右侧信息栏）出现
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script(
                    "var ds = document.querySelectorAll('[role=dialog]');"
                    "for(var d of ds){if(d.getAttribute('aria-labelledby')==='js_104')return true;}"
                    "return false;"
                )
            )
        except Exception:
            pass
        time.sleep(2)

        # 获取 Dialog 1（主模态框）文本
        full_text = get_main_dialog_text()
        detail_data["raw_detail_text"] = full_text
        lines = [l.strip() for l in full_text.split('|TD|') if l.strip()]

        # ========== 提取通用字段 ==========
        # 性别
        for line in lines:
            for sep in ['：', ':']:
                if sep in line and any(kw in line for kw in ['性别', 'Gender']):
                    val = line.split(sep, 1)[1].strip()
                    if val and val not in ['不限', '不限']:
                        detail_data["gender"] = val
                        break
        if not detail_data["gender"] and 'All genders' in full_text:
            detail_data["gender"] = "不限"

        # 年龄
        for line in lines:
            for sep in ['：', ':']:
                if sep in line and any(kw in line for kw in ['年龄', 'Age']):
                    detail_data["age_range"] = line.split(sep, 1)[1].strip()
                    break

        # 覆盖人数
        for line in lines:
            for sep in ['：', ':']:
                if sep in line and any(kw in line for kw in ['覆盖', 'Reach']):
                    detail_data["reach_count"] = line.split(sep, 1)[1].strip()
                    break

        # 广告文案（取最长且不含字段名的文本）
        skip_kw = ['性别', '年龄', '覆盖', '投放', '广告主', '赞助', '付费', 'Gender', 'Age', 'Reach',
                   '编号', '平台', '投放中', '开始投放', '广告资料库', '资料库', '广告链接', '关闭',
                   '欧盟', '国家', '包含', '排除', '筛选', '地区类型', '广告受众', '广告信息公示',
                   '关于广告赞助方', '关于广告主', '广告主和付费方', '详细了解', '赞助内容', '资料库编号']
        for block in lines:
            block = block.strip()
            if len(block) < 15:
                continue
            if any(kw in block for kw in skip_kw):
                continue
            if len(block) > len(detail_data["ad_text"]):
                detail_data["ad_text"] = block

        # 日期
        for pattern in [
            r'(?:首次投放|开始投放)\s*[:：]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
            r'(\d{4}[-/]\d{2}[-/]\d{2})(?:开始投放|投放)',
        ]:
            m = re.search(pattern, full_text)
            if m and not detail_data["start_date"]:
                detail_data["start_date"] = m.group(1)
                break

        # ========== 抓取4个展开块（isTrusted:true 触发 XHR） ==========
        # 关键技术：isTrusted:true 必须传入 MouseEvent，Facebook 才触发 XHR 加载
        blocks_to_scrape = [
            ("block_ad_disclosure", "广告信息公示（按地区）"),
            ("block_about_sponsor", "关于广告赞助方"),
            ("block_about_advertiser", "关于广告主"),
            ("block_advertiser_payer", "广告主和付费方"),
        ]

        prev_text = ""
        for block_key, heading_text in blocks_to_scrape:
            # 点击 block 标题（用 isTrusted:true）
            click_result = _click_block_isTrusted(driver, heading_text)
            if click_result == 'NOT_FOUND':
                # fallback：尝试关键词的部分匹配
                click_result = driver.execute_script(f"""
                    var dialogs = document.querySelectorAll('[role="dialog"]');
                    for (var d of dialogs) {{
                        if (d.getAttribute('aria-labelledby') === 'js_104') {{
                            var headings = d.querySelectorAll('[role="heading"]');
                            for (var h of headings) {{
                                if (h.textContent.includes('{heading_text}')) {{
                                    var link = h.parentElement;
                                    var rect = link.getBoundingClientRect();
                                    var clientX = Math.floor(rect.left + rect.width/2);
                                    var clientY = Math.floor(rect.top + rect.height/2);
                                    ['mousedown','mouseup','click'].forEach(function(t){{
                                        link.dispatchEvent(new MouseEvent(t,{{view:window,bubbles:true,cancelable:true,clientX:clientX,clientY:clientY,isTrusted:true}}));
                                    }});
                                    return 'OK:'+clientX+','+clientY;
                                }}
                            }}
                        }}
                    }}
                    return 'NOT_FOUND';
                """)

            time.sleep(3)  # 等待 XHR 响应

            # 获取 Dialog 2 的完整文本
            dlg2_text = get_dialog2_text()

            # 提取这个 block 的内容（从标题到下一个 block 之间）
            block_start = dlg2_text.find(heading_text)
            if block_start < 0:
                detail_data[block_key] = ""
                continue

            # 找下一个 block 的起始位置
            next_pos = len(dlg2_text)
            for _, next_heading in blocks_to_scrape:
                if next_heading == heading_text:
                    continue
                npos = dlg2_text.find(next_heading, block_start + 1)
                if npos > block_start and npos < next_pos:
                    next_pos = npos

            block_content = dlg2_text[block_start:next_pos].strip()
            detail_data[block_key] = block_content

            if block_content:
                preview = block_content[:100].replace('\n', ' | ')
                print(f"[详情] {block_key}: {preview}...", flush=True)
            else:
                print(f"[详情] {block_key}: (空)", flush=True)

    except Exception as e:
        print(f"[详情] 解析异常: {e}", flush=True)

    return detail_data

# ============================================================
# 【文件处理】
# ============================================================

def load_json_file(file_path):
    """安全加载 JSON 文件"""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'ads' in data:
                return data['ads']
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                return []
    except Exception as e:
        print(f"[文件] 加载失败 {file_path}: {e}", flush=True)
        return []


def save_json_file(file_path, data, indent=2):
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def process_and_deduplicate(daily_file, agg_file, ads, keyword):
    """
    处理每日数据：与汇总文件去重，保存到每日文件和汇总文件
    
    返回：
        (不重复的广告列表, 新增数量)
    """
    # 加载现有汇总数据
    existing_ads = load_json_file(agg_file)
    existing_ids = {a['library_id'] for a in existing_ads}
    
    # 找出不重复的广告
    new_ads = [a for a in ads if a['library_id'] not in existing_ids]
    
    print(f"[去重] 汇总原有 {len(existing_ads)} 条", flush=True)
    print(f"[去重] 本次新增 {len(new_ads)} 条（不重复）", flush=True)
    
    # 保存每日文件（包含本次所有广告）
    daily_data = {
        "keyword": keyword,
        "scrape_date": datetime.now().strftime('%Y-%m-%d'),
        "total_ads": len(ads),
        "new_ads": len(new_ads),
        "ads": ads,
    }
    save_json_file(daily_file, daily_data)
    print(f"[文件] 已保存每日文件: {daily_file.name}", flush=True)
    
    # 更新汇总文件（只添加不重复的）
    updated_ads = existing_ads + new_ads
    agg_data = {
        "keyword": keyword,
        "last_updated": datetime.now().isoformat(),
        "total_ads": len(updated_ads),
        "ads": updated_ads,
    }
    save_json_file(agg_file, agg_data)
    print(f"[文件] 已更新汇总文件: {agg_file.name}", flush=True)
    
    return new_ads


# ============================================================
# 【视频下载】
# ============================================================

def download_videos(ads, video_dir, keyword):
    """下载广告视频"""
    if not ads:
        print("[视频] 没有广告数据，跳过", flush=True)
        return
    
    # 收集视频 URL（从 creative_data.video_url 或 video_urls 获取）
    video_tasks = []
    for ad in ads:
        # 优先从 creative_data.video_url 获取
        video_url = ad.get("creative_data", {}).get("video_url", "")
        if not video_url:
            # 备选：从 video_urls 列表获取
            for vurl in ad.get("video_urls", []):
                if vurl:
                    video_url = vurl
                    break
        
        if video_url:
            video_tasks.append({
                "url": video_url,
                "library_id": ad.get("library_id", "unknown"),
                "keyword": keyword,
            })
    
    if not video_tasks:
        print("[视频] 没有找到视频 URL", flush=True)
        return
    
    print(f"[视频] 共 {len(video_tasks)} 个视频待下载", flush=True)
    
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # 过滤已存在的
    pending = []
    for task in video_tasks:
        fname = f"{task['library_id']}.mp4"
        vpath = video_dir / fname
        if not (vpath.exists() and vpath.stat().st_size > 0):
            pending.append((task, vpath))
        else:
            print(f"[视频] 已存在，跳过: {fname}", flush=True)
    
    if not pending:
        print("[视频] 所有视频已下载完成", flush=True)
        return
    
    print(f"[视频] 开始下载 {len(pending)} 个视频...", flush=True)
    
    def download_one(task_vpath):
        task, vpath = task_vpath
        try:
            req = urllib.request.Request(task["url"], headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(vpath, "wb") as f:
                    shutil.copyfileobj(resp, f)
            print(f"[视频] 下载完成: {vpath.name} ({vpath.stat().st_size} bytes)", flush=True)
            return True
        except Exception as e:
            print(f"[视频] 下载失败 [{task['library_id']}]: {e}", flush=True)
            return False
    
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as ex:
        futures = {ex.submit(download_one, tp): tp for tp in pending}
        for future in as_completed(futures):
            future.result()
    
    print("[视频] 视频下载完成", flush=True)


# ============================================================
# 【主函数】
# ============================================================

def scrape_keyword(keyword):
    """抓取单个关键词"""
    start_date, end_date = get_date_range()
    folder, daily_file, agg_file, video_dir = get_output_paths(keyword, end_date)
    
    print(f"\n{'='*60}", flush=True)
    print(f"关键词: {keyword}", flush=True)
    print(f"日期范围: {start_date} ~ {end_date}", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"汇总文件: {agg_file.name}", flush=True)
    print(f"{'='*60}", flush=True)
    
    # 构建 URL
    scrape_url = build_url(keyword, start_date, end_date)
    print(f"[URL] {scrape_url}", flush=True)
    
    driver = None
    try:
        # 步骤1：抓取列表页
        print("\n>>> 第1步：抓取广告列表 >>>", flush=True)
        driver = make_driver(headless=HEADLESS)
        ads = scroll_and_collect(driver, scrape_url, keyword, MAX_SCROLLS, WAIT_SEC)
        print(f"\n[第1步完成] 共抓取 {len(ads)} 条广告", flush=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[错误] 抓取失败: {e}", flush=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return
    
    if not ads:
        print("[警告] 没有抓到广告，跳过后续步骤", flush=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return
    
    # 步骤2：详情页抓取（获取4个展开块的详细信息）- 默认跳过以提高速度
    if SCRAPE_DETAIL:
        print("\n>>> 第2步：抓取详情页（4个展开块信息）>>>", flush=True)
        detail_count = 0
        # 限制抓取数量，防止ChromeDriver断开
        detail_ads = ads[:MAX_DETAIL_SCRAPES] if MAX_DETAIL_SCRAPES > 0 else ads
        for i, ad in enumerate(detail_ads):
            try:
                print(f"[详情] 正在抓取 {i+1}/{len(detail_ads)}: {ad['library_id']}", flush=True)
                detail_data = scrape_ad_detail(driver, ad['library_id'], wait_sec=5)
                ad.update(detail_data)
                detail_count += 1
                time.sleep(2)
            except Exception as e:
                print(f"[详情] 抓取失败 {ad['library_id']}: {e}", flush=True)
                continue
        print(f"[详情] 完成，成功抓取 {detail_count}/{len(detail_ads)} 条详情", flush=True)
    else:
        print("\n>>> 第2步：跳过详情页抓取（SCRAPE_DETAIL=False）>>>", flush=True)
        print("[提示] 开启详情页抓取：修改 run.py 中 SCRAPE_DETAIL = True", flush=True)
    
    # 步骤3：去重合并
    print("\n>>> 第3步：去重并更新文件 >>>", flush=True)
    new_ads = process_and_deduplicate(daily_file, agg_file, ads, keyword)
    
    # 步骤4：下载视频（下载本次抓取的所有广告视频，已存在则跳过）
    print("\n>>> 第4步：下载广告视频 >>>", flush=True)
    download_videos(ads, video_dir, keyword)
    
    # 关闭浏览器
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
    
    print(f"\n[完成] 关键词 {keyword} 抓取完毕！", flush=True)
    print(f"  本次新增: {len(new_ads)} 条", flush=True)
    print(f"  汇总总计: {len(load_json_file(agg_file))} 条", flush=True)


def main():
    """主流程"""
    start_date, end_date = get_date_range()
    
    print("=" * 60, flush=True)
    print("Facebook Ad Library 抓取工具 v3", flush=True)
    print(f"执行日期: {end_date}", flush=True)
    if AUTO_DATE:
        print(f"抓取范围: {start_date} ~ {end_date} (最近7天，自动)", flush=True)
    else:
        print(f"抓取范围: {start_date} ~ {end_date} (手动指定)", flush=True)
    print(f"关键词数量: {len(KEYWORDS)}", flush=True)
    print("=" * 60, flush=True)
    
    for i, keyword in enumerate(KEYWORDS, 1):
        print(f"\n\n>>> 开始处理第 {i}/{len(KEYWORDS)} 个关键词: {keyword} >>>", flush=True)
        scrape_keyword(keyword)
    
    print(f"\n\n{'='*60}", flush=True)
    print("全部关键词抓取完成！", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
