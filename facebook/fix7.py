import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

# Build replacement using actual Unicode characters
old_payer = (
    r'    # 广告主主体：在"广告主\n"之后的行（公司全名）'
    '\n        adidx = pblock.find("广告主\\n")'
    '\n        if adidx >= 0:'
    '\n            for line in pblock[adidx + 4:].split("\\n"):'
    '\n                line = line.strip()'
    '\n                if line and len(line) > 2:'
    '\n                    result["advertiser_entity"] = line'
    '\n                    break'
    '\n        if not result["advertiser_entity"]:'
    '\n            am = re.search(r"广告主\\s*[:：]\\s*([^\\n]{2,120})", pblock)'
    '\n            if am:'
    '\n                result["advertiser_entity"] = am.group(1).strip()'
)

new_payer = (
    r'    # 广告主主体：在"当前"之后找"广告主\n"才是真正的广告主行'
    '\n        curr_idx = pblock.find("当前")'
    '\n        after_curr = pblock[curr_idx + 2:] if curr_idx >= 0 else pblock'
    '\n        adidx = after_curr.find("广告主\\n")'
    '\n        if adidx >= 0:'
    '\n            for line in after_curr[adidx + 4:].split("\\n"):'
    '\n                line = line.strip()'
    '\n                if line and len(line) > 2:'
    '\n                    result["advertiser_entity"] = line'
    '\n                    break'
    '\n        if not result["advertiser_entity"]:'
    '\n            am = re.search(r"广告主\\s*[:：]\\s*([^\\n]{2,120})", pblock)'
    '\n            if am:'
    '\n                result["advertiser_entity"] = am.group(1).strip()'
)

if old_payer not in src:
    print("ERROR: old_payer not found")
    sys.exit(1)
src = src.replace(old_payer, new_payer, 1)
print("Payer section updated")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error: {e.msg} at line {e.lineno}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print("Done")