"""
Facebook Ad Library 抓取 + 去重合并 + 视频下载
============================================

【功能说明】
  1. 抓取列表页广告（通过滚动翻页加载）
  2. 逐个访问详情页，提取性别/年龄/覆盖等字段
  3. 去重后合并到汇总文件
  4. 下载视频（支持断点续传，已下载跳过）

【与 TikTok 版的差异】
  - URL 参数用日期字符串（不是时间戳）
  - 翻页方式：滚动页面到底（不是点击 View more）
  - 页面到底标志：滚动后无新内容视为到顶
  - 广告ID：从 URL ?id= 参数提取
  - 详情页：提取性别/年龄/覆盖等定向字段

【配置区说明】
  - AUTO_DATE=True  -> 自动模式：抓最近7天（END_DATE=今日，START_DATE=今日-6天）
  - AUTO_DATE=False -> 手动模式：使用下方指定的 START_DATE 和 END_DATE
  - MODE="fixed"    -> 只抓固定数量（由 MAX_ADS 控制）
  - MODE="all"      -> 抓取全部数据（直到页面底部才停止）
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
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 忽略 undetected_chromedriver 析构器警告（不影响程序运行）
warnings.filterwarnings('ignore', category=DeprecationWarning, module='undetected_chromedriver')

# 全局禁用 SSL 验证（解决 SSL 连接错误问题）
ssl._create_default_https_context = ssl._create_unverified_context

# 修复 urllib 的 SSL 问题
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36')]
urllib.request.install_opener(opener)

# ============================================================
#                    【配置区】
#                   （修改这里即可）
# ============================================================

# ----- 搜索条件 -----
KEYWORD = "Block Blast"        # 搜索关键词

# ----- 日期设置 -----
# AUTO_DATE = True  -> 自动模式：抓最近7天（END_DATE=今日，START_DATE=今日-6天）
# AUTO_DATE = False -> 手动模式：使用下方指定的 START_DATE 和 END_DATE
AUTO_DATE = True

START_DATE = "2026-04-15"    # 手动模式时的开始日期（格式：YYYY-MM-DD）
END_DATE = ""                # 手动模式时的结束日期，留空 "" 表示今天

# ----- 抓取模式 -----
#   MODE = "fixed"  -> 只抓固定数量（由 MAX_ADS 控制）
#   MODE = "all"    -> 抓取全部数据（直到页面底部才停止）
MODE = "fixed"                  # ★ 重要：选 "fixed" 或 "all"
MAX_ADS = 20                  # MODE="fixed" 时生效，表示最多抓多少条

# ----- 浏览器模式 -----
#   True  = 无头模式（不弹窗，后台运行，更稳定，推荐）
#   False = 可见浏览器（弹出 Chrome 窗口）
HEADLESS = False

# ----- 等待时间（秒）-----
# 每次滚动后等待（给页面加载时间）
# 数据多或网速慢 → 可以调大，如 5 或 8
WAIT_SEC = 5

# ----- 并发数 -----
MAX_DOWNLOAD_WORKERS = 3       # 视频下载的并发线程数

# ----- 详情页抓取 -----
SCRAPE_DETAILS = True         # True=抓取详情页，False=只抓列表页
DETAIL_WAIT = 3               # 详情页打开后等待秒数（给页面加载时间）
DETAIL_BATCH = 5              # 每处理多少个详情页后保存一次（防止内存累积）

# ============================================================


# ========== Selenium 依赖 ==========
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException


# ============================================================
# 【固定路径】
# （一般不需要改）
# ============================================================
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Chrome 程序路径
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ChromeDriver 路径（注意版本要和本机 Chrome 匹配）
CHROMEDRIVER_PATH = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"

# HTTP 请求头（下载视频时模拟浏览器）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.56 Safari/537.36',
    'Referer': 'https://www.facebook.com/',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Encoding': 'identity',
}


# ============================================================
# 【工具函数】
# ============================================================

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
    daily_file = OUTPUT_DIR / f"ads_{name}_{date_str}.json"  # 每日文件
    video_dir = OUTPUT_DIR / f"videos_{name}"                 # 视频目录
    return agg_file, daily_file, video_dir, date_str


# ============================================================
# 【浏览器驱动】
# ============================================================

def make_driver(headless, max_retries=3):
    """
    创建 Chrome 浏览器实例（带重试机制）

    反爬措施:
      - 优先使用 undetected-chromedriver（如果安装）
      - 禁用 webdriver 特征
      - 禁用通知、弹窗、GPU
      - 设置 User-Agent
      - 固定窗口大小
      - 注入 JS 伪装 navigator 属性
      
    参数:
        headless: 是否使用无头模式
        max_retries: 最大重试次数
    
    返回:
        Chrome 浏览器实例
    """
    for attempt in range(max_retries):
        try:
            # 尝试使用 undetected-chromedriver（更难被检测）
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

            # 使用已有的 chromedriver，避免自动下载
            driver = uc.Chrome(
                options=options, 
                use_subprocess=True,
                driver_executable_path=CHROMEDRIVER_PATH
            )
            print("[浏览器] 使用 undetected-chromedriver（防检测模式）", flush=True)
            return driver
        except ImportError:
            # 未安装 undetected-chromedriver，回退到普通 selenium
            print("[浏览器] 使用普通 selenium（建议安装 undetected-chromedriver）", flush=True)
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
                '--ssl-protocol=TLSv1.2',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content',
            ]:
                options.add_argument(arg)

            if headless:
                options.add_argument('--headless=new')

            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            service = Service(executable_path=CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)

            # 注入 JS：把 webdriver 特征抹掉
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
                print(f"[浏览器] 5秒后重试...", flush=True)
                time.sleep(5)
            else:
                print(f"[浏览器] 已重试 {max_retries} 次，仍失败", flush=True)
                raise
    
    raise Exception("浏览器驱动初始化失败")


# ============================================================
# 【页面交互】
# ============================================================

def accept_cookies_if_present(driver):
    """
    接受 Cookie 弹窗（如果出现）
    """
    for text in ['Accept', 'Accept all', 'Allow', 'I accept', '同意', '接受', 'Allow all cookies']:
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), '" + text + "')]")
            if btn.is_displayed():
                btn.click()
                print(f"[弹窗] 已点击 Cookie 按钮: {text}", flush=True)
                time.sleep(2)
                return
        except NoSuchElementException:
            continue


def safe_click(driver, element, timeout=5):
    """
    安全点击元素（带重试机制）
    如果直接点击失败，会尝试用 JavaScript 点击
    """
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
# 【URL 构建】
# ============================================================

def build_url(keyword, start_date, end_date):
    """
    构建 Facebook Ad Library 搜索 URL

    参数:
        keyword:    搜索关键词
        start_date: 开始日期字符串（如 "2026-04-14"）
        end_date:   结束日期字符串（留空表示今天）

    返回:
        完整 URL 字符串
    """
    base = "https://www.facebook.com/ads/library/"
    params = [
        ("activeStatus", "all"),
        ("category", "ALL"),
        ("view_all_page_id", ""),
        ("search_recency_date", "ALL"),
    ]
    
    # 日期筛选
    if start_date:
        params.append(("date", f"{start_date}_{end_date}" if end_date else start_date))
    
    # 关键词
    if keyword:
        params.append(("q", keyword))
    
    query = urllib.parse.urlencode(params)
    return base + "?" + query


# ============================================================
# 【广告解析（列表页）】
# ============================================================

def parse_ads_from_page(driver):
    """
    从当前列表页解析所有广告

    Facebook 广告库页面结构：
      每个广告卡片包含 ad_id，URL 格式为 /ads/library/?id=xxx

    返回:
        广告字典列表
    """
    ads = []
    seen_ids = set()

    # 找所有广告详情链接
    links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ads/library/?id=')]")

    for link in links:
        href = link.get_attribute("href") or ""

        # 提取广告 ID（URL 中的 id 参数值）
        m = re.search(r'[?&]id=(\d+)', href)
        if not m:
            continue
        ad_id = m.group(1)
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        # 获取链接文字作为广告文案备选
        text = link.text or ""

        ad = {
            "library_id": ad_id,
            "index": len(ads) + 1,
            "platforms": ["Facebook"],
            "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
            "ad_text": text[:500] if text else "",
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

    return ads


# ============================================================
# 【滚动翻页】
# ============================================================

def scroll_and_collect(driver, url, max_scrolls, wait_sec):
    """
    滚动列表页并收集广告

    返回:
        (ads列表, 最后一次获取的页面HTML)
    """
    driver.get(url)
    time.sleep(wait_sec)
    
    accept_cookies_if_present(driver)
    time.sleep(2)

    ads = []
    prev_count = 0
    no_new_count = 0

    while True:
        # 解析当前页广告
        page_ads = parse_ads_from_page(driver)
        
        # 去重合并
        new_ids = set(a['library_id'] for a in page_ads)
        for a in page_ads:
            if a['library_id'] not in [existing['library_id'] for existing in ads]:
                ads.append(a)

        print(f"  滚动中... 已抓 {len(ads)} 条广告", flush=True)

        # MODE="fixed" 时检查是否达标
        if MODE == "fixed" and len(ads) >= MAX_ADS:
            ads = ads[:MAX_ADS]
            print(f"[模式] 已达 MAX_ADS={MAX_ADS}，停止抓取", flush=True)
            break

        # 检查是否到底
        if len(ads) == prev_count:
            no_new_count += 1
            if no_new_count >= 3:
                print("[抓取] 连续3次无新广告，认为已到底", flush=True)
                break
        else:
            no_new_count = 0

        prev_count = len(ads)

        # 滚到页面底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_sec)

        # 如果滚动次数用完
        if MODE == "fixed":
            # 已经在上面 break 了，这里只处理 all 模式
            pass

    # 最后一次滚动回到顶部
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    html = driver.execute_script("return document.body.innerHTML")
    return ads, html


# ============================================================
# 【详情页抓取】
# ============================================================

def scrape_ad_detail(driver, library_id, wait_sec=5):
    """
    访问 Facebook 广告详情页，提取详细信息
    
    参数:
        driver: Selenium 浏览器实例
        library_id: 广告 library_id
        wait_sec: 页面加载等待秒数
    
    返回:
        包含详细信息的字典
    """
    detail_url = f"https://www.facebook.com/ads/library/?id={library_id}"
    
    detail_data = {
        "library_id": library_id,
        "detail_url": detail_url,
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
    
    try:
        driver.get(detail_url)
        time.sleep(wait_sec)
        
        # 点击"查看广告详情"按钮
        view_detail_clicked = False
        for xpath in [
            "//div[contains(text(), '查看广告详情')]",
            "//span[contains(text(), '查看广告详情')]",
        ]:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    try:
                        if '查看广告详情' in el.text.strip():
                            if safe_click(driver, el):
                                view_detail_clicked = True
                                time.sleep(3)
                                break
                    except Exception:
                        continue
                if view_detail_clicked:
                    break
            except Exception:
                continue
        
        # 展开4个指定区域
        expand_sections = [
            "广告信息公示（按地区）",
            "关于广告赞助方",
            "关于广告主",
            "广告主和付费方",
        ]
        
        for section in expand_sections:
            try:
                xpath = f"//div[contains(text(), '{section}')]"
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    try:
                        if section in el.text.strip():
                            safe_click(driver, el)
                            time.sleep(1.5)
                            break
                    except Exception:
                        continue
            except Exception:
                continue
        
        # 检测并展开未展开的区域
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "打开下拉菜单" in body_text:
                for xpath in ["//div[contains(text(), '打开下拉菜单')]", "//span[contains(text(), '打开下拉菜单')]"]:
                    try:
                        dropdowns = driver.find_elements(By.XPATH, xpath)
                        for dd in dropdowns:
                            try:
                                parent = dd.find_element(By.XPATH, "..")
                                safe_click(driver, parent)
                                time.sleep(1.5)
                            except Exception:
                                pass
                    except Exception:
                        continue
        except Exception:
            pass
        
        time.sleep(2)
        
        # 获取页面文本
        try:
            body_element = driver.find_element(By.TAG_NAME, "body")
            full_text = body_element.text
            detail_data["raw_detail_text"] = full_text
        except Exception:
            pass
        
        # ========== 解析字段 ==========
        lines = full_text.split('\n')
        
        # 提取性别
        gender_found = False
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if any(kw in line_stripped for kw in ['性别：', '性别:', 'Gender：', 'Gender:']):
                for sep in ['：', ':']:
                    if sep in line_stripped:
                        parts = line_stripped.split(sep)
                        if len(parts) >= 2:
                            gender_val = parts[1].strip()
                            if gender_val and gender_val not in [' ']:
                                detail_data["gender"] = gender_val
                                gender_found = True
                                break
                if gender_found:
                    break
            
            if 'All genders' in line_stripped or '性别不限' in line_stripped:
                detail_data["gender"] = "不限"
                gender_found = True
                break
            
            if not gender_found and i > 0:
                prev_line = lines[i-1].strip() if i > 0 else ""
                if prev_line in ['性别', 'Gender', '性别：', 'Gender:']:
                    if line_stripped and line_stripped not in [' ']:
                        detail_data["gender"] = line_stripped
                        gender_found = True
                        break
        
        # 备选方案：在原始文本中用正则搜索
        if not detail_data["gender"]:
            gender_patterns = [
                r'性别[：:]\s*([^\n]+)',
                r'Gender[：:]\s*([^\n]+)',
                r'All genders',
                r'性别不限',
            ]
            for pattern in gender_patterns:
                m = re.search(pattern, full_text)
                if m:
                    detail_data["gender"] = m.group(1).strip() if m.groups() and m.group(1).strip() else "不限"
                    break
        
        # 提取年龄
        for i, line in enumerate(lines):
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
        
        if not detail_data["age_range"]:
            age_patterns = [
                r'(\d+[-~至]\d+\+?岁)',
                r'(13[-~至]65\+?岁)',
            ]
            for pattern in age_patterns:
                m = re.search(pattern, full_text)
                if m:
                    detail_data["age_range"] = m.group(1)
                    break
        
        # 提取覆盖
        for i, line in enumerate(lines):
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
        
        if not detail_data["reach_count"]:
            reach_patterns = [
                r'覆盖\s*([\d,万]+)',
                r'Reached\s*([\d,万]+)',
            ]
            for pattern in reach_patterns:
                m = re.search(pattern, full_text)
                if m:
                    detail_data["reach_count"] = m.group(1)
                    break
        
        # 提取广告文案（广告文字通常是卡片中最长的那段）
        text_blocks = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9\s.,!?;:]{20,200}', full_text)
        for block in text_blocks:
            block = block.strip()
            # 过滤掉包含关键词的块
            if any(kw in block for kw in ['性别', '年龄', '覆盖', '投放', '广告主', '赞助', '付费', 'Gender', 'Age', 'Reach', 'Advertiser', 'Disclosure']):
                continue
            if len(block) > len(detail_data["ad_text"]):
                detail_data["ad_text"] = block
        
        # 提取开始日期
        date_patterns = [
            r'(?:首次投放|First shown|开始投放)\s*[:：]?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
            r'(\d{4}[-/]\d{2}[-/]\d{2})',
        ]
        for pattern in date_patterns:
            m = re.search(pattern, full_text)
            if m:
                detail_data["start_date"] = m.group(1)
                break
        
        # 提取广告主名称
        advertiser_patterns = [
            r'(?:广告主|Advertiser|广告主名称)\s*[:：]?\s*([^\n]{2,50})',
        ]
        for pattern in advertiser_patterns:
            m = re.search(pattern, full_text)
            if m:
                detail_data["advertiser_name"] = m.group(1).strip()
                break
        
        # 提取付费方名称
        payer_patterns = [
            r'(?:付费方|Paid by|付费方名称)\s*[:：]?\s*([^\n]{2,50})',
        ]
        for pattern in payer_patterns:
            m = re.search(pattern, full_text)
            if m:
                detail_data["payer_name"] = m.group(1).strip()
                break
        
    except Exception as e:
        print(f"[详情] 解析异常: {e}", flush=True)
    
    return detail_data


# ============================================================
# 【文件处理】
# ============================================================

def process_files(keyword, ads, scrape_url):
    """
    处理广告数据：
      1. 加载已有每日文件（如有）
      2. 和汇总文件合并去重
      3. 保存每日文件和汇总文件

    返回:
        (每日文件路径, 汇总文件路径, 视频目录路径, 新增广告列表)
    """
    name = keyword_to_name(keyword)
    date_str = get_today_date_str()
    
    agg_file = OUTPUT_DIR / f"ads_{name}.json"              # 汇总文件
    daily_file = OUTPUT_DIR / f"ads_{name}_{date_str}.json"  # 每日文件
    video_dir = OUTPUT_DIR / f"videos_{name}"
    video_dir.mkdir(parents=True, exist_ok=True)

    # 已有汇总数据
    existing_agg = []
    if agg_file.exists():
        try:
            with open(agg_file, "r", encoding="utf-8") as f:
                existing_agg = json.load(f)
        except Exception:
            existing_agg = []

    existing_ids = {a['library_id'] for a in existing_agg}
    
    # 本次新增（去重）
    new_ads = [a for a in ads if a['library_id'] not in existing_ids]
    
    # 构建每日文件（只包含本次抓到的）
    daily_data = {
        "keyword": keyword,
        "scrape_date": date_str,
        "scrape_url": scrape_url,
        "total_ads": len(ads),
        "ads": ads,
    }
    
    # 构建汇总文件（所有历史）
    agg_data = {
        "keyword": keyword,
        "last_updated": datetime.now().isoformat(),
        "total_ads": len(existing_agg) + len(new_ads),
        "ads": existing_agg + new_ads,
    }
    
    # 保存每日文件
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=2)
    print(f"[文件] 已保存每日文件: {daily_file.name}", flush=True)
    
    # 保存汇总文件
    with open(agg_file, "w", encoding="utf-8") as f:
        json.dump(agg_data, f, ensure_ascii=False, indent=2)
    print(f"[文件] 已保存汇总文件: {agg_file.name}", flush=True)
    
    print(f"[去重] 汇总去重：原有 {len(existing_agg)} 条 + 新增 {len(new_ads)} 条", flush=True)
    
    return daily_file, agg_file, video_dir, new_ads


# ============================================================
# 【视频下载】
# ============================================================

def download_videos(daily_file, video_dir, keyword):
    """
    从每日文件中读取视频 URL 并下载
    支持断点续传：已下载的文件会跳过
    """
    if not daily_file.exists():
        print("[视频] 每日文件不存在，跳过视频下载", flush=True)
        return

    with open(daily_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    ads = data.get("ads", [])
    if not ads:
        print("[视频] 没有广告数据", flush=True)
        return

    # 收集所有视频 URL
    video_tasks = []
    for ad in ads:
        for vurl in ad.get("video_urls", []):
            if vurl:
                video_tasks.append({
                    "url": vurl,
                    "library_id": ad.get("library_id", "unknown"),
                })

    if not video_tasks:
        print("[视频] 没有找到视频 URL", flush=True)
        return

    print(f"[视频] 共 {len(video_tasks)} 个视频待下载", flush=True)

    # 过滤已存在的
    def get_video_path(vurl, video_dir):
        ext = ".mp4"
        if ".m3u8" in vurl:
            ext = ".m3u8"
        fname = vurl.split("/")[-1].split("?")[0]
        if not any(ext in fname for ext in [".mp4", ".m3u8", ".mov", ".avi"]):
            fname += ext
        return video_dir / fname

    pending = []
    for task in video_tasks:
        vpath = get_video_path(task["url"], video_dir)
        if vpath.exists() and vpath.stat().st_size > 0:
            print(f"[视频] 已存在，跳过: {vpath.name}", flush=True)
        else:
            pending.append((task, vpath))

    if not pending:
        print("[视频] 所有视频已下载完成", flush=True)
        return

    print(f"[视频] 开始下载 {len(pending)} 个视频...", flush=True)

    def download_one(task_path):
        task, vpath = task_path
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

def main():
    """主流程"""
    # 确定日期
    start_date, end_date = resolve_dates()
    date_str = get_today_date_str()
    
    # 生成文件路径
    agg_file, daily_file, video_dir, _ = get_file_paths(KEYWORD, date_str)
    
    # 打印配置摘要
    mode_name = f"fixed({MAX_ADS})" if MODE == "fixed" else "all"
    print(f"Facebook Ad Library 抓取 + 合并 + 视频下载", flush=True)
    print(f"关键词: {KEYWORD}", flush=True)
    print(f"日期范围: {start_date} ~ {end_date}", flush=True)
    print(f"执行日期: {date_str}", flush=True)
    print(f"模式: {mode_name}", flush=True)
    print(f"详情抓取: {'开启' if SCRAPE_DETAILS else '关闭'}", flush=True)
    print("=" * 60, flush=True)

    driver = None
    try:
        # ---- 步骤1：抓取列表页广告 ----
        print("\n>>> 第1步：抓取广告数据（列表页） >>>", flush=True)
        scrape_url = build_url(KEYWORD, start_date, end_date)
        print("[启动] Chrome...", flush=True)
        print(f"  访问: {scrape_url}", flush=True)

        driver = make_driver(headless=HEADLESS)
        ads, html = scroll_and_collect(driver, scrape_url, MAX_SCROLLS if MODE == "fixed" else 999, WAIT_SEC)

        print(f"\n[第1步完成] 共收集 {len(ads)} 条广告", flush=True)

        # ---- 步骤2：抓取详情页 ----
        if SCRAPE_DETAILS and ads:
            print("\n>>> 第2步：抓取详情页（性别/年龄/覆盖等） >>>", flush=True)
            
            driver_detail = make_driver(headless=HEADLESS)
            
            for i, ad in enumerate(ads, 1):
                lib_id = ad.get('library_id', '')
                if not lib_id:
                    continue
                
                print(f"\n[{i}/{len(ads)}] 处理广告: {lib_id}", flush=True)
                print(f"  正在访问详情页...", end="", flush=True)
                
                detail = scrape_ad_detail(driver_detail, lib_id, wait_sec=DETAIL_WAIT)
                
                # 合并详情数据到广告
                ad['detail_url'] = detail.get('detail_url', '')
                ad['ad_text'] = detail.get('ad_text', ad.get('ad_text', ''))
                ad['start_date'] = detail.get('start_date', ad.get('start_date', ''))
                ad['delivery_status'] = detail.get('delivery_status', '')
                ad['ad_disclosure_regions'] = detail.get('ad_disclosure_regions', [])
                ad['age_range'] = detail.get('age_range', '')
                ad['gender'] = detail.get('gender', '')
                ad['reach_count'] = detail.get('reach_count', '')
                ad['advertiser_name'] = detail.get('advertiser_name', '')
                ad['advertiser_description'] = detail.get('advertiser_description', '')
                ad['payer_name'] = detail.get('payer_name', '')
                ad['creative_data'] = detail.get('creative_data', {})
                ad['raw_detail_text'] = detail.get('raw_detail_text', '')
                ad['detail_scrape_time'] = datetime.now().isoformat()
                
                # 打印关键字段
                print("[OK]", flush=True)
                print(f"    date: {ad['start_date'] or '(empty)'}", flush=True)
                print(f"    gender: {ad['gender'] or '(empty)'}", flush=True)
                print(f"    age: {ad['age_range'] or '(empty)'}", flush=True)
                print(f"    reach: {ad['reach_count'] or '(empty)'}", flush=True)
                print(f"    advertiser: {ad['advertiser_name'] or '(empty)'}", flush=True)
                
                # 每 DETAIL_BATCH 个保存一次（防止内存累积 + 中途崩溃丢失数据）
                if i % DETAIL_BATCH == 0:
                    print(f"\n[中间保存] 每 {DETAIL_BATCH} 条保存一次...", flush=True)
                    daily_file_tmp, agg_file_tmp, _, _ = get_file_paths(KEYWORD, date_str)
                    process_files(KEYWORD, ads[:i], scrape_url)
            
            try:
                driver_detail.quit()
            except Exception:
                pass
            
            print(f"\n[第2步完成] 详情页抓取完毕", flush=True)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[错误] 抓取失败: {e}", flush=True)
        return
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ---- 步骤3：去重合并到汇总文件 ----
    print("\n>>> 第3步：去重并更新汇总文件 >>>", flush=True)
    daily_file, agg_file, video_dir, new_ads = process_files(KEYWORD, ads, scrape_url)

    # ---- 步骤4：下载视频 ----
    print("\n>>> 第4步：下载视频 >>>", flush=True)
    download_videos(daily_file, video_dir, KEYWORD)

    # ---- 完成摘要 ----
    print(f"\n{'='*60}", flush=True)
    print(f"抓取完成！", flush=True)
    print(f"本次抓取: {len(ads)} 条", flush=True)
    print(f"每日文件: {daily_file.name}", flush=True)
    print(f"汇总文件: {agg_file.name}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
