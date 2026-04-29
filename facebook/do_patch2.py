# -*- coding: utf-8 -*-
"""直接写入新的 parse_detail_text 到 scrape_detail.py"""

import re, sys

PATH = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

func_start = content.find('\ndef parse_detail_text(')
region_start = content.find('\ndef parse_region_block(', func_start)
print(f"func_start={func_start}, region_start={region_start}")

# 使用普通字符串（不用 f-string，不用 r-string，避免转义问题）
new_func = """
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

    # ---- A. 头部 ----
    head = text[:ad_info_start] if ad_info_start >= 0 else text[:400]
    if "已停止" in head:
        result["delivery_status"] = "已停止投放"
    elif "投放中" in head:
        result["delivery_status"] = "投放中"

    id_m = re.search(r"资料库编号：(\\d+)", head)
    if id_m:
        result["account_id"] = id_m.group(1)

    period_m = re.search(r"(\\d{4}年\\d{1,2}月\\d{1,2}日)\\s*[-~]+\\s*(\\d{4}年\\d{1,2}月\\d{1,2}日)", head)
    if period_m:
        result["delivery_period"] = period_m.group(1) + " ~ " + period_m.group(2)

    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 3 or line in ("广告详情", "关闭", "已停止", "平台", "赞助内容"):
            continue
        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break

    # ---- B. 广告信息公示（按地区）----
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

    # ---- C. 关于广告赞助方 ----
    if sponsor_start >= 0:
        nxt = [x for x in [advertiser_start, payer_start] if x > sponsor_start]
        sp_end = min(nxt) if nxt else len(text)
        sp_text = text[sponsor_start:sponsor_end]
        result["about_sponsor"] = _clean(sp_text[len(_B_SPONSOR):].strip())

    # ---- D. 关于广告主 ----
    if advertiser_start >= 0:
        nxt = [x for x in [payer_start] if x > advertiser_start]
        adv_end = min(nxt) if nxt else len(text)
        adv_text = text[advertiser_start:adv_end][len(_B_ADVERTISER):].strip()
        result["advertiser_description"] = _clean(adv_text, max_len=300)

        acct_m = re.search(r"编号：(\\d+)", adv_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        flw_m = re.search(r"([\\d.]+)\\s*万位?粉丝", adv_text)
        if flw_m:
            result["followers"] = flw_m.group(1) + " 万"

        for kw in ["电子游戏", "网络游戏", "手机游戏", "食品", "美妆", "日化", "服装", "运动", "医疗", "教育", "金融"]:
            if kw in adv_text:
                result["industry"] = kw
                break

        nm = re.search(r"广告主\\s*[:：]\\s*([^\\n]{2,80})", adv_text)
        if nm:
            result["advertiser_name"] = nm.group(1).strip()
        elif not result["advertiser_name"]:
            first = adv_text.split("\\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # ---- E. 广告主和付费方 ----
    if payer_start >= 0:
        pblock = text[payer_start:][len(_B_PAYER):].strip()

        # 付费方
        pm = re.search(r"付费方\\s*[:：]?\\s*([^\\n]{2,120})", pblock)
        if pm:
            result["payer_name"] = pm.group(1).strip()
        else:
            pidx = pblock.find("付费方")
            if pidx >= 0:
                for line in pblock[pidx + 3:].lstrip("\\n ").split("\\n"):
                    line = line.strip()
                    if line and len(line) > 2:
                        result["payer_name"] = line
                        break

        # 广告主主体
        adidx = pblock.find("广告主\\n")
        if adidx >= 0:
            for line in pblock[adidx + 4:].split("\\n"):
                line = line.strip()
                if line and len(line) > 2:
                    result["advertiser_entity"] = line
                    break
        if not result["advertiser_entity"]:
            am = re.search(r"广告主\\s*[:：]\\s*([^\\n]{2,120})", pblock)
            if am:
                result["advertiser_entity"] = am.group(1).strip()

    # ---- F. 广告文本 ----
    at_m = re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)[^\\n]*\\n([^\\n]{4,500})", text)
    if at_m:
        result["ad_text"] = at_m.group(1).strip()

    return result


def _clean(text, max_len=2000):
    if not text:
        return ""
    text = re.sub(r"\\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text
"""

new_content = content[:func_start] + new_func + "\n" + content[region_start:]
with open(PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Done")