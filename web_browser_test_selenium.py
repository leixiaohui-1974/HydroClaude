#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Web界面自动化测试（带Selenium）
自动打开浏览器、测试功能、保存截图

Author: HydroClaude Team
Date: 2025-11-12
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
import json


def check_services():
    """检查服务状态"""
    print("=" * 80)
    print("Step 1: Checking Services...")
    print("=" * 80)
    
    try:
        import requests
        
        # 检查后端
        try:
            resp = requests.get('http://localhost:8000/health', timeout=3)
            if resp.status_code == 200:
                print("  [OK] Backend API: Running (http://localhost:8000)")
                backend_ok = True
            else:
                print(f"  [WARNING] Backend API: Status {resp.status_code}")
                backend_ok = False
        except Exception as e:
            print(f"  [ERROR] Backend API: Not running - {e}")
            print("  Please start: cd web/backend/api_gateway && python main.py")
            backend_ok = False
        
        # 检查前端
        try:
            resp = requests.get('http://localhost:5173', timeout=3)
            if resp.status_code == 200:
                print("  [OK] Frontend: Running (http://localhost:5173)")
                frontend_ok = True
            else:
                print(f"  [WARNING] Frontend: Status {resp.status_code}")
                frontend_ok = False
        except Exception as e:
            print(f"  [ERROR] Frontend: Not running - {e}")
            print("  Please start: cd web/frontend && npm run dev")
            frontend_ok = False
        
        return backend_ok, frontend_ok
    
    except ImportError:
        print("  [ERROR] 'requests' library not installed")
        print("  Install: pip install requests")
        return False, False


def test_with_selenium():
    """使用Selenium进行自动化测试"""
    print("\n" + "=" * 80)
    print("Step 2: Automated Browser Testing (Selenium)")
    print("=" * 80)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        print("\n[INFO] Selenium is available")
        
        # 创建截图目录
        screenshots_dir = Path('web_test_screenshots')
        screenshots_dir.mkdir(exist_ok=True)
        
        # 配置Chrome选项
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 注释掉以显示浏览器
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        
        print("\n[INFO] Starting Chrome browser...")
        
        try:
            # 尝试启动Chrome
            driver = webdriver.Chrome(options=chrome_options)
            print("[OK] Chrome started successfully")
        except Exception as e:
            print(f"[ERROR] Failed to start Chrome: {e}")
            print("\nTrying to install ChromeDriver...")
            
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("[OK] Chrome started with webdriver-manager")
            except:
                print("[ERROR] Please install: pip install webdriver-manager")
                return False
        
        driver.implicitly_wait(10)
        test_results = []
        
        try:
            # Test 1: Homepage Loading
            print("\n" + "-" * 80)
            print("Test 1: Homepage Loading")
            print("-" * 80)
            
            driver.get('http://localhost:5173')
            time.sleep(3)  # 等待页面加载
            
            screenshot_path = screenshots_dir / '01_homepage.png'
            driver.save_screenshot(str(screenshot_path))
            
            title = driver.title
            print(f"  Page Title: {title}")
            print(f"  Screenshot: {screenshot_path}")
            
            # 检查是否有错误
            logs = driver.get_log('browser')
            errors = [log for log in logs if log['level'] == 'SEVERE']
            
            test_results.append({
                'test': 'Homepage Loading',
                'status': 'PASS' if len(errors) == 0 else 'WARNING',
                'title': title,
                'errors': len(errors),
                'screenshot': str(screenshot_path)
            })
            
            if len(errors) == 0:
                print("  [PASS] No console errors")
            else:
                print(f"  [WARNING] {len(errors)} console errors found")
            
            # Test 2: Find Input Fields
            print("\n" + "-" * 80)
            print("Test 2: Model Editor - Input Fields")
            print("-" * 80)
            
            time.sleep(2)
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            
            screenshot_path = screenshots_dir / '02_model_editor.png'
            driver.save_screenshot(str(screenshot_path))
            
            print(f"  Found {len(inputs)} input fields")
            print(f"  Screenshot: {screenshot_path}")
            
            test_results.append({
                'test': 'Model Editor',
                'status': 'PASS' if len(inputs) > 0 else 'FAIL',
                'input_count': len(inputs),
                'screenshot': str(screenshot_path)
            })
            
            if len(inputs) > 0:
                print("  [PASS] Input fields found")
            else:
                print("  [FAIL] No input fields found")
            
            # Test 3: Find Buttons
            print("\n" + "-" * 80)
            print("Test 3: UI Buttons")
            print("-" * 80)
            
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            
            screenshot_path = screenshots_dir / '03_ui_buttons.png'
            driver.save_screenshot(str(screenshot_path))
            
            print(f"  Found {len(buttons)} buttons")
            print(f"  Screenshot: {screenshot_path}")
            
            # 列出前5个按钮的文本
            for i, btn in enumerate(buttons[:5]):
                try:
                    text = btn.text
                    if text:
                        print(f"    Button {i+1}: '{text}'")
                except:
                    pass
            
            test_results.append({
                'test': 'UI Buttons',
                'status': 'PASS' if len(buttons) > 0 else 'FAIL',
                'button_count': len(buttons),
                'screenshot': str(screenshot_path)
            })
            
            if len(buttons) > 0:
                print("  [PASS] Buttons found")
            else:
                print("  [FAIL] No buttons found")
            
            # Test 4: Check for Forms
            print("\n" + "-" * 80)
            print("Test 4: Forms and Controls")
            print("-" * 80)
            
            forms = driver.find_elements(By.TAG_NAME, 'form')
            selects = driver.find_elements(By.TAG_NAME, 'select')
            textareas = driver.find_elements(By.TAG_NAME, 'textarea')
            
            screenshot_path = screenshots_dir / '04_forms_controls.png'
            driver.save_screenshot(str(screenshot_path))
            
            print(f"  Forms: {len(forms)}")
            print(f"  Select dropdowns: {len(selects)}")
            print(f"  Textareas: {len(textareas)}")
            print(f"  Screenshot: {screenshot_path}")
            
            test_results.append({
                'test': 'Forms and Controls',
                'status': 'PASS',
                'forms': len(forms),
                'selects': len(selects),
                'textareas': len(textareas),
                'screenshot': str(screenshot_path)
            })
            
            print("  [PASS] UI elements scanned")
            
            # Test 5: Full Page Screenshot
            print("\n" + "-" * 80)
            print("Test 5: Full Page Screenshot")
            print("-" * 80)
            
            # 滚动到页面底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            screenshot_path = screenshots_dir / '05_full_page.png'
            driver.save_screenshot(str(screenshot_path))
            
            # 滚动回顶部
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            print(f"  Screenshot: {screenshot_path}")
            print("  [PASS] Full page captured")
            
            test_results.append({
                'test': 'Full Page Screenshot',
                'status': 'PASS',
                'screenshot': str(screenshot_path)
            })
            
        finally:
            print("\n" + "=" * 80)
            print("Closing browser...")
            print("=" * 80)
            driver.quit()
        
        # 保存测试结果
        results_path = screenshots_dir / 'test_results.json'
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump({
                'test_time': datetime.now().isoformat(),
                'results': test_results,
                'summary': {
                    'total': len(test_results),
                    'passed': len([r for r in test_results if r['status'] == 'PASS']),
                    'failed': len([r for r in test_results if r['status'] == 'FAIL']),
                    'warnings': len([r for r in test_results if r['status'] == 'WARNING'])
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n[INFO] Test results saved: {results_path}")
        
        # 打印总结
        print("\n" + "=" * 80)
        print("Test Summary")
        print("=" * 80)
        
        passed = len([r for r in test_results if r['status'] == 'PASS'])
        failed = len([r for r in test_results if r['status'] == 'FAIL'])
        warnings = len([r for r in test_results if r['status'] == 'WARNING'])
        
        print(f"\nTotal Tests: {len(test_results)}")
        print(f"  PASSED:   {passed}")
        print(f"  FAILED:   {failed}")
        print(f"  WARNINGS: {warnings}")
        print(f"\nScreenshots saved to: {screenshots_dir.absolute()}")
        
        return True
    
    except ImportError:
        print("\n[ERROR] Selenium not installed")
        print("Install: pip install selenium webdriver-manager")
        return False
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def manual_test_guide():
    """显示手动测试指南"""
    print("\n" + "=" * 80)
    print("Manual Testing Guide")
    print("=" * 80)
    print("\nIf automated testing is not available, please test manually:")
    print("\n1. Open browser: http://localhost:5173")
    print("\n2. Test checklist:")
    print("   [ ] Homepage loads without errors")
    print("   [ ] Input fields are editable")
    print("   [ ] Buttons are clickable")
    print("   [ ] Forms can be submitted")
    print("   [ ] Simulation can be run")
    print("   [ ] Results are displayed")
    print("   [ ] Charts are rendered")
    print("   [ ] Export functionality works")
    print("\n3. Save screenshots manually:")
    print("   - Use Win + Shift + S")
    print("   - Save to: web_test_screenshots/")
    print("\n4. Fill checklist:")
    print("   - Edit: web_test_screenshots/test_checklist.txt")
    print("=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("HydroClaude Web Interface Testing Tool")
    print("=" * 80)
    print(f"\nStart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查服务
    backend_ok, frontend_ok = check_services()
    
    if not backend_ok or not frontend_ok:
        print("\n" + "=" * 80)
        print("[ERROR] Services not ready")
        print("=" * 80)
        print("\nPlease start services first:")
        if not backend_ok:
            print("  Backend: cd web/backend/api_gateway && python main.py")
        if not frontend_ok:
            print("  Frontend: cd web/frontend && npm run dev")
        print("\nOr use: cd web && ./start_servers.sh")
        return
    
    print("\n[OK] All services are running")
    
    # 尝试自动化测试
    selenium_ok = test_with_selenium()
    
    # 如果Selenium不可用，显示手动测试指南
    if not selenium_ok:
        manual_test_guide()
    
    print("\n" + "=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review screenshots in: web_test_screenshots/")
    print("  2. Check test results: web_test_screenshots/test_results.json")
    print("  3. Fill checklist: web_test_screenshots/test_checklist.txt")
    print("  4. Review reports:")
    print("     - FINAL_TEST_REPORT_2025-11-12.md")
    print("     - TEST_EXECUTION_SUMMARY.md")
    print("=" * 80)


if __name__ == '__main__':
    main()







