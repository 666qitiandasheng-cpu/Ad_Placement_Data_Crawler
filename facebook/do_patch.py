# -*- coding: utf-8 -*-
"""把新的 parse_detail_text 直接写入 scrape_detail.py（不使用字符串转义）"""

import re

# 读取原文件
PATH = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 parse_detail_text 函数开始和 parse_region_block 函数开始
func_start = content.find('\ndef parse_detail_text(')
region_start = content.find('\ndef parse_region_block(', func_start)
print(f"func_start={func_start}, region_start={region_start}")

# 直接写新的函数（带真实 Unicode 字符）
NEW_FUNC = '''

def parse_detail_text(text, library_id):
    """
    从弹窗完整文本中解析所有字段。
    对应 full_text 区块结构：
      头部 → 广告主、状态、资料库编号、投放时间
      广告信息公示（按地区）→ EU/UK + 年龄/性别/覆盖人数
      关于广告赞助方
      关于广告主 → 广告主名称、账号编号、粉丝、行业
      广告主和付费方 → 广告主主体（中英文）、付费方
    """
    result = {
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
        "region_targeting": {},
        "ad_disclosure_regions": [],
        # ---- 内容 ----
        "about_sponsor": "",
        "advertiser_description": "",
        "ad_text": "",
    }

    # ------ 区块分割标记 ------
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

    # ===========================================================
    # A. 头部信息（开头 → 广告信息公示之前）
    # ===========================================================
    head_block = text[:ad_info_start] if ad_info_start >= 0 else text[:400]

    # 状态
    if "已停止" in head_block:
        result["delivery_status"] = "已停止投放"
    elif "投放中" in head_block:
        result["delivery_status"] = "投放中"

    # 账号编号（资料库编号）
    id_m = re.search(r"资料库编号：(\d+)", head_block)
    if id_m:
        result["account_id"] = id_m.group(1)

    # 投放时间
    period_m = re.search(
        r"(\d{4}年\d{1,2}月\d{1,2}日)\s*[-~]+\s*(\d{4}年\d{1,2}月\d{1,2}日)",
        head_block
    )
    if period_m:
        result["delivery_period"] = f"{period_m.group(1)} ~ {period_m.group(2)}"

    # 广告主名称（赞助内容标题区，第一行）
    lines = head_block.split('\n')
    for line in lines:
        line = line.strip()
        # 跳过空行、短行、状态行
        if len(line) < 3 or line in ("广告详情", "关闭", "已停止", "平台", "赞助内容"):
            continue
        # 如果包含字母/数字且长度合理，认为是广告主名
        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break

    # ===========================================================
    # B. 广告信息公示（按地区）→ 年龄/性别/覆盖人数
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
    # D. 关于广告主：账号编号、粉丝、行业（来源："关于广告主"区块）
    # ===========================================================
    if advertiser_start >= 0:
        next_starts = [x for x in [payer_start] if x > advertiser_start]
        advertiser_end = min(next_starts) if next_starts else len(text)
        advertiser_block = text[advertiser_start:advertiser_end]
        advertiser_text = advertiser_block[len(_B_ADVERTISER):].strip()

        result["advertiser_description"] = _clean_text(advertiser_text, max_len=300)

        # 账号编号
        acct_m = re.search(r"编号：(\d+)", advertiser_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        # 粉丝（12.1\xa0万位粉丝 或 12.1万位粉丝）
        followers_m = re.search(r"([\d.]+)\s*万位?粉丝", advertiser_text)
        if followers_m:
            result["followers"] = followers_m.group(1) + " 万"

        # 行业（从"电子游戏"等关键词）
        industry_keywords = [
            "电子游戏", "网络游戏", "手机游戏",
            "食品", "美妆", "日化", "服装", "运动",
            "医疗", "教育", "金融", "企业服务",
        ]
        for kw in industry_keywords:
            if kw in advertiser_text:
                result["industry"] = kw
                break

        # 广告主名称：从"广告主："后面取
        name_m = re.search(r"广告主\s*[:：]\s*([^\n]{2,80})", advertiser_text)
        if name_m:
            result["advertiser_name"] = name_m.group(1).strip()
        elif not result["advertiser_name"]:
            # 兜底：取第一行
            first = advertiser_text.split("\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # ===========================================================
    # E. 广告主和付费方：广告主主体（中英文）、付费方
    # ===========================================================
    if payer_start >= 0:
        payer_block = text[payer_start:]
        payer_text = payer_block[len(_B_PAYER):].strip()

        # 付费方：出现在"付费方\n"之后的第一行（非空行）
        payer_line_m = re.search(r"付费方\s*[:：]?\s*([^\n]{2,120})", payer_text)
        if payer_line_m:
            result["payer_name"] = payer_line_m.group(1).strip()
        else:
            # 找"付费方\n"后面紧跟的行
            payer_idx = payer_text.find("付费方")
            if payer_idx >= 0:
                after = payer_text[payer_idx + 3:].lstrip("\n ").split("\n")
                for line in after:
                    line = line.strip()
                    if line and len(line) > 2:
                        result["payer_name"] = line
                        break

        # 广告主主体：出现在"广告主\n"之后（通常是公司名）
        adv_idx = payer_text.find("广告主\n")
        if adv_idx >= 0:
            after = payer_text[adv_idx + 4:].split("\n")
            for line in after:
                line = line.strip()
                if line and len(line) > 2:
                    result["advertiser_entity"] = line
                    break

        # 如果 advertiser_entity 为空，尝试从"广告主："后面取
        if not result["advertiser_entity"]:
            adv_m = re.search(r"广告主\s*[:：]\s*([^\n]{2,120})", payer_text)
            if adv_m:
                result["advertiser_entity"] = adv_m.group(1).strip()

    # ===========================================================
    # F. 广告文本（视频链接后面的描述）
    # ===========================================================
    ad_text_m = re.search(r"(?:PLAY\.GOOGLE\.COM|ITUNES\.APPLE\.COM)[^\n]*\n([^\n]{4,500})", text)
    if ad_text_m:
        result["ad_text"] = ad_text_m.group(1).strip()
    else:
        # 兜底
        fallback = re.search(r"(?:PLAY\.GOOGLE\.COM|ITUNES\.APPLE\.COM)[^\n]*\n(.+)", text)
        if fallback:
            result["ad_text"] = fallback.group(1).strip()[:300]

    return result


def _clean_text(text, max_len=2000):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text
'''

# 拼接
new_content = content[:func_start] + NEW_FUNC.strip() + '\n' + content[region_start:]

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patched OK")