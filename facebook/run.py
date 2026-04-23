"""
Facebook Ad Library 抓取工具 v3
============================================

【功能说明】
  1. 根据给定 URL 抓取广告数据
  2. 每日数据单独存储（按关键词+日期）
  3. 每日数据与汇总文件去重合并（按 library_id + 关键词）
  4. 下载每日文件中不重复广告的视频

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

# 忽略 undetected_chromedriver 析构器警告
warnings.filterwarnings('ignore', category=DeprecationWarning, module='undetected_chromedriver')

# 全局禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36')]
urllib.request.install_opener(opener)

# ============================================================
#                    【配置区】
# ============================================================

# 关键词列表（后续由文件或表格提供）
KEYWORDS = [
    "Block Blast"
]

# 国家代码（Facebook Ad Library 国家筛选）
# 可选：US, CN, GB, JP, KR, DE, FR, TW, HK, SG 等
COUNTRY = "US"

# 日期设置：抓取 start_date[min] = 今天 - DAYS_BACK 天
DAYS_BACK = 6

# 浏览器模式
HEADLESS = False

# 是否抓取详情页（4个展开块）- 耗时长且可能不稳定
# True = 启用（每个广告额外5-10秒，可能导致超时）
# False = 跳过（只抓取列表页信息）
SCRAPE_DETAIL = False

# 等待时间
WAIT_SEC = 5

# 最大滚动次数
MAX_SCROLLS = 3  # 约10条广告

# 目标广告数量（0=不限制）
MAX_ADS = 10

# 并发数
MAX_DOWNLOAD_WORKERS = 3

# 视频下载等待秒数
DETAIL_WAIT = 1

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
    """获取日期范围：今天 和 今天-DAYS_BACK天"""
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    start_date = (today - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
    return start_date, today_str


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
    folder = OUTPUT_DIR / keyword_to_folder(keyword)
    daily_file = folder / f"{date_str}.json"
    agg_file = folder / "all_ads.json"
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
# 【详情页抓取】
# ============================================================

def scrape_ad_detail(driver, library_id, wait_sec=8):
    """访问详情页提取更多信息（包括4个展开块）"""
    detail_url = f"https://www.facebook.com/ads/library/?id={library_id}"
    
    detail_data = {
        "library_id": library_id,
        "detail_url": detail_url,
        "ad_text": "",
        "start_date": "",
        "end_date": "",
        "delivery_status": "",
        "ad_disclosure_regions": [],  # 广告信息公示（按地区）
        "age_range": "",
        "gender": "",
        "reach_count": "",
        "advertiser_name": "",  # 关于广告主
        "advertiser_description": "",  # 关于广告主描述
        "payer_name": "",  # 广告主和付费方
        "creative_data": {},
        "raw_detail_text": "",
        # 4个展开块的详细内容
        "block_ad_disclosure": {},  # 广告信息公示（按地区）
        "block_about_sponsor": {},  # 关于广告赞助方
        "block_about_advertiser": {},  # 关于广告主
        "block_advertiser_payer": {},  # 广告主和付费方
    }
    
    try:
        driver.get(detail_url)
        time.sleep(wait_sec)
        
        # 点击"查看广告详情"按钮（如果存在）
        view_detail_selectors = [
            "//span[contains(text(), '查看广告详情')]",
            "//div[contains(text(), '查看广告详情')]",
            "//a[contains(text(), '查看广告详情')]",
            "//button[contains(text(), '查看广告详情')]",
        ]
        for selector in view_detail_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for el in elements:
                    if '查看广告详情' in el.text.strip():
                        safe_click(driver, el)
                        time.sleep(3)
                        break
            except Exception:
                continue
        
        # 等待页面加载完成
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        
        time.sleep(3)
        
        # 查找并点击4个展开块
        expandable_blocks = {
            "block_ad_disclosure": [
                "//div[contains(text(), '广告信息公示')]",
                "//div[contains(text(), '按地区')]",
                "//span[contains(text(), '广告信息公示')]",
            ],
            "block_about_sponsor": [
                "//div[contains(text(), '关于广告赞助方')]",
                "//span[contains(text(), '关于广告赞助方')]",
            ],
            "block_about_advertiser": [
                "//div[contains(text(), '关于广告主')]",
                "//span[contains(text(), '关于广告主')]",
            ],
            "block_advertiser_payer": [
                "//div[contains(text(), '广告主和付费方')]",
                "//span[contains(text(), '广告主和付费方')]",
            ],
        }
        
        # 依次点击每个块并提取内容
        for block_name, selectors in expandable_blocks.items():
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for el in elements:
                        try:
                            safe_click(driver, el)
                            time.sleep(2)
                        except Exception:
                            pass
                        
                        try:
                            parent = el.find_element(By.XPATH, "..")
                            expanded_content = None
                            try:
                                expanded_content = parent.find_element(By.XPATH, "following-sibling::*[contains(@class, 'expand') or contains(@class, 'content')]")
                            except Exception:
                                pass
                            
                            if not expanded_content:
                                try:
                                    expanded_content = parent.find_element(By.XPATH, ".//div[contains(@class, 'content') or contains(@class, 'detail')]")
                                except Exception:
                                    pass
                            
                            if expanded_content:
                                content_text = expanded_content.text
                                if content_text:
                                    detail_data[block_name]["content"] = content_text
                                    print(f"[详情] {block_name}: {content_text[:100]}...", flush=True)
                                    break
                        except Exception:
                            pass
                        
                        try:
                            visible_text = el.text
                            if visible_text and len(visible_text) > 10:
                                detail_data[block_name]["visible_text"] = visible_text
                        except Exception:
                            pass
                        
                except Exception:
                    continue
        
        # 获取完整页面文本
        try:
            body_element = driver.find_element(By.TAG_NAME, "body")
            full_text = body_element.text
            detail_data["raw_detail_text"] = full_text
        except Exception:
            pass
        
        # 提取通用字段
        lines = full_text.split('\n')
        
        # 性别
        if not detail_data["gender"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['性别：', '性别:', 'Gender：', 'Gender:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2 and parts[1].strip():
                                detail_data["gender"] = parts[1].strip()
                                break
                    if detail_data["gender"]:
                        break
        
        if not detail_data["gender"]:
            if 'All genders' in full_text or '性别不限' in full_text:
                detail_data["gender"] = "不限"
        
        # 年龄
        if not detail_data["age_range"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['年龄：', '年龄:', 'Age：', 'Age:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2:
                                detail_data["age_range"] = parts[1].strip()
                                break
                    if detail_data["age_range"]:
                        break
        
        # 覆盖人数
        if not detail_data["reach_count"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['覆盖：', '覆盖:', '覆盖人数', 'Reached：', 'Reached:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2:
                                detail_data["reach_count"] = parts[1].strip()
                                break
                    if detail_data["reach_count"]:
                        break
        
        # 广告文案
        text_blocks = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:]{20,200}', full_text)
        for block in text_blocks:
            block = block.strip()
            if any(kw in block for kw in ['性别', '年龄', '覆盖', '投放', '广告主', '赞助', '付费', 'Gender', 'Age', 'Reach']):
                continue
            if len(block) > len(detail_data["ad_text"]):
                detail_data["ad_text"] = block
        
        # 日期
        date_patterns = [
            r'(?:首次投放|First shown|开始投放)\s*[:：]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
            r'(?:结束日期|Ended|Ends)\s*[:：]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
        ]
        for pattern in date_patterns:
            m = re.search(pattern, full_text)
            if m:
                if not detail_data["start_date"]:
                    detail_data["start_date"] = m.group(1)
                else:
                    detail_data["end_date"] = m.group(1)
        
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
    
    # 收集视频 URL
    video_tasks = []
    for ad in ads:
        for vurl in ad.get("video_urls", []):
            if vurl:
                video_tasks.append({
                    "url": vurl,
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
        for i, ad in enumerate(ads):
            try:
                print(f"[详情] 正在抓取 {i+1}/{len(ads)}: {ad['library_id']}", flush=True)
                detail_data = scrape_ad_detail(driver, ad['library_id'], wait_sec=5)
                ad.update(detail_data)
                detail_count += 1
                time.sleep(2)
            except Exception as e:
                print(f"[详情] 抓取失败 {ad['library_id']}: {e}", flush=True)
                continue
        print(f"[详情] 完成，成功抓取 {detail_count}/{len(ads)} 条详情")
    else:
        print("\n>>> 第2步：跳过详情页抓取（SCRAPE_DETAIL=False）>>>", flush=True)
        print("[提示] 开启详情页抓取：修改 run.py 中 SCRAPE_DETAIL = True", flush=True)
    
    # 步骤3：去重合并
    print("\n>>> 第3步：去重并更新文件 >>>", flush=True)
    new_ads = process_and_deduplicate(daily_file, agg_file, ads, keyword)
    
    # 步骤4：下载视频（只下载不重复的广告）
    print("\n>>> 第4步：下载新增广告的视频 >>>", flush=True)
    download_videos(new_ads, video_dir, keyword)
    
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
    print(f"抓取范围: {start_date} ~ {end_date} (最近{DAYS_BACK}天)", flush=True)
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
