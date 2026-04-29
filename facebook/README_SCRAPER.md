# Facebook Ad Library Scraper

两个脚本配合使用，先抓列表再抓详情。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `scrape_list.py` | 抓 Facebook Ad Library 列表页，输出 JSON，视频下载 |
| `scrape_detail.py` | 读取列表 JSON，按 library_id 抓详情页弹窗数据 |

---

## 一、安装依赖

### 1. Python 版本
```
Python 3.9 或更高
```

### 2. 安装 Python 包
```bash
pip install selenium>=4.0.0 webdriver-manager>=4.0.0 undetected-chromedriver>=3.5.0
```

> `undetected-chromedriver` 是核心，自动处理 Chrome 驱动和反检测。

### 3. Chrome 浏览器
确保本机已安装 **Google Chrome**（任意版本），脚本会自动匹配驱动。

### 4. 网络
确保能访问 `www.facebook.com`（需要 VPN 或代理如果网络受限）。

---

## 二、scrape_list.py 功能

### 抓什么
- Facebook Ad Library 列表页所有广告的 **library_id**
- **标题 / 广告文本 / 开始日期 / 平台**（Facebook / Instagram / Audience Network）
- **advertiser_name / payer_name**（部分可从列表页提取）
- **video_url**（列表页 JSON 里能拿到就直接写进 creative_data）
- 已抓过的 library_id 不重复抓（自动去重合并）

### 输出文件
```
output/<keyword>/ads_<keyword>_<date>.json
output/<keyword>/videos/   # 视频下载目录
```
- 按关键词分目录
- 按日期生成每日文件（如 `ads_Block_Blast_2026-04-28.json`）
- 支持多关键字并行修改 `KEYWORDS` 列表即可

### 命令行参数
```bash
# 单个关键词
python scrape_list.py --keyword "Block Blast"

# 指定日期范围（最近多少天）
python scrape_list.py --keyword "Block Blast" --days 30

# 多关键词：直接修改脚本顶部的 KEYWORDS 列表
KEYWORDS = ["Block Blast", "Block Puzzle", "Match 3D"]
```

### 配置（脚本顶部）
```python
KEYWORDS     = ["Block Blast"]       # 关键词列表，支持多个
DAYS_BACK    = 7                    # 抓最近多少天的广告
MAX_SCROLLS  = 30                   # 列表页最大滚动次数
WAIT_SEC     = 2                    # 每次滚动后等待秒数
HEADLESS     = False                # True=无头模式（不显示浏览器）
```

---

## 三、scrape_detail.py 功能

### 抓什么
读取列表 JSON，按 library_id 逐个打开详情页，点击展开：
- **广告信息公示（按地区）** → 欧盟 / 英国定向（年龄、性别、覆盖人数）
- **关于广告赞助方**
- **关于广告主**
- **广告主和付费方**

### 输出文件
```
output/<keyword>/detail_ads_<keyword>_<date>.json
```
- 以 **library_id 为 key**，所有字段在同一层级
- 已抓过的 library_id 自动跳过，支持中断后继续

### 命令行参数
```bash
# 默认处理今天的列表文件
python scrape_detail.py

# 指定日期（自动找对应列表文件）
python scrape_detail.py --date 2026-04-27

# 手动指定列表文件
python scrape_detail.py -i output/Block_Blast/ads_Block_Blast_2026-04-28.json

# 限制抓取数量（测试用）
python scrape_detail.py --max 5
```

---

## 四、日常使用流程

```bash
# Step 1: 每天跑一次列表（抓新广告 + 下载视频）
python scrape_list.py --keyword "Block Blast"

# Step 2: 抓详情（只抓今天列表里新增的 library_id）
python scrape_detail.py

# 查看详情数据
# output/Block_Blast/detail_ads_Block_Blast_2026-04-28.json
```

---

## 五、常见问题

### Q: 报错 "undetected_chromedriver not found"
```bash
pip install undetected-chromedriver
```

### Q: 报错 "Chrome not reachable"
Chrome 驱动问题，重装：
```bash
pip uninstall selenium webdriver-manager undetected-chromedriver
pip install selenium webdriver-manager undetected-chromedriver
```

### Q: Facebook 弹验证码 / 显示异常
- 降低 `MAX_SCROLLS`（少滚几次）
- 或在 Facebook 设置里退出登录后重新授权

### Q: 视频下载失败
视频 URL 有时效性，列表页拿到的 URL 可能过期。详情页重新抓可以更新 URL。

### Q: 想同时跑多个关键词
修改 `scrape_list.py` 顶部的 `KEYWORDS` 列表：
```python
KEYWORDS = ["Block Blast", "Block Puzzle", "Match 3D"]
```
按顺序逐个执行，非并行。

---

## 六、依赖总览

```
selenium >= 4.0.0
webdriver-manager >= 4.0.0
undetected-chromedriver >= 3.5.0
Python >= 3.9
Google Chrome（已安装）
```
