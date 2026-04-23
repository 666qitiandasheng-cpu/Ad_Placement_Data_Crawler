#!/usr/bin/env python3
"""
快速测试详情页抓取
"""
import sys
import os
import time
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper')

# 设置为可见浏览器方便调试
import run
run.HEADLESS = False

# 测试单个广告
test_ad_id = "25763115839960996"

print(f"测试详情页抓取: {test_ad_id}")

driver = None
try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    
    driver = run.make_driver(headless=False)
    detail_data = run.scrape_ad_detail(driver, test_ad_id, wait_sec=5)
    
    print(f"\n=== 详情数据 ===")
    print(f"library_id: {detail_data.get('library_id')}")
    print(f"ad_text: {detail_data.get('ad_text', '')[:100]}...")
    print(f"start_date: {detail_data.get('start_date')}")
    print(f"gender: {detail_data.get('gender')}")
    print(f"age_range: {detail_data.get('age_range')}")
    print(f"reach_count: {detail_data.get('reach_count')}")
    print(f"\n4个展开块:")
    for block_name in ['block_ad_disclosure', 'block_about_sponsor', 'block_about_advertiser', 'block_advertiser_payer']:
        block_data = detail_data.get(block_name, {})
        if block_data:
            print(f"  {block_name}: {str(block_data)[:100]}...")
        else:
            print(f"  {block_name}: (empty)")
    
    print(f"\nraw_detail_text 长度: {len(detail_data.get('raw_detail_text', ''))}")
    
    input("\n按回车键关闭浏览器...")
    
finally:
    if driver:
        driver.quit()
