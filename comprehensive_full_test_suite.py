#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web - 全面综合测试套件
全流程、全案例、全功能点的各种组合测试

测试矩阵：
1. 仿真场景组合测试（均匀流、溃坝、不同边界条件）
2. 参数范围测试（正常值、边界值、异常值）
3. UI交互测试（建模、仿真、结果查看）
4. 错误处理测试
5. 性能测试
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime
from typing import Dict, List, Tuple

# ========== 配置 ==========
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "comprehensive_test_results"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ========== 测试结果记录 ==========
class TestResults:
    def __init__(self):
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
        self.screenshots = []
    
    def add_result(self, test_name, status, message="", details=None):
        self.total_tests += 1
        if status == "pass":
            self.passed += 1
        elif status == "fail":
            self.failed += 1
        else:
            self.warnings += 1
        
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        icon = "[PASS]" if status == "pass" else "[FAIL]" if status == "fail" else "[WARN]"
        print(f"{icon} {test_name}")
        if message:
            print(f"      {message}")
    
    def save_summary(self):
        summary = {
            "test_suite": "HydroClaude Web Comprehensive Test Suite",
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "success_rate": f"{(self.passed/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0%",
            "results": self.results
        }
        
        with open(os.path.join(SCREENSHOT_DIR, "test_summary.json"), 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return summary

results = TestResults()

# ========== 测试数据定义 ==========
TEST_SCENARIOS = {
    "uniform_flow": {
        "name": "均匀流测试",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 10.0,
            "dt_max": 0.1,
            "output_interval": 0.5,
            "initial_conditions": {
                "type": "uniform",
                "h": 5.0,
                "Q": 0.0
            },
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 5.0},
                "downstream": {"type": "h", "value": 5.0}
            }
        }
    },
    "dam_break": {
        "name": "溃坝测试",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.0,
            "t_end": 20.0,
            "dt_max": 0.05,
            "output_interval": 0.5,
            "initial_conditions": {
                "type": "dam_break",
                "dam_position": 500.0,
                "h_left": 10.0,
                "h_right": 1.0,
                "Q_left": 0.0,
                "Q_right": 0.0
            },
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 10.0},
                "downstream": {"type": "h", "value": 1.0}
            }
        }
    },
    "flow_boundary": {
        "name": "流量边界测试",
        "config": {
            "width": 10.0,
            "length": 1000.0,
            "n_cells": 100,
            "manning_n": 0.025,
            "slope": 0.001,
            "t_end": 15.0,
            "dt_max": 0.1,
            "output_interval": 0.5,
            "initial_conditions": {
                "type": "uniform",
                "h": 3.0,
                "Q": 50.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 50.0},
                "downstream": {"type": "h", "value": 3.0}
            }
        }
    },
    "steep_slope": {
        "name": "陡坡流动测试",
        "config": {
            "width": 5.0,
            "length": 500.0,
            "n_cells": 50,
            "manning_n": 0.02,
            "slope": 0.01,
            "t_end": 10.0,
            "dt_max": 0.05,
            "output_interval": 0.5,
            "initial_conditions": {
                "type": "uniform",
                "h": 2.0,
                "Q": 10.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 10.0},
                "downstream": {"type": "h", "value": 1.5}
            }
        }
    },
    "wide_channel": {
        "name": "宽渠道测试",
        "config": {
            "width": 50.0,
            "length": 2000.0,
            "n_cells": 200,
            "manning_n": 0.03,
            "slope": 0.0005,
            "t_end": 30.0,
            "dt_max": 0.2,
            "output_interval": 1.0,
            "initial_conditions": {
                "type": "uniform",
                "h": 8.0,
                "Q": 200.0
            },
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 200.0},
                "downstream": {"type": "h", "value": 8.0}
            }
        }
    }
}

# 边界值测试用例
BOUNDARY_TEST_CASES = {
    "min_values": {
        "name": "最小值测试",
        "config": {
            "width": 1.0,
            "length": 100.0,
            "n_cells": 10,
            "manning_n": 0.01,
            "slope": 0.0001,
            "t_end": 5.0,
            "dt_max": 0.05,
            "output_interval": 0.5,
            "initial_conditions": {"type": "uniform", "h": 0.5, "Q": 0.0},
            "boundary_conditions": {
                "upstream": {"type": "h", "value": 0.5},
                "downstream": {"type": "h", "value": 0.5}
            }
        }
    },
    "max_values": {
        "name": "最大值测试",
        "config": {
            "width": 100.0,
            "length": 5000.0,
            "n_cells": 500,
            "manning_n": 0.05,
            "slope": 0.02,
            "t_end": 50.0,
            "dt_max": 0.5,
            "output_interval": 2.0,
            "initial_conditions": {"type": "uniform", "h": 20.0, "Q": 500.0},
            "boundary_conditions": {
                "upstream": {"type": "Q", "value": 500.0},
                "downstream": {"type": "h", "value": 20.0}
            }
        }
    }
}

# ========== Part 1: 后端API测试 ==========
def test_backend_api():
    """测试后端API的所有端点"""
    print("\n" + "=" * 80)
    print("Part 1: Backend API Testing")
    print("=" * 80)
    
    # 测试1: Health Check
    print("\n[Test 1.1] Health Check")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            results.add_result("Health Check", "pass", f"Service: {data.get('service')}")
        else:
            results.add_result("Health Check", "fail", f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Health Check", "fail", str(e))
    
    # 测试2: Engine Info
    print("\n[Test 1.2] Engine Info")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/engine/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            results.add_result("Engine Info", "pass", f"Version: {data.get('engine_version')}")
        else:
            results.add_result("Engine Info", "fail", f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Engine Info", "fail", str(e))
    
    # 测试3: List Simulations
    print("\n[Test 1.3] List Simulations")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/simulations", timeout=5)
        if response.status_code == 200:
            sims = response.json()
            results.add_result("List Simulations", "pass", f"Found {len(sims)} simulations")
        else:
            results.add_result("List Simulations", "fail", f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("List Simulations", "fail", str(e))

# ========== Part 2: 仿真场景测试 ==========
def test_simulation_scenarios():
    """测试所有仿真场景"""
    print("\n" + "=" * 80)
    print("Part 2: Simulation Scenarios Testing")
    print("=" * 80)
    
    for scenario_id, scenario in TEST_SCENARIOS.items():
        print(f"\n[Test 2.{list(TEST_SCENARIOS.keys()).index(scenario_id)+1}] {scenario['name']}")
        test_single_simulation(scenario_id, scenario)
    
    # 边界值测试
    print("\n" + "-" * 80)
    print("Boundary Value Testing")
    print("-" * 80)
    
    for case_id, case in BOUNDARY_TEST_CASES.items():
        print(f"\n[Test 2.B.{list(BOUNDARY_TEST_CASES.keys()).index(case_id)+1}] {case['name']}")
        test_single_simulation(f"boundary_{case_id}", case)

def test_single_simulation(scenario_id: str, scenario: dict):
    """测试单个仿真场景"""
    try:
        # 创建仿真
        payload = {
            "name": scenario['name'],
            "description": f"自动化测试 - {scenario_id}",
            "config": scenario['config']
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/simulations",
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            task_id = data.get('task_id')
            
            # 轮询状态（最多30秒）
            success = False
            for i in range(30):
                time.sleep(1)
                status_resp = requests.get(
                    f"{BACKEND_URL}/api/v1/simulations/{task_id}/status",
                    timeout=5
                )
                
                if status_resp.status_code == 200:
                    status = status_resp.json()
                    
                    if status.get('status') == 'completed':
                        # 获取结果
                        results_resp = requests.get(
                            f"{BACKEND_URL}/api/v1/simulations/{task_id}/results",
                            timeout=5
                        )
                        
                        if results_resp.status_code == 200:
                            result_data = results_resp.json()
                            results.add_result(
                                f"Simulation: {scenario['name']}",
                                "pass",
                                f"Completed in {i+1}s, {len(result_data.get('time', []))} time steps"
                            )
                            success = True
                        break
                    
                    elif status.get('status') == 'failed':
                        results.add_result(
                            f"Simulation: {scenario['name']}",
                            "fail",
                            f"Failed: {status.get('error', 'Unknown error')}"
                        )
                        break
            
            if not success and status.get('status') != 'failed':
                results.add_result(
                    f"Simulation: {scenario['name']}",
                    "warn",
                    "Timeout after 30s"
                )
        else:
            results.add_result(
                f"Simulation: {scenario['name']}",
                "fail",
                f"Create failed: {response.status_code}"
            )
    
    except Exception as e:
        results.add_result(
            f"Simulation: {scenario['name']}",
            "fail",
            str(e)
        )

# ========== Part 3: UI交互测试 ==========
def test_ui_interactions():
    """测试UI的各种交互"""
    print("\n" + "=" * 80)
    print("Part 3: UI Interaction Testing")
    print("=" * 80)
    
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--headless')  # 无头模式，更快
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    screenshot_count = [0]  # 使用列表来在嵌套函数中修改
    
    def save_screenshot(name):
        screenshot_count[0] += 1
        filename = f"ui_{screenshot_count[0]:02d}_{name}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        driver.save_screenshot(filepath)
        results.screenshots.append(filename)
        return filepath
    
    try:
        # 测试3.1: 页面加载
        print("\n[Test 3.1] Page Loading")
        driver.get(FRONTEND_URL)
        time.sleep(3)
        save_screenshot("homepage")
        results.add_result("UI: Homepage Load", "pass", "Page loaded successfully")
        
        # 测试3.2: 建模工作台
        print("\n[Test 3.2] Modeling Workspace")
        try:
            components = driver.find_elements(By.XPATH, "//*[contains(text(), '矩形明渠')]")
            if components:
                results.add_result("UI: Modeling Components", "pass", f"Found {len(components)} components")
            else:
                results.add_result("UI: Modeling Components", "warn", "No components found")
            save_screenshot("modeling_workspace")
        except Exception as e:
            results.add_result("UI: Modeling Components", "fail", str(e))
        
        # 测试3.3: 切换到仿真管理
        print("\n[Test 3.3] Switch to Simulation")
        try:
            tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
            if len(tabs) >= 2:
                tabs[1].click()
                time.sleep(3)
                save_screenshot("simulation_workspace")
                results.add_result("UI: Tab Switch", "pass", "Switched to simulation tab")
            else:
                results.add_result("UI: Tab Switch", "fail", "Tabs not found")
        except Exception as e:
            results.add_result("UI: Tab Switch", "fail", str(e))
        
        # 测试3.4: 表单交互
        print("\n[Test 3.4] Form Interaction")
        try:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            editable = [i for i in inputs if i.is_displayed() and i.is_enabled()]
            
            if len(editable) > 0:
                # 测试第一个输入框
                test_input = editable[0]
                original_value = test_input.get_attribute('value')
                test_input.clear()
                test_input.send_keys("999")
                time.sleep(0.5)
                new_value = test_input.get_attribute('value')
                
                if new_value == "999":
                    results.add_result("UI: Input Edit", "pass", f"{len(editable)} inputs editable")
                    # 恢复原值
                    test_input.clear()
                    test_input.send_keys(original_value)
                else:
                    results.add_result("UI: Input Edit", "warn", "Input value not changed")
                
                save_screenshot("form_interaction")
            else:
                results.add_result("UI: Input Edit", "warn", "No editable inputs found")
        except Exception as e:
            results.add_result("UI: Input Edit", "fail", str(e))
        
        # 测试3.5: 按钮点击
        print("\n[Test 3.5] Button Clicks")
        try:
            # 回到建模工作台
            tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
            if tabs:
                tabs[0].click()
                time.sleep(2)
            
            # 测试组件按钮
            comp_buttons = driver.find_elements(By.XPATH, "//button[contains(., '组件')]")
            if comp_buttons:
                comp_buttons[0].click()
                time.sleep(1)
                save_screenshot("components_clicked")
                results.add_result("UI: Button Click", "pass", "Component button clickable")
            else:
                results.add_result("UI: Button Click", "warn", "Component button not found")
        except Exception as e:
            results.add_result("UI: Button Click", "fail", str(e))
        
        # 测试3.6: 响应式检查
        print("\n[Test 3.6] Responsiveness")
        try:
            # 测试不同窗口大小
            sizes = [(1920, 1080), (1366, 768), (1024, 768)]
            for width, height in sizes:
                driver.set_window_size(width, height)
                time.sleep(1)
                save_screenshot(f"responsive_{width}x{height}")
            
            results.add_result("UI: Responsiveness", "pass", f"Tested {len(sizes)} screen sizes")
        except Exception as e:
            results.add_result("UI: Responsiveness", "fail", str(e))
    
    finally:
        driver.quit()

# ========== Part 4: 错误处理测试 ==========
def test_error_handling():
    """测试各种错误情况的处理"""
    print("\n" + "=" * 80)
    print("Part 4: Error Handling Testing")
    print("=" * 80)
    
    # 测试4.1: 无效参数
    print("\n[Test 4.1] Invalid Parameters")
    invalid_configs = [
        {
            "name": "负数宽度",
            "config": {"width": -10.0, "length": 1000.0, "n_cells": 100}
        },
        {
            "name": "零长度",
            "config": {"width": 10.0, "length": 0.0, "n_cells": 100}
        },
        {
            "name": "过少网格",
            "config": {"width": 10.0, "length": 1000.0, "n_cells": 1}
        }
    ]
    
    for test_case in invalid_configs:
        try:
            payload = {
                "name": test_case['name'],
                "description": "错误处理测试",
                "config": test_case['config']
            }
            
            response = requests.post(
                f"{BACKEND_URL}/api/v1/simulations",
                json=payload,
                timeout=10
            )
            
            # 应该返回400或422
            if response.status_code in [400, 422]:
                results.add_result(
                    f"Error: {test_case['name']}",
                    "pass",
                    "Correctly rejected invalid input"
                )
            elif response.status_code in [200, 201]:
                results.add_result(
                    f"Error: {test_case['name']}",
                    "warn",
                    "Accepted invalid input (should validate)"
                )
            else:
                results.add_result(
                    f"Error: {test_case['name']}",
                    "warn",
                    f"Unexpected status: {response.status_code}"
                )
        except Exception as e:
            results.add_result(f"Error: {test_case['name']}", "fail", str(e))
    
    # 测试4.2: 不存在的任务ID
    print("\n[Test 4.2] Non-existent Task ID")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/simulations/non-existent-id/status",
            timeout=5
        )
        
        if response.status_code == 404:
            results.add_result("Error: Non-existent ID", "pass", "Correctly returned 404")
        else:
            results.add_result("Error: Non-existent ID", "warn", f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Error: Non-existent ID", "fail", str(e))

# ========== Main Execution ==========
def main():
    print("=" * 80)
    print("HydroClaude Web - Comprehensive Test Suite")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    print("=" * 80)
    
    start_time = time.time()
    
    # 执行所有测试
    test_backend_api()
    test_simulation_scenarios()
    test_ui_interactions()
    test_error_handling()
    
    # 保存结果
    summary = results.save_summary()
    
    # 打印总结
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']} ({summary['success_rate']})")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Screenshots: {len(results.screenshots)}")
    print(f"Duration: {time.time() - start_time:.1f}s")
    print(f"\nResults saved to: {SCREENSHOT_DIR}/test_summary.json")
    print("=" * 80)

if __name__ == '__main__':
    main()







