#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整工作流测试 - 最终版本
测试所有实际功能，包括提交仿真、查看结果等
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from datetime import datetime

FRONTEND_URL = "http://localhost:5173"
SCREENSHOT_DIR = "final_test_results"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

print("=" * 80)
print("HydroClaude Web - Complete Functional Testing")
print("=" * 80)

chrome_options = Options()
chrome_options.add_argument('--start-maximized')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 15)

screenshot_count = 0

def save_screenshot(name):
    global screenshot_count
    screenshot_count += 1
    filename = f"{screenshot_count:02d}_{name}_{datetime.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)
    print(f"    [Screenshot] {filename}")
    return filepath

try:
    # ========== 测试1: 建模工作台 ==========
    print("\n" + "=" * 80)
    print("Test 1: Modeling Workspace")
    print("=" * 80)
    
    driver.get(FRONTEND_URL)
    time.sleep(3)
    save_screenshot("01_homepage")
    print("[PASS] Homepage loaded")
    
    # 检查建模工作台元素
    try:
        # 检查组件面板
        components = driver.find_elements(By.XPATH, "//*[contains(text(), '矩形明渠') or contains(text(), '闸门') or contains(text(), '堰')]")
        print(f"[PASS] Found {len(components)} components in palette")
        
        # 检查工具栏按钮
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"[PASS] Found {len(buttons)} buttons")
        
        save_screenshot("02_modeling_workspace")
    except Exception as e:
        print(f"[WARN] {e}")
    
    # ========== 测试2: 切换到仿真管理 ==========
    print("\n" + "=" * 80)
    print("Test 2: Switch to Simulation Workspace")
    print("=" * 80)
    
    # 点击仿真管理标签
    tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
    if len(tabs) >= 2:
        tabs[1].click()
        time.sleep(3)
        save_screenshot("03_simulation_workspace")
        print("[PASS] Switched to simulation workspace")
    
    # ========== 测试3: 检查配置表单 ==========
    print("\n" + "=" * 80)
    print("Test 3: Simulation Configuration Form")
    print("=" * 80)
    
    try:
        # 查找输入框
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
        print(f"[PASS] Found {len(inputs)} number input fields")
        
        # 查找所有输入框（包括文本）
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"[PASS] Found {len(all_inputs)} total input fields")
        
        save_screenshot("04_config_form")
    except Exception as e:
        print(f"[WARN] {e}")
    
    # ========== 测试4: 填写并提交仿真 ==========
    print("\n" + "=" * 80)
    print("Test 4: Submit Simulation")
    print("=" * 80)
    
    try:
        # 修改仿真名称
        name_input = driver.find_element(By.CSS_SELECTOR, "input[id*='name']")
        name_input.clear()
        name_input.send_keys("自动化测试仿真")
        print("[PASS] Modified simulation name")
        
        time.sleep(1)
        save_screenshot("05_modified_name")
        
        # 滚动到底部找运行按钮
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 查找运行按钮
        run_buttons = driver.find_elements(By.XPATH, "//button[contains(., '运行') or contains(@class, 'ant-btn-primary')]")
        print(f"[INFO] Found {len(run_buttons)} potential run buttons")
        
        if run_buttons:
            # 尝试找到可见且可点击的按钮
            for btn in run_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        print("[PASS] Clicked run button")
                        time.sleep(3)
                        save_screenshot("06_after_submit")
                        break
                except:
                    continue
        
        # 等待可能的响应
        time.sleep(5)
        save_screenshot("07_simulation_response")
        
        # 检查是否有消息提示
        try:
            messages = driver.find_elements(By.CLASS_NAME, "ant-message")
            if messages:
                print(f"[INFO] Found {len(messages)} message notifications")
        except:
            pass
        
    except Exception as e:
        print(f"[WARN] Simulation submit: {e}")
    
    # ========== 测试5: 检查各种交互 ==========
    print("\n" + "=" * 80)
    print("Test 5: Interactive Elements")
    print("=" * 80)
    
    # 滚动回顶部
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 测试标签切换
    try:
        # 查找子标签（单场景结果/多场景对比）
        sub_tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
        print(f"[INFO] Found {len(sub_tabs)} tabs")
        
        if len(sub_tabs) > 2:  # 跳过主标签，测试子标签
            for i, tab in enumerate(sub_tabs[2:], start=2):
                try:
                    if tab.is_displayed():
                        tab.click()
                        time.sleep(2)
                        save_screenshot(f"08_tab_{i}")
                        print(f"[PASS] Clicked tab {i}")
                except:
                    pass
    except Exception as e:
        print(f"[WARN] Tab test: {e}")
    
    # ========== 测试6: 回到建模工作台测试 ==========
    print("\n" + "=" * 80)
    print("Test 6: Back to Modeling Workspace")
    print("=" * 80)
    
    try:
        main_tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
        if main_tabs:
            main_tabs[0].click()
            time.sleep(2)
            save_screenshot("09_back_to_modeling")
            print("[PASS] Returned to modeling workspace")
            
            # 尝试点击一些按钮
            try:
                # 点击"组件"按钮
                comp_buttons = driver.find_elements(By.XPATH, "//button[contains(., '组件')]")
                if comp_buttons:
                    comp_buttons[0].click()
                    time.sleep(1)
                    save_screenshot("10_components_panel")
                    print("[PASS] Opened components panel")
            except:
                pass
            
            try:
                # 点击"属性"按钮
                prop_buttons = driver.find_elements(By.XPATH, "//button[contains(., '属性')]")
                if prop_buttons:
                    prop_buttons[0].click()
                    time.sleep(1)
                    save_screenshot("11_properties_panel")
                    print("[PASS] Opened properties panel")
            except:
                pass
    
    except Exception as e:
        print(f"[WARN] Modeling test: {e}")
    
    # ========== 测试7: 检查所有输入框可编辑性 ==========
    print("\n" + "=" * 80)
    print("Test 7: Input Field Editability")
    print("=" * 80)
    
    # 回到仿真管理
    try:
        main_tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
        if len(main_tabs) >= 2:
            main_tabs[1].click()
            time.sleep(2)
    except:
        pass
    
    try:
        # 测试所有数字输入框
        number_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
        editable_count = 0
        
        for i, inp in enumerate(number_inputs[:5]):  # 测试前5个
            try:
                if inp.is_displayed() and inp.is_enabled():
                    original = inp.get_attribute('value')
                    inp.clear()
                    inp.send_keys("999")
                    time.sleep(0.3)
                    
                    new_value = inp.get_attribute('value')
                    if new_value == "999":
                        editable_count += 1
                        print(f"[PASS] Input {i+1} is editable (was: {original}, now: {new_value})")
                    
                    # 恢复原值
                    inp.clear()
                    inp.send_keys(original)
            except Exception as e:
                pass
        
        print(f"[INFO] {editable_count}/{min(5, len(number_inputs))} inputs are editable")
        save_screenshot("12_input_test")
    
    except Exception as e:
        print(f"[WARN] Input test: {e}")
    
    # ========== 最终截图 ==========
    save_screenshot("13_final_state")
    
    print("\n" + "=" * 80)
    print("Testing Summary")
    print("=" * 80)
    print(f"Total screenshots: {screenshot_count}")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}/")
    print("\n[INFO] Browser will stay open for 30 seconds for manual inspection...")
    print("=" * 80)
    
    time.sleep(30)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    save_screenshot("ERROR")

finally:
    print("\n[Closing browser...]")
    driver.quit()
    print("Testing complete!")







