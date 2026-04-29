# -*- coding: utf-8 -*-
"""Fix: replace parse_detail_text in scrape_detail.py"""

import re, sys

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'

with open(DEST, 'rb') as f:
    raw = f.read()

# Find parse_detail_text - use bytes to avoid encoding issues
# It appears after "# ===..." 
func_idx = raw.find(b'def parse_detail_text')
region_idx = raw.find(b'def parse_region_block', func_idx + 100)
print(f"func_idx={func_idx}, region_idx={region_idx}")

if func_idx == -1 or region_idx == -1:
    print("ERROR")
    sys.exit(1)

# New function as bytes (Unicode escapes → actual bytes)
NEW_FUNC = b'''

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

    _B_AD_INFO = "\\u5e7f\\u544a\\u4fe1\\u606f\\u516c\\u793a\\uff08\\u6309\\u5730\\u533a\\uff09"
    _B_SPONSOR = "\\u5173\\u4e8e\\u5e7f\\u544a\\u8d5a\\u52a9\\u65b9"
    _B_ADVERTISER = "\\u5173\\u4e8e\\u5e7f\\u544a\\u4e3b"
    _B_PAYER = "\\u5e7f\\u544a\\u4e3b\\u548c\\u4ed8\\u8d39\\u65b9"
    _EU = "\\u6b27\\u76df"
    _UK = "\\u82f1\\u56fd"

    ad_info_start = text.find(_B_AD_INFO)
    sponsor_start = text.find(_B_SPONSOR)
    advertiser_start = text.find(_B_ADVERTISER)
    payer_start = text.find(_B_PAYER)

    # A. 头部
    head = text[:ad_info_start] if ad_info_start >= 0 else text[:400]
    if "\\u5df2\\u505c\\u6b62" in head:
        result["delivery_status"] = "\\u5df2\\u505c\\u6b62\\u6295\\u653e"
    elif "\\u6295\\u653e\\u4e2d" in head:
        result["delivery_status"] = "\\u6295\\u653e\\u4e2d"

    id_m = re.search(r"\\u8d44\\u6599\\u5e93\\u7f16\\u53f7\\uff1a(\\d+)", head)
    if id_m:
        result["account_id"] = id_m.group(1)

    period_m = re.search(
        r"(\\d{4}\\u5e74\\d{1,2}\\u6708\\d{1,2}\\u65e5)\\s*[-~]+\\s*(\\d{4}\\u5e74\\d{1,2}\\u6708\\d{1,2}\\u65e5)",
        head
    )
    if period_m:
        result["delivery_period"] = period_m.group(1) + " ~ " + period_m.group(2)

    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 3 or line in ("\\u5e7f\\u544a\\u8be6\\u60c5", "\\u5173\\u95ed",
                                      "\\u5df2\\u505c\\u6b62", "\\u5e73\\u53f0", "\\u8d5a\\u52a9\\u5185\\u5bb9"):
            continue
        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:
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
        result["about_sponsor"] = _clean_text(sp_block[len(_B_SPONSOR):].strip())

    # D. 关于广告主
    if advertiser_start >= 0:
        nxt = [x for x in [payer_start] if x > advertiser_start]
        adv_end = min(nxt) if nxt else len(text)
        adv_text = text[advertiser_start:adv_end][len(_B_ADVERTISER):].strip()
        result["advertiser_description"] = _clean_text(adv_text, max_len=300)

        acct_m = re.search(r"\\u7f16\\u53f7\\uff1a(\\d+)", adv_text)
        if acct_m:
            result["account_id"] = acct_m.group(1)

        flw_m = re.search(r"([\\d.]+)\\s*\\u4e07\\u4f4d?\\u7c89\\u4e1d", adv_text)
        if flw_m:
            result["followers"] = flw_m.group(1) + " \\u4e07"

        for kw in ["\\u7535\\u5b50\\u6e38\\u620f", "\\u7f51\\u7edc\\u6e38\\u620f",
                   "\\u98df\\u54c1", "\\u7f8e\\u5986", "\\u65e5\\u5316",
                   "\\u670d\\u88c5", "\\u8fd0\\u52a8", "\\u533b\\u7597",
                   "\\u6559\\u80b2", "\\u91d1\\u878d"]:
            if kw in adv_text:
                result["industry"] = kw
                break

        nm = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{2,80})", adv_text)
        if nm:
            result["advertiser_name"] = nm.group(1).strip()
        elif not result["advertiser_name"]:
            first = adv_text.split("\\n")[0].strip()
            if first and len(first) > 1:
                result["advertiser_name"] = first[:80]

    # E. 广告主和付费方
    if payer_start >= 0:
        pblock = text[payer_start:][len(_B_PAYER):].strip()

        # 付费方
        pm = re.search(r"\\u4ed8\\u8d39\\u65b9\\s*[:\\uff1a]?\\s*([^\\n]{2,120})", pblock)
        if pm:
            result["payer_name"] = pm.group(1).strip()
        else:
            pidx = pblock.find("\\u4ed8\\u8d39\\u65b9")
            if pidx >= 0:
                for line in pblock[pidx + 3:].lstrip("\\n ").split("\\n"):
                    line = line.strip()
                    if line and len(line) > 2:
                        result["payer_name"] = line
                        break

        # 广告主主体
        adidx = pblock.find("\\u5e7f\\u544a\\u4e3b\\n")
        if adidx >= 0:
            for line in pblock[adidx + 4:].split("\\n"):
                line = line.strip()
                if line and len(line) > 2:
                    result["advertiser_entity"] = line
                    break
        if not result["advertiser_entity"]:
            am = re.search(r"\\u5e7f\\u544a\\u4e3b\\s*[:\\uff1a]\\s*([^\\n]{2,120})", pblock)
            if am:
                result["advertiser_entity"] = am.group(1).strip()

    # F. 广告文本
    at_m = re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)[^\\n]*\\n([^\\n]{4,500})", text)
    if at_m:
        result["ad_text"] = at_m.group(1).strip()

    return result


def _clean_text(text, max_len=2000):
    if not text:
        return ""
    text = re.sub(r"\\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text
'''

new_data = raw[:func_idx] + NEW_FUNC + raw[region_idx:]

with open(DEST, 'wb') as f:
    f.write(new_data)

print("Patched OK")