import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

old_return = '    return result\n\n\ndef _clean_text_new(text, max_len'
new_return = '''    # 如果广告主主体是 MeetSocial，说明"广告主"和"付费方"顺序反了，交换
    if result["advertiser_entity"] and result["advertiser_entity"].startswith("MeetSocial"):
        result["advertiser_entity"], result["payer_name"] = result["payer_name"], result["advertiser_entity"]

    return result


def _clean_text_new(text, max_len'''

if old_return not in src:
    print("ERROR: old_return not found")
    sys.exit(1)
src = src.replace(old_return, new_return, 1)
print("Swap fix added")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print("Done")