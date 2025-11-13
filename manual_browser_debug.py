#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动打开浏览器进行调试，查看控制台错误
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

FRONTEND_URL = "http://localhost:5173"

print("=" * 80)
print("Opening browser for manual debugging")
print("=" * 80)
print("\nInstructions:")
print("1. Browser will open and stay open for 5 minutes")
print("2. Open Developer Tools (F12)")
print("3. Switch to 'Console' tab")
print("4. Click on '仿真管理' tab")
print("5. Check for any JavaScript errors")
print("6. Also check 'Network' tab for failed requests")
print("=" * 80)

chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--disable-gpu')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 访问页面
    driver.get(FRONTEND_URL)
    time.sleep(3)
    
    # 获取浏览器控制台日志
    print("\n[Browser Console Logs]")
    logs = driver.get_log('browser')
    for log in logs:
        print(f"  [{log['level']}] {log['message']}")
    
    if not logs:
        print("  No console logs yet")
    
    print("\n[Waiting for manual inspection...]")
    print("Browser will stay open for 5 minutes...")
    print("Press Ctrl+C to close earlier")
    
    # 保持浏览器打开5分钟供手动检查
    time.sleep(300)
    
except KeyboardInterrupt:
    print("\n\n[Interrupted by user]")
finally:
    print("\n[Closing browser...]")
    driver.quit()







