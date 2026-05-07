# FacebookPlaywright

Facebook Ad Library 抓取工具，基于 Playwright纯浏览器实现。

## 文件说明

| 文件 | 说明 |
|------|------|
| `FacebookPlaywright_list.py` | 抓列表页：搜索关键词，滚动收集广告基本信息（library_id/标题/广告文本/广告主等） |
| `FacebookPlaywright_detail.py` | 抓详情页：逐个访问广告详情页，提取受众定向、投放周期、付费方等字段 |

## 依赖

```bash
pip install playwright
playwright install chromium
```

> **注意**：不再依赖 Selenium / webdriver-manager / 系统 Chrome，只需 Playwright 自己管理的 Chromium 浏览器。

## 配置

编辑文件顶部的代理配置：

```python
PROXY_SERVER = "http://127.0.0.1:7890"   # ← 改成你的代理端口，7890 是 Clash 默认
```

## 使用方法

```bash
# 抓列表
python FacebookPlaywright_list.py --keyword "Block Blast" --days 7

# 抓详情（默认处理今天生成的列表文件）
python FacebookPlaywright_detail.py
python FacebookPlaywright_detail.py --date 2026-04-28
python FacebookPlaywright_detail.py -i output/Block_Blast/ads_Block_Blast_2026-04-28.json --max 5
```

## 更新日志

### 2026-04-30
- **重写为纯 Playwright 实现**
  - `FacebookPlaywright_list.py`：移除 Selenium + webdriver-manager，改为 Playwright 直接启动 Chromium
  - `FacebookPlaywright_detail.py`：移除 Playwright CDP（连接外部 Chrome）和 Selenium 备选方案，改为 Playwright 直接启动 Chromium
  - 不再需要系统已安装 Chrome，不再需要手动打开 `--remote-debugging-port`
  - 新电脑只需：`pip install playwright && playwright install chromium`
