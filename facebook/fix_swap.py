import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

old = '\n    return result\n\n\ndef _clean_text_new(text, max_len'
new = '''
    # 修正：广告1原始数据里"广告主"和"付费方"顺序反了
    # 当 advertiser_entity 是 MeetSocial 时说明它是付费方，需要交换
    if result["advertiser_entity"] and result["advertiser_entity"].startswith("MeetSocial"):
        result["advertiser_entity"], result["payer_name"] = result["payer_name"], result["advertiser_entity"]

    return result


def _clean_text_new(text, max_len'''

if old not in src:
    print("ERROR: anchor not found")
    sys.exit(1)
src = src.replace(old, new, 1)
print("Swap fix inserted")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)
print("Done")
