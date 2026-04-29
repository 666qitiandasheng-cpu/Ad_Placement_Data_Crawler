import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: head loop - use actual newlines not \n in string literals
# Find the head loop and replace
old_head = '''    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 3 or line in ("广告详情", "关闭", "已停止", "平台", "赞助内容"):
            continue
        if "\\u8d44\\u6599\\u5e93\\u7f16\\u53f7" in line or "\\u8d5a\\u52a9\\u5185\\u5bb9" in line:
            continue
        if re.search(r"[A-Za-z0-9]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break'''

new_head = '''    for line in head.split("\\n"):
        line = line.strip()
        if len(line) < 2:
            continue
        # 跳过日期行、纯数字行、资料库编号行
        if re.match(r"^\\d+$", line):
            continue
        if re.match(r"^\\d{4}年", line):
            continue
        if "\\u8d44\\u6599\\u5e93\\u7f16\\u53f7" in line:
            continue
        if line in ("广告详情", "关闭", "已停止", "平台", "赞助内容", "打开下拉菜单", "\\u200b"):
            continue
        if re.search(r"[A-Za-z]", line) and len(line) < 80:
            result["advertiser_name"] = line
            break'''

if old_head not in src:
    print("ERROR: old_head not found")
    sys.exit(1)
src = src.replace(old_head, new_head, 1)
print("Head loop fixed")

# Fix 2: payer section advertiser_entity - use raw \n not \\n in pblock.find
old_payer = '        adidx = pblock.find("广告主\\n")\n        if adidx >= 0:\n            for line in pblock[adidx + 4:].split("\\n"):'
new_payer = '        adidx = pblock.find("\\u5e7f\\u544a\\u4e3b\\n")\n        if adidx >= 0:\n            for line in pblock[adidx + 4:].split("\\n"):'

if old_payer not in src:
    print("ERROR: old_payer not found")
    sys.exit(1)
src = src.replace(old_payer, new_payer, 1)
print("Payer section fixed")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print("All done")