# -*- coding: utf-8 -*-
"""Fix 3 bugs in parse_detail_text"""
import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'

with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

# ---- Bug 1: advertiser_name 误取"资料库编号：..." ----
old1 = '        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:\n            result["advertiser_name"] = line\n            break'
new1 = '        if "\\u8d44\\u6599\\u5e93\\u7f16\\u53f7" in line or "\\u8d5a\\u52a9\\u5185\\u5bb9" in line:\n            continue\n        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:\n            result["advertiser_name"] = line\n            break'
if old1 not in src:
    print("ERROR: old1 not found")
    sys.exit(1)
src = src.replace(old1, new1, 1)
print("Bug 1 patched")

# ---- Bug 2: payer_name 误取"的详细信息。" ----
old2 = '        # 付费方：找"付费方"后面紧跟的非空行\n        pm = re.search(r"付费方\\s*[:：]?\\s*([^\\n]{2,120})", pblock)\n        if pm:\n            result["payer_name"] = pm.group(1).strip()\n        else:\n            pidx = pblock.find("付费方")\n            if pidx >= 0:\n                for line in pblock[pidx + 3:].lstrip("\\n ").split("\\n"):\n                    line = line.strip()\n                    if line and len(line) > 2:\n                        result["payer_name"] = line\n                        break'
new2 = '        # 付费方：结构为 "付费方\\nMeetSocial..."，直接匹配下一行\n        pm = re.search(r"\\u4ed8\\u8d39\\u65b9\\n([^\\n]{2,120})", pblock)\n        if pm:\n            result["payer_name"] = pm.group(1).strip()'
if old2 not in src:
    print("ERROR: old2 not found")
    sys.exit(1)
src = src.replace(old2, new2, 1)
print("Bug 2 patched")

# ---- Bug 3: ad_text 提取到 emoji ----
old3 = '    at_m = re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)[^\\n]*\\n([^\\n]{4,500})", text)\n    if at_m:\n        result["ad_text"] = at_m.group(1).strip()'
new3 = '    # 广告文本：视频链接行之后，找第一行含英文描述的文字\n    lines = text.split("\\n")\n    for i, line in enumerate(lines):\n        if re.search(r"(?:PLAY\\.GOOGLE\\.COM|ITUNES\\.APPLE\\.COM)", line):\n            for j in range(i + 1, min(i + 6, len(lines))):\n                nxt = lines[j].strip()\n                if len(nxt) >= 4 and re.search(r"[A-Za-z]", nxt):\n                    result["ad_text"] = nxt\n                    break\n            break'
if old3 not in src:
    print("ERROR: old3 not found")
    sys.exit(1)
src = src.replace(old3, new3, 1)
print("Bug 3 patched")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print("All done!")