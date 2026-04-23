#!/usr/bin/env python3
"""
测试浏览器驱动是否能正常初始化
"""
import sys
import os
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入run.py中的配置和函数
from run import make_driver, HEADLESS, CHROMEDRIVER_PATH

def test_driver_init():
    """测试浏览器驱动初始化"""
    print("=" * 50)
    print("浏览器驱动测试")
    print("=" * 50)
    print(f"ChromeDriver路径: {CHROMEDRIVER_PATH}")
    print(f"文件存在: {os.path.exists(CHROMEDRIVER_PATH)}")
    print(f"无头模式: {HEADLESS}")
    print()
    
    try:
        print("正在初始化浏览器...")
        driver = make_driver(headless=HEADLESS)
        print("✅ 浏览器初始化成功!")
        
        # 测试访问网页
        print("正在测试访问网页...")
        driver.get("https://www.baidu.com")
        print(f"✅ 成功访问: {driver.title}")
        
        # 关闭浏览器
        print("正在关闭浏览器...")
        driver.quit()
        print("✅ 浏览器已关闭")
        
        print()
        print("=" * 50)
        print("测试完成: 所有功能正常!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print()
        print("=" * 50)
        print("错误详情:")
        import traceback
        traceback.print_exc()
        print("=" * 50)
        return False

if __name__ == "__main__":
    success = test_driver_init()
    sys.exit(0 if success else 1)