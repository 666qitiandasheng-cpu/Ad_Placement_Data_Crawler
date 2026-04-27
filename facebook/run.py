"""
Facebook Ad Library Scraper
===========================
Features:
  1. List page scraping via Playwright CDP (OpenClaw Chrome) or Selenium
  2. Detail page scraping with full field extraction (CDP first, Selenium fallback)
  3. Full ad fields: video_url, age_range, gender, reach_count, body_text,
     advertiser_name, payer_name, ad_disclosure_regions, etc.
  4. Deduplication and daily + aggregate JSON output
  5. Video download with resume support

Usage:
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

warnings.filterwarnings('ignore', category=DeprecationWarning, module='undetected_chromedriver')
ssl._create_default_https_context = ssl._create_unverified_context

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
urllib.request.install_opener(opener)

# ============================================================
# CONFIG
# ============================================================

KEYWORDS = [
    "Block Blast",
]

COUNTRY = "US"

AUTO_DATE = True
START_DATE = "2026-04-21"
END_DATE = "2026-04-27"

MODE = "fixed"
MAX_ADS = 10

HEADLESS = False
WAIT_SEC = 5
MAX_SCROLLS = 50

SCRAPE_DETAIL = True
MAX_DETAIL_SCRAPES = 0  # 0 = all ads (via else branch)
CDP_URL = "http://127.0.0.1:18800"
DETAIL_WAIT = 5

MAX_DOWNLOAD_WORKERS = 3

# ============================================================
# IMPORTS
# ============================================================

from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROMEDRIVER_PATH = r"C:\Users\Ivy\.wdm\drivers\chromedriver\win64\147.0.7727.56\chromedriver-win32\chromedriver.exe"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.facebook.com/',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Encoding': 'identity',
}

# ============================================================
# UTILS
# ============================================================

def get_date_range():
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
    return keyword.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")


def get_output_paths(keyword, date_str):
    folder_name = keyword_to_folder(keyword)
    folder = OUTPUT_DIR / folder_name
    daily_file = folder / f"ads_{folder_name}_{date_str}.json"
    agg_file = folder / f"ads_{folder_name}.json"
    video_dir = folder / "videos"
    return folder, daily_file, agg_file, video_dir


# ============================================================
# BROWSER
# ============================================================

def make_driver(headless, max_retries=3):
    for attempt in range(max_retries):
        try:
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
            for arg in [
                '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
                '--disable-extensions', '--disable-notifications',
                '--disable-popup-blocking', '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--ssl-protocol=TLSv1.2', '--ignore-certificate-errors',
                '--allow-running-insecure-content',
            ]:
                options.add_argument(arg)
            if headless:
                options.add_argument('--headless=new')
            driver = uc.Chrome(options=options, use_subprocess=True,
                               driver_executable_path=CHROMEDRIVER_PATH)
            print("[Browser] Using undetected-chromedriver", flush=True)
            return driver
        except ImportError:
            print("[Browser] Using selenium", flush=True)
            options = Options()
            options.binary_location = CHROME_PATH
            for arg in [
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
                '--disable-extensions', '--disable-notifications',
                '--disable-popup-blocking', '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
            print(f"[Browser] Init attempt {attempt+1} failed: {e}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise


# ============================================================
# PAGE INTERACTION
# ============================================================

def accept_cookies_if_present(driver):
    for text in ['Accept', 'Accept all', 'Allow', 'I accept', '同意', '接受', 'Allow all cookies']:
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), '" + text + "')]")
            if btn.is_displayed():
                btn.click()
                print(f"[Popup] Clicked: {text}", flush=True)
                time.sleep(2)
                return
        except NoSuchElementException:
            continue


# ============================================================
# DETAIL HTML PARSING
# ============================================================

def extract_video_from_detail_html(html):
    m = re.search(r'"videos":\[\{"video_hd_url":"([^"]+)"', html)
    if m:
        return m.group(1).replace('\\/', '/')
    return ''


def find_ad_data_in_json(obj, ad_id, depth=0):
    if depth > 30:
        return None
    if isinstance(obj, dict):
        if obj.get('ad_archive_id') and str(obj.get('ad_archive_id')) == str(ad_id):
            return obj
        for v in obj.values():
            r = find_ad_data_in_json(v, ad_id, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = find_ad_data_in_json(item, ad_id, depth + 1)
            if r:
                return r
    return None


def extract_all_fields_from_html(html, ad_id):
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

    # Video URL
    m = re.search(r'"videos":\[\{"video_hd_url":"([^"]+)"', html)
    if m:
        result['video_url'] = m.group(1).replace('\\/', '/')

    # JSON scripts
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

        snap = ad_data.get('snapshot', {})
        result['page_name'] = snap.get('page_name', '')
        result['title'] = snap.get('title', '')
        body = snap.get('body', {})
        if isinstance(body, dict):
            result['body_text'] = body.get('text', '')
        elif body:
            result['body_text'] = str(body)
        result['link_url'] = snap.get('link_url', '')
        result['cta_type'] = snap.get('cta_type', '')
        result['display_format'] = snap.get('display_format', '')
        result['publisher_platform'] = snap.get('publisher_platform', [])

        sd = snap.get('start_date')
        if sd:
            try:
                result['start_date'] = datetime.fromtimestamp(int(sd)).strftime('%Y-%m-%d')
            except:
                pass
        ed = snap.get('end_date')
        if ed:
            try:
                result['end_date'] = datetime.fromtimestamp(int(ed)).strftime('%Y-%m-%d')
            except:
                pass

        disp = snap.get('disclaimer_label')
        if disp:
            result['ad_disclosure_regions'] = [disp]

        imp = snap.get('impressions_with_index') or {}
        if isinstance(imp, dict):
            result['reach_count'] = imp.get('impressions_text', '')

        result['spend'] = snap.get('spend', '')
        result['currency'] = snap.get('currency', '')

        gated = snap.get('gated_type', '')
        if gated == 'ALL_AGES':
            result['age_range'] = 'All ages'
        elif gated == 'MULTI_AGE_RANGE':
            result['age_range'] = 'Multi-age'
        elif gated:
            result['age_range'] = gated

        gender = snap.get('gender', '')
        result['gender'] = 'All ages' if gender == 'ALL' else gender

        result['advertiser_name'] = result['page_name']
        payer = snap.get('payer_name', '')
        if payer:
            result['payer_name'] = payer
        break

    # Fallback global searches
    if not result['advertiser_name']:
        m = re.search(r'"page_name":"((?:[^"\\]|\\.)*)"', html)
        if m:
            try:
                result['advertiser_name'] = m.group(1).encode().decode('unicode_escape')
            except:
                result['advertiser_name'] = m.group(1)

    if not result['body_text']:
        m = re.search(r'"body":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
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
            result['age_range'] = 'All ages' if gt == 'ALL_AGES' else ('Multi-age' if gt == 'MULTI_AGE_RANGE' else gt)

    if not result['gender']:
        m = re.search(r'"gender":"([^"]+)"', html)
        if m:
            g = m.group(1)
            result['gender'] = 'All ages' if g == 'ALL' else g

    if not result['ad_disclosure_regions']:
        m = re.search(r'"disclaimer_label":"([^"]+)"', html)
        if m:
            result['ad_disclosure_regions'] = [m.group(1)]

    if not result['payer_name']:
        m = re.search(r'"payer_name":"((?:[^"\\]|\\.)*)"', html)
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
            url = (f"https://www.facebook.com/ads/library/?id={library_id}"
                   "&active_status=active&ad_type=all&country=US"
                   "&is_targeted_country=false&media_type=all&search_type=page")
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(wait_sec)
            html = page.content()
            video_url = extract_video_from_detail_html(html)
            browser.close()
            return html, video_url
    except Exception as e:
        print("[CDP] Fetch failed " + library_id + ": " + str(e))
        return '', ''


# ============================================================
# AD PARSING
# ============================================================

def extract_ad_details(page_source, ad_id):
    from datetime import datetime
    pattern = r'ad_archive_id[":\s]+' + re.escape(ad_id)
    match = re.search(pattern, page_source)
    if not match:
        return '', ''
    pos = match.start()
    start = max(0, pos - 3000)
    end = min(len(page_source), pos + 5000)
    context = page_source[start:end]
    video_url = ''
    vm = re.search(r'"video_hd_url":"([^"]+)"', context)
    if vm:
        video_url = vm.group(1).replace('\\/', '/')
    else:
        if not re.search(r'video_hd_url[":\s]+null', context):
            video_url = ''
    start_date = ''
    sdm = re.search(r'start_date[":\s]+(\d+)', context)
    if sdm:
        try:
            start_date = datetime.fromtimestamp(int(sdm.group(1))).strftime('%Y-%m-%d')
        except:
            pass
    return video_url, start_date


def parse_ads_from_page(driver):
    ads = []
    seen_ids = set()
    try:
        page_source = driver.page_source
        ad_ids = re.findall(r'ad_archive_id[":\s]+(\d+)', page_source)
        if ad_ids:
            ad_ids = list(set(ad_ids))
            print(f"[JSON] Found {len(ad_ids)} ad IDs", flush=True)
            for ad_id in ad_ids:
                if ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    video_url, start_date = extract_ad_details(page_source, ad_id)
                    if video_url or start_date:
                        print(f"  [Detail] {ad_id}: video={bool(video_url)}, date={start_date}", flush=True)
                    ad = {
                        "library_id": ad_id, "keyword": "", "index": len(ads) + 1,
                        "platforms": ["Facebook"],
                        "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                        "ad_text": "", "start_date": start_date, "delivery_status": "",
                        "ad_disclosure_regions": [], "age_range": "", "gender": "",
                        "reach_count": "", "advertiser_name": "", "advertiser_description": "",
                        "payer_name": "", "creative_data": {"video_url": video_url},
                        "raw_detail_text": "", "title": "",
                    }
                    ads.append(ad)
    except Exception as e:
        print(f"[JSON] Parse error: {e}", flush=True)

    if not ads:
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/ads/library/?id=')]")
        print(f"[DOM] Found {len(links)} links", flush=True)
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
            video_url, start_date = extract_ad_details(driver.page_source, ad_id)
            ad = {
                "library_id": ad_id, "keyword": "", "index": len(ads) + 1,
                "platforms": ["Facebook"],
                "detail_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                "ad_text": text[:500] if text else "", "start_date": start_date,
                "delivery_status": "", "ad_disclosure_regions": [], "age_range": "",
                "gender": "", "reach_count": "", "advertiser_name": "",
                "advertiser_description": "", "payer_name": "",
                "creative_data": {"video_url": video_url},
                "raw_detail_text": "", "title": "",
            }
            ads.append(ad)

    print(f"[Parse] Total ads: {len(ads)}", flush=True)
    return ads


# ============================================================
# SCROLL (Selenium)
# ============================================================

def scroll_and_collect(driver, url, keyword, max_scrolls, wait_sec):
    driver.get(url)
    time.sleep(wait_sec)
    accept_cookies_if_present(driver)
    time.sleep(3)
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("[Page] Loaded", flush=True)
    except Exception:
        print("[Page] Timeout", flush=True)
    time.sleep(5)

    ads = []
    scroll_count = 0
    prev_count = 0
    no_new_count = 0

    while True:
        page_ads = parse_ads_from_page(driver)
        for ad in page_ads:
            ad['keyword'] = keyword
        new_count = 0
        for a in page_ads:
            if MAX_ADS and len(ads) >= MAX_ADS:
                print(f"[Done] Reached target {MAX_ADS} ads")
                break
            if a['library_id'] not in [e['library_id'] for e in ads]:
                ads.append(a)
                new_count += 1

        print(f"  Scroll {scroll_count}: {len(ads)} ads ({new_count} new)", flush=True)

        if len(ads) == prev_count:
            no_new_count += 1
            if no_new_count >= 3:
                print("[Done] No new ads for 3 scrolls", flush=True)
                break
        else:
            no_new_count = 0
        prev_count = len(ads)

        if MAX_ADS and len(ads) >= MAX_ADS:
            print(f"[Done] Reached target {MAX_ADS}", flush=True)
            break
        if scroll_count >= max_scrolls:
            print(f"[Done] Max scrolls {max_scrolls}", flush=True)
            break

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
# SCROLL (CDP fallback)
# ============================================================

def scroll_and_collect_via_cdp(url, keyword, max_scrolls, wait_sec):
    ads = []
    seen_ids = set()

    def get_page_ads(page):
        page_ads = []
        try:
            page_source = page.content()
        except Exception:
            return page_ads
        ad_ids = re.findall(r'ad_archive_id[":\s]+(\d{10,})', page_source)
        ad_ids = list(set(ad_ids))
        for ad_id in ad_ids:
            if ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)
            video_url, start_date = '', ''
            pos = page_source.find('ad_archive_id')
            if pos >= 0:
                snippet = page_source[max(0, pos - 200):pos + 500]
                vm = re.search(r'"video_hd_url":"([^"]+)"', snippet)
                if vm:
                    video_url = vm.group(1).replace('\\/', '/')
            ad = {
                "library_id": ad_id, "keyword": keyword, "index": len(ads) + 1,
                "platforms": ["Facebook"],
                "detail_url": "https://www.facebook.com/ads/library/?id=" + ad_id,
                "ad_text": "", "start_date": start_date, "delivery_status": "",
                "ad_disclosure_regions": [], "age_range": "", "gender": "",
                "reach_count": "", "advertiser_name": "", "advertiser_description": "",
                "payer_name": "", "creative_data": {"video_url": video_url},
                "raw_detail_text": "", "title": "",
            }
            page_ads.append(ad)
        return page_ads

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            contexts = browser.contexts
            if not contexts:
                print("[CDP-List] No contexts")
                browser.close()
                return []
            ctx = contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            print("[CDP-List] Loading: " + url)
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(wait_sec)

            scroll_count = 0
            prev_count = 0
            no_new_count = 0

            while True:
                page_ads = get_page_ads(page)
                for a in page_ads:
                    if MAX_ADS and len(ads) >= MAX_ADS:
                        print(f"[CDP-List] Reached target {MAX_ADS}")
                        break
                    a['keyword'] = keyword
                    if a['library_id'] not in [e['library_id'] for e in ads]:
                        ads.append(a)

                new_count = len(ads) - prev_count
                print("  Scroll " + str(scroll_count) + ": " + str(len(ads)) + " ads (" + str(new_count) + " new)")
                prev_count = len(ads)

                if no_new_count >= 3:
                    print("[CDP-List] No new ads")
                    break
                if MAX_ADS and len(ads) >= MAX_ADS:
                    print("[CDP-List] Reached target " + str(MAX_ADS))
                    break
                if scroll_count >= max_scrolls:
                    print("[CDP-List] Max scrolls")
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                scroll_count += 1
                time.sleep(wait_sec)

            page.close()
            browser.close()
            print("[CDP-List] Done: " + str(len(ads)) + " ads")
            return ads
    except Exception as e:
        print("[CDP-List] Failed: " + str(e))
        return []


# ============================================================
# DETAIL SCRAPING (Modal)
# ============================================================

MODAL_TAB_NAMES = [
    "广告信息公示（按地区）",
    "关于广告赞助方",
    "关于广告主",
    "广告主和付费方",
]


def _click_element(page, selector, timeout=10):
    """Click element, scrolling into view first if needed."""
    try:
        page.evaluate(f"""
            el = document.querySelector('{selector}');
            if (el) {{ el.scrollIntoView({{block:'center'}}); }}
        """)
        page.click(selector, timeout=timeout * 1000)
        return True
    except Exception:
        return False


def _wait_modal(page, timeout=15):
    """Wait for the modal dialog to appear."""
    for _ in range(timeout):
        if page.query_selector('[role="dialog"]'):
            return True
        time.sleep(1)
    return False


def _get_text_safe(page_or_elem):
    """Get text content safely."""
    try:
        return page_or_elem.inner_text().strip()
    except Exception:
        return ''


def scrape_ad_detail(driver, library_id, wait_sec=8):
    """Wrapper: scrape detail using Selenium modal interaction."""
    return scrape_ad_detail_via_modal(driver, library_id, wait_sec=wait_sec)


def scrape_ad_detail_via_modal(driver, library_id, wait_sec=8):
    """
    Use Selenium to open the detail page URL, click "View ad details",
    wait for modal, expand the 4 disclosure section headers, then extract fields.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    result = {
        "library_id": library_id,
        "ad_disclosure_regions": [],
        "age_range": "",
        "gender": "",
        "reach_count": "",
        "about_sponsor": "",
        "advertiser_name": "",
        "advertiser_description": "",
        "payer_name": "",
        "ad_text": "",
        "region_targeting": {},
    }

    try:
        detail_url = "https://www.facebook.com/ads/library/?id=" + library_id
        driver.get(detail_url)
        time.sleep(3)

        # Wait for page to load
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        time.sleep(wait_sec)

        # --- Click "View ad details" button ---
        btn_clicked = False
        for btn_text in ["\u67e5\u770b\u5e7f\u544a\u8be6\u60c5", "View Ad Details", "view ad details"]:
            try:
                for btn in driver.find_elements(By.XPATH, "//*[contains(text(),'" + btn_text + "')]"):
                    if btn.is_displayed():
                        btn.click()
                        btn_clicked = True
                        print(f"[Modal] Clicked: {btn_text}")
                        break
            except Exception:
                pass
            if btn_clicked:
                break

        if not btn_clicked:
            try:
                for btn in driver.find_elements(By.XPATH, "//*[@aria-label='View ad details']"):
                    if btn.is_displayed():
                        btn.click()
                        btn_clicked = True
                        print("[Modal] Clicked via aria-label")
                        break
            except Exception:
                pass

        if not btn_clicked:
            print(f"[Modal] Button not found: {library_id}")
            return result

        # --- Wait for modal dialog ---
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
            )
        except TimeoutException:
            print(f"[Modal] No modal appeared: {library_id}")
            return result

        print(f"[Modal] Opened: {library_id}")
        time.sleep(3)

        # --- Find the ad detail modal (last dialog, not the sidebar) ---
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, '[role="dialog"]')) >= 3
            )
        except Exception:
            pass
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            dialog = dialogs[-1]  # last dialog = ad detail modal (largest, visible)
        except Exception:
            print(f"[Modal] No modal dialog found: {library_id}")
            return result

        # Scroll modal to bottom so section headers are in view
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
        time.sleep(1)

        # --- Find and click each expandable section header inside the modal ---
        section_labels = [
            "\u5e7f\u544a\u4fe1\u606f\u516c\u793a",   # 广告信息公示
            "\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9",  # 关于广告赞助方
            "\u5173\u4e8e\u5e7f\u544a\u4e3b",            # 关于广告主
            "\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9", # 广告主和付费方
            "Ad Disclosure",
            "About the Sponsor",
            "About the Advertiser",
            "Advertiser & Payer",
        ]

        expanded_count = 0
        for _ in range(3):
            # Re-find the last dialog each iteration (DOM may change)
            try:
                dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
                dialog = dialogs[-1]
            except Exception:
                pass
            for label in section_labels:
                try:
                    matching = dialog.find_elements(By.XPATH, ".//*[contains(text(),'" + label + "')]")
                    for el in matching:
                        if el.is_displayed():
                            try:
                                el.click()
                            except Exception:
                                # Element may be covered by other content — scroll it into view and retry
                                driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center'})", el
                                )
                                time.sleep(0.3)
                                try:
                                    el.click()
                                except Exception:
                                    pass
                            expanded_count += 1
                            time.sleep(0.8)
                            print(f"[Modal] Expanded section: {label}")
                            break
                except Exception:
                    pass
            time.sleep(1.5)

        print(f"[Modal] Expanded {expanded_count} sections for {library_id}")

        # Re-scroll after clicking so all expanded content is in the viewport
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            dialog = dialogs[-1]
        except Exception:
            pass
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
        time.sleep(2)

        # --- Per-region targeting: click each region tab in "广告信息公示" section ---
        region_targeting = {}
        region_labels = [
            "\u6b27\u7f9f", "\u6b27\u6d32", "\u82f1\u56fd", "\u5fb7\u56fd",
            "\u6cd5\u56fd", "\u610f\u5927\u5229", "\u897f\u73b0\u4e16", "\u8377\u5170",
            "\u6ce2\u5170", "\u745e\u5179", "\u4e39\u9ea6", "\u5965\u5730\u5229",
            "\u6bd4\u5229\u65f6",
            "EU", "United Kingdom", "Germany", "France", "Italy", "Spain",
            "Netherlands", "Poland", "Sweden", "Austria", "Belgium",
            "United States", "Brazil", "India", "Japan", "Korea", "Vietnam",
            "\u7f8e\u56fd", "\u82f1\u56fd", "\u65b0\u52a0\u5761",
        ]
        try:
            # Find the disclosure section by header text
            disc_header = None
            for lbl in ["\u5e7f\u544a\u4fe1\u606f\u516c\u793a", "Ad Disclosure"]:
                try:
                    headers = dialog.find_elements(By.XPATH, ".//*[contains(text(),'" + lbl + "')]")
                    for h in headers:
                        if h.is_displayed():
                            disc_header = h
                            break
                except Exception:
                    pass

            if disc_header is not None:
                # Scroll to the disclosure section
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", disc_header)
                time.sleep(1)

                # REPLACEMENT: Pure JS region extraction via tab clicking
                # Facebook uses [role="tab"] elements for switching between disclosure regions (欧盟/英国).
                # We click each tab, read the targeting data, then switch back.
                region_targeting = {}
                try:
                    extract_js = r"""
                        var RA = ["\u6b27\u7f9f","\u6b27\u6d32","\u82f1\u56fd","\u5fb7\u56fd","\u6cd5\u56fd","\u610f\u5927\u5229","\u897f\u73b0\u4e16","\u8377\u5170","\u6ce2\u5170","\u745e\u5179","\u4e39\u9ea6","\u5965\u5730\u5229","\u6bd4\u5229\u65f6","EU","United Kingdom","Germany","France","Italy","Spain","Netherlands","Poland","Sweden","Austria","Belgium","United States","Brazil","India","Japan","Korea","Vietnam","\u7f8e\u56fd","\u65b0\u52a0\u5761"];
                        var dialogs = document.querySelectorAll('[role="dialog"]');
                        if (!dialogs.length) return JSON.stringify({error: 'no dialogs'});
                        var dlg = dialogs[dialogs.length - 1];
                        var tabs = dlg.querySelectorAll('[role="tab"]');
                        if (!tabs.length) return JSON.stringify({error: 'no tabs found'});
                        var results = [];
                        // Click each tab that matches a known region name
                        for (var i = 0; i < tabs.length; i++) {
                            var tab = tabs[i];
                            var txt = (tab.innerText || '').trim();
                            var matchedRegion = null;
                            for (var rn of RA) {
                                if (txt === rn) { matchedRegion = rn; break; }
                            }
                            if (!matchedRegion) continue;
                            tab.scrollIntoView({block: 'center'});
                            tab.click();
                            var tStart = Date.now();
                            while (Date.now() - tStart < 2000) {}
                            var fullText = document.body.innerText;
                            var age = '';
                            var ageMatch = fullText.match(/(\d{1,2})\s*[-~]\s*(\d+\+?)\s*[\u5c81|years?]/i);
                            if (ageMatch) {
                                var lo = ageMatch[1], hi = ageMatch[2];
                                age = hi === '+' ? lo + '\u5c81+' : lo + '-' + hi + '\u5c81';
                            }
                            var gender = '';
                            if (/\u6027\u522b\s*[:\u3001]?\s*\u4e0d\u9650|Gender\s*:\s*All/i.test(fullText)) gender = '\u4e0d\u9650';
                            else if (/\u6027\u522b\s*[:\u3001]?\s*\u7537\u6027|Gender\s*:\s*Male/i.test(fullText)) gender = '\u7537\u6027';
                            else if (/\u6027\u522b\s*[:\u3001]?\s*\u5973\u6027|Gender\s*:\s*Female/i.test(fullText)) gender = '\u5973\u6027';
                            var reach = '';
                            var reachMatch = fullText.match(/\u8986\u76d6[\s\S]{0,300}?([\d,]+)\s*(?:\u4eba|people|users|impressions)/i);
                            if (!reachMatch) reachMatch = fullText.match(/(?:Reach|Impressions)[^:]*:\s*([\d,]+)/i);
                            if (!reachMatch) reachMatch = fullText.match(/\u8986\u76d6\u4eba\u6570\s*[:\u3001]?\s*([\d,]+)/i);
                            if (reachMatch) {
                                var raw = reachMatch[1].replace(/,/g, '').trim();
                                if (/^\d+$/.test(raw) && raw.length >= 3) reach = raw;
                            }
                            results.push([matchedRegion, age, gender, reach]);
                        }
                        // Switch back to first tab so the dialog shows the default region
                        if (tabs.length > 0) {
                            tabs[0].scrollIntoView({block: 'center'});
                            tabs[0].click();
                        }
                        return JSON.stringify(results);
                    """
                    for attempt in range(2):
                        try:
                            js_result = driver.execute_script(extract_js)
                            if js_result:
                                import json as _json
                                all_regions = _json.loads(js_result)
                                if isinstance(all_regions, dict) and 'error' in all_regions:
                                    print(f"[Modal] JS error: {all_regions['error']}")
                                    break
                                for r_data in all_regions:
                                    if len(r_data) == 4:
                                        rn, age, gender, reach = r_data
                                        if rn and len(rn) <= 40 and (age or gender or reach):
                                            region_targeting[rn] = {
                                                'age_range': age,
                                                'gender': gender,
                                                'reach_count': reach,
                                            }
                                            print(f"[Modal] Region '{rn}': age={age}, gender={gender}, reach={reach}")
                                if region_targeting:
                                    break
                        except Exception as e:
                            print(f"[Modal] JS region extraction attempt {attempt+1} error: {e}")
                            time.sleep(2)
                except Exception as e:
                    print(f"[Modal] JS region extraction error: {e}")

        except Exception as e:
            print(f"[Modal] Region extraction error: {e}")

        # Store per-region targeting in result
        if region_targeting:
            result["region_targeting"] = region_targeting

        # --- Get full text from ad detail modal (last dialog) ---
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            dialog = dialogs[-1]
            # Use innerText via JS to capture text from ALL visible expanded sections
            full_text = driver.execute_script("return arguments[0].innerText", dialog)
        except Exception:
            print(f"[Modal] No dialog text: {library_id}")
            return result

        if not full_text or len(full_text) < 20:
            print(f"[Modal] Empty dialog: {library_id}")
            return result

        print(f"[Modal] Text length: {len(full_text)} chars")

        # (1) Disclosure regions — use tab region names (e.g. 欧盟, 英国) not individual countries
        # If JS tab extraction succeeded, use its keys; otherwise fall back to text regex
        if region_targeting:
            result["ad_disclosure_regions"] = list(region_targeting.keys())
            print(f"[Modal] Regions from tabs: {result['ad_disclosure_regions']}")
        else:
            # Fallback: regex on full_text (may pick up individual countries, less accurate)
            region_ptrn = (
                "(?:"
                "\u6b27\u7f9f|\u6b27\u6d32|\u5fb7\u56fd|\u6cd5\u56fd|"
                "\u610f\u5927\u5229|\u897f\u73b0\u4e16|\u8377\u5170|"
                "\u6ce2\u5170|\u745e\u5179|\u4e39\u9ea6|\u5965\u5730\u5229|"
                "\u6bd4\u5229\u65f6|"
                "EU|United Kingdom|Germany|France|Italy|Spain|Netherlands|Poland|"
                "Sweden|Denmark|Austria|Belgium|United States|Brazil|India|Japan|"
                "Korea|Vietnam|Thailand|"
                "\u6b27\u7f9f\u5e7f\u544a\u6295\u653e|US\u5e7f\u544a\u6295\u653e|EU ad)"
            )
            regions_found = re.findall(region_ptrn, full_text)
            seen = set()
            regions = []
            for r in regions_found:
                r = r.strip()
                if len(r) <= 2 or r in seen:
                    continue
                seen.add(r)
                regions.append(r)
            if regions:
                result["ad_disclosure_regions"] = regions

        # (2) Age range — if region_targeting exists, use first region's age; otherwise regex on full_text
        if region_targeting:
            first_region = list(region_targeting.keys())[0]
            result["age_range"] = region_targeting[first_region].get('age_range', '')
        else:
            age_m = re.search(r"(\d{1,2})\s*[-~]\s*(\d+\+?)\s*\u5c81", full_text)
            if not age_m:
                age_m = re.search(r"\u5e74\u9f84\s*[-~]\s*(\d+\+?)", full_text)
            if not age_m:
                age_m = re.search(r"Age\s*:\s*(\d{1,2})\s*[-~]\s*(\d+\+?)", full_text, re.I)
            if age_m:
                lo, hi = age_m.group(1), age_m.group(2)
                result["age_range"] = f"{lo}-{hi}\u5c81" if hi != "+" else f"{lo}\u5c81+"

        # (3) Gender — if region_targeting exists, use first region's gender; otherwise regex
        if region_targeting:
            first_region = list(region_targeting.keys())[0]
            result["gender"] = region_targeting[first_region].get('gender', '')
        else:
            if re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u4e0d\u9650|Gender\s*:\s*All", full_text, re.I):
                result["gender"] = "\u4e0d\u9650"
            elif re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u7537\u6027|Gender\s*:\s*Male", full_text, re.I):
                result["gender"] = "\u7537\u6027"
            elif re.search(r"\u6027\u522b\s*[:\u3001]?\s*\u5973\u6027|Gender\s*:\s*Female", full_text, re.I):
                result["gender"] = "\u5973\u6027"

        # (4) Reach count — if region_targeting exists, use first region's reach; otherwise regex
        if region_targeting:
            first_region = list(region_targeting.keys())[0]
            result["reach_count"] = region_targeting[first_region].get('reach_count', '')
        else:
            reach_m = re.search(r"\u8986\u76d6[^\n]{0,50}?([\d,]+)\s*(?:\u4eba|people|users|impressions)", full_text)
            if not reach_m:
                reach_m = re.search(r"(?:Reach|Impressions)[^:]*:\s*([\d,]+)", full_text, re.I)
            if not reach_m:
                reach_m = re.search(r"\u8986\u76d6\u4eba\u6570\s*[:\u3001]?\s*([\d,]+)", full_text)
            if reach_m:
                raw = reach_m.group(1).replace(",", "").replace("\u3000", "").strip()
                if raw.isdigit() and len(raw) >= 3:
                    result["reach_count"] = raw

        # (5) Ad text - longest block excluding labels
        skip_labels = [
            "\u5e7f\u544a\u4fe1\u606f\u516c\u793a",
            "\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9",
            "\u5173\u4e8e\u5e7f\u544a\u4e3b",
            "\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9",
            "View ad details", "Facebook", "Meta", "Close",
            "advertiser", "sponsor", "payer", "disclosure",
            "Age", "Gender", "Reach", "\u6253\u5f00\u4e0b\u62c9\u83dc\u5355",
            "Ad Disclosure", "About the Sponsor", "About the Advertiser", "Advertiser & Payer",
        ]
        lines_t = [l.strip() for l in full_text.split("\n") if l.strip()]
        for line in lines_t:
            if len(line) > 50 and not any(s in line for s in skip_labels):
                if not result.get("ad_text") or len(line) > len(result.get("ad_text", "")):
                    result["ad_text"] = line[:2000]

                # (6) Advertiser name - match label on its own line, then first uppercase line
        adv_m = re.search(r'\n\u5e7f\u544a\u4e3b\n([A-Z][^\n]+)', full_text)
        if adv_m:
            name = adv_m.group(1).strip()
            if len(name) > 3:
                result["advertiser_name"] = name

        # Fallback: company name pattern
        if not result.get("advertiser_name"):
            co_kw = (
                r'[A-Z][a-zA-Z\s]{2,40}'
                r'(?:Ltd|L\.|Inc|Co\.|Company|Limited|LLC|DMCC|'
                r"\u79d1\u6280|\u6709\u9650|\u96c6\u56e2|\u516c\u53f8|Co\.,|GmbH|S\.A\.|SARL|AG|SA|PL|Tech|Group)"
            )
            co_matches = re.findall(co_kw, full_text)
            for name in co_matches:
                name = name.strip()
                if 4 < len(name) < 100 and not any(c.isdigit() for c in name[:3]):
                    if not result.get("advertiser_name"):
                        result["advertiser_name"] = name
                        break

        # If about_sponsor was captured but advertiser_name is still the short app name,
        # prefer about_sponsor (it contains the full legal company name)
        if result.get("about_sponsor") and result.get("advertiser_name"):
            app_names = ["Block Blast", "Block Blast Adventure", "Block Blast 3D", "Block Blast Puzzle"]
            if result["advertiser_name"] in app_names:
                result["advertiser_name"] = result["about_sponsor"]

        # (7) Payer name - match label on its own line, then first uppercase line
        payer_m = re.search(r'\n\u4ed8\u8d39\u65b9\n([A-Z][^\n]+)', full_text)
        if payer_m:
            payer = payer_m.group(1).strip()
            if len(payer) > 3:
                result["payer_name"] = payer

        # Fallback: known marketing company names
        if not result.get("payer_name"):
            for name in [n.strip() for n in co_matches]:
                if any(kw in name for kw in ["MeetSocial", "Google", "Meta", "TikTok", "ByteDance", "Tencent"]):
                    result["payer_name"] = name
                    break

        print(f"[Modal] {library_id} | regions={result['ad_disclosure_regions']} | "
              f"age={result['age_range']} | advertiser={result['advertiser_name'][:30]}")
        return result

    except Exception as e:
        import traceback
        print(f"[Modal] Error {library_id}: {e}")
        traceback.print_exc()
        return result



def load_json_file(path):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"ads": []}


def clean_ad(ad):
    """Remove empty fields from ad dict for cleaner JSON output."""
    def is_empty(v):
        if v is None:
            return True
        if isinstance(v, str) and v.strip() == '':
            return True
        if isinstance(v, list) and len(v) == 0:
            return True
        return False
    return {k: v for k, v in ad.items() if not is_empty(v)}


def process_and_deduplicate(daily_file, agg_file, new_ads, keyword):
    daily_data = load_json_file(daily_file)
    agg_data = load_json_file(agg_file)

    daily_ads = {a['library_id']: a for a in daily_data.get('ads', [])}
    agg_ads = {a['library_id']: a for a in agg_data.get('ads', [])}

    for ad in new_ads:
        lid = ad['library_id']
        ad['keyword'] = keyword

        # Merge into daily: keep the more complete version
        if lid in daily_ads:
            daily_ads[lid] = _merge_ad(daily_ads[lid], ad)
        else:
            daily_ads[lid] = ad

        # Merge into aggregate: same logic
        if lid in agg_ads:
            agg_ads[lid] = _merge_ad(agg_ads[lid], ad)
        else:
            agg_ads[lid] = ad

    daily_data['ads'] = list(daily_ads.values())
    agg_data['ads'] = list(agg_ads.values())
    daily_data['last_updated'] = datetime.now().isoformat()
    agg_data['last_updated'] = datetime.now().isoformat()

    for f, data in [(daily_file, daily_data), (agg_file, agg_data)]:
        f.parent.mkdir(parents=True, exist_ok=True)
        if 'ads' in data:
            data['ads'] = [clean_ad(ad) for ad in data['ads']]
        with open(f, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    print(f"[Dedupe] Daily: {len(daily_data['ads'])} ads, Aggregate: {len(agg_data['ads'])} ads")
    return list(daily_ads.values())


def _merge_ad(existing, new_ad):
    """
    Merge two ad dicts. Detail-page data (new_ad) is authoritative - 
    it always overwrites list-page data, except for creative_data which merges deep.
    """
    # Detail data is authoritative for these fields
    AUTHORITATIVE_FIELDS = {
        'age_range', 'gender', 'reach_count', 'advertiser_name',
        'payer_name', 'about_sponsor', 'ad_disclosure_regions',
        'body_text', 'title', 'start_date', 'region_targeting',
    }
    merged = dict(existing)
    for k, v in new_ad.items():
        if k == 'region_targeting' and isinstance(v, dict) and v:
            # Deep merge: combine all regions from both
            existing_rt = merged.get('region_targeting', {})
            merged['region_targeting'] = {**existing_rt, **v}
        elif k in AUTHORITATIVE_FIELDS and v and v != []:
            # Detail page wins for these fields (including region_targeting if dict)
            if k == 'region_targeting' and isinstance(v, dict):
                existing_rt = merged.get('region_targeting', {})
                merged['region_targeting'] = {**existing_rt, **v}
            else:
                merged[k] = v
        elif k == 'creative_data' and isinstance(v, dict):
            merged[k] = {**merged.get(k, {}), **v}
        elif k not in merged or merged[k] == '' or merged[k] == []:
            merged[k] = v
    return merged


# ============================================================
# VIDEO DOWNLOAD
# ============================================================

def download_videos(ads, video_dir, keyword):
    video_dir.mkdir(parents=True, exist_ok=True)
    existing = {f.stem for f in video_dir.glob("*.mp4")}
    to_download = [a for a in ads if a['library_id'] not in existing
                   and a.get('creative_data', {}).get('video_url', '').startswith('http')]
    if not to_download:
        print("[Video] No new videos to download")
        return
    print(f"[Video] Downloading {len(to_download)} videos")

    def download_one(ad):
        video_url = ad.get('creative_data', {}).get('video_url', '')
        if not video_url:
            return False
        fname = video_dir / (ad['library_id'] + ".mp4")
        try:
            req = urllib.request.Request(video_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(fname, 'wb') as f:
                    shutil.copyfileobj(resp, f)
            print(f"[Video] Downloaded: {fname.name} ({fname.stat().st_size // 1024 // 1024} MB)")
            return True
        except Exception as e:
            print(f"[Video] Failed {ad['library_id']}: {e}")
            if fname.exists():
                fname.unlink()
            return False

    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_one, ad): ad for ad in to_download}
        for future in as_completed(futures):
            future.result()


# ============================================================
# MAIN
# ============================================================

def scrape_keyword(keyword):
    start_date, end_date = get_date_range()
    folder, daily_file, agg_file, video_dir = get_output_paths(keyword, end_date)

    print(f"\n{'='*60}", flush=True)
    print(f"Keyword: {keyword}", flush=True)
    print(f"Date range: {start_date} ~ {end_date}", flush=True)
    print(f"Daily file: {daily_file.name}", flush=True)
    print(f"Aggregate file: {agg_file.name}", flush=True)
    print(f"{'='*60}", flush=True)

    scrape_url = build_url(keyword, start_date, end_date)
    print(f"[URL] {scrape_url}", flush=True)

    driver = None
    # Step 1: retry up to 3 times on connection errors
    for attempt in range(3):
        try:
            print("\n>>> Step 1: Scrape list page (attempt " + str(attempt + 1) + ") >>>", flush=True)
            driver = make_driver(headless=HEADLESS)
            ads = scroll_and_collect(driver, scrape_url, keyword, MAX_SCROLLS, WAIT_SEC)
            print(f"\n[Step 1 done] {len(ads)} ads scraped", flush=True)
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Error] Selenium attempt {attempt+1} failed: {e}", flush=True)
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            driver = None
            if attempt < 2:
                print("[Retry] Waiting 5 seconds before retry...", flush=True)
                time.sleep(5)
            else:
                print("\n[Fallback] Switching to Playwright...", flush=True)
                ads = scroll_and_collect_via_cdp(scrape_url, keyword, MAX_SCROLLS, WAIT_SEC)
                if not ads:
                    print("[Error] All methods failed, skipping", flush=True)
                    return

    if not ads:
        print("[Warning] No ads found, skipping", flush=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return

    # Restart browser before Step 2 to avoid accumulated memory/connection issues
    try:
        driver.quit()
    except Exception:
        pass
    time.sleep(2)
    try:
        driver = make_driver(headless=HEADLESS)
        print("[Browser] Restarted for Step 2", flush=True)
    except Exception as e:
        print(f"[Browser] Restart failed for Step 2: {e}", flush=True)

    # Step 2: detail pages (with browser restart on crash + incremental save)
    if SCRAPE_DETAIL:
        print(f"\n>>> Step 2: Scrape detail pages ({MAX_DETAIL_SCRAPES or 'all'}) >>>", flush=True)
        detail_ads = ads[:MAX_DETAIL_SCRAPES] if MAX_DETAIL_SCRAPES > 0 else ads
        detail_count = 0
        browser_restart_interval = 3  # restart browser every N ads

        for i, ad in enumerate(detail_ads):
            # Restart browser periodically to avoid Chrome crashes
            if detail_count > 0 and detail_count % browser_restart_interval == 0:
                print(f"[Browser] Restarting browser at ad {detail_count}...", flush=True)
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                try:
                    driver = make_driver(headless=HEADLESS)
                except Exception as e:
                    print(f"[Browser] Restart failed: {e}, continuing with current driver...", flush=True)

            try:
                print(f"[Detail] {i+1}/{len(detail_ads)}: {ad['library_id']}", flush=True)
                detail_data = scrape_ad_detail(driver, ad['library_id'], wait_sec=DETAIL_WAIT)
                if detail_data:
                    for k, v in detail_data.items():
                        if v == '' or v == [] or v is None:
                            continue
                        if isinstance(v, dict) and k in ad and isinstance(ad[k], dict):
                            ad[k] = {**ad[k], **v}
                        else:
                            ad[k] = v
                    detail_count += 1
                    # Incremental save after each successful detail scrape
                    process_and_deduplicate(daily_file, agg_file, [ad], keyword)
                time.sleep(2)
            except Exception as e:
                print(f"[Detail] Failed {ad['library_id']}: {e}", flush=True)
                # Save what we have so far
                process_and_deduplicate(daily_file, agg_file, ads[:i], keyword)
                # Try to restart browser and continue
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                try:
                    driver = make_driver(headless=HEADLESS)
                except Exception as restart_err:
                    print(f"[Browser] Restart after error failed: {restart_err}", flush=True)
                    break
                continue
        print(f"[Detail] Done: {detail_count}/{len(detail_ads)}", flush=True)
    else:
        print("\n>>> Step 2: Skipped (SCRAPE_DETAIL=False) >>>", flush=True)

    # Step 3: dedupe
    print("\n>>> Step 3: Dedupe and save >>>", flush=True)
    new_ads = process_and_deduplicate(daily_file, agg_file, ads, keyword)

    # Step 4: download videos
    print("\n>>> Step 4: Download videos >>>", flush=True)
    download_videos(ads, video_dir, keyword)

    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n[Done] Keyword {keyword}: {len(new_ads)} new ads", flush=True)
    print(f"  Aggregate total: {len(load_json_file(agg_file))} ads", flush=True)


def main():
    start_date, end_date = get_date_range()

    print("=" * 60, flush=True)
    print("Facebook Ad Library Scraper", flush=True)
    print(f"Date: {end_date}", flush=True)
    if AUTO_DATE:
        print(f"Range: {start_date} ~ {end_date} (auto 7 days)", flush=True)
    else:
        print(f"Range: {start_date} ~ {end_date} (manual)", flush=True)
    print(f"Keywords: {len(KEYWORDS)}", flush=True)
    print("=" * 60, flush=True)

    for i, keyword in enumerate(KEYWORDS, 1):
        print(f"\n\n>>> Keyword {i}/{len(KEYWORDS)}: {keyword} >>>", flush=True)
        scrape_keyword(keyword)

    print(f"\n\n{'='*60}", flush=True)
    print("All keywords done!", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
