#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web端到端完整测试脚本 (增强版)
遍历所有API获取的测试案例，执行端到端测试并截图

Author: HydroClaude Test Team
Date: 2025-11-25 (Enhanced)
"""

import sys
import os
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 确保输出使用UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("错误: 需要安装 selenium")
    print("请运行: pip install selenium")
    sys.exit(1)

# 项目路径
PROJECT_ROOT = Path(__file__).parent.absolute()
SCREENSHOTS_DIR = PROJECT_ROOT / "web_test_screenshots_final"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# 测试配置
# 注意: 前端端口根据 'npm run dev' 的日志设置为 3000
TEST_CONFIG = {
    'base_url': 'http://localhost:3000',
    'backend_api_url': 'http://localhost:8000/api/v1',
    'timeout': 120,  # 增加超时以适应复杂的模拟
    'screenshot_delay': 2.0
}


class WebE2ETestRunner:
    """Web端到端测试运行器 (遍历所有案例)"""
    
    def __init__(self):
        self.driver = None
        self.test_results = []
        self.screenshot_counter = 0
        self.start_time = None
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        print("\n初始化Chrome浏览器...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=zh-CN')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print("✓ Chrome浏览器启动成功")
            return True
        except Exception as e:
            print(f"✗ Chrome浏览器启动失败: {e}")
            return False
    
    def teardown_driver(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("\n✓ 浏览器已关闭")
    
    def take_screenshot(self, name: str, description: str = ""):
        """截图并保存"""
        # 清理文件名中的非法字符
        safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).rstrip()
        self.screenshot_counter += 1
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{self.screenshot_counter:03d}_{safe_name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        time.sleep(TEST_CONFIG['screenshot_delay'])
        self.driver.save_screenshot(str(filepath))
        
        print(f"  📸 截图保存: {filename} ({description})")
        return str(filepath)

    def wait_for_element(self, by, value, timeout=None):
        """等待元素出现"""
        if timeout is None:
            timeout = TEST_CONFIG['timeout']
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            print(f"  ⚠️ 超时: 元素未找到 {value}")
            return None

    def get_all_test_cases(self) -> List[Dict[str, str]]:
        """从后端API获取所有测试案例"""
        print("\nFetching all test cases from the API...")
        # 限制为前20个案例以进行初步测试，后续可放开
        limit = 20
        try:
            url = f"{TEST_CONFIG['backend_api_url']}/test-cases?limit={limit}&offset=0"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            cases = data.get('cases', [])
            
            if not cases:
                print("  ✗ API返回了空的案例列表。")
                return []

            case_info = [{
                "id": case.get('metadata', {}).get('id'),
                "name": case.get('metadata', {}).get('nameCN') or case.get('metadata', {}).get('name')
            } for case in cases if case.get('metadata', {}).get('id')]
            
            print(f"  ✓ 从API获取到 {len(case_info)} 个测试案例。")
            return case_info
        except requests.exceptions.RequestException as e:
            print(f"  ✗ API请求失败: {e}")
            return []

    def run_single_case(self, case_info: Dict[str, str]):
        """为单个案例运行端到端测试"""
        case_id = case_info['id']
        case_name = case_info['name']
        print("\n" + "="*80)
        print(f"▶️  开始测试: [{case_id}] - {case_name}")
        print("="*80)

        result = {
            'test_id': case_id,
            'name': case_name,
            'status': 'failed', # 默认为失败
            'duration': 0,
            'screenshots': [],
            'notes': []
        }
        start = time.time()

        try:
            # 1. 选择测试案例
            # 为了稳定，每次都重新导航到仿真页面
            print("  1. 导航到仿真页面...")
            sim_tab = self.wait_for_element(By.XPATH, "//span[contains(text(), '仿真计算')]", 10)
            if not sim_tab: raise TimeoutException("无法找到'仿真计算'标签页。")
            sim_tab.click()
            time.sleep(2)

            print(f"  2. 从下拉框选择案例: {case_id}")
            # 点击下拉框以展开选项 (使用JS点击以防止被拦截)
            selector_dropdown = self.wait_for_element(By.ID, 'test-case-selector', 10)
            if not selector_dropdown: raise TimeoutException("无法找到ID为 'test-case-selector' 的案例选择下拉框。")
            self.driver.execute_script("arguments[0].click();", selector_dropdown)
            time.sleep(1)

            # 选择对应的选项，使用更健壮的包含文本的选择器
            option_xpath = f"//div[contains(@class, 'ant-select-item-option-content') and contains(text(), '{case_id}')]"
            option = self.wait_for_element(By.XPATH, option_xpath, 10)
            if not option: raise TimeoutException(f"在下拉框中找不到包含文本 '{case_id}' 的选项。")
            # Antd有时需要点击父级元素
            option_parent = option.find_element(By.XPATH, "./..")
            option_parent.click()
            time.sleep(1)
            result['notes'].append("成功从UI选择案例。")

            # 2. 点击运行按钮
            print("  3. 点击运行按钮...")
            run_button = self.wait_for_element(By.XPATH, "//button[contains(., '运行仿真')]", 10)
            if not run_button: raise TimeoutException("无法找到'运行仿真'按钮。")
            self.driver.execute_script("arguments[0].click();", run_button)
            result['notes'].append("已点击运行按钮。")
            
            # 3. 等待结果
            print("  4. 等待仿真完成 (最长 {}s)...".format(TEST_CONFIG['timeout']))
            # 等待加载动画出现，然后再等待它消失
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ant-spin-spinning')))
            print("    - 检测到加载动画...")
            WebDriverWait(self.driver, TEST_CONFIG['timeout']).until(EC.invisibility_of_element_located((By.CLASS_NAME, 'ant-spin-spinning')))
            print("    - 加载动画已消失。")
            
            # 检查是否有错误提示
            errors = self.driver.find_elements(By.CLASS_NAME, 'ant-message-error')
            if errors:
                error_text = errors[0].text
                raise Exception(f"仿真失败，UI提示: {error_text}")

            result['notes'].append("仿真成功完成（未检测到错误）。")
            print("  5. 仿真完成，截取结果图...")
            screenshot = self.take_screenshot(f"{case_id}_results", "仿真结果")
            result['screenshots'].append(screenshot)

            result['status'] = 'passed'
            print(f"✅ 测试通过: [{case_id}]")

        except (TimeoutException, NoSuchElementException) as e:
            result['notes'].append(f"测试失败 (元素查找超时或不存在): {e}")
            print(f"❌ 测试失败: {e}")
        except Exception as e:
            result['notes'].append(f"测试失败 (未知异常): {e}")
            print(f"❌ 测试失败: {e}")
        finally:
            # 无论成功失败，都尝试截图
            if result['status'] == 'failed':
                try:
                    err_screenshot = self.take_screenshot(f"{case_id}_error", "失败状态截图")
                    result['screenshots'].append(err_screenshot)
                except Exception as ss_e:
                    print(f"  无法截取失败状态图: {ss_e}")
            
            result['duration'] = time.time() - start
            self.test_results.append(result)

    def run_all_tests(self):
        """运行所有端到端测试"""
        self.start_time = datetime.now()
        print("\n" + "="*80)
        print("  HydroClaude Web 端到端完整测试 (增强版)")
        print("="*80)
        
        if not self.setup_driver():
            return
        
        try:
            # 1. 首页健康检查
            print("访问首页进行健康检查...")
            self.driver.get(TEST_CONFIG['base_url'])
            WebDriverWait(self.driver, 20).until(lambda d: d.title != "")
            if "HydroClaude" not in self.driver.title and "React App" not in self.driver.title:
                raise Exception(f"首页标题不正确: '{self.driver.title}'")
            print("✓ 首页加载成功。")
            self.take_screenshot("00_health_check", "首页加载")

            # 2. 获取测试案例
            cases_to_run = self.get_all_test_cases()
            if not cases_to_run:
                print("\n未获取到测试案例，测试终止。")
                return
            
            # 3. 循环执行测试
            for i, case in enumerate(cases_to_run):
                self.run_single_case(case)
                print(f"--- 测试 {i+1}/{len(cases_to_run)} 完成 ---")
            
            # 4. 生成报告
            self.print_summary()
            self.save_results()

        except Exception as e:
            print(f"\n\n💥 测试流程发生致命错误: {e}")
            import traceback
            traceback.print_exc()
            self.take_screenshot("00_fatal_error", "致命错误")
        finally:
            self.teardown_driver()

    def print_summary(self):
        """打印测试总结"""
        duration = (datetime.now() - self.start_time).total_seconds()
        stats = {'passed': 0, 'failed': 0}
        for res in self.test_results:
            stats[res['status']] = stats.get(res['status'], 0) + 1

        print("\n" + "="*80)
        print("  测试总结")
        print("="*80)
        print(f"总耗时: {duration:.2f}秒")
        print(f"总案例数: {len(self.test_results)}")
        print(f"  - ✅ 通过: {stats['passed']}")
        print(f"  - ❌ 失败: {stats['failed']}")
        print(f"总截图数: {self.screenshot_counter}")

        if stats['failed'] > 0:
            print("\n失败案例详情:")
            for res in self.test_results:
                if res['status'] == 'failed':
                    print(f"  - [{res['test_id']}] {res['name']}")
                    for note in res['notes']:
                        if "ERROR" in note or "失败" in note:
                            print(f"    - {note}")
        print("="*80)

    def save_results(self):
        """保存测试结果到JSON文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"e2e_test_results_{timestamp}.json"
        output_file = SCREENSHOTS_DIR / filename
        
        summary = {
            'startTime': self.start_time.isoformat(),
            'durationSeconds': (datetime.now() - self.start_time).total_seconds(),
            'config': TEST_CONFIG,
            'totalTests': len(self.test_results),
            'screenshots': self.screenshot_counter,
            'results': self.test_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 测试结果已保存: {output_file}")


def main():
    """主函数"""
    print("请确保:")
    print(f"1. 前端服务正在运行 ({TEST_CONFIG['base_url']})")
    print(f"2. 后端服务正在运行 ({TEST_CONFIG['backend_api_url']})")
    
    runner = WebE2ETestRunner()
    runner.run_all_tests()

if __name__ == '__main__':
    main()
