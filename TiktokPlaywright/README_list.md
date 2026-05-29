# TiktokPlaywright_list.py — TikTok 广告列表页抓取（仅 ID）

## 概述

本工具使用 Playwright 抓取 TikTok Ad Library **列表页**，提取广告 ID，不进详情页，不下载视频。

**输入**：关键词列表（KEYWORDS）  
**输出**：`output/ads_<date>.json` + `output/ads_all.json`（汇总）

---

## 目录结构

```
TiktokPlaywright/
├── TiktokPlaywright_list.py   # 本文件 — 列表页抓取
├── TiktokPlaywright_detail.py  # 详情页抓取 + 视频下载（Part 2）
├── output/
│   ├── ads_2026-05-29.json     # 当日广告列表
│   ├── ads_all.json             # 全量汇总（所有历史广告）
│   └── videos/                  # 视频文件目录（detail 阶段）
└── (logs/ 可选)
```

---

## 核心配置（文件顶部）

```python
# 搜索关键词
KEYWORDS = ["Block Blast", "Easybrain Ltd", "Tripledot Studios", ...]

# 日期范围
AUTO_DATE = True               # True=自动最近7天，False=用 START_DATE / END_DATE
START_DATE = "2026-04-16"
END_DATE = "2026-04-22"

# 抓取模式
MODE = "all"                   # "all"=全量，"fixed"=固定数量
MAX_ADS = 10                   # MODE=fixed 时的上限

# 浏览器
HEADLESS = False
WAIT_SEC = 7                   # 每次 View More 后等待秒数

# 断点续抓
RESUME_ENABLED = True
ZERO_RESULT_THRESHOLD = 3      # 连续 N 次无新广告 → 指数退避
BACKOFF_BASE_SEC = 30           # 退避基数秒
```

---

## 工作流程

### Step 1 — 构建搜索 URL
```
URL = https://library.tiktok.com/ads?
      region=all
      &start_time=<timestamp_ms>
      &end_time=<timestamp_ms>
      &adv_name=<URL编码的关键词>
      &query_type=1
      &sort_type=last_shown_date,desc
```

### Step 2 — 浏览器启动
- 启动 Chromium（随机窗口尺寸 1920/1366/1536...）
- 注入反检测脚本（webdriver / plugins / languages 等伪装）
- 添加 `meta robots noindex` 防止被索引

### Step 3 — 页面交互
1. `page.goto(url)` — 访问 TikTok Ad Library
2. `accept_cookies_if_present()` — 处理 cookie 弹窗（多语言适配）
3. `scroll_and_collect()` — 开始收集

### Step 4 — 滚动收集（View More 翻页）
```
while True:
    点击 "View more" 按钮
    等待 WAIT_SEC
    解析页面所有广告 ID
    检测是否 "End of results" 或 View More 按钮消失 → 停止
    连续 ZERO_RESULT_THRESHOLD 次无新广告 → 指数退避等待
```

### Step 5 — 解析广告字段
从页面 `<a href*='/ads/detail/?ad_id='>` 链接提取：
- `library_id` — 广告 ID
- `detail_url` — 详情页链接
- `first_shown` / `last_shown` — 首次/最近展示时间
- `unique_users` — 覆盖独立用户数
- `ad_text` — 广告文本（正文前500字）

### Step 6 — 去重 & 保存
- 与 `ads_all.json` 汇总文件对比去重
- 追加到 `ads_<date>.json`（**不覆盖已有记录**）
- 更新 `ads_all.json` 汇总文件

---

## 使用方式

```bash
# 默认（全自动最近7天，所有关键词）
python TiktokPlaywright_list.py

# 自定义日期范围（自动日期关闭时）
python TiktokPlaywright_list.py

# 查看帮助
python TiktokPlaywright_list.py --help
```

---

## 输出文件格式

### ads_<date>.json

```json
{
  "scrape_time": "2026-05-29T16:00:00.000Z",
  "keywords": ["Block Blast", "Easybrain Ltd"],
  "start_date": "2026-04-16",
  "end_date": "2026-04-22",
  "today": "2026-05-29",
  "ads_count": 142,
  "new_ads_count": 23,
  "total_in_summary": 1190,
  "ads": [
    {
      "library_id": "7123456789012345678",
      "index": 1,
      "platforms": ["TikTok"],
      "first_shown": "04/16/2026",
      "last_shown": "04/22/2026",
      "unique_users": "100K-1M",
      "ad_text": "Block Blast is the ultimate...",
      "detail_url": "https://library.tiktok.com/ads/detail/?ad_id=7123456789012345678"
    }
  ]
}
```

---

## 反爬机制

| 机制 | 说明 |
|------|------|
| 随机窗口尺寸 | 每次启动随机选择 width/height，降低特征辨识 |
| `ZERO_RESULT_THRESHOLD` | 连续 3 次点击 View More 无新广告 → 指数退避（最长 300s） |
| 随机 User-Agent | Chrome 147，真实桌面 UA |
| 隐身参数 | `navigator.webdriver` 伪装，`cdc_adoQpoasnfa76pfcZLmcfl_*` 删除 |
| `WAIT_SEC` | 每次翻页等待 7s，避免过快触发风控 |

---

## 断点续抓逻辑

```
existing_ids = ads_<date>.json 中所有 library_id
本次抓取时：若 library_id in existing_ids → 跳过
```

---

## 下一步

用 `TiktokPlaywright_detail.py` 抓取详情 + 视频：

```bash
# 抓取今天的详情
python TiktokPlaywright_detail.py

# 指定日期
python TiktokPlaywright_detail.py --date 2026-05-29
```