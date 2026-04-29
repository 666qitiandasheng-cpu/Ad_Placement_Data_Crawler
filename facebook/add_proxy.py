import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(DEST, 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Add proxy config before CONFIG section ──
ANCHOR = '\n# ====== CONFIG ======\nHEADLESS = False\n'
PROXY_CONFIG = '''# ====== 代理配置（根据你的梯子端口修改）====================
PROXY_SERVER = "http://127.0.0.1:7890"   # ← 改成你的代理地址，7890 是 Clash 默认端口

# ====== CONFIG ======
HEADLESS = False
'''

if ANCHOR not in src:
    print("ERROR: CONFIG anchor not found")
    sys.exit(1)
src = src.replace(ANCHOR, PROXY_CONFIG, 1)
print("Proxy constant added")

# ── 2. Selenium make_driver: add --proxy-server argument ──
SEL_ANCHOR = '        opts.add_argument("--disable-gpu")\n'
SEL_ADD = '        opts.add_argument(f"--proxy-server={PROXY_SERVER}")\n'
if SEL_ANCHOR not in src:
    print("ERROR: Selenium anchor not found")
    sys.exit(1)
src = src.replace(SEL_ANCHOR, SEL_ADD + SEL_ANCHOR, 1)
print("Selenium proxy added")

# ── 3. Playwright CDP: add proxy to browser.new_page() ──
PW_ANCHOR = '        page = browser.new_page()\n        page.goto(f"https://www.facebook.com'
PW_REPLACE = '        page = browser.new_page(proxy={"server": PROXY_SERVER})\n        page.goto(f"https://www.facebook.com'
if PW_ANCHOR not in src:
    print("ERROR: Playwright anchor not found")
    sys.exit(1)
src = src.replace(PW_ANCHOR, PW_REPLACE, 1)
print("Playwright proxy added")

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)
print("Done")
