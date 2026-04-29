import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("[START] Testing scrape_detail.py...", flush=True)

# Read the input file
input_file = r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\ads_Block_Blast_2026-04-29.json"
print(f"[FILE] Reading {input_file}", flush=True)
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
ads = data.get('ads', [])
print(f"[LOAD] {len(ads)} ads found", flush=True)

# Test ChromeDriver
print("[CHROME] Launching...", flush=True)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-blink-features=AutomationControlled')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)
driver.set_page_load_timeout(30)
driver.implicitly_wait(5)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})
print("[CHROME] Launched!", flush=True)

# Navigate to first ad
lid = ads[0]['library_id']
url = f"https://www.facebook.com/ads/library/?id={lid}"
print(f"[NAV] Going to {url}", flush=True)
driver.get(url)
print(f"[TITLE] {driver.title}", flush=True)

# Save output
print("[DONE] Test passed!", flush=True)
driver.quit()