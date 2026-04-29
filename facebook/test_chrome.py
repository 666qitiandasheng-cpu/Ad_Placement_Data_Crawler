import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

print("Starting test...", flush=True)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    print("Imports OK", flush=True)

    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # 反检测
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    print("Installing ChromeDriver...", flush=True)
    service = Service(ChromeDriverManager().install())

    print("Launching Chrome...", flush=True)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)

    # 额外反检测
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    print("Navigating to Google...", flush=True)
    driver.get("https://www.google.com")

    print(f"Page loaded: {driver.title}", flush=True)
    driver.quit()
    print("Test passed!", flush=True)

except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc()