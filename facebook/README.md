# Facebook Ad Library 抓取工具

## 功能简介

这是一个用于抓取 Facebook Ad Library 广告数据的 Python 脚本，包含以下功能：
- 📋 抓取列表页广告数据
- 🔍 访问详情页提取性别、年龄、覆盖人群等定向信息
- 📁 去重并合并到汇总文件
- 🎬 下载广告视频（支持断点续传）

## 配置说明

所有配置都集中在脚本顶部的【配置区】：

### 搜索条件
```python
KEYWORD = "Block Blast"        # 搜索关键词
```

### 日期设置
```python
AUTO_DATE = True              # 自动模式（抓最近7天）/ 手动模式
START_DATE = "2026-04-15"    # 手动模式开始日期（YYYY-MM-DD）
END_DATE = ""                # 手动模式结束日期（留空表示今天）
```

### 抓取模式
```python
MODE = "fixed"                # "fixed" 固定数量 / "all" 抓取全部
MAX_ADS = 20                  # MODE="fixed" 时的最大广告数量
MAX_SCROLLS = 30              # 列表页最大滚动次数
```

### 其他设置
```python
HEADLESS = False              # 是否无头模式（后台运行）
WAIT_SEC = 5                  # 每次滚动后等待秒数
MAX_DOWNLOAD_WORKERS = 3      # 视频下载并发数
SCRAPE_DETAILS = True         # 是否抓取详情页
DETAIL_WAIT = 3               # 详情页等待秒数
DETAIL_BATCH = 5              # 详情页中间保存批次
```

## 运行方法

### 依赖安装
```bash
pip install selenium undetected-chromedriver
```

### 直接运行
```bash
cd facebook_ad_scraper
python run.py
```

## 文件说明

### 输出文件
- `output/ads_{name}.json` - 汇总文件（所有历史数据）
- `output/ads_{name}_{date}.json` - 每日文件（当日抓取数据）
- `output/videos_{name}/` - 视频下载目录

### 脚本结构
1. **配置区** - 所有可配置参数
2. **工具函数** - 文件处理、日期处理等通用函数
3. **浏览器驱动** - 初始化带反爬的浏览器
4. **页面交互** - 滚动翻页、广告解析
5. **详情页抓取** - 提取性别/年龄/覆盖等字段
6. **文件处理** - 去重合并、保存文件
7. **视频下载** - 断点续传下载视频
8. **主函数** - 协调执行所有步骤

## 反爬机制说明

1. **undetected-chromedriver** - 优先使用防检测的 chromedriver
2. **JS 注入** - 伪装 `navigator.webdriver/plugins/languages` 等特征
3. **分阶段滚动** - 先滚动到中间再到底部，模拟人类行为
4. **固定 User-Agent** - 使用 Chrome 最新版本的 User-Agent
5. **SSL 关闭** - 防止 SSL 指纹识别
6. **随机等待** - 每次滚动后等待随机时间

## 常见问题

### Q: 为什么抓取到 0 条广告？
A: 可能原因：
1. 关键词确实没有对应的广告
2. Facebook 反爬机制限制
3. 页面结构变化导致解析失败

**解决方案**：
- 尝试热门关键词（如 "Facebook"）
- 调整日期范围或模式
- 更新 undetected-chromedriver

### Q: 为什么运行时出现浏览器窗口闪一下就消失？
A: 这是正常的，因为脚本使用了无头模式。如果想看到浏览器窗口，请设置 `HEADLESS = False`。

### Q: 视频下载失败怎么办？
A: 脚本支持断点续传，再次运行会自动跳过已下载的视频。如果持续失败，可能是视频链接已失效。

## 更新日志

### v2.0 (2026-04-23)
- ✅ 重构为与 TikTok 版本统一的配置与执行流程
- ✅ 新增多阶段广告解析（原始+通用+兜底）
- ✅ 增强反爬机制（undetected-chromedriver+JS注入）
- ✅ 完善日志与错误处理
- ✅ 修复各类运行时错误