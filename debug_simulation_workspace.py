#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试仿真管理页面loading问题 - 捕获详细的浏览器日志
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import time
import json
from datetime import datetime

FRONTEND_URL = "http://localhost:5173"

print("=" * 80)
print("Debugging Simulation Workspace Loading Issue")
print("=" * 80)

# 启用Chrome的详细日志
chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--enable-logging')
chrome_options.add_argument('--v=1')
# 启用浏览器日志
chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    # Step 1: 访问页面
    print("\n[Step 1] Loading homepage...")
    driver.get(FRONTEND_URL)
    time.sleep(3)
    
    # 获取初始控制台日志
    print("\n[Initial Console Logs]")
    logs = driver.get_log('browser')
    for log in logs:
        print(f"  [{log['level']}] {log['message']}")
    
    # Step 2: 点击仿真管理标签
    print("\n[Step 2] Clicking simulation tab...")
    try:
        # 尝试多种方式定位标签
        tab = None
        try:
            tab = driver.find_element(By.XPATH, "//div[@class='ant-tabs-tab' and contains(., '仿真管理')]")
        except:
            try:
                tabs = driver.find_elements(By.CLASS_NAME, "ant-tabs-tab")
                if len(tabs) >= 2:
                    tab = tabs[1]  # 第二个标签
            except:
                pass
        
        if tab:
            print(f"  Found tab: {tab.text}")
            tab.click()
            print("  Clicked simulation tab")
        else:
            print("  [WARNING] Tab not found, trying manual navigation")
    
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    # Step 3: 等待并监控loading状态
    print("\n[Step 3] Monitoring loading state...")
    
    for i in range(10):  # 监控10秒
        time.sleep(1)
        
        # 检查是否还有loading
        try:
            loading = driver.find_elements(By.CLASS_NAME, "ant-spin")
            if loading:
                print(f"  [{i+1}s] Still loading... ({len(loading)} spinners)")
            else:
                print(f"  [{i+1}s] No loading spinner")
                break
        except:
            pass
        
        # 获取新的控制台日志
        new_logs = driver.get_log('browser')
        if new_logs:
            print(f"  [{i+1}s] New console logs:")
            for log in new_logs:
                print(f"    [{log['level']}] {log['message']}")
    
    # Step 4: 检查页面状态
    print("\n[Step 4] Checking page state...")
    
    # 检查React是否报错
    try:
        react_errors = driver.find_elements(By.XPATH, "//*[contains(text(), 'Error') or contains(text(), 'error')]")
        if react_errors:
            print(f"  Found {len(react_errors)} error elements:")
            for err in react_errors[:3]:  # 只显示前3个
                print(f"    - {err.text[:100]}")
    except:
        pass
    
    # 检查页面内容
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "加载" in body_text or "loading" in body_text.lower():
            print("  [WARNING] Page still shows loading text")
        if len(body_text) < 100:
            print(f"  [WARNING] Page content very short: {len(body_text)} chars")
    except:
        pass
    
    # Step 5: 截图
    print("\n[Step 5] Taking screenshots...")
    driver.save_screenshot("debug_sim_1_initial.png")
    print("  Saved: debug_sim_1_initial.png")
    
    time.sleep(2)
    driver.save_screenshot("debug_sim_2_after_wait.png")
    print("  Saved: debug_sim_2_after_wait.png")
    
    # Step 6: 检查网络请求
    print("\n[Step 6] Checking network requests...")
    try:
        performance_logs = driver.get_log('performance')
        print(f"  Total performance logs: {len(performance_logs)}")
        
        # 查找失败的请求
        failed_requests = []
        for log in performance_logs:
            try:
                log_entry = json.loads(log['message'])
                message = log_entry.get('message', {})
                method = message.get('method', '')
                
                if method == 'Network.responseReceived':
                    params = message.get('params', {})
                    response = params.get('response', {})
                    status = response.get('status', 0)
                    url = response.get('url', '')
                    
                    if status >= 400:
                        failed_requests.append((url, status))
            except:
                continue
        
        if failed_requests:
            print(f"  Found {len(failed_requests)} failed requests:")
            for url, status in failed_requests[:5]:
                print(f"    - {status}: {url}")
        else:
            print("  No failed requests found")
    
    except Exception as e:
        print(f"  [ERROR] Cannot get performance logs: {e}")
    
    # Step 7: 获取所有控制台日志的汇总
    print("\n[Step 7] Final console log summary...")
    all_logs = driver.get_log('browser')
    
    errors = [log for log in all_logs if log['level'] == 'SEVERE']
    warnings = [log for log in all_logs if log['level'] == 'WARNING']
    
    print(f"  Total logs: {len(all_logs)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    
    if errors:
        print("\n  [ERRORS]:")
        for err in errors[:5]:
            print(f"    {err['message'][:200]}")
    
    if warnings:
        print("\n  [WARNINGS]:")
        for warn in warnings[:3]:
            print(f"    {warn['message'][:200]}")
    
    # 保持浏览器打开60秒供手动检查
    print("\n" + "=" * 80)
    print("Browser will stay open for 60 seconds for manual inspection...")
    print("Check the console (F12) for errors!")
    print("=" * 80)
    time.sleep(60)

except Exception as e:
    print(f"\n[FATAL ERROR] {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n[Closing browser...]")
    driver.quit()
    print("Done!")







