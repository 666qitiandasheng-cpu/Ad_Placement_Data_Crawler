with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py', 'r', encoding='utf-8') as f:
    src = f.read()

a1 = '        page = browser.new_page()\n        page.goto'
a2 = '        opts.add_argument("--disable-gpu")'
a3 = '\n# ====== CONFIG ======\nHEADLESS = False\n'

print('Playwright anchor found:', a1 in src)
print('Selenium anchor found:', a2 in src)
print('CONFIG anchor found:', a3 in src)

idx = src.find(a1)
if idx >= 0:
    print('Playwright context:', repr(src[idx-30:idx+80]))
