# -*- coding: utf-8 -*-
"""Fix: head loop advertiser_name extraction + payer_name advertiser_entity swap"""
import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

# ---- Fix 1: Head loop skips date lines and finds "Block Blast" ----
old_head = '''    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 3 or line in ("\\u5e7f\\u544a\\u8be6\\u60c5", "\\u5173\\u95ed",
                                      "\\u5df2\\u505c\\u6b62", "\\u5e73\\u53f0", "\\u8d5a\\u52a9\\u5185\\u5bb9"):
            continue
        # 跳过资料库编号、赞助内容标记等干扰行
        if "\\u8d44\\u6599\\u5e93\\u7f16\\u53f7" in line or "\\u8d5a\\u52a9\\u5185\\u5bb9" in line:
            continue
        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break'''

new_head = '''    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 2:
            continue
        # 跳过纯数字、资料库编号、日期、平台、赞助内容、空行
        if re.match(r"^\d+$", line):  # 纯数字（资料库编号行）
            continue
        if re.match(r"^\d{4}年", line):  # 日期行
            continue
        if "\\u8d44\\u6599\\u5e93\\u7f16\\u53f7" in line:
            continue
        if line in ("\\u5e7f\\u544a\\u8be6\\u60c5", "\\u5173\\u95ed",
                    "\\u5df2\\u505c\\u6b62", "\\u5e73\\u53f0",
                    "\\u8d5a\\u52a9\\u5185\\u5bb9", "\\u6253\\u5f00\\u4e0b\\u62c9\\u83dc\\u5355",
                    "\\u200b", "\\u0"):
            continue
        # 找含英文字母的标题行（广告主名称）
        if re.search(r"[A-Za-z]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break'''

if old_head not in src:
    print("ERROR: old_head not found")
    sys.exit(1)
src = src.replace(old_head, new_head, 1)
print("Head loop fixed")

# ---- Fix 2: payer_name and advertiser_entity are swapped ----
# In the payer section, the first entity after "广告主\n" is Beijing... (advertiser_entity)
# and the first entity after "付费方\n" is MeetSocial... (payer_name)
old_payer = '        # 广告主主体：找"广告主\\n"后面紧跟的非空行\n        adidx = pblock.find("广告主\\n")\n        if adidx >= 0:\n            for line in pblock[adidx + 4:].split("\\n"):\n                line = line.strip()\n                if line and len(line) > 2:\n                    result["advertiser_entity"] = line\n                    break'
new_payer = '        # 广告主主体：在"广告主\\n"之后的行（公司全名）\n        adidx = pblock.find("\\u5e7f\\u544a\\u4e3b\\n")\n        if adidx >= 0:\n            for line in pblock[adidx + 4:].split("\\n"):\n                line = line.strip()\n                if line and len(line) > 3:\n                    result["advertiser_entity"] = line\n                    break'

if old_payer not in src:
    print("ERROR: old_payer not found")
    sys.exit(1)
src = src.replace(old_payer, new_payer, 1)
print("Payer section fixed")

# Verify syntax
try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print("All fixes applied OK")