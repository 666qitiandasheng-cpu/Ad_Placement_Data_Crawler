#!/usr/bin/env python3
"""
Facebook Ad Library 抓取 - 配置运行示例
========================================

本文件用于快速配置并运行 Facebook 广告抓取脚本
修改下方配置后直接运行本文件即可
"""

import os
import sys
import json
from pathlib import Path

# ============================================================
#                    【快速配置】
# ============================================================

# ----- 搜索条件 -----
KEYWORD = "Facebook"              # 搜索关键词（热门关键词更容易找到广告）

# ----- 日期设置 -----
AUTO_DATE = False                 # True=自动抓最近7天，False=手动指定
START_DATE = "2026-04-17"        # 开始日期（格式：YYYY-MM-DD）
END_DATE = "2026-04-23"          # 结束日期（留空表示今天）

# ----- 抓取模式 -----
MODE = "all"                     # "fixed"=固定数量，"all"=抓取全部
MAX_ADS = 50                     # MODE="fixed" 时生效
MAX_SCROLLS = 50                 # 最大滚动次数

# ----- 浏览器模式 -----
HEADLESS = False                 # False=可见浏览器（方便调试）

# ============================================================

# 保存配置到 config.json
config = {
    "keyword": KEYWORD,
    "auto_date": AUTO_DATE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "mode": MODE,
    "max_ads": MAX_ADS,
    "max_scrolls": MAX_SCROLLS,
    "headless": HEADLESS
}

config_path = Path(__file__).parent / "config.json"
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("OK - Config saved to:", config_path)
print("KEY - Keyword:", KEYWORD)
print("DAT - Date range:", START_DATE, "~", END_DATE)
print("MOD - Mode:", MODE, ("(" + str(MAX_ADS) + ")" if MODE == "fixed" else ""))
print("BRW - Browser:", "Headless" if HEADLESS else "Visible")

# 运行主脚本
print("\n--- Starting scraper... ---")

# 动态导入并运行（这样可以获取更新后的配置）
import run
run.main()
