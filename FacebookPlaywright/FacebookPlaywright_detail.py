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

纯 Playwright 实现（不依赖 Selenium 或外部 Chrome）。

Usage:
  python FacebookPlaywright_detail.py                                    # 处理今天的列表文件
  python FacebookPlaywright_detail.py --date 2026-04-28                 # 指定日期
  python FacebookPlaywright_detail.py -i output/Block_Blast/ads_Block_Blast_2026-04-28.json
  python FacebookPlaywright_detail.py --max 5                           # 只抓前5个（测试用）
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
HEADLESS = False              # Playwright 是否无头模式
# ====================

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# Playwright 主抓取函数（自己启动浏览器）
# ============================================================

def scrape_detail_playwright(library_id, wait_sec=8):
    """
    使用 Playwright 直接启动 Chromium 抓取广告详情。

    完整流程：
      1. 启动 Chromium（代理 + 反检测）
      2. 打开 https://www.facebook.com/ads/library/?id=<library_id>
      3. 点击"查看广告详情"按钮，弹出详情弹窗
      4. 依次点击 4 个标签页（广告信息公示/关于广告赞助方/关于广告主/广告主和付费方）
      5. 获取弹窗完整文本，传入 parse_detail_text 解析
      6. 返回解析后的字段字典

    返回字段（详情见 parse_detail_text 注释）：
      library_id / advertiser_name / delivery_period / delivery_status
      advertiser_entity / account_id / followers / industry / payer_name
      age_range / gender / reach_count / region_targeting / ad_disclosure_regions
      about_sponsor / advertiser_description / ad_text
    """
    from playwright.sync_api import sync_playwright

    result_data = None

    with sync_playwright() as p:
        # ---- 启动 Chromium，带代理和反检测参数 ----
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

        # ---- 打开详情页，等待网络空闲 ----
        page.goto(f"https://www.facebook.com/ads/library/?id={library_id}", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(wait_sec * 1000)

        # ---- 步骤1: 点击"查看广告详情" ----
        # Facebook 页面有多语言版本，中英文按钮文本都需要尝试
        clicked = False
        for kw in ['\u67e5\u770b\u5e7f\u544a\u8be6\u60c5', 'View ad details', 'View Ad Details']:
            try:
                page.get_by_text(kw, exact=False).first.click(timeout=5000, force=True)
                print(f"  [Playwright] 点击按钮: {kw}")
                clicked = True
                break
            except Exception:
                pass

        if not clicked:
            print(f"  [Playwright] 未找到'查看广告详情'按钮")
            browser.close()
            return {"library_id": library_id, "error": "button not found"}

        # ---- 步骤2: 等待弹窗出现 ----
        try:
            page.wait_for_selector('[role="dialog"]', state='visible', timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # ---- 步骤3: 依次点击4个标签页，展开内容 ----
        # 4 个标签页文本（Unicode 转义对照）：
        #   广告信息公示（按地区）
        #   关于广告赞助方
        #   关于广告主
        #   广告主和付费方
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
        # Facebook 页面可能有多个 [role="dialog"]，最后一个是详情弹窗
        full_text = ""
        try:
            dialogs = page.locator('[role="dialog"]').all()
            if dialogs:
                full_text = dialogs[-1].inner_text()
                print(f"  [Playwright] 弹窗文本长度: {len(full_text)}")
        except Exception as e:
            print(f"  [Playwright] 获取弹窗文本失败: {e}")

        if not full_text:
            browser.close()
            return {"library_id": library_id, "error": "no dialog text"}

        # ---- 步骤5: 解析4个区块的数据 ----
        result_data = parse_detail_text(full_text, library_id)

        browser.close()

    return result_data if result_data else {"library_id": library_id, "error": "unknown error"}


# ============================================================
# 解析详情页文本
# ============================================================
def parse_detail_text(text, library_id):
    """
    将弹窗完整文本解析为结构化字段。

    返回字段说明：
      library_id               - 广告 ID
      advertiser_name          - 广告主名称（顶部横条或关于广告主区块第一行）
      delivery_period          - 投放时间（例：2025年12月4日 ~ 2026年2月14日）
      delivery_status          - 投放状态（已停止投放 / 投放中）
      advertiser_entity        - 广告主主体/公司全称（北京阿瑞斯蒂科技有限公司）
      account_id                - 账号编号（例：105422708937000）
      followers                 - 粉丝数（例：12.1 万）
      industry                  - 行业（例：电子游戏）
      payer_name                - 付费方名称
      age_range                 - 年龄定向（例：13岁-65岁+）
      gender                    - 性别定向（例：不限）
      reach_count               - 覆盖人数（例：1221554）
      region_targeting          - 分地区数据 {"欧盟":{age/gender/reach}, "英国":{...}}
      ad_disclosure_regions    - 投放地区列表（例：["欧盟","英国"]）
      about_sponsor             - 关于广告赞助方（自由文本）
      advertiser_description    - 关于广告主（自由文本，最多300字）
      ad_text                   - 广告正文英文文本（从 Google Play / App Store 链接附近提取）

    解析分区：
      A 区（text 开头 ~ 广告信息公示）：头部基础信息
      B 区（广告信息公示）：EU/UK 分地区受众数据
      C 区（关于广告赞助方）：about_sponsor
      D 区（关于广告主）：advertiser_description + account_id + followers + industry
      E 区（广告主和付费方）：payer_name + advertiser_entity（含顺序修复逻辑）
      F 区（穿插在各处）：ad_text
    """
    result = {
        "library_id": library_id,
        "advertiser_name": "",           # 广告主名称：Block Blast
        "delivery_period": "",           # 投放时间：2025年12月4日 ~ 2026年2月14日
        "delivery_status": "",          # 状态：已停止投放 / 投放中
        # ---- 账号维度 ----
        "advertiser_entity": "",         # 广告主主体：北京阿瑞斯蒂科技有限公司
        "account_id": "",                # 账号编号：105422708937000
        "followers": "",                 # 粉丝：12.1 万
        "industry": "",                  # 行业：电子游戏
        "payer_name": "",                # 付费方
        # ---- 受众定向 ----
        "age_range": "",                 # 年龄：13岁-65岁+
        "gender": "",                    # 性别：不限
        "reach_count": "",               # 覆盖人数（总）：1,221,554
        "region_targeting": {},          # 分地区数据 {"欧盟":{...}, "英国":{...}}
        "ad_disclosure_regions": [],     # 投放地区列表：["欧盟","英国"]
        # ---- 内容 ----
        "about_sponsor": "",             # 关于广告赞助方（自由文本）
        "advertiser_description": "",    # 关于广告主（最多300字）
        "ad_text": "",                   # 广告正文英文（Google Play / App Store 链接附近）
    }

    # ---- 区块边界定位 ----
    _B_AD_INFO = "广告信息公示（按地区）"
    _B_SPONSOR = "关于广告赞助方"
    _B_ADVERTISER = "关于广告主"
    _B_PAYER = "广告主和付费方"
    _EU = "欧盟"
    _UK = "英国"

    # 找每个区块的起始位置（用于切分文本范围）
    ad_info_start = text.find(_B_AD_INFO)
    sponsor_start = text.find(_B_SPONSOR)
    advertiser_start = text.find(_B_ADVERTISER)
    payer_start = text.find(_B_PAYER)

    # =====================
    # A. 头部基础信息
    # =====================
    # 头部范围：text 开头 ~ 广告信息公示区块（取前400字符兜底）
    head = text[:ad_info_start] if ad_info_start >= 0 else text[:400]

    # 投放状态：已停止 / 投放中
    if "已停止" in head:
        result["delivery_status"] = "已停止投放"
    elif "投放中" in head:
        result["delivery_status"] = "投放中"

    # 账号编号：资料库编号：<数字>
    id_m = re.search(r"资料库编号：(\d+)", head)
    if id_m:
        result["account_id"] = id_m.group(1)

    # 投放周期：2025年12月4日 ~ 2026年2月14日
    period_m = re.search(
        r"(\d{4}年\d{1,2}月\d{1,2}日)\s*[-~]+\s*(\d{4}年\d{1,2}月\d{1,2}日)",
        head
    )
    if period_m:
        result["delivery_period"] = period_m.group(1) + " ~ " + period_m.group(2)

    # 广告主名称：头部第一个含英文的行（跳过纯数字/日期/特殊字符行）
    for line in head.split("\n"):
        line = line.strip()
        if len(line) < 2:
            continue
        # 跳过纯数字行、日期行、资料库编号行
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{4}年", line):
            continue
        if "\u8d44\u6599\u5e93\u7f16\u53f7" in line:  # 资料库编号
            continue
        if line in ("广告详情", "关闭", "已停止", "平台", "赞助内容", "打开下拉菜单", "\u200b"):
            continue
        # 含英文字母且长度合理 → 是广告主名称
        if re.search(r"[A-Za-z]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break

    # =====================
    # B. 广告信息公示（按地区）
    # =====================
    # 从广告信息公示区块提取 EU/UK 的受众数据
    if ad_info_start >= 0:
        # 计算区块结束位置 = 下一个区块（赞助方/广告主/付费方）的起始位置
        nxt = [x for x in [sponsor_start, advertiser_start, payer_start] if x > ad_info_start]
        ad_end = min(nxt) if nxt else len(text)
        ad_block = text[ad_info_start:ad_end]

        # 解析 EU 数据块
        eu_idx = ad_block.find(_EU)
        if eu_idx >= 0:
            eu_data = parse_region_block(ad_block[eu_idx:eu_idx + 6000])
            if eu_data:
                result["region_targeting"][_EU] = eu_data

        # 解析 UK 数据块
        uk_idx = ad_block.find(_UK)
        if uk_idx >= 0:
            uk_data = parse_region_block(ad_block[uk_idx:uk_idx + 6000])
            if uk_data:
                result["region_targeting"][_UK] = uk_data

        # 从第一个地区数据填充全局受众字段（age/gender/reach 取 EU 或 UK 的）
        if result["region_targeting"]:
            f1 = list(result["region_targeting"].values())[0]
            result["age_range"] = f1.get("age_range", "")
            result["gender"] = f1.get("gender", "")
            result["reach_count"] = f1.get("reach_count", "")
            result["ad_disclosure_regions"] = list(result["region_targeting"].keys())

    # =====================
    # C. 关于广告赞助方
    # =====================
    # 提取自由文本，去掉标题前缀
    if sponsor_start >= 0:
        nxt = [x for x in [advertiser_start, payer_start] if x > sponsor_start]
        sp_end = min(nxt) if nxt else len(text)
        sp_block = text[sponsor_start:sp_end]
        result["about_sponsor"] = _clean_text_new(sp_block[len(_B_SPONSOR):].strip())

    # =====================
    # D. 关于广告主
    # =====================
    if advertiser_start >= 0:
        nxt = [x for x in [payer_start] if x > advertiser_start]
        adv_end = min(nxt) if nxt else len(text)
        adv_text = text[advertiser_start:adv_end][len(_B_ADVERTISER):].strip()

        # 关于广告主正文（自由文本，最多300字）
        result["advertiser_description"] = _clean_text_new(adv_text, max_len=300)

        # 账号编号（可能出现在关于广告主区块）
        acct_m = re.search(r"编号：(\d+)", adv_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        # 粉丝数：12.1 万
        flw_m = re.search(r"([\d.]+)\s*万位?粉丝", adv_text)
        if flw_m:
            result["followers"] = flw_m.group(1) + " 万"

        # 行业：电子游戏/食品/美妆等关键词匹配
        for kw in ["电子游戏", "网络游戏", "手机游戏", "食品", "美妆", "日化", "服装", "运动", "医疗", "教育", "金融"]:
            if kw in adv_text:
                result["industry"] = kw
                break

        # 广告主名称：优先用"广告主：xxx"格式，其次用第一行
        nm = re.search(r"广告主\s*[:：]\s*([^\n]{2,80})", adv_text)
        if nm:
            result["advertiser_name"] = nm.group(1).strip()
        elif not result["advertiser_name"]:
            first = adv_text.split("\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # =====================
    # E. 广告主和付费方
    # =====================
    # 付费方和广告主主体从"当前"标记之后开始找更准确
    if payer_start >= 0:
        pblock = text[payer_start:][len(_B_PAYER):].strip()

        # 找到"当前"关键字，从其位置之后开始搜索付费方/广告主行
        current_marker = pblock.find("\u5f53\u524d")  # "当前"
        search_start = current_marker if current_marker >= 0 else 0

        after_current = pblock[search_start:]
        # 付费方：付费方\n<内容行>
        pm = re.search(r"\u4ed8\u8d39\u65b9\n([^\n]{2,120})", after_current)
        if pm:
            result["payer_name"] = pm.group(1).strip()

        # 广告主主体：在付费方之后找"广告主\n<公司名>"
        adidx = after_current.find("\u5e7f\u544a\u4e3b\n")
        if adidx >= 0:
            for line in after_current[adidx + 4:].split("\n"):
                line = line.strip()
                if line and len(line) > 2:
                    result["advertiser_entity"] = line
                    break
        # 兜底：用正则直接匹配"广告主：xxx"格式
        if not result["advertiser_entity"]:
            am = re.search(r"\u5e7f\u544a\u4e3b\s*[:\uff1a]\s*([^\n]{2,120})", pblock)
            if am:
                result["advertiser_entity"] = am.group(1).strip()

    # =====================
    # F. 广告正文（英文）
    # =====================
    # 策略：从 Google Play / App Store 链接之后几行内找英文描述
    lines = text.split("\n")
    ad_text_found = False
    for i, line in enumerate(lines):
        if re.search(r"(?:PLAY\.GOOGLE\.COM|ITUNES\.APPLE\.COM)", line):
            for j in range(i + 1, min(i + 8, len(lines))):
                nxt = lines[j].strip()
                # 英文描述行特征：4字符以上，至少2个完整英文单词
                if (len(nxt) >= 4 and re.search(r"[A-Za-z]{4,}", nxt)
                        and len(re.findall(r"[A-Za-z]+", nxt)) >= 2):
                    result["ad_text"] = nxt
                    ad_text_found = True
                    break
            if ad_text_found:
                break

    # 兜底策略：从 "The classic" 附近找英文段落
    if not ad_text_found:
        classic_idx = text.find("The classic")
        if classic_idx >= 0:
            snippet = text[classic_idx:classic_idx + 500]
            m = re.search(r'([^"\n]{10,300})', snippet)
            if m:
                result["ad_text"] = m.group(1).strip()

    # ---- 修正：某些广告里付费方和广告主顺序反了 ----
    # 典型情况：MeetSocial 等代理商的 advertiser_entity 错误出现在 payer_name 位置
    if result["advertiser_entity"] and result["advertiser_entity"].startswith("MeetSocial"):
        result["advertiser_entity"], result["payer_name"] = result["payer_name"], result["advertiser_entity"]

    return result


def _clean_text_new(text, max_len=2000):
    """
    清理文本：去除多余空白，截断超长内容。
    
    参数：
      text    - 原始文本
      max_len - 最大字符数，超出截断并加省略号
    
    处理：
      - 多个空白字符合并为一个
      - 首尾去空格
      - 超出 max_len 截断
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def parse_region_block(block_text):
    """
    从 EU/UK 地区数据块中提取受众定向字段。
    
    参数：block_text - 截取的地区区块文本（前6000字符）
    
    返回示例：
      {
        "age_range": "18岁-65岁+",
        "gender": "不限",
        "reach_count": "1221554"
      }
    
    解析逻辑：
      - 年龄：正则匹配 "数字-数字岁" 或 "数字+岁"
      - 性别：匹配"不限/男性/女性"关键字
      - 覆盖人数：匹配6位以上的纯数字（去逗号）
    """
    if not block_text or len(block_text) < 10:
        return None

    age = ""
    # 年龄范围：18-65岁+ 或 18-65岁
    age_m = re.search(r'(\d{1,2})\s*[-~\u2013]\s*(\d{1,2})(\+?)\s*\u5c81', block_text)
    if age_m:
        lo, hi, plus = age_m.group(1), age_m.group(2), age_m.group(3)
        age = f"{lo}岁-{hi}岁+" if plus == "+" else f"{lo}岁-{hi}岁"
    else:
        # 单一年龄+：65+岁
        age_m2 = re.search(r'(\d{1,2})\+(\u5c81)', block_text)
        if age_m2:
            age = f"{age_m2.group(1)}岁+"

    gender = ""
    if re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u4e0d\u9650', block_text):
        gender = "\u4e0d\u9650"     # 不限
    elif re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u7537\u6027', block_text):
        gender = "\u7537\u6027"     # 男性
    elif re.search(r'\u6027\u522b\s*[:\u3001\uff1a]?\s*\u5973\u6027', block_text):
        gender = "\u5973\u6027"     # 女性

    reach = ""
    # 覆盖人数：6位以上数字（去逗号）
    reach_m = re.search(r'([\d,]{6,})', block_text)
    if reach_m:
        raw = reach_m.group(1).replace(",", "").strip()
        if raw.isdigit() and len(raw) >= 4:
            reach = raw

    if age or gender or reach:
        return {"age_range": age, "gender": gender, "reach_count": reach}
    return None


# ============================================================
# 主逻辑
# ============================================================

def load_json_file(path):
    """读取 JSON 文件，返回内容（失败返回空结构）。"""
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"ads": []}


def save_detail_json(detail_file, detail_data):
    """
    将详情数据追加到 JSON 文件（已有文件则合并，不覆盖）。
    detail_file 格式：{<library_id>: {fields...}, ...}
    """
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
    """
    查找列表 JSON 文件：
      - 优先精确匹配日期（如 2026-04-28）
      - 找不到则用最新修改的文件（并打印警告）
      - 完全没有则返回 None
    """
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
    """
    主入口流程：
    
    1. 解析命令行参数（--input / --date / --max）
    2. 定位列表 JSON 文件
    3. 读取已有详情文件，实现断点续抓（跳过 done_ids）
    4. 遍历待抓广告，逐个调用 scrape_detail_playwright
    5. 每抓完一个实时写入 JSON（防止中途崩溃丢失数据）
    6. 打印完成统计
    
    输出文件：与列表文件同目录，名为 detail_<原文件名>.json
    """
    import argparse
    parser = argparse.ArgumentParser(description="Facebook Ad Library - Detail Scraper (Playwright)")
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
        print(f"[Error] No list JSON found. Run FacebookPlaywright_list.py first.")
        print(f"  date={args.date or datetime.now().strftime('%Y-%m-%d')}")
        return

    print(f"[Input] {input_path}")
    data = load_json_file(input_path)
    ads = data.get('ads', [])
    print(f"[Load] {len(ads)} ads from list file")

    # 输出文件路径：output/Block_Blast/detail_ads_Block_Blast_2026-04-28.json
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

    # ---- 逐个抓取 ----
    success_count = 0
    for i, ad in enumerate(to_scrape, 1):
        lid = ad['library_id']
        print(f"\n[Detail] {i}/{len(to_scrape)}: {lid}")

        detail = scrape_detail_playwright(lid, wait_sec=8)

        # 实时保存（每抓一个写一次，防止崩溃丢失进度）
        if detail:
            save_detail_json(detail_file, {lid: detail})
            regions = detail.get('ad_disclosure_regions', [])
            age = detail.get('age_range', '')
            advertiser = detail.get('advertiser_name', '')[:40]
            print(f"  -> regions={regions} age={age} advertiser={advertiser}")
            if detail.get('library_id'):
                success_count += 1

    print(f"\n[Saved] {detail_file}")
    print(f"Done! {success_count}/{len(to_scrape)} ads scraped.")


if __name__ == "__main__":
    main()
