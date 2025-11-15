#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E真实Web界面测试
使用Playwright进行浏览器自动化测试和截图
"""

import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
SCREENSHOTS_DIR = "/workspace/web/screenshots_e2e"

# 创建截图目录
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def take_screenshot(page: Page, name: str):
    """保存截图"""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{name}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    page.screenshot(path=filepath)
    print(f"  📸 截图: {filename}")
    return filepath

def main():
    print("="*80)
    print("  HydroClaude Web - E2E真实界面测试")
    print("="*80)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"前端地址: {FRONTEND_URL}")
    print(f"后端地址: {BACKEND_URL}")
    print(f"截图目录: {SCREENSHOTS_DIR}")
    
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "screenshots": [],
        "errors": []
    }
    
    with sync_playwright() as p:
        # 启动浏览器
        print("\n[1/6] 启动浏览器...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            # 测试1: 加载主页
            print("\n[2/6] 测试主页加载...")
            results["total_tests"] += 1
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查标题
            title = page.title()
            print(f"  页面标题: {title}")
            
            # 截图
            screenshot = take_screenshot(page, "01_homepage")
            results["screenshots"].append(screenshot)
            
            # 检查关键元素
            if page.is_visible("text=HydroClaude"):
                print("  ✅ 页面加载成功")
                results["passed"] += 1
            else:
                print("  ❌ 未找到HydroClaude标题")
                results["failed"] += 1
                results["errors"].append("主页未正确加载")
            
            # 测试2: 导航栏
            print("\n[3/6] 测试导航栏...")
            results["total_tests"] += 1
            
            # 查找导航元素
            nav_items = ["建模工作台", "仿真管理", "结果分析"]
            found_items = 0
            for item in nav_items:
                if page.locator(f"text={item}").count() > 0:
                    print(f"  ✅ 找到: {item}")
                    found_items += 1
                else:
                    print(f"  ⚠️  未找到: {item}")
            
            screenshot = take_screenshot(page, "02_navigation")
            results["screenshots"].append(screenshot)
            
            if found_items >= 2:
                print(f"  ✅ 导航栏正常 ({found_items}/{len(nav_items)})")
                results["passed"] += 1
            else:
                print(f"  ❌ 导航栏不完整 ({found_items}/{len(nav_items)})")
                results["failed"] += 1
                results["errors"].append("导航栏元素缺失")
            
            # 测试3: 建模工作台
            print("\n[4/6] 测试建模工作台...")
            results["total_tests"] += 1
            
            try:
                # 尝试点击建模工作台标签
                if page.locator("text=建模工作台").count() > 0:
                    page.click("text=建模工作台", timeout=5000)
                    time.sleep(2)
                    screenshot = take_screenshot(page, "03_modeling_workspace")
                    results["screenshots"].append(screenshot)
                    print("  ✅ 建模工作台可访问")
                    results["passed"] += 1
                else:
                    print("  ⚠️  未找到建模工作台标签")
                    results["failed"] += 1
                    results["errors"].append("建模工作台不可访问")
            except Exception as e:
                print(f"  ❌ 建模工作台错误: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"建模工作台: {str(e)}")
            
            # 测试4: 仿真管理
            print("\n[5/6] 测试仿真管理...")
            results["total_tests"] += 1
            
            try:
                if page.locator("text=仿真管理").count() > 0:
                    page.click("text=仿真管理", timeout=5000)
                    time.sleep(2)
                    screenshot = take_screenshot(page, "04_simulation_management")
                    results["screenshots"].append(screenshot)
                    print("  ✅ 仿真管理可访问")
                    results["passed"] += 1
                else:
                    print("  ⚠️  未找到仿真管理标签")
                    results["failed"] += 1
                    results["errors"].append("仿真管理不可访问")
            except Exception as e:
                print(f"  ❌ 仿真管理错误: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"仿真管理: {str(e)}")
            
            # 测试5: 页面完整性
            print("\n[6/6] 检查页面完整性...")
            results["total_tests"] += 1
            
            # 检查是否有错误消息
            error_indicators = ["error", "Error", "错误", "失败"]
            has_errors = False
            for indicator in error_indicators:
                if indicator.lower() in page.content().lower():
                    print(f"  ⚠️  页面包含'{indicator}'")
                    has_errors = True
            
            screenshot = take_screenshot(page, "05_final_state")
            results["screenshots"].append(screenshot)
            
            if not has_errors:
                print("  ✅ 页面无明显错误")
                results["passed"] += 1
            else:
                print("  ⚠️  页面可能有错误")
                results["failed"] += 1
                results["errors"].append("页面包含错误提示")
            
        except Exception as e:
            print(f"\n❌ 测试异常: {str(e)}")
            results["errors"].append(f"测试异常: {str(e)}")
            take_screenshot(page, "error")
        finally:
            browser.close()
    
    # 打印总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    print(f"  总测试数: {results['total_tests']}")
    print(f"  通过: {results['passed']} ✅")
    print(f"  失败: {results['failed']} ❌")
    print(f"  成功率: {results['passed']/results['total_tests']*100:.1f}%")
    print(f"  截图数: {len(results['screenshots'])}")
    print(f"  截图目录: {SCREENSHOTS_DIR}")
    
    if results['errors']:
        print(f"\n错误列表:")
        for i, error in enumerate(results['errors'], 1):
            print(f"  {i}. {error}")
    
    print(f"\n{'='*80}")
    
    return 0 if results['failed'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
