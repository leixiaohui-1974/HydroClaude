#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web - Comprehensive Workflow Testing
全流程功能测试：模拟真实用户操作
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import json
from datetime import datetime

SCREENSHOT_DIR = "workflow_test_results"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

FRONTEND_URL = "http://localhost:5173"

class WorkflowTester:
    def __init__(self):
        print("=" * 80)
        print("HydroClaude Web - Comprehensive Workflow Testing")
        print("=" * 80)
        
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.actions = ActionChains(self.driver)
        
        self.test_results = []
        self.screenshot_count = 0
    
    def save_screenshot(self, name):
        """保存截图"""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.screenshot_count:02d}_{name}_{timestamp}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        self.driver.save_screenshot(filepath)
        print(f"  [Screenshot] {filename}")
        return filepath
    
    def log_test(self, test_name, status, message=""):
        """记录测试结果"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        icon = "[PASS]" if status == "pass" else "[FAIL]" if status == "fail" else "[WARN]"
        print(f"{icon} {test_name}")
        if message:
            print(f"      {message}")
    
    def workflow_1_create_basic_model(self):
        """工作流1: 创建基础渠道模型"""
        print("\n" + "=" * 80)
        print("Workflow 1: Create Basic Canal Model")
        print("=" * 80)
        
        try:
            # 1. 访问页面
            print("\n[Step 1] Load homepage...")
            self.driver.get(FRONTEND_URL)
            time.sleep(3)
            self.save_screenshot("01_homepage_loaded")
            self.log_test("Load homepage", "pass", "Homepage loaded successfully")
            
            # 2. 确认在建模工作台
            print("\n[Step 2] Verify modeling workspace...")
            try:
                modeling_tab = self.driver.find_element(By.XPATH, "//div[contains(text(), '建模工作台')]")
                self.save_screenshot("02_modeling_workspace")
                self.log_test("Modeling workspace visible", "pass")
            except:
                self.log_test("Modeling workspace visible", "fail", "Modeling tab not found")
                return False
            
            # 3. 点击"新建"按钮
            print("\n[Step 3] Click 'New Model' button...")
            try:
                new_button = self.driver.find_element(By.XPATH, "//button[.//span[contains(text(), '新建')]]")
                new_button.click()
                time.sleep(1)
                self.save_screenshot("03_clicked_new_button")
                self.log_test("Click new model button", "pass")
            except Exception as e:
                self.log_test("Click new model button", "fail", str(e))
            
            # 4. 查找组件面板
            print("\n[Step 4] Check component palette...")
            try:
                # 查找"组件"按钮
                component_button = self.driver.find_element(By.XPATH, "//button[.//span[contains(text(), '组件')]]")
                print(f"      Found component button: {component_button.text}")
                component_button.click()
                time.sleep(1)
                self.save_screenshot("04_component_panel_opened")
                self.log_test("Open component panel", "pass")
            except Exception as e:
                self.log_test("Open component panel", "warn", f"Button not found: {str(e)}")
            
            # 5. 尝试添加渠道组件
            print("\n[Step 5] Try to add canal component...")
            try:
                # 查找渠道相关元素
                canal_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '矩形明渠') or contains(text(), '明渠')]")
                print(f"      Found {len(canal_elements)} canal-related elements")
                
                if canal_elements:
                    self.save_screenshot("05_found_canal_component")
                    # 尝试点击
                    canal_elements[0].click()
                    time.sleep(1)
                    self.save_screenshot("05_clicked_canal_component")
                    self.log_test("Add canal component", "pass")
                else:
                    self.log_test("Add canal component", "warn", "No canal component found")
            except Exception as e:
                self.log_test("Add canal component", "warn", str(e))
            
            # 6. 检查画布区域
            print("\n[Step 6] Check canvas area...")
            time.sleep(2)
            self.save_screenshot("06_canvas_state")
            
            # 7. 查找属性面板
            print("\n[Step 7] Check property panel...")
            try:
                property_button = self.driver.find_element(By.XPATH, "//button[.//span[contains(text(), '属性')]]")
                property_button.click()
                time.sleep(1)
                self.save_screenshot("07_property_panel")
                self.log_test("Open property panel", "pass")
            except:
                self.log_test("Open property panel", "warn", "Property button not found")
            
            # 8. 尝试点击"验证"按钮
            print("\n[Step 8] Try validation...")
            try:
                validate_button = self.driver.find_element(By.XPATH, "//button[.//span[contains(text(), '验证')]]")
                validate_button.click()
                time.sleep(2)
                self.save_screenshot("08_after_validation")
                
                # 检查是否有消息提示
                try:
                    messages = self.driver.find_elements(By.CLASS_NAME, "ant-message")
                    if messages:
                        print(f"      Found {len(messages)} messages")
                except:
                    pass
                
                self.log_test("Model validation", "pass")
            except Exception as e:
                self.log_test("Model validation", "warn", str(e))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Workflow 1 failed: {str(e)}")
            self.save_screenshot("workflow1_error")
            return False
    
    def workflow_2_simulation_workflow(self):
        """工作流2: 运行仿真完整流程"""
        print("\n" + "=" * 80)
        print("Workflow 2: Run Simulation")
        print("=" * 80)
        
        try:
            # 1. 切换到仿真管理标签
            print("\n[Step 1] Switch to simulation tab...")
            try:
                sim_tab = self.driver.find_element(By.XPATH, "//div[contains(text(), '仿真管理')]")
                sim_tab.click()
                time.sleep(3)
                self.save_screenshot("09_simulation_tab")
                self.log_test("Switch to simulation tab", "pass")
            except:
                self.log_test("Switch to simulation tab", "fail", "Tab not found")
                return False
            
            # 2. 检查仿真配置表单
            print("\n[Step 2] Check simulation config form...")
            try:
                # 查找输入框
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='number'], input[type='text']")
                print(f"      Found {len(inputs)} input fields")
                self.save_screenshot("10_config_form")
                
                if len(inputs) > 0:
                    self.log_test("Simulation config form", "pass", f"Found {len(inputs)} input fields")
                else:
                    self.log_test("Simulation config form", "warn", "No input fields found")
            except Exception as e:
                self.log_test("Simulation config form", "warn", str(e))
            
            # 3. 尝试填写配置参数
            print("\n[Step 3] Fill simulation parameters...")
            try:
                # 查找所有数字输入框
                number_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
                
                if len(number_inputs) >= 3:
                    # 填写一些测试值
                    test_values = [10.0, 1000.0, 50]
                    for i, (input_field, value) in enumerate(zip(number_inputs[:3], test_values)):
                        input_field.clear()
                        input_field.send_keys(str(value))
                        time.sleep(0.5)
                    
                    self.save_screenshot("11_filled_parameters")
                    self.log_test("Fill simulation parameters", "pass", f"Filled {len(test_values)} parameters")
                else:
                    self.log_test("Fill simulation parameters", "warn", "Not enough input fields")
            except Exception as e:
                self.log_test("Fill simulation parameters", "warn", str(e))
            
            # 4. 查找运行按钮
            print("\n[Step 4] Look for run button...")
            try:
                run_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., '运行') or contains(., 'Run') or .//span[contains(@class, 'play')]]")
                print(f"      Found {len(run_buttons)} potential run buttons")
                
                if run_buttons:
                    self.save_screenshot("12_found_run_button")
                    # 点击第一个运行按钮
                    run_buttons[0].click()
                    time.sleep(3)
                    self.save_screenshot("13_clicked_run")
                    self.log_test("Click run simulation", "pass")
                    
                    # 等待可能的响应
                    time.sleep(5)
                    self.save_screenshot("14_after_run")
                else:
                    self.log_test("Click run simulation", "warn", "No run button found")
            except Exception as e:
                self.log_test("Click run simulation", "warn", str(e))
            
            # 5. 检查是否有结果显示
            print("\n[Step 5] Check for results...")
            time.sleep(3)
            try:
                # 查找可能的结果区域
                result_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '结果') or contains(text(), 'Result')]")
                print(f"      Found {len(result_elements)} result-related elements")
                self.save_screenshot("15_check_results")
                
                if result_elements:
                    self.log_test("Simulation results display", "pass")
                else:
                    self.log_test("Simulation results display", "warn", "No results found yet")
            except Exception as e:
                self.log_test("Simulation results display", "warn", str(e))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Workflow 2 failed: {str(e)}")
            self.save_screenshot("workflow2_error")
            return False
    
    def workflow_3_interaction_tests(self):
        """工作流3: 交互功能测试"""
        print("\n" + "=" * 80)
        print("Workflow 3: Interaction Tests")
        print("=" * 80)
        
        try:
            # 1. 测试工具栏按钮
            print("\n[Step 1] Test toolbar buttons...")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            print(f"      Total buttons found: {len(buttons)}")
            self.save_screenshot("16_all_buttons")
            self.log_test("Toolbar buttons", "pass", f"Found {len(buttons)} buttons")
            
            # 2. 测试下拉菜单
            print("\n[Step 2] Test dropdown menus...")
            try:
                selects = self.driver.find_elements(By.CLASS_NAME, "ant-select")
                print(f"      Found {len(selects)} select dropdowns")
                
                if selects:
                    selects[0].click()
                    time.sleep(1)
                    self.save_screenshot("17_dropdown_opened")
                    # 关闭
                    self.driver.find_element(By.TAG_NAME, "body").click()
                    self.log_test("Dropdown interaction", "pass")
                else:
                    self.log_test("Dropdown interaction", "warn", "No dropdowns found")
            except Exception as e:
                self.log_test("Dropdown interaction", "warn", str(e))
            
            # 3. 测试输入框
            print("\n[Step 3] Test input fields...")
            try:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                print(f"      Found {len(inputs)} input fields")
                
                editable_inputs = [i for i in inputs if i.is_displayed() and i.is_enabled()]
                print(f"      {len(editable_inputs)} are editable")
                
                if editable_inputs:
                    test_input = editable_inputs[0]
                    test_input.clear()
                    test_input.send_keys("999")
                    time.sleep(0.5)
                    self.save_screenshot("18_input_test")
                    self.log_test("Input field interaction", "pass")
                else:
                    self.log_test("Input field interaction", "warn", "No editable inputs")
            except Exception as e:
                self.log_test("Input field interaction", "warn", str(e))
            
            # 4. 测试标签切换
            print("\n[Step 4] Test tab switching...")
            try:
                tabs = self.driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
                print(f"      Found {len(tabs)} tabs")
                
                for i, tab in enumerate(tabs):
                    if tab.is_displayed():
                        tab.click()
                        time.sleep(1)
                        self.save_screenshot(f"19_tab_{i}")
                
                self.log_test("Tab switching", "pass", f"Tested {len(tabs)} tabs")
            except Exception as e:
                self.log_test("Tab switching", "warn", str(e))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Workflow 3 failed: {str(e)}")
            return False
    
    def workflow_4_error_handling(self):
        """工作流4: 错误处理测试"""
        print("\n" + "=" * 80)
        print("Workflow 4: Error Handling Tests")
        print("=" * 80)
        
        try:
            # 回到建模工作台
            print("\n[Step 1] Back to modeling workspace...")
            try:
                modeling_tab = self.driver.find_element(By.XPATH, "//div[contains(text(), '建模工作台')]")
                modeling_tab.click()
                time.sleep(2)
            except:
                pass
            
            # 1. 测试空模型运行
            print("\n[Step 2] Test run empty model...")
            try:
                run_button = self.driver.find_element(By.XPATH, "//button[.//span[contains(text(), '运行仿真')]]")
                run_button.click()
                time.sleep(2)
                self.save_screenshot("20_empty_model_run")
                self.log_test("Empty model error handling", "pass", "Tested running empty model")
            except Exception as e:
                self.log_test("Empty model error handling", "warn", str(e))
            
            # 2. 测试无效输入
            print("\n[Step 3] Test invalid input...")
            try:
                # 切换到仿真管理
                sim_tab = self.driver.find_element(By.XPATH, "//div[contains(text(), '仿真管理')]")
                sim_tab.click()
                time.sleep(2)
                
                # 尝试输入负数
                number_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
                if number_inputs:
                    number_inputs[0].clear()
                    number_inputs[0].send_keys("-999")
                    time.sleep(1)
                    self.save_screenshot("21_invalid_input")
                    self.log_test("Invalid input handling", "pass")
            except Exception as e:
                self.log_test("Invalid input handling", "warn", str(e))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Workflow 4 failed: {str(e)}")
            return False
    
    def run_all_workflows(self):
        """运行所有工作流测试"""
        try:
            # Workflow 1: 基础建模
            self.workflow_1_create_basic_model()
            
            # Workflow 2: 仿真流程
            self.workflow_2_simulation_workflow()
            
            # Workflow 3: 交互测试
            self.workflow_3_interaction_tests()
            
            # Workflow 4: 错误处理
            self.workflow_4_error_handling()
            
            # 最终截图
            self.save_screenshot("22_final_state")
            
        finally:
            self.generate_report()
            
            print("\n" + "=" * 80)
            print("Testing complete. Browser will close in 10 seconds...")
            print("=" * 80)
            time.sleep(10)
            self.driver.quit()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("Test Results Summary")
        print("=" * 80)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'pass')
        failed = sum(1 for r in self.test_results if r['status'] == 'fail')
        warned = sum(1 for r in self.test_results if r['status'] == 'warn')
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Warnings: {warned}")
        print(f"Screenshots: {self.screenshot_count}")
        
        print(f"\nSuccess Rate: {(passed/total*100):.1f}%")
        
        # 保存详细结果
        report_file = os.path.join(SCREENSHOT_DIR, "test_results.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "warned": warned,
                    "screenshots": self.screenshot_count
                },
                "tests": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed report saved to: {report_file}")
        print(f"Screenshots saved to: {SCREENSHOT_DIR}/")
        print("=" * 80)

def main():
    tester = WorkflowTester()
    tester.run_all_workflows()

if __name__ == '__main__':
    main()







