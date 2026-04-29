"""
Facebook Ad Library Scraper - Part 2: Detail Page
==================================================
从 scrape_list.py 生成的 JSON 读取 library_id，逐个抓取详情页。

流程：
  1. 打开 https://www.facebook.com/ads/library/?id=<library_id>
  2. 点击"查看广告详情"按钮，弹出详情弹窗
  3. 弹窗右侧有 4 个标签页：广告信息公示（按地区）、关于广告赞助方、关于广告主、广告主和付费方
  4. 依次点击每个标签展开，提取所有文字内容
  5. 保存到 detail_<keyword>_<date>.json

Usage:
  python scrape_detail.py                                    # 处理今天的列表文件
  python scrape_detail.py --date 2026-04-28                # 指定日期
  python scrape_detail.py -i output/Block_Blast/ads_Block_Blast_2026-04-28.json
  python scrape_detail.py --max 5                          # 只抓前5个（测试用）
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
from pathlib import Path
from datetime import datetime
# ====== 代理配置（根据你的梯子端口修改）====================
PROXY_SERVER = "http://127.0.0.1:7890"   # ← 改成你的代理地址，7890 是 Clash 默认端口

# ====== CONFIG ======
HEADLESS = False
# CDP 端口列表，按优先级尝试自动检测
# 如果 18800（OpenClaw 浏览器）连不上，会自动试 9222（用户 Chrome）
CDP_URLS = [
    "http://127.0.0.1:18800",   # OpenClaw 浏览器
    "http://127.0.0.1:9222",    # 用户自己开的 Chrome
]
# ====================

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# 自动检测 CDP 端口（只检测一次，缓存结果）
# ============================================================
_CACHED_CDP_URL = None

def detect_cdp_url():
    """自动检测可用 Chrome CDP 端口，返回第一个可用的 URL。只检测一次，后续复用。"""
    global _CACHED_CDP_URL
    if _CACHED_CDP_URL is not None:
        return _CACHED_CDP_URL
    import urllib.request
    for url in CDP_URLS:
        try:
            resp = urllib.request.urlopen(url + "/json/version", timeout=3)
            if resp.status == 200:
                print(f"[CDP] 检测到可用端口: {url}")
                _CACHED_CDP_URL = url
                return url
        except Exception:
            pass
    print("[CDP] 无法连接到任何 Chrome CDP 端口")
    print("[CDP] 请确保 OpenClaw 浏览器已启动（openclaw browser start），或手动打开 Chrome --remote-debugging-port=9222")
    return None


# ============================================================
# CDP 主抓取函数（使用你已登录的 Chrome）
# ============================================================

def scrape_detail_cdp(library_id, wait_sec=8, cdp_url=None):
    """
    通过 Chrome DevTools Protocol (CDP) 抓取广告详情。
    使用 Playwright 连接 Chrome，点击"查看广告详情"，
    展开4个标签页，获取完整弹窗文本。
    """
    import urllib.request

    # 如果没有传入 cdp_url，自动检测
    if cdp_url is None:
        cdp_url = detect_cdp_url()
    if cdp_url is None:
        return None

    # 预导航到目标页面
    try:
        payload = json.dumps({
            "method": "Page.navigate",
            "params": {"url": f"https://www.facebook.com/ads/library/?id={library_id}"}
        }).encode()
        urllib.request.urlopen(
            urllib.request.Request(cdp_url + "/json", data=payload,
                                   headers={"Content-Type": "application/json"}),
            timeout=5
        )
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Error] playwright not installed. Run: pip install playwright")
        return None

    result_data = None
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.new_page(proxy={"server": PROXY_SERVER})
        page.goto(f"https://www.facebook.com/ads/library/?id={library_id}", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(wait_sec * 1000)

        # ---- 步骤1: 点击"查看广告详情" ----
        clicked = False
        for kw in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View ad details', 'View Ad Details']:
            try:
                page.get_by_text(kw, exact=False).first.click(timeout=5000, force=True)
                print(f"  [CDP] 点击按钮: {kw}")
                clicked = True
                break
            except Exception:
                pass

        if not clicked:
            print(f"  [CDP] 未找到'查看广告详情'按钮")
            return None

        # ---- 步骤2: 等待弹窗出现 ----
        try:
            page.wait_for_selector('[role="dialog"]', state='visible', timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # ---- 步骤3: 依次点击4个标签页，展开内容 ----
        tab_labels = [
            '\u5e7f\u544a\u4fe1\u606f\u516c\u793a\uff08\u6309\u5730\u533a\uff09',  # 广告信息公示（按地区）
            '\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9',                           # 关于广告赞助方
            '\u5173\u4e8e\u5e7f\u544a\u4e3b',                                        # 关于广告主
            '\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9',                             # 广告主和付费方
        ]

        for tab in tab_labels:
            try:
                els = page.get_by_text(tab, exact=False).all()
                for el in els:
                    if el.is_visible():
                        el.click(force=True)
                        page.wait_for_timeout(1000)
                        break
            except Exception:
                pass

        page.wait_for_timeout(2000)

        # ---- 步骤4: 获取弹窗完整文本 ----
        full_text = ""
        try:
            dialogs = page.locator('[role="dialog"]').all()
            if dialogs:
                full_text = dialogs[-1].inner_text()
                print(f"  [CDP] 弹窗文本长度: {len(full_text)}")
        except Exception as e:
            print(f"  [CDP] 获取弹窗文本失败: {e}")

        if not full_text:
            return {"library_id": library_id, "error": "no dialog text"}

        # ---- 步骤5: 解析4个区块的数据 ----
        result_data = parse_detail_text(full_text, library_id)

    # with 块结束
    if result_data is None:
        return {"library_id": library_id, "error": "unknown error"}
    return result_data


# ============================================================
# Selenium 备选方案
# ============================================================

def make_driver(headless=False, max_retries=3):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    for attempt in range(max_retries):
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument(f"--proxy-server={PROXY_SERVER}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # 反检测：让 Facebook 认不出是 Selenium
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)
            # 额外反检测：去掉 webdriver 属性
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
            return driver
        except Exception as e:
            print(f"[Driver] Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                raise


def scrape_detail_selenium(driver, library_id, wait_sec=8):
    """Selenium 备选方案。"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    result = {
        "library_id": library_id,
        # ---- 头部基础信息 ----
        "advertiser_name": "",       # 广告主名称：Block Blast
        "delivery_period": "",       # 投放时间：2025年12月4日 ~ 2026年2月14日
        "delivery_status": "",       # 状态：已停止投放 / 投放中
        # ---- 账号维度 ----
        "advertiser_entity": "",     # 广告主主体：北京阿瑞斯蒂科技有限公司
        "account_id": "",            # 账号编号：105422708937000
        "followers": "",             # 粉丝：12.1 万
        "industry": "",              # 行业：电子游戏
        "payer_name": "",            # 付费方
        # ---- 受众定向 ----
        "age_range": "",             # 年龄：13岁-65岁+
        "gender": "",                # 性别：不限
        "reach_count": "",           # 覆盖人数（总）：1,221,554
        "region_targeting": {},       # 分地区数据 {"欧盟":{...}, "英国":{...}}
        "ad_disclosure_regions": [],  # 投放地区列表：["欧盟","英国"]
        # ---- 内容 ----
        "about_sponsor": "",
        "advertiser_description": "",
        "ad_text": "",
    }

    try:
        detail_url = "https://www.facebook.com/ads/library/?id=" + library_id
        driver.get(detail_url)
        time.sleep(wait_sec)

        # 点击"查看广告详情"
        for btn_text in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View Ad Details']:
            try:
                btns = driver.find_elements(
                    By.XPATH, "//*[contains(text(),'" + btn_text + "')]"
                )
                for btn in btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click({force:true})", btn)
                        break
            except Exception:
                pass

        time.sleep(3)

        # 等待弹窗
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
            )
        except TimeoutException:
            print(f"[Selenium] No modal for {library_id}")
            return result

        time.sleep(2)

        # 点击4个标签页
        tab_labels = [
            '\u5e7f\u544a\u4fe1\u606f\u516c\u793a\uff08\u6309\u5730\u533a\uff09',
            '\u5173\u4e8e\u5e7f\u544a\u8d5a\u52a9\u65b9',
            '\u5173\u4e8e\u5e7f\u544a\u4e3b',
            '\u5e7f\u544a\u4e3b\u548c\u4ed8\u8d39\u65b9',
        ]
        for tab in tab_labels:
            try:
                els = driver.find_elements(
                    By.XPATH, ".//*[contains(text(),'" + tab + "')]"
                )
                for el in els:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click({force:true})", el)
                        time.sleep(1000)
                        break
            except Exception:
                pass

        time.sleep(2000)

        # 获取弹窗文本
        try:
            dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
            if dialogs:
                full_text = driver.execute_script(
                    "return arguments[0].innerText", dialogs[-1]
                )
            else:
                full_text = ""
        except Exception:
            full_text = ""

        if not full_text:
            return result

        result = parse_detail_text(full_text, library_id)
        print(f"[Selenium] {library_id} | regions={result['ad_disclosure_regions']} | "
              f"age={result['age_range']} | advertiser={result['advertiser_name'][:40]}")
        return result

    except Exception as e:
        import traceback
        print(f"[Selenium] Error {library_id}: {e}")
        traceback.print_exc()
        return result


# ============================================================
# 解析详情页文本
# ============================================================
def parse_detail_text(text, library_id):
    result = {
        "library_id": library_id,
        "advertiser_name": "",
        "delivery_period": "",
        "delivery_status": "",
        "advertiser_entity": "",
        "account_id": "",
        "followers": "",
        "industry": "",
        "payer_name": "",
        "age_range": "",
        "gender": "",
        "reach_count": "",
        "region_targeting": {},
        "ad_disclosure_regions": [],
        "about_sponsor": "",
        "advertiser_description": "",
        "ad_text": "",
    }

    _B_AD_INFO = "广告信息公示（按地区）"
    _B_SPONSOR = "关于广告赞助方"
    _B_ADVERTISER = "关于广告主"
    _B_PAYER = "广告主和付费方"
    _EU = "欧盟"
    _UK = "英国"

    ad_info_start = text.find(_B_AD_INFO)
    sponsor_start = text.find(_B_SPONSOR)
    advertiser_start = text.find(_B_ADVERTISER)
    payer_start = text.find(_B_PAYER)

    # A. 头部
    head = text[:ad_info_start] if ad_info_start >= 0 else text[:400]
    if "已停止" in head:
        result["delivery_status"] = "已停止投放"
    elif "投放中" in head:
        result["delivery_status"] = "投放中"

    id_m = re.search(r"资料库编号：(\d+)", head)
    if id_m:
        result["account_id"] = id_m.group(1)

    period_m = re.search(
        r"(\d{4}年\d{1,2}月\d{1,2}日)\s*[-~]+\s*(\d{4}年\d{1,2}月\d{1,2}日)",
        head
    )
    if period_m:
        result["delivery_period"] = period_m.group(1) + " ~ " + period_m.group(2)

    for line in head.split("\n"):
        line = line.strip()
        if len(line) < 2:
            continue
        # 跳过日期行、纯数字行、资料库编号行
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{4}年", line):
            continue
        if "\u8d44\u6599\u5e93\u7f16\u53f7" in line:
            continue
        if line in ("广告详情", "关闭", "已停止", "平台", "赞助内容", "打开下拉菜单", "\u200b"):
            continue
        if re.search(r"[A-Za-z]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break

    # B. 广告信息公示（按地区）
    if ad_info_start >= 0:
        nxt = [x for x in [sponsor_start, advertiser_start, payer_start] if x > ad_info_start]
        ad_end = min(nxt) if nxt else len(text)
        ad_block = text[ad_info_start:ad_end]

        eu_idx = ad_block.find(_EU)
        if eu_idx >= 0:
            eu_data = parse_region_block(ad_block[eu_idx:eu_idx + 6000])
            if eu_data:
                result["region_targeting"][_EU] = eu_data

        uk_idx = ad_block.find(_UK)
        if uk_idx >= 0:
            uk_data = parse_region_block(ad_block[uk_idx:uk_idx + 6000])
            if uk_data:
                result["region_targeting"][_UK] = uk_data

        if result["region_targeting"]:
            f1 = list(result["region_targeting"].values())[0]
            result["age_range"] = f1.get("age_range", "")
            result["gender"] = f1.get("gender", "")
            result["reach_count"] = f1.get("reach_count", "")
            result["ad_disclosure_regions"] = list(result["region_targeting"].keys())

    # C. 关于广告赞助方
    if sponsor_start >= 0:
        nxt = [x for x in [advertiser_start, payer_start] if x > sponsor_start]
        sp_end = min(nxt) if nxt else len(text)
        sp_block = text[sponsor_start:sp_end]
        result["about_sponsor"] = _clean_text_new(sp_block[len(_B_SPONSOR):].strip())

    # D. 关于广告主
    if advertiser_start >= 0:
        nxt = [x for x in [payer_start] if x > advertiser_start]
        adv_end = min(nxt) if nxt else len(text)
        adv_text = text[advertiser_start:adv_end][len(_B_ADVERTISER):].strip()
        result["advertiser_description"] = _clean_text_new(adv_text, max_len=300)

        acct_m = re.search(r"编号：(\d+)", adv_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        flw_m = re.search(r"([\d.]+)\s*万位?粉丝", adv_text)
        if flw_m:
            result["followers"] = flw_m.group(1) + " 万"

        for kw in ["电子游戏", "网络游戏", "手机游戏", "食品", "美妆", "日化", "服装", "运动", "医疗", "教育", "金融"]:
            if kw in adv_text:
                result["industry"] = kw
                break

        nm = re.search(r"广告主\s*[:：]\s*([^\n]{2,80})", adv_text)
        if nm:
            result["advertiser_name"] = nm.group(1).strip()
        elif not result["advertiser_name"]:
            first = adv_text.split("\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # E. 广告主和付费方
    if payer_start >= 0:
        pblock = text[payer_start:][len(_B_PAYER):].strip()

        # 找"当前" marker（表示以下是当前有效数据），从其位置之后开始解析
        current_marker = pblock.find("\u5f53\u524d")  # "当前"
        search_start = current_marker if current_marker >= 0 else 0

        # 付费方：在"当前"之后找"付费方\n"，取下一行
        after_current = pblock[search_start:]
        pm = re.search(r"\u4ed8\u8d39\u65b9\n([^\n]{2,120})", after_current)
        if pm:
            result["payer_name"] = pm.group(1).strip()

        # 广告主主体：在"当前"之后找"广告主\n"，取下一行
        adidx = after_current.find("\u5e7f\u544a\u4e3b\n")
        if adidx >= 0:
            for line in after_current[adidx + 4:].split("\n"):
                line = line.strip()
                if line and len(line) > 2:
                    result["advertiser_entity"] = line
                    break
        if not result["advertiser_entity"]:
            am = re.search(r"\u5e7f\u544a\u4e3b\s*[:\uff1a]\s*([^\n]{2,120})", pblock)
            if am:
                result["advertiser_entity"] = am.group(1).strip()

    # F. 广告文本：平台链接行之后，找有 4+ 连续英文字母的描述行
    lines = text.split("\n")
    ad_text_found = False
    for i, line in enumerate(lines):
        if re.search(r"(?:PLAY\.GOOGLE\.COM|ITUNES\.APPLE\.COM)", line):
            for j in range(i + 1, min(i + 8, len(lines))):
                nxt = lines[j].strip()
                # Require: 4+ English letters AND at least 2 English words (to filter out
                # Chinese text containing a single English word like "Meta")
                if (len(nxt) >= 4 and re.search(r"[A-Za-z]{4,}", nxt)
                        and len(re.findall(r"[A-Za-z]+", nxt)) >= 2):
                    result["ad_text"] = nxt
                    ad_text_found = True
                    break
            if ad_text_found:
                break

    # Fallback: 如果还没找到英文 ad_text，搜索 "The classic" 关键词（来自"更多信息"段落）
    if not ad_text_found:
        classic_idx = text.find("The classic")
        if classic_idx >= 0:
            snippet = text[classic_idx:classic_idx + 500]
            m = re.search(r'([^"\n]{10,300})', snippet)
            if m:
                result["ad_text"] = m.group(1).strip()

    # 修正：广告1原始数据里"广告主"和"付费方"顺序反了
    # 当 advertiser_entity 是 MeetSocial 时说明它是付费方，需要交换
    if result["advertiser_entity"] and result["advertiser_entity"].startswith("MeetSocial"):
        result["advertiser_entity"], result["payer_name"] = result["payer_name"], result["advertiser_entity"]

    return result


def _clean_text_new(text, max_len=2000):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text
def parse_region_block(block_text):
    """从 EU/UK 地区数据块中提取年龄/性别/覆盖人数。"""
    if not block_text or len(block_text) < 10:
        return None

    # 年龄范围: 21-65+岁, 18-25岁, 25-34岁, 65+岁
    age = ""
    age_m = re.search(r'(\d{1,2})\s*[-~\u2013]\s*(\d{1,2})(\+?)\s*\u5c81', block_text)
    if age_m:
        lo, hi, plus = age_m.group(1), age_m.group(2), age_m.group(3)
        age = f"{lo}岁-{hi}岁+" if plus == "+" else f"{lo}岁-{hi}岁"
    else:
        age_m2 = re.search(r'(\d{1,2})\+(\u5c81)', block_text)
        if age_m2:
            age = f"{age_m2.group(1)}岁+"

    # 性别
    gender = ""
    if re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u4e0d\u9650', block_text):
        gender = "\u4e0d\u9650"
    elif re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u7537\u6027', block_text):
        gender = "\u7537\u6027"
    elif re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u5973\u6027', block_text):
        gender = "\u5973\u6027"

    # 覆盖人数
    reach = ""
    reach_m = re.search(r'([\d,]{6,})', block_text)
    if reach_m:
        raw = reach_m.group(1).replace(",", "").strip()
        if raw.isdigit() and len(raw) >= 4:
            reach = raw

    if age or gender or reach:
        return {"age_range": age, "gender": gender, "reach_count": reach}
    return None


def clean_text(text, max_len=2000):
    """清理文本：合并空白字符，截断到最大长度。"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


# ============================================================
# 主逻辑：加载列表 → 逐个抓取 → 增量保存
# ============================================================

def load_json_file(path):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"ads": []}


def save_detail_json(detail_file, detail_data):
    """增量保存详情 JSON（以 library_id 为 key）。"""
    existing = {}
    if detail_file.exists():
        try:
            with open(detail_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            pass
    if not isinstance(existing, dict):
        existing = {}
    existing.update(detail_data)
    detail_file.parent.mkdir(parents=True, exist_ok=True)
    with open(detail_file, 'w', encoding='utf-8') as fp:
        json.dump(existing, fp, ensure_ascii=False, indent=2)


def find_list_file(date_str=None):
    """查找列表 JSON 文件：优先精确匹配日期，否则用最新文件。"""
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    candidates = list(BASE_DIR.glob(f"output/*/ads_*_{today}.json"))
    if candidates:
        return candidates[0]
    all_files = sorted(
        BASE_DIR.glob("output/*/ads_*.json"),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    if all_files:
        print(f"[Warn] No file for {today}, using: {all_files[0].name}")
        return all_files[0]
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Ad Library - Detail Scraper")
    parser.add_argument("--input", "-i", default=None,
                        help="Input list JSON file (overrides date lookup)")
    parser.add_argument("--date", "-d", default=None,
                        help="Date of list file, e.g. 2026-04-28")
    parser.add_argument("--max", "-m", type=int, default=0,
                        help="Max ads to scrape (0=all)")
    args = parser.parse_args()

    # ---- 找到输入文件 ----
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = find_list_file(args.date)

    if not input_path or not input_path.exists():
        print(f"[Error] No list JSON found. Run scrape_list.py first.")
        print(f"  date={args.date or datetime.now().strftime('%Y-%m-%d')}")
        return

    print(f"[Input] {input_path}")
    data = load_json_file(input_path)
    ads = data.get('ads', [])
    print(f"[Load] {len(ads)} ads from list file")

    # 输出文件路径
    detail_name = f"detail_{input_path.stem}.json"
    detail_file = input_path.parent / detail_name

    # ---- 断点续抓：跳过已完成的 ----
    done_ids = set()
    if detail_file.exists():
        try:
            done = json.load(open(detail_file, 'r', encoding='utf-8'))
            done_ids = set(done.keys())
            print(f"[Resume] {len(done_ids)} already scraped")
        except Exception:
            pass

    to_scrape = [a for a in ads if a['library_id'] not in done_ids]
    if args.max > 0:
        to_scrape = to_scrape[:args.max]

    print(f"[To scrape] {len(to_scrape)} ads")
    if not to_scrape:
        print("All ads already scraped!")
        return

    # ---- 检测可用方案：CDP 还是 Selenium ----
    cdp_url = detect_cdp_url()
    use_cdp = (cdp_url is not None)
    driver = None   # Selenium 会话级 driver（CDP 模式下不需要）

    if not use_cdp:
        print("[Selenium] CDP 不可用，使用 Selenium 直接启动浏览器")
        driver = make_driver(headless=HEADLESS)

    # ---- 逐个抓取 ----
    success_count = 0
    for i, ad in enumerate(to_scrape, 1):
        lid = ad['library_id']
        print(f"\n[Detail] {i}/{len(to_scrape)}: {lid}")

        if use_cdp:
            detail = scrape_detail_cdp(lid, wait_sec=8, cdp_url=cdp_url)
        else:
            detail = scrape_detail_selenium(driver, lid, wait_sec=8)

        # 保存
        if detail:
            save_detail_json(detail_file, {lid: detail})
            regions = detail.get('ad_disclosure_regions', [])
            age = detail.get('age_range', '')
            advertiser = detail.get('advertiser_name', '')[:40]
            print(f"  -> regions={regions} age={age} advertiser={advertiser}")
            if detail.get('library_id'):
                success_count += 1

    # ---- 关闭 Selenium 会话级 driver ----
    if driver:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n[Saved] {detail_file}")
    print(f"Done! {success_count}/{len(to_scrape)} ads scraped.")


if __name__ == "__main__":
    main()
