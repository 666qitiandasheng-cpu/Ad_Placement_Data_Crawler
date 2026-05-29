# FacebookPlaywright_list.py — 列表页抓取工具

## 概述

本工具使用 Playwright（纯 Python，无 Selenium/无外部 Chrome）抓取 Facebook Ad Library 的**广告列表页**，提取 `library_id`、视频 URL 及基础字段。

**输入**：关键词搜索  
**输出**：`output/ads_<date>.json`（所有关键词合并到统一每日文件）

---

## 目录结构

```
FacebookPlaywright/
├── FacebookPlaywright_list.py   # 本文件 — 列表页抓取
├── FacebookPlaywright_detail.py # 详情页抓取（Part 2）
├── output/
│   ├── ads_2026-05-29.json     # 统一每日广告列表（含所有关键词）
│   ├── ads_master.json          # 总表，记录所有 library_id（去重）
│   └── videos/                  # 下载的广告视频
└── logs/
    └── playwright_list_2026-05-29.log  # 当日运行日志
```

---

## 核心配置（文件顶部）

```python
# 代理配置（根据梯子端口修改）
PROXY_SERVER = "http://127.0.0.1:7890"

# Chrome 用户数据目录（保留登录状态）
CHROME_USER_DATA_DIR = r"C:\Users\Ivy\.openclaw\workspace\facebook_chrome_profile"
ANONYMOUS_MODE = False

# 搜索关键词列表
KEYWORDS = ["Block Blast", "Woodoku", ...]  # 支持 70+ 个关键词

# 滚动配置
MAX_SCROLLS = 999         # 最大滚动次数
WAIT_SEC = 5              # 每次滚动后等待秒数
CHECK_BOTTOM = True       # 智能检测滚动到底部（推荐开启）
HEADLESS = False          # 是否无头模式
MAX_ADS_LIMIT = 0        # 最大收集广告数，0=不限
```

---

## 工作流程

### Step 1 — 初始化
- 启动 Playwright Chromium（代理 + 反检测参数）
- 加载 Chrome 用户数据（如配置了且非匿名模式），保留登录状态

### Step 2 — 页面设置
1. 打开 `https://www.facebook.com/ads/library`
2. 处理微软/ Facebook 的 cookies 弹窗
3. 国家下拉框 → 搜索 "United States" → ArrowDown + Enter 选择美国
4. 广告类型保持默认"全部"

### Step 3 — 搜索
1. 在搜索框输入关键词，回车
2. 等待 2 秒后复制地址栏 URL（Facebook UI 操作会产生完整参数）
3. 检查 URL 参数是否正确（`country=US`, `ad_type=all`）
4. 若被覆盖，强制拼接正确参数重新加载

### Step 4 — 滚动收集
```
for scroll in range(max_scrolls):
    window.scrollTo(0, document.body.scrollHeight)
    等待 WAIT_SEC
    解析页面所有广告
    检测底部：广告数连续 3 次不增长 → 停止
    检测底部：页面高度连续不变 → 停止
```

### Step 5 — 解析字段
从页面 HTML 提取：
- `library_id` — 广告 ID
- `detail_url` — 详情页链接
- `video_url` — 视频 URL（从 JSON 块一次性提取）
- `age_range` / `gender` / `reach_count` / `spend` / `impressions`
- `ad_disclosure_regions` / `advertiser_name` / `payer_name` / `body_text`

### Step 6 — 去重 & 保存
1. 与 `ads_master.json` 总表对比，去除已抓过的 `library_id`
2. 合并到 `output/ads_<date>.json`（**只存今日新增**，用 `first_seen_date` 过滤历史）
3. 更新总表
4. 下载新广告视频（多线程，最多 3 并发）

---

## 使用方式

```bash
# 默认配置（所有关键词）
python FacebookPlaywright_list.py

# 单个关键词测试
python FacebookPlaywright_list.py --keyword "Block Blast"

# 多个关键词（逗号分隔）
python FacebookPlaywright_list.py --keyword "Block Blast,Woodoku"

# 限制最大广告数
python FacebookPlaywright_list.py --keyword "Block Blast" --max-ads 50
```

---

## 输出文件格式

```json
{
  "date": "2026-05-29",
  "last_updated": "2026-05-29T15:30:00.000Z",
  "keywords": ["Block Blast", "Woodoku"],
  "ads": [
    {
      "library_id": "123456789012345",
      "detail_url": "https://www.facebook.com/ads/library/?id=123456789012345",
      "keyword": "Block Blast",
      "first_seen_date": "2026-05-29",
      "video_url": "https://video.facebook.com/...",
      "advertiser_name": "Rollic Games",
      "payer_name": "Rollic Games",
      "age_range": "18岁-65岁+",
      "gender": "不限",
      "reach_count": "1221554",
      "ad_disclosure_regions": ["欧盟", "英国"]
    }
  ]
}
```

---

## 注意事项

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 看不到广告内容（空白） | 未登录 / 被 Facebook 检测 | 首次运行前先运行 `setup_chrome_profile.py` 登录 Facebook |
| 滚动到底部后还在滚 | `CHECK_BOTTOM=False` 或网速慢 | 开启 `CHECK_BOTTOM=True`，或增大 `WAIT_SEC` |
| 视频下载失败 | 视频不存在或代理问题 | 检查 `PROXY_SERVER` 端口，`videos/` 目录权限 |
| 大量重复广告 | 总表未更新 | 检查 `output/ads_master.json` 是否损坏 |
| 页面加载慢 | 网络问题 | 增加 `WAIT_SEC` 到 8~10 |

---

## 下一步

用 `FacebookPlaywright_detail.py` 抓取详情页：

```bash
# 抓取今天的列表详情
python FacebookPlaywright_detail.py

# 抓取指定日期
python FacebookPlaywright_detail.py --date 2026-05-29

# 只抓前 5 个（测试）
python FacebookPlaywright_detail.py --max 5
```