def scrape_tiktok_detail_page(driver, ad_id, wait_sec):
    """
    访问 TikTok 广告详情页（https://library.tiktok.com/ads/detail/?ad_id=xxx）
    提取页面上的详细信息（公司信息、投放数据、受众覆盖等）

    参数:
        driver:    Selenium 浏览器实例
        ad_id:     广告 ID
        wait_sec:  打开详情页后等待秒数

    返回:
        详情页抓取的字典数据，包含所有字段；提取失败返回空字典
    """
    detail_url = f"https://library.tiktok.com/ads/detail/?ad_id={ad_id}"
    data = {
        "ad_id": ad_id,
        "detail_url": detail_url,
        "scrape_time": datetime.now().isoformat(),
        # 基本信息
        "advertiser_name": "",
        "advertiser_description": "",
        "ad_text": "",
        # 投放信息
        "first_seen": "",
        "last_seen": "",
        "delivery_status": "",
        "active_ad_delivery": "",
        # 受众
        "target_audience_size": "",
        "gender_summary": "",
        "age_summary": "",
        "gender_detail": {},   # {country: {male: bool, female: bool, unknown: bool}}
        "age_detail": {},      # {country: {13-17: bool, 18-24: bool, ...}}
        "locations": [],
        "locations_detail": {},
        "language": "",
        # 覆盖
        "unique_users": "",
        "impressions": "",
        # 创意
        "video_url": "",
        "thumbnail_url": "",
        # 原始文本
        "raw_text": "",
    }

    try:
        from bs4 import BeautifulSoup

        driver.get(detail_url)
        time.sleep(wait_sec)

        # 获取页面源码
        html = driver.page_source

        # 获取页面文本
        body = driver.find_element(By.TAG_NAME, "body")
        full_text = body.text
        data["raw_text"] = full_text

        # 解析 HTML
        soup = BeautifulSoup(html, "html.parser")

        # ==================== 提取基本信息 ====================

        # ---- 广告文本（赞助内容）----
        lines = full_text.split('\n')
        in_sponsored = False
        sponsored_parts = []
        skip_keys = {'advertiser', 'active', 'delivery', 'status', 'seen', 'gender',
                     'age', 'location', 'language', 'unique', 'impression', 'first',
                     'last', 'meta', 'tiktok', 'learn more', 'see more', 'additional',
                     'audience', 'number', 'country', 'target'}
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 3:
                continue
            if 'sponsor' in stripped.lower():
                in_sponsored = True
                continue
            if in_sponsored:
                if stripped.lower() in skip_keys or any(k in stripped.lower() for k in skip_keys):
                    continue
                if len(stripped) > 5:
                    sponsored_parts.append(stripped)
        if sponsored_parts:
            data["ad_text"] = ' '.join(sponsored_parts)[:800]

        # ---- 公司名 ----
        advertiser_m = re.search(r'Advertiser\s+([^\n]+?)\s+See all', full_text)
        if advertiser_m:
            data["advertiser_name"] = advertiser_m.group(1).strip()
        else:
            advertiser_m2 = re.search(r'Ad paid for by\s+([^\n]+?)\s+Advertiser', full_text)
            if advertiser_m2:
                data["advertiser_name"] = advertiser_m2.group(1).strip()

        # ---- 首次/最后投放时间 ----
        first_m = re.search(r'First shown:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if first_m:
            data["first_seen"] = first_m.group(1)
        last_m = re.search(r'Last shown:\s*(\d{2}/\d{2}/\d{4})', full_text)
        if last_m:
            data["last_seen"] = last_m.group(1)

        # ---- 投放状态 ----
        status_m = re.search(r'Delivery status\s+(\w+)', full_text)
        if status_m:
            data["delivery_status"] = status_m.group(1)
        if 'Active ad' in full_text or 'active ad' in full_text.lower():
            data["active_ad_delivery"] = "Yes"
        elif 'Not active' in full_text:
            data["active_ad_delivery"] = "No"

        # ---- 目标观众人数 ----
        audience_m = re.search(r'Target audience size\s+([\d\.,]+[MBK]?-?[\d\.,]+[MBK]?)', full_text, re.IGNORECASE)
        if audience_m:
            data["target_audience_size"] = audience_m.group(1).strip()
        else:
            audience_m2 = re.search(r'Target audience size\s+([^\n]+)', full_text)
            if audience_m2:
                data["target_audience_size"] = audience_m2.group(1).strip().split('\n')[0]

        # ---- Gender / Age / Location 表格解析（HTML） ----
        # 查找所有 targeting 表格
        targeting_tables = soup.find_all("table", role="table")

        # 打勾颜色常量
        CHECK_COLOR = "#FE2C55"   # 粉色 = 勾选
        UNCHECK_COLOR = "rgba(22, 24, 35, 0.34)"  # 灰色 = 未勾选

        def is_checked(svg_tag):
            """检查 SVG 是否表示勾选状态"""
            if not svg_tag or not svg_tag.get("fill"):
                return False
            color = svg_tag.get("fill", "")
            # 如果 fill="currentColor" 且有 color 属性
            if color.lower() == "currentcolor":
                color = svg_tag.get("color", "") or ""
            return CHECK_COLOR.lower() in color.lower()

        def parse_targeting_table(table, col_headers):
            """
            解析 targeting 表格，返回 (country_rows, global_flags)
            country_rows: [(country_name, {col_name: checked_bool}), ...]
            global_flags: {col_name: checked_bool} 如果是第一行是全局勾选框
            """
            rows = table.find_all("tr", role="row")
            if not rows:
                return [], {}

            results = []
            global_flags = {}

            # 解析表头
            header_row = rows[0]
            header_cols = header_row.find_all(["th", "td"])
            col_count = len(col_cols) if (col_cols := header_row.find_all("th", scope="col")) > 0 else len(header_cols)

            # 检查第一行是否是全局勾选（没有国家名列）
            first_data_row = rows[1] if len(rows) > 1 else None
            if first_data_row:
                cells = first_data_row.find_all("td", role="cell")
                if cells and cells[0].get("aria-colindex") == "1":
                    first_cell_text = cells[0].get_text(strip=True)
                    if not first_cell_text.isdigit():
                        # 第一行是全局勾选行，不是国家
                        for cell in cells:
                            col_idx = int(cell.get("aria-colindex", 0)) - 1
                            if col_idx < len(col_headers):
                                svg = cell.find("svg")
                                global_flags[col_headers[col_idx]] = is_checked(svg)

            # 解析每个国家的数据行
            for row in rows[1:]:
                cells = row.find_all("td", role="cell")
                if not cells:
                    continue
                # 第一列是序号，第二列是国家名
                country_name = ""
                row_data = {}
                for cell in cells:
                    col_idx = int(cell.get("aria-colindex", 0)) - 1
                    if col_idx == 1:
                        # 国家名列
                        country_name = cell.get_text(strip=True)
                    elif col_idx >= 2 and col_idx - 2 < len(col_headers):
                        svg = cell.find("svg")
                        row_data[col_headers[col_idx - 2]] = is_checked(svg)
                    elif col_idx < len(col_headers):
                        svg = cell.find("svg")
                        row_data[col_headers[col_idx]] = is_checked(svg)
                if country_name:
                    results.append((country_name, row_data))

            return results, global_flags

        # 遍历所有 targeting 表格，找到 Gender / Age / Location
        for table in targeting_tables:
            # 检查表头，确定表格类型
            header_row = table.find("thead")
            if not header_row:
                continue
            header_cells = header_row.find_all("th", scope="col")
            header_titles = [th.get_text(strip=True) for th in header_cells]

            header_set = set(header_titles)

            # Gender 表格检测：包含 Male, Female, Unknown gender
            gender_cols = [h for h in header_titles if h in ("Male", "Female", "Unknown gender")]
            if gender_cols and len(gender_cols) >= 2:
                # 这是 Gender 表格
                country_rows, global_flags = parse_targeting_table(table, gender_cols)

                # 汇总性别勾选：只要有一个国家勾选了就算有
                has_male = global_flags.get("Male", False)
                has_female = global_flags.get("Female", False)
                has_unknown = global_flags.get("Unknown gender", False)

                # 如果没有全局标志，从国家行汇总
                if not global_flags:
                    for country, row_data in country_rows:
                        has_male = has_male or row_data.get("Male", False)
                        has_female = has_female or row_data.get("Female", False)
                        has_unknown = has_unknown or row_data.get("Unknown gender", False)
                        data["gender_detail"][country] = row_data

                # 生成 gender_summary
                all_checked = has_male and has_female and has_unknown
                if all_checked:
                    data["gender_summary"] = "不限"
                elif has_male and has_female:
                    data["gender_summary"] = "Male, Female"
                elif has_male and has_unknown:
                    data["gender_summary"] = "Male, Unknown gender"
                elif has_female and has_unknown:
                    data["gender_summary"] = "Female, Unknown gender"
                elif has_male:
                    data["gender_summary"] = "Male only"
                elif has_female:
                    data["gender_summary"] = "Female only"
                elif has_unknown:
                    data["gender_summary"] = "Unknown gender only"
                else:
                    data["gender_summary"] = "不限"

            # Age 表格检测：包含年龄范围如 13-17, 18-24, 25-34, 35-44, 45-54, 55+
            age_range_cols = [h for h in header_titles if re.match(r'\d+-\d+\+?', h)]
            if age_range_cols and len(age_range_cols) >= 2:
                # 这是 Age 表格
                country_rows, global_flags = parse_targeting_table(table, age_range_cols)

                # 收集所有勾选的年龄
                checked_ages = set()
                age_detail = {}

                for country, row_data in country_rows:
                    age_detail[country] = row_data
                    for age_range, checked in row_data.items():
                        if checked:
                            checked_ages.add(age_range)

                data["age_detail"] = age_detail

                # 汇总年龄范围
                if checked_ages:
                    # 从年龄字符串提取最小和最大
                    all_mins = []
                    all_maxs = []
                    for age_range in checked_ages:
                        m = re.match(r'(\d+)-(\d+\+?)', age_range)
                        if m:
                            all_mins.append(int(m.group(1)))
                            if '+' in m.group(2):
                                all_maxs.append(65)
                            else:
                                all_maxs.append(int(m.group(2)))
                    if all_mins and all_maxs:
                        min_age = min(all_mins)
                        max_age = max(all_maxs)
                        if max_age >= 65:
                            data["age_summary"] = f"{min_age}-65+"
                        else:
                            data["age_summary"] = f"{min_age}-{max_age}"
                else:
                    data["age_summary"] = "不限"

        # ---- Location 国家列表 ----
        location_sections = soup.find_all("h2", class_="ad_details_targeting_title")
        for section in location_sections:
            if section.get_text(strip=True) == "Location":
                # 找下一个表格
                next_table = section.find_next_sibling("div")
                if next_table:
                    table = next_table.find("table", role="table")
                    if table:
                        rows = table.find_all("tr", role="row")
                        for row in rows[1:]:  # 跳过表头
                            cells = row.find_all("td", role="cell")
                            if len(cells) >= 3:
                                num = cells[0].get_text(strip=True)
                                country = cells[1].get_text(strip=True)
                                users = cells[2].get_text(strip=True)
                                if country and num.isdigit():
                                    data["locations"].append(country)
                                    data["locations_detail"][country] = users

        # 如果 Location 表格没找到，用文本解析
        if not data["locations"]:
            location_m = re.search(r'Location\s+This ad was shown to [^\n]+?\s+Number\s+Country\s+Unique users seen\s+(.+?)(?=Ad\s+Advertiser|$)', full_text, re.DOTALL | re.IGNORECASE)
            if location_m:
                loc_text = location_m.group(1)
                user_blocks = re.findall(r'(\d+)\s+([A-Za-z\s]+?)\s+(0-1K|1K-10K|10K-100K|100K-1M|1M-10M|10M-100M)', loc_text)
                for num, country, users in user_blocks:
                    country = country.strip()
                    if country and len(country) > 1:
                        data["locations"].append(country)
                        data["locations_detail"][country] = users

        # ---- 覆盖 ----
        unique_m = re.search(r'Unique users seen:\s*([^\n]+)', full_text)
        if unique_m:
            data["unique_users"] = unique_m.group(1).strip()

        # ---- 视频 URL ----
        try:
            video_el = driver.find_element(By.TAG_NAME, "video")
            v_url = video_el.get_attribute('currentSrc') or video_el.get_attribute('src') or ''
            if v_url and v_url != 'null' and len(v_url) > 20:
                data["video_url"] = v_url
                poster = video_el.get_attribute('poster')
                if poster:
                    data["thumbnail_url"] = poster
        except NoSuchElementException:
            pass

        # ---- 广告描述 ----
        desc_m = re.search(r'Advertiser[\\\'\"]?\s+([^\n]{10,300})', full_text)
        if desc_m:
            data["advertiser_description"] = desc_m.group(1).strip()[:500]

    except Exception as e:
        print(f"[详情] 抓取失败 {ad_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return data