#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web端到端完整测试脚本 (最终健壮版 V4 - 内置运行器)
通过点击前端的“一键运行所有案例”按钮，触发内置的、可靠的批量测试流程

Author: HydroClaude Test Team
Date: 2025-11-25 (Robust Version 4)
"""
import sys
import os
import time
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
except ImportError:
    print("错误: 需要安装 selenium", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.absolute()
SCREENSHOTS_DIR = PROJECT_ROOT / "web_test_screenshots_final"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

TEST_CONFIG = {
    'base_url': 'http://localhost:3000',
    'timeout': 1800,  # 30分钟，以适应所有案例的运行
}


class WebE2ETestRunner:
    """Web端到端测试运行器 (内置运行器触发器)"""

    def __init__(self):
        self.driver = None
        self.start_time = None

    def setup_driver(self):
        print("\n初始化Chrome浏览器...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=options)
            print("✓ Chrome浏览器启动成功")
            return True
        except Exception as e:
            print(f"✗ Chrome浏览器启动失败: {e}", file=sys.stderr)
            return False

    def teardown_driver(self):
        if self.driver:
            self.driver.quit()
            print("\n✓ 浏览器已关闭")

    def take_screenshot(self, name: str, description: str = ""):
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        time.sleep(2.0)
        self.driver.save_screenshot(str(filepath))

        print(f"  📸 截图保存: {filename} ({description})")
        return str(filepath)

    def run_tests(self):
        self.start_time = datetime.now()
        print("\n" + "="*80)
        print("  HydroClaude Web E2E测试 (内置运行器触发)")
        print("="*80)

        if not self.setup_driver(): return

        try:
            # 1. 导航到仿真页面
            print("1. 导航到仿真页面...")
            self.driver.get(TEST_CONFIG['base_url'])
            sim_tab = WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '仿真计算')]")))
            sim_tab.click()
            time.sleep(2)
            self.take_screenshot("01_simulation_page", "进入仿真页面")

            # 2. 找到并点击“一键运行所有案例”按钮
            print("2. 点击“一键运行所有案例”按钮...")
            run_all_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "run-all-cases-button")))
            run_all_button.click()

            # 3. 等待测试完成
            print(f"3. 等待所有案例运行完成 (最长 {TEST_CONFIG['timeout']} 秒)...")
            # The button becomes disabled while running, and enabled when finished.
            # We wait for it to be clickable again.
            WebDriverWait(self.driver, TEST_CONFIG['timeout']).until(
                EC.element_to_be_clickable((By.ID, "run-all-cases-button"))
            )
            print("✓ 所有案例运行完毕！")

            # 4. 截取最终结果
            self.take_screenshot("02_final_results", "所有测试完成后的最终界面")

            duration = (datetime.now() - self.start_time).total_seconds()
            print("\n" + "="*80)
            print(f"✅ 端到端测试执行成功完成！")
            print(f"总耗时: {duration:.2f}秒")
            print(f"详细结果请在浏览器UI中查看。最终截图已保存。")
            print("="*80)

        except TimeoutException:
            print("\n❌ 测试超时！并非所有案例都在规定时间内完成。", file=sys.stderr)
            self.take_screenshot("03_timeout_error", "测试超时")
        except Exception as e:
            print(f"\n💥 测试流程发生致命错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self.take_screenshot("04_fatal_error", "致命错误")
        finally:
            self.teardown_driver()

def main():
    print("请确保:")
    print(f"1. 前端服务正在运行 ({TEST_CONFIG['base_url']})")
    print(f"2. 后端服务正在运行")

    runner = WebE2ETestRunner()
    runner.run_tests()

if __name__ == '__main__':
    main()
