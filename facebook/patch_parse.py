"""临时脚本：把新的 parse_detail_text 函数正文写入 scrape_detail.py"""
import re, sys

NEW_FUNC = '''
def parse_detail_text(text, library_id):
    """
    从弹窗完整文本中解析所有字段。
    对应 full_text 中的区块结构：
      - 头部：广告主、投放时间、状态、资料库编号
      - 广告信息公示（按地区）：EU/UK + 年龄/性别/覆盖人数
      - 关于广告赞助方
      - 关于广告主：账号编号、粉丝、行业
      - 广告主和付费方：广告主主体（中英文）、付费方
    """
    result = {
        "library_id": library_id,
        # ---- 头部基础信息 ----
        "advertiser_name": "",       # 广告主：Block Blast
        "delivery_period": "",       # 投放时间：2025年12月4日 - 2026年2月14日
        "delivery_status": "",       # 状态：已停止 / 投放中
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
        "region_targeting": {},      # 分地区详细数据
        "ad_disclosure_regions": [], # 投放地区列表：["欧盟","英国"]
        # ---- 内容 ----
        "about_sponsor": "",
        "advertiser_description": "",
        "ad_text": "",
    }

    # ------ 区块分割标记 ------
    BLOCK_AD_INFO = "\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a"             # 广告信息公示（按地区）
    BLOCK_ABOUT_SPONSOR = "\\u5e7f\\u544a\\u5173\\u4e8e\\u5e7f\\u544a\\u8d5a\\u52a9\\u65b9"  # 关于广告赞助方
    BLOCK_ABOUT_ADVERTISER = "\\u5173\\u4e8e\\u5e7f\\u544a\\u4e3b"            # 关于广告主
    BLOCK_SPONSOR_PAYER = "\\u5e7f\\u544a\\u4e3b\\u548c\\u4ed8\\u8d39\\u65b9" # 广告主和付费方

    EU_MARKER = "\\u6b27\\u76df"   # 欧盟
    UK_MARKER = "\\u82f1\\u56fd"   # 英国

    ad_info_start = text.find(BLOCK_AD_INFO)
    sponsor_start = text.find(BLOCK_ABOUT_SPONSOR)
    advertiser_start = text.find(BLOCK_ABOUT_ADVERTISER)
    payer_start = text.find(BLOCK_SPONSOR_PAYER)

    # ===========================================================
    # A. 头部信息：从开头到 BLOCK_AD_INFO 之前
    # ===========================================================
    head_block = text[:ad_info_start] if ad_info_start >= 0 else text[:300]

    # 状态（已停止 / 投放中）
    if "\\u5df2\\u505c\\u6b62" in head_block:
        result["delivery_status"] = "\\u5df2\\u505c\\u6b62\\u6295\\u653e"
    elif "\\u6295\\u653e\\u4e2d" in head_block:
        result["delivery_status"] = "\\u6295\\u653e\\u4e2d"

    # 资料库编号（账号编号）
    id_m = re.search(r"\\u8d44\\u6599\\u5e93\\u7f16\\u53f7\\uff1a(\\d+)", head_block)
    if id_m:
        result["account_id"] = id_m.group(1)

    # 投放时间
    period_m = re.search(r"(\\d{4}\\u5e74\\d{1,2}\\u6708\\d{1,2}\\u65e5)\\s*[-~]+\\s*(\\d{4}\\u5e74\\d{1,2}\\u6708\\d{1,2}\\u65e5)", head_block)
    if period_m:
        result["delivery_period"] = f"{period_m.group(1)} ~ {period_m.group(2)}"

    # 广告主名称（标题区，赞助内容之后）
    name_m = re.search(r"^([A-Za-z0-9 \\-]{2,50})\\n\\u8d85\\u8d3a\\u5185\\u5bb9", head_block, re.MULTILINE)
    if name_m:
        result["advertiser_name"] = name_m.group(1).strip()

    # ===========================================================
    # B. 广告信息公示（按地区）：年龄/性别/覆盖人数/分地区
    # ===========================================================
    if ad_info_start >= 0:
        next_starts = [x for x in [sponsor_start, advertiser_start, payer_start] if x > ad_info_start]
        ad_info_end = min(next_starts) if next_starts else len(text)
        ad_info_block = text[ad_info_start:ad_info_end]

        # 从整个 ad_info_block 提取 EU 和 UK 的年龄/性别/覆盖人数
        for region_name, marker in [("\\u6b27\\u7f9f", EU_MARKER), ("\\u82f1\\u56fd", UK_MARKER)]:
            idx = ad_info_block.find(marker)
            if idx < 0:
                continue
            region_block = ad_info_block[idx:idx + 5000]
            data = parse_region_block(region_block)
            if data:
                result["region_targeting"][region_name] = data

        if result["region_targeting"]:
            first = list(result["region_targeting"].values())[0]
            result["age_range"] = first.get("age_range", "")
            result["gender"] = first.get("gender", "")
            result["reach_count"] = first.get("reach_count", "")
            result["ad_disclosure_regions"] = list(result["region_targeting"].keys())

    # ===========================================================
    # C. 关于广告赞助方
    # ===========================================================
    if sponsor_start >= 0:
        next_starts = [x for x in [advertiser_start, payer_start] if x > sponsor_start]
        sponsor_end = min(next_starts) if next_starts else len(text)
        sponsor_block = text[sponsor_start:sponsor_end]
        sponsor_text = sponsor_block[len(BLOCK_ABOUT_SPONSOR):].strip()
        result["about_sponsor"] = clean_text(sponsor_text, max_len=2000)

    # ===========================================================
    # D. 关于广告主：账号编号、粉丝、行业
    # ===========================================================
    if advertiser_start >= 0:
        next_starts = [x for x in [payer_start] if x > advertiser_start]
        advertiser_end = min(next_starts) if next_starts else len(text)
        advertiser_block = text[advertiser_start:advertiser_end]
        advertiser_text = advertiser_block[len(BLOCK_ABOUT_ADVERTISER):].strip()

        # 取前 300 字符作为 description
        result["advertiser_description"] = clean_text(advertiser_text, max_len=300)

        # 账号编号（\\u7f16\\u53f7：后面跟数字）
        acct_m = re.search(r"\\u7f16\\u53f7\\uff1a(\\d+)", advertiser_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        # 粉丝数（12.1 \\u4e07\\u4f4d\\u7c89\\u4e1d）
        followers_m = re.search(r"([\\d.,]+)\\u4e07\\u4f4d?\\u7c89\\u4e1d", advertiser_text)
        if followers_m:
            result["followers"] = followers_m.group(1).replace(",", "") + " \\u4e07"

        # 行业
        industry_keywords = [
            "\\u7535\\u5b50\\u6e38\\u620f", "\\u624b\\u673a\\u6e38\\u620f", "\\u7f51\\u7edc\\u6e38\\u620f",
            "\\u98df\\u54c1", "\\u7f8e\\u5986", "\\u65e5\\u5316", "\\u670d\\u88c5", "\\u8fd0\\u52a8",
            "\\u533b\\u7597", "\\u6559\\u80b2", "\\u91d1\\u878d", "\\u4f01\\u4e1a\\u670d\\u52a1",
        ]
        for kw in industry_keywords:
            if kw in advertiser_text:
                result["industry"] = kw
                break

        # 广告主名称：找"广告主："或直接取第一行
        name_m = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{2,80})", advertiser_text)
        if name_m:
            result["advertiser_name"] = name_m.group(1).strip()
        elif not result["advertiser_name"]:
            first = advertiser_text.split("\\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # ===========================================================
    # E. 广告主和付费方：广告主主体（中英文）、付费方
    # ===========================================================
    if payer_start >= 0:
        payer_block = text[payer_start:]
        payer_text = payer_block[len(BLOCK_SPONSOR_PAYER):].strip()

        # 付费方
        payer_m = re.search(r"\\u4ed8\\u8d39\\u65b9\\s*[:\\uff1a]\\s*([^\\n]{2,100})", payer_text)
        if payer_m:
            result["payer_name"] = payer_m.group(1).strip()

        # 广告主主体：广告主：后面跟中文+英文混合
        adv_m = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{2,120})", payer_text)
        if adv_m:
            result["advertiser_entity"] = adv_m.group(1).strip()
            # 如果还没有广告主名称，尝试从主体中提取英文名
            if not result["advertiser_name"]:
                en_m = re.search(r"([A-Za-z][A-Za-z0-9 \\-.,]{2,60})", adv_m.group(1))
                if en_m:
                    result["advertiser_name"] = en_m.group(1).strip()

    # ===========================================================
    # F. 广告文本（正文内容）
    # ===========================================================
    # 找视频链接后面的描述文字
    ad_text_m = re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)[^\\n]*\\n([^\\n]{4,500})", text)
    if ad_text_m:
        result["ad_text"] = ad_text_m.group(1).strip()
    else:
        # 兜底：找 emoji 序列后面的中文字符
        fallback = re.search(r"[\\U0001F600-\\U0001F64F]{2,}[^\\n]*\\n([^\\n\\u4e00-\\u9fff]{0,20}[\\u4e00-\\u9fff]{4,200})", text)
        if fallback:
            result["ad_text"] = fallback.group(1).strip()

    return result
'''

# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of parse_detail_text (line 338: "def parse_detail_text")
func_start = content.find('\ndef parse_detail_text(')
if func_start == -1:
    print("ERROR: parse_detail_text function not found!", file=sys.stderr)
    sys.exit(1)

# Find the start of parse_region_block (the next top-level def)
region_block_start = content.find('\ndef parse_region_block(', func_start)
if region_block_start == -1:
    print("ERROR: parse_region_block not found!", file=sys.stderr)
    sys.exit(1)

# Replace everything from "def parse_detail_text" to just before "def parse_region_block"
new_content = content[:func_start] + NEW_FUNC.strip() + '\n' + content[region_block_start:]

with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patched successfully!")
