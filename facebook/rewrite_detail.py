"""
重写 scrape_ad_detail 函数
"""
import re

# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new function
new_function = '''# ============================================================
# 【详情页抓取】
# ============================================================

def scrape_ad_detail(driver, library_id, wait_sec=8):
    """访问详情页提取更多信息（包括4个展开块）"""
    detail_url = f"https://www.facebook.com/ads/library/?id={library_id}"
    
    detail_data = {
        "library_id": library_id,
        "detail_url": detail_url,
        "ad_text": "",
        "start_date": "",
        "end_date": "",
        "delivery_status": "",
        "ad_disclosure_regions": [],  # 广告信息公示（按地区）
        "age_range": "",
        "gender": "",
        "reach_count": "",
        "advertiser_name": "",  # 关于广告主
        "advertiser_description": "",  # 关于广告主描述
        "payer_name": "",  # 广告主和付费方
        "creative_data": {},
        "raw_detail_text": "",
        # 4个展开块的详细内容
        "block_ad_disclosure": {},  # 广告信息公示（按地区）
        "block_about_sponsor": {},  # 关于广告赞助方
        "block_about_advertiser": {},  # 关于广告主
        "block_advertiser_payer": {},  # 广告主和付费方
    }
    
    try:
        driver.get(detail_url)
        time.sleep(wait_sec)
        
        # 点击"查看广告详情"按钮（如果存在）
        view_detail_selectors = [
            "//span[contains(text(), '查看广告详情')]",
            "//div[contains(text(), '查看广告详情')]",
            "//a[contains(text(), '查看广告详情')]",
            "//button[contains(text(), '查看广告详情')]",
        ]
        for selector in view_detail_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for el in elements:
                    if '查看广告详情' in el.text.strip():
                        safe_click(driver, el)
                        time.sleep(3)
                        break
            except Exception:
                continue
        
        # 等待页面加载完成
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        
        time.sleep(3)
        
        # 查找并点击4个展开块
        expandable_blocks = {
            "block_ad_disclosure": [
                "//div[contains(text(), '广告信息公示')]",
                "//div[contains(text(), '按地区')]",
                "//span[contains(text(), '广告信息公示')]",
            ],
            "block_about_sponsor": [
                "//div[contains(text(), '关于广告赞助方')]",
                "//span[contains(text(), '关于广告赞助方')]",
            ],
            "block_about_advertiser": [
                "//div[contains(text(), '关于广告主')]",
                "//span[contains(text(), '关于广告主')]",
            ],
            "block_advertiser_payer": [
                "//div[contains(text(), '广告主和付费方')]",
                "//span[contains(text(), '广告主和付费方')]",
            ],
        }
        
        # 依次点击每个块并提取内容
        for block_name, selectors in expandable_blocks.items():
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for el in elements:
                        try:
                            safe_click(driver, el)
                            time.sleep(2)
                        except Exception:
                            pass
                        
                        try:
                            parent = el.find_element(By.XPATH, "..")
                            expanded_content = None
                            try:
                                expanded_content = parent.find_element(By.XPATH, "following-sibling::*[contains(@class, 'expand') or contains(@class, 'content')]")
                            except Exception:
                                pass
                            
                            if not expanded_content:
                                try:
                                    expanded_content = parent.find_element(By.XPATH, ".//div[contains(@class, 'content') or contains(@class, 'detail')]")
                                except Exception:
                                    pass
                            
                            if expanded_content:
                                content_text = expanded_content.text
                                if content_text:
                                    detail_data[block_name]["content"] = content_text
                                    print(f"[详情] {block_name}: {content_text[:100]}...", flush=True)
                                    break
                        except Exception:
                            pass
                        
                        try:
                            visible_text = el.text
                            if visible_text and len(visible_text) > 10:
                                detail_data[block_name]["visible_text"] = visible_text
                        except Exception:
                            pass
                        
                except Exception:
                    continue
        
        # 获取完整页面文本
        try:
            body_element = driver.find_element(By.TAG_NAME, "body")
            full_text = body_element.text
            detail_data["raw_detail_text"] = full_text
        except Exception:
            pass
        
        # 提取通用字段
        lines = full_text.split('\\n')
        
        # 性别
        if not detail_data["gender"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['性别：', '性别:', 'Gender：', 'Gender:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2 and parts[1].strip():
                                detail_data["gender"] = parts[1].strip()
                                break
                    if detail_data["gender"]:
                        break
        
        if not detail_data["gender"]:
            if 'All genders' in full_text or '性别不限' in full_text:
                detail_data["gender"] = "不限"
        
        # 年龄
        if not detail_data["age_range"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['年龄：', '年龄:', 'Age：', 'Age:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2:
                                detail_data["age_range"] = parts[1].strip()
                                break
                    if detail_data["age_range"]:
                        break
        
        # 覆盖人数
        if not detail_data["reach_count"]:
            for line in lines:
                line_stripped = line.strip()
                if any(kw in line_stripped for kw in ['覆盖：', '覆盖:', '覆盖人数', 'Reached：', 'Reached:']):
                    for sep in ['：', ':']:
                        if sep in line_stripped:
                            parts = line_stripped.split(sep, 1)
                            if len(parts) >= 2:
                                detail_data["reach_count"] = parts[1].strip()
                                break
                    if detail_data["reach_count"]:
                        break
        
        # 广告文案
        text_blocks = re.findall(r'[\\u4e00-\\u9fa5a-zA-Z0-9\\s.,!?;:]{20,200}', full_text)
        for block in text_blocks:
            block = block.strip()
            if any(kw in block for kw in ['性别', '年龄', '覆盖', '投放', '广告主', '赞助', '付费', 'Gender', 'Age', 'Reach']):
                continue
            if len(block) > len(detail_data["ad_text"]):
                detail_data["ad_text"] = block
        
        # 日期
        date_patterns = [
            r'(?:首次投放|First shown|开始投放)\\s*[:：]?\\s*(\\d{4}[-/]\\d{2}[-/]\\d{2})',
            r'(?:结束日期|Ended|Ends)\\s*[:：]?\\s*(\\d{4}[-/]\\d{2}[-/]\\d{2})',
        ]
        for pattern in date_patterns:
            m = re.search(pattern, full_text)
            if m:
                if not detail_data["start_date"]:
                    detail_data["start_date"] = m.group(1)
                else:
                    detail_data["end_date"] = m.group(1)
        
    except Exception as e:
        print(f"[详情] 解析异常: {e}", flush=True)
    
    return detail_data'''

# Find the start and end of the old function
start_marker = '# ============================================================\n# 【详情页抓取】\n# ============================================================'
end_marker = '# ============================================================\n# 【文件处理】'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find markers. start_idx={start_idx}, end_idx={end_idx}")
else:
    # Replace
    new_content = content[:start_idx] + new_function + '\n\n' + content[end_idx:]
    
    # Write back
    with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Done! Function replaced successfully.")
