"""直接写入新的 parse_detail_text 到文件（避免转义混乱）"""

BLOCK_AD_INFO = "广告信息公示（按地区）"
BLOCK_ABOUT_SPONSOR = "关于广告赞助方"
BLOCK_ABOUT_ADVERTISER = "关于广告主"
BLOCK_SPONSOR_PAYER = "广告主和付费方"
EU_MARKER = "欧盟"
UK_MARKER = "英国"

NEW_FUNC = f'''
def parse_detail_text(text, library_id):
    """
    从弹窗完整文本中解析所有字段。

    full_text 区块结构：
      头部 → 广告主、状态、资料库编号、投放时间
      广告信息公示（按地区）→ EU/UK + 年龄/性别/覆盖人数
      关于广告赞助方
      关于广告主 → 广告主名称、账号编号、粉丝、行业
      广告主和付费方 → 广告主主体（中英文）、付费方
    """
    result = {{
        "library_id": library_id,
        # ---- 头部基础信息 ----
        "advertiser_name": "",
        "delivery_period": "",
        "delivery_status": "",
        # ---- 账号维度 ----
        "advertiser_entity": "",
        "account_id": "",
        "followers": "",
        "industry": "",
        "payer_name": "",
        # ---- 受众定向 ----
        "age_range": "",
        "gender": "",
        "reach_count": "",
        "region_targeting": {{}},
        "ad_disclosure_regions": [],
        # ---- 内容 ----
        "about_sponsor": "",
        "advertiser_description": "",
        "ad_text": "",
    }}

    # ------ 区块分割标记 ------
    _B_AD_INFO = "{BLOCK_AD_INFO}"
    _B_SPONSOR = "{BLOCK_ABOUT_SPONSOR}"
    _B_ADVERTISER = "{BLOCK_ABOUT_ADVERTISER}"
    _B_PAYER = "{BLOCK_SPONSOR_PAYER}"
    _EU = "{EU_MARKER}"
    _UK = "{UK_MARKER}"

    ad_info_start = text.find(_B_AD_INFO)
    sponsor_start = text.find(_B_SPONSOR)
    advertiser_start = text.find(_B_ADVERTISER)
    payer_start = text.find(_B_PAYER)

    # ===========================================================
    # A. 头部信息（开头 → 广告信息公示之前）
    # ===========================================================
    head_block = text[:ad_info_start] if ad_info_start >= 0 else text[:400]

    # 状态
    if "\\u5df2\\u505c\\u6b62" in head_block:
        result["delivery_status"] = "\\u5df2\\u505c\\u6b62\\u6295\\u653e"
    elif "\\u6295\\u653e\\u4e2d" in head_block:
        result["delivery_status"] = "\\u6295\\u653e\\u4e2d"

    # 资料库编号（账号编号）
    import re
    id_m = re.search(r"\\u8d44\\u6599\\u5e93\\u7f16\\u53f7\\uff1a(\\d+)", head_block)
    if id_m:
        result["account_id"] = id_m.group(1)

    # 投放时间
    period_m = re.search(
        r"(\\d{{4}}\\u5e74\\d{{1,2}}\\u6708\\d{{1,2}}\\u65e5)\\s*[-~]+\\s*(\\d{{4}}\\u5e74\\d{{1,2}}\\u6708\\d{{1,2}}\\u65e5)",
        head_block
    )
    if period_m:
        result["delivery_period"] = f"{{period_m.group(1)}} ~ {{period_m.group(2)}}"

    # 广告主名称（赞助内容标题区）
    name_m = re.search(r"^([A-Za-z0-9 \\-要注意]{{2,60}})\\n\\u8d3a\\u5185\\u5bb9", head_block, re.MULTILINE)
    if name_m:
        result["advertiser_name"] = name_m.group(1).strip()

    # ===========================================================
    # B. 广告信息公示（按地区）
    # ===========================================================
    if ad_info_start >= 0:
        next_starts = [x for x in [sponsor_start, advertiser_start, payer_start] if x > ad_info_start]
        ad_info_end = min(next_starts) if next_starts else len(text)
        ad_info_block = text[ad_info_start:ad_info_end]

        # EU
        eu_idx = ad_info_block.find(_EU)
        if eu_idx >= 0:
            eu_block = ad_info_block[eu_idx:eu_idx + 6000]
            eu_data = parse_region_block(eu_block)
            if eu_data:
                result["region_targeting"][_EU] = eu_data

        # UK
        uk_idx = ad_info_block.find(_UK)
        if uk_idx >= 0:
            uk_block = ad_info_block[uk_idx:uk_idx + 6000]
            uk_data = parse_region_block(uk_block)
            if uk_data:
                result["region_targeting"][_UK] = uk_data

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
        sponsor_text = sponsor_block[len(_B_SPONSOR):].strip()
        result["about_sponsor"] = _clean_text(sponsor_text, max_len=2000)

    # ===========================================================
    # D. 关于广告主：广告主名称、账号编号、粉丝、行业
    # ===========================================================
    if advertiser_start >= 0:
        next_starts = [x for x in [payer_start] if x > advertiser_start]
        advertiser_end = min(next_starts) if next_starts else len(text)
        advertiser_block = text[advertiser_start:advertiser_end]
        advertiser_text = advertiser_block[len(_B_ADVERTISER):].strip()

        result["advertiser_description"] = _clean_text(advertiser_text, max_len=300)

        # 账号编号
        acct_m = re.search(r"\\u7f16\\u53f7\\uff1a(\\d+)", advertiser_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        # 粉丝（12.1\\xa0万位粉丝）
        followers_m = re.search(r"([\\d.]+)\\s*\\u4e07\\u4f4d?\\u7c89\\u4e1d", advertiser_text)
        if followers_m:
            result["followers"] = followers_m.group(1).replace(",", "") + " \\u4e07"

        # 行业
        industry_keywords = [
            "\\u7535\\u5b50\\u6e38\\u620f", "\\u624b\\u673a\\u6e38\\u620f",
            "\\u7f51\\u7edc\\u6e38\\u620f", "\\u98df\\u54c1", "\\u7f8e\\u5986",
            "\\u65e5\\u5316", "\\u670d\\u88c5", "\\u8fd0\\u52a8",
            "\\u533b\\u7597", "\\u6559\\u80b2", "\\u91d1\\u878d",
        ]
        for kw in industry_keywords:
            if kw in advertiser_text:
                result["industry"] = kw
                break

        # 广告主名称（找"广告主："后面）
        name_m2 = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{{2,80}})", advertiser_text)
        if name_m2:
            result["advertiser_name"] = name_m2.group(1).strip()
        elif not result["advertiser_name"]:
            first = advertiser_text.split("\\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # ===========================================================
    # E. 广告主和付费方
    # ===========================================================
    if payer_start >= 0:
        payer_block = text[payer_start:]
        payer_text = payer_block[len(_B_PAYER):].strip()

        # 付费方：找"付费方\n"之后的行
        payer_line_m = re.search(r"\\u4ed8\\u8d39\\u65b9\\n([^\\n]{{2,120}})", payer_text)
        if payer_line_m:
            result["payer_name"] = payer_line_m.group(1).strip()

        # 广告主主体：找"广告主\n"之后的几行（通常第二行是公司名）
        adv_entity_m = re.search(r"\\u5e7f\\u544a\\u4e3b\\n(.{{2,120}})\\n", payer_text)
        if adv_entity_m:
            entity_line = adv_entity_m.group(1).strip()
            if entity_line and len(entity_line) > 2:
                result["advertiser_entity"] = entity_line

        # 如果主体为空，尝试从"广告主："后面取
        if not result["advertiser_entity"]:
            adv_m = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{{2,120}})", payer_text)
            if adv_m:
                result["advertiser_entity"] = adv_m.group(1).strip()

    # ===========================================================
    # F. 广告文本
    # ===========================================================
    ad_text_m = re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)[^\\n]*\\n([^\\n]{{4,500}})", text)
    if ad_text_m:
        result["ad_text"] = ad_text_m.group(1).strip()

    return result


def _clean_text(text, max_len=2000):
    import re
    if not text:
        return ""
    text = re.sub(r"\\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text
'''

# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find parse_detail_text and parse_region_block boundaries
func_start = content.find('\ndef parse_detail_text(')
region_start = content.find('\ndef parse_region_block(', func_start)

if func_start == -1 or region_start == -1:
    print(f"ERROR: func_start={func_start}, region_start={region_start}")
    import sys; sys.exit(1)

# Replace
new_content = content[:func_start] + NEW_FUNC.strip() + '\n' + content[region_start:]

with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("OK - patched")
