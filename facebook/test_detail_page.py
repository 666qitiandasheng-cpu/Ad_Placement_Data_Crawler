#!/usr/bin/env python3
"""
测试 Facebook Ad Library 详情页结构
"""
import time
import sys
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper')

from run import make_driver, HEADLESS

# 测试详情页 URL
test_ad_id = "25763115839960996"
detail_url = f"https://www.facebook.com/ads/library/?id={test_ad_id}"

print(f"测试详情页: {detail_url}")

driver = make_driver(headless=False)  # 可见浏览器方便观察
try:
    driver.get(detail_url)
    time.sleep(5)
    
    # 打印页面标题
    print(f"页面标题: {driver.title}")
    
    # 查找"查看广告详情"按钮
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # 尝试多种方式查找按钮
    button_selectors = [
        "//span[contains(text(), '查看广告详情')]",
        "//div[contains(text(), '查看广告详情')]",
        "//a[contains(text(), '查看广告详情')]",
        "//button[contains(text(), '查看广告详情')]",
        "//span[contains(text(), 'View Ad Details')]",
        "//div[contains(text(), 'View Ad Details')]",
    ]
    
    for selector in button_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"找到按钮: {selector}")
                for el in elements:
                    print(f"  元素: {el.tag_name} - {el.text[:50]}")
                break
        except:
            pass
    
    # 查找右侧面板中的可展开元素
    expandable_selectors = [
        "//div[contains(@class, 'Expandable')]",
        "//div[contains(text(), '广告信息公示')]",
        "//div[contains(text(), '关于广告赞助方')]",
        "//div[contains(text(), '关于广告主')]",
        "//div[contains(text(), '广告主和付费方')]",
    ]
    
    print("\n查找可展开元素:")
    for selector in expandable_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"  {selector}: 找到 {len(elements)} 个")
        except:
            pass
    
    # 等待页面加载
    time.sleep(3)
    
    # 截图保存
    driver.save_screenshot(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\detail_page.png')
    print("\n截图已保存: detail_page.png")
    
    # 获取页面源码
    page_source = driver.page_source
    with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\detail_page_source.html', 'w', encoding='utf-8') as f:
        f.write(page_source)
    print(f"页面源码已保存: detail_page_source.html ({len(page_source)} 字符)")
    
finally:
    input("按回车关闭浏览器...")
    driver.quit()
