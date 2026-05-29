# TiktokPlaywright_detail.py — TikTok 广告详情页抓取 + 视频下载

## 概述

本工具从 `TiktokPlaywright_list.py` 输出的 `ads_<date>.json` 读取广告 ID，逐个抓取**详情页**，提取完整受众定向字段，并通过 Playwright 提取视频 URL（通过 yt-dlp 下载）。

**输入**：`output/ads_<date>.json`  
**输出**：
- `ads_<date>.json` — 更新后（含 `tiktok_detail` + `video_urls`）
- `ads_all.json` — 同步更新汇总文件
- `output/videos/*.mp4` — 下载的广告视频

---

## 工作流程

### Step 1 — 读取列表文件
- 定位 `output/ads_<date>.json`
- 加载已有详情数据（断点续抓，跳过已完成 `library_id`）

### Step 2 — 批量抓取详情页
- 每批 `DETAIL_BATCH = 5` 个广告
- 批次间有随机等待（防风控）
- 每个广告访问 `https://library.tiktok.com/ads/detail/?ad_id=<ad_id>`

### Step 3 — 详情页解析字段
从页面 HTML / text 提取：
- `advertiser_name` / `advertiser_description` — 广告主名称和描述
- `ad_text` — 广告正文（sponsored 段落）
- `payer_name` — 付费方
- `advertiser_registered_location` — 广告主注册地
- `first_seen` / `last_seen` — 投放时间
- `delivery_status` / `active_ad_delivery` — 投放状态
- `target_audience_size` — 目标受众规模
- `gender_summary` / `gender_detail` — 性别定向（含表格解析）
- `age_summary` / `age_detail` — 年龄定向（含表格解析）
- `locations` / `locations_detail` — 地区定向
- `unique_users` / `impressions` — 覆盖人数
- `video_url` / `thumbnail_url` — 视频 URL（从 `<video>` 标签提取）

### Step 4 — 视频下载（yt-dlp）
- 通过 `yt-dlp` 下载视频（绕过直接请求的 403 问题）
- 已下载跳过（`output/videos/<ad_id>.mp4`）
- 失败重试 3 次，超时 120s

### Step 5 — 保存 & 汇总
- 每批次保存一次详情 JSON（断点续抓）
- 最终合并到 `ads_all.json` 汇总文件

---

## 核心配置

```python
TARGET_DATE = ""              # 空=当天，指定如 "2026-05-14"
HEADLESS = False              # 是否无头模式
DETAIL_WAIT = 5               # 详情页加载等待秒数
RESUME_ENABLED = True         # 断点续抓
ZERO_RESULT_THRESHOLD = 3     # 连续 N 批无有效数据 → 指数退避
MAX_DETAIL_WORKERS = 2        # 详情页并发数（当前未使用）
DETAIL_BATCH = 5              # 每批次抓取广告数
```

---

## 详情页字段对照

| 字段 | 说明 | 示例 |
|------|------|------|
| `ad_id` | 广告 ID | `7123456789012345678` |
| `advertiser_name` | 广告主名称 | `Easybrain Ltd` |
| `advertiser_description` | 广告主描述 | `Easybrain is a leading...` |
| `ad_text` | 广告正文 | `Block Blast is the ultimate...` |
| `payer_name` | 付费方 | `Easybrain Ltd` |
| `advertiser_registered_location` | 注册地 | `Cyprus` |
| `first_seen` / `last_seen` | 投放时间段 | `04/16/2026` / `04/22/2026` |
| `delivery_status` | 投放状态 | `Active` |
| `active_ad_delivery` | 是否活跃 | `Yes` / `No` |
| `target_audience_size` | 目标受众规模 | `1M-10M` |
| `gender_summary` | 性别定向（汇总） | `不限` / `Male, Female` |
| `age_summary` | 年龄定向（汇总） | `18-65+` |
| `locations` | 投放国家列表 | `["United States", "United Kingdom"]` |
| `locations_detail` | 各国覆盖人数 | `{"United States": "100K-1M", ...}` |
| `unique_users` | 独立用户覆盖 | `100K-1M` |
| `video_url` | 视频 URL | `https://v16-m可否...` |
| `thumbnail_url` | 视频封面 URL | `https://p16...` |

---

## 使用方式

```bash
# 处理今天的列表文件
python TiktokPlaywright_detail.py

# 指定日期
python TiktokPlaywright_detail.py --date 2026-05-29
```

---

## 断点续抓逻辑

```python
# 若已有 tiktok_detail 且含 advertiser_name 或 video_url → 跳过
existing_detail = ad.get("tiktok_detail", {})
if existing_detail and (existing_detail.get("advertiser_name") 
                        or existing_detail.get("video_url")):
    skip  # 已完成
else:
    scrape  # 抓详情
```

---

## 性别/年龄表格解析逻辑

通过 `table role="table"` 的 `aria-colindex` 和 SVG `fill` 属性判断勾选状态：
- `fill` 含 `#FE2C55`（TikTok 主题色）→ 勾选
- 男性 + 女性 + 未知全勾 → `gender_summary = "不限"`
- 多个年龄段全勾 → 合并为 `min-max+` 范围

---

## 视频下载（yt-dlp）

```
yt-dlp --no-playlist -o <path> --user-agent <UA> --socket-timeout 60 --retries 3 -q <url>
```

- 无需 Playwright，纯 subprocess 调用 yt-dlp
- 自动处理签名 URL 和 CDN 路由问题
- 已下载跳过，不重复下载

---

## 反爬机制

| 机制 | 说明 |
|------|------|
| 批次间随机等待 | 每 5 个广告休息 5~10s |
| 详情页随机等待 | `time.sleep(random.uniform(2, 8))` |
| `ZERO_RESULT_THRESHOLD` | 连续 3 批 0 有效数据 → 指数退避最长 300s |
| 反检测脚本 | 同 list（webdriver / plugins 伪装） |
| 详情页随机点击 | 每个广告内有一定随机性 |

---

## 输出结构

```json
{
  "ads": [
    {
      "library_id": "7123456789012345678",
      "detail_url": "https://library.tiktok.com/ads/detail/?ad_id=7123456789012345678",
      "video_urls": ["https://v16-m可否..."],
      "tiktok_detail": {
        "ad_id": "7123456789012345678",
        "advertiser_name": "Easybrain Ltd",
        "ad_text": "Block Blast is the ultimate...",
        "gender_summary": "不限",
        "age_summary": "18-65+",
        "locations": ["United States"],
        "video_url": "https://v16-m可否...",
        ...
      }
    }
  ]
}
```