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
START_DATE = "2026-04-17"
END_DATE = "2026-04-23"

MODE = "fixed"
MAX_ADS = 10

HEADLESS = False
WAIT_SEC = 5
MAX_SCROLLS = 50

SCRAPE_DETAIL = True
MAX_DETAIL_SCRAPES = 0
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
# DETAIL SCRAPING
# ============================================================

def scrape_ad_detail(driver, library_id, wait_sec=8):
    # Try CDP first
    html, video_url = fetch_detail_page_via_cdp(library_id, CDP_URL, wait_sec=wait_sec)
    if html:
        fields = extract_all_fields_from_html(html, library_id)
        if fields.get('video_url'):
            print("[CDP] " + library_id + " full fields | video=" + fields['video_url'][:50] + "...")
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
            print("[CDP] " + library_id + " page loaded, no video")
            return {
                "library_id": library_id,
                "detail_url": "https://www.facebook.com/ads/library/?id=" + library_id,
                "video_url": "", "video_sd_url": "", "video_preview_image_url": "",
                "start_date": "", "end_date": "", "delivery_status": "",
                "ad_disclosure_regions": [], "age_range": "", "gender": "",
                "reach_count": "", "advertiser_name": "", "advertiser_description": "",
                "payer_name": "", "creative_data": {}, "raw_detail_text": "",
                "ad_text": "", "title": "",
                "block_ad_disclosure": "", "block_about_sponsor": "",
                "block_about_advertiser": "", "block_advertiser_payer": "",
            }
    else:
        print("[CDP] " + library_id + " CDP failed, falling back to Selenium")
    return None


# ============================================================
# DATA PROCESSING
# ============================================================

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

    existing_in_daily = {a['library_id'] for a in daily_data.get('ads', [])}
    existing_in_agg = {a['library_id'] for a in agg_data.get('ads', [])}

    new_daily = [a for a in new_ads if a['library_id'] not in existing_in_daily]
    new_agg = [a for a in new_ads if a['library_id'] not in existing_in_agg]

    for ad in new_daily:
        ad['keyword'] = keyword
    for ad in new_agg:
        ad['keyword'] = keyword

    daily_data.setdefault('ads', []).extend(new_daily)
    agg_data.setdefault('ads', []).extend(new_agg)

    daily_data['last_updated'] = datetime.now().isoformat()
    agg_data['last_updated'] = datetime.now().isoformat()

    for f, data in [(daily_file, daily_data), (agg_file, agg_data)]:
        f.parent.mkdir(parents=True, exist_ok=True)
        # Clean empty fields from all ads before saving
        if 'ads' in data:
            data['ads'] = [clean_ad(ad) for ad in data['ads']]
        with open(f, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    print(f"[Dedupe] Added {len(new_daily)} to daily, {len(new_agg)} to aggregate")
    return new_agg


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
    try:
        print("\n>>> Step 1: Scrape list page >>>", flush=True)
        driver = make_driver(headless=HEADLESS)
        ads = scroll_and_collect(driver, scrape_url, keyword, MAX_SCROLLS, WAIT_SEC)
        print(f"\n[Step 1 done] {len(ads)} ads scraped", flush=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Error] Selenium failed: {e}", flush=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print("\n[Fallback] Switching to Playwright CDP...", flush=True)
        ads = scroll_and_collect_via_cdp(scrape_url, keyword, MAX_SCROLLS, WAIT_SEC)
        if not ads:
            print("[Error] CDP also failed, skipping", flush=True)
            return

    if not ads:
        print("[Warning] No ads found, skipping", flush=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return

    # Step 2: detail pages
    if SCRAPE_DETAIL:
        print(f"\n>>> Step 2: Scrape detail pages ({MAX_DETAIL_SCRAPES or 'all'}) >>>", flush=True)
        detail_ads = ads[:MAX_DETAIL_SCRAPES] if MAX_DETAIL_SCRAPES > 0 else ads
        detail_count = 0
        for i, ad in enumerate(detail_ads):
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
                time.sleep(2)
            except Exception as e:
                print(f"[Detail] Failed {ad['library_id']}: {e}", flush=True)
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
