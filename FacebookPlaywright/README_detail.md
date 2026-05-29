# FacebookPlaywright_detail.py — 详情页抓取工具

## 概述

本工具从 `FacebookPlaywright_list.py` 生成的列表 JSON 读取 `library_id`，逐个抓取广告**详情页**，提取完整的受众定向、广告主、付费方等信息。

**输入**：`output/ads_<date>.json`（列表文件）  
**输出**：`output/detail_ads_<date>.json`（详情数据）

---

## 工作流程

### Step 1 — 读取列表文件
- 定位今日列表文件 `output/ads_<date>.json`
- 加载已有详情文件（断点续抓，跳过已完成的 `library_id`）

### Step 2 — 打开详情页
```
URL: https://www.facebook.com/ads/library/?id=<library_id>
等待 networkidle（最长 20s）
等待固定 8s（让 JS 动态内容完全渲染）
```

### Step 3 — 严格检测页面是否真正加载
- 用 JS 检测"这条广告来自一个网址链接"是否在 DOM 中
- 若不存在，视为被 Facebook 屏蔽，跳过该广告

### Step 4 — 点击"查看广告详情"
- JS 定位策略：找到包含特定文本的容器 div → 在其内部找 `role=button` 且文本为"查看广告详情"的按钮 → `scrollIntoView` + `click`
- 回退策略：用 Playwright 的 `get_by_text` 找 y 值最小的按钮

### Step 5 — 等待详情弹窗
- 等待所有 `[role="dialog"]` 出现
- 遍历所有 dialog，取 `innerText` 最长的那个（内容最丰富）
- 固定等待 5s 让标签页内容渲染

### Step 6 — 展开标签页
依次点击 4 个标签，展开隐藏内容：
1. **广告信息公示（按地区）** — EU / UK 分地区受众数据
2. **关于广告赞助方** — about_sponsor 自由文本
3. **关于广告主** — advertiser_description + account_id + followers + industry
4. **广告主和付费方** — payer_name + advertiser_entity

### Step 7 — 解析 & 保存
- 获取弹窗完整 `innerText`（含隐藏内容）
- 传入 `parse_detail_text()` 解析为结构化字段
- **实时保存**：每抓完一个广告立即写入 JSON（防止崩溃丢失进度）
- 限速：每个广告之间等待 5s（防 Facebook 风控）

---

## 解析字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `library_id` | 广告 ID | `123456789012345` |
| `advertiser_name` | 广告主名称 | `Rollic Games` |
| `delivery_period` | 投放时间 | `2025年12月4日 ~ 2026年2月14日` |
| `delivery_status` | 投放状态 | `已停止投放` / `投放中` |
| `advertiser_entity` | 广告主主体/公司全称 | `北京阿瑞斯蒂科技有限公司` |
| `account_id` | 账号编号 | `105422708937000` |
| `followers` | 粉丝数 | `12.1 万` |
| `industry` | 行业 | `电子游戏` |
| `payer_name` | 付费方名称 | `Rollic Games` |
| `age_range` | 年龄定向 | `18岁-65岁+` |
| `gender` | 性别定向 | `不限` |
| `reach_count` | 覆盖人数 | `1221554` |
| `region_targeting` | 分地区数据 | `{"欧盟": {...}, "英国": {...}}` |
| `ad_disclosure_regions` | 投放地区列表 | `["欧盟", "英国"]` |
| `about_sponsor` | 关于广告赞助方（自由文本） | `MeetSocial...` |
| `advertiser_description` | 关于广告主（最多300字） | `Rollic Games is a...` |
| `ad_text` | 广告正文英文 | `The classic block puzzle...` |

---

## 使用方式

```bash
# 处理今天的列表文件
python FacebookPlaywright_detail.py

# 指定日期
python FacebookPlaywright_detail.py --date 2026-05-29

# 指定输入文件
python FacebookPlaywright_detail.py -i output/ads_2026-05-29.json

# 只抓前 5 个（测试）
python FacebookPlaywright_detail.py --max 5
```

---

## 断点续抓

详情文件实时写入，程序中断后可安全恢复：

```
[Resume] 23 already scraped    ← 跳过已完成的
[To scrape] 47 ads             ← 只抓剩余的
```

---

## 详情弹窗文本分区（解析逻辑）

```
┌─────────────────────────────────────────────────────┐
│  A 区（开头 ~ 广告信息公示）                          │
│   delivery_status / account_id / delivery_period     │
│   advertiser_name（头部第一个含英文的行）             │
├─────────────────────────────────────────────────────┤
│  B 区「广告信息公示（按地区）」                        │
│   → parse_region_block() 解析 EU / UK               │
│   → 填充 age_range / gender / reach_count           │
│     ad_disclosure_regions / region_targeting         │
├─────────────────────────────────────────────────────┤
│  C 区「关于广告赞助方」                               │
│   → about_sponsor（自由文本）                        │
├─────────────────────────────────────────────────────┤
│  D 区「关于广告主」                                  │
│   → advertiser_description / account_id             │
│   → followers / industry / advertiser_name          │
├─────────────────────────────────────────────────────┤
│  E 区「广告主和付费方」                              │
│   → payer_name（"当前"标记之后）                     │
│   → advertiser_entity（广告主\n 之后第一行）        │
│   ⚠ 顺序修复：MeetSocial 等代理商特殊处理           │
├─────────────────────────────────────────────────────┤
│  F 区（穿插在各区块）                                │
│   → ad_text（Google Play / App Store 链接附近）     │
└─────────────────────────────────────────────────────┘
```

---

## 已知问题 & 修复方向

| 问题 | 原因 | 当前处理 |
|------|------|----------|
| `payer_name` 和 `advertiser_entity` 顺序反 | MeetSocial 等代理商场景 | 有 swap 补丁，但治本需在"当前"标记之后才找广告主行 |
| `ad_text` 找不到英文 | 英文描述不在平台链接附近，在"更多信息"段落 | 有 fallback 策略（"The classic" 附近），但不够完善 |

---

## 下一步

详情抓完后，可结合其他数据源进行广告素材分析、竞品对比等操作。