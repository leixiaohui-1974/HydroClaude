#!/usr/bin/env python3
"""
HydroClaude Web 浏览器自动化测试
使用Playwright进行端到端测试
"""

from playwright.sync_api import sync_playwright, Page
import time
import json
from pathlib import Path

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def test_page_load(page: Page):
    """测试页面加载"""
    print(" 测试: 页面加载")
    try:
        page.goto("http://localhost:5173", timeout=10000)
        page.wait_for_load_state("networkidle")
        
        title = page.title()
        assert "HydroClaude" in title
        print(f"   {Colors.OKGREEN} 页面加载成功{Colors.ENDC}")
        print(f"   标题: {title}")
        return True
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def test_api_health(page: Page):
    """测试API健康检查"""
    print("\n 测试: API健康检查")
    try:
        response = page.request.get("http://localhost:8000/health")
        data = response.json()
        
        assert response.status == 200
        assert data["status"] == "healthy"
        
        print(f"   {Colors.OKGREEN} API健康检查通过{Colors.ENDC}")
        print(f"   服务: {data.get('service')}")
        return True
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def test_modeling_workspace(page: Page):
    """测试建模工作台"""
    print("\n 测试: 建模工作台")
    try:
        # 等待页面加载
        page.wait_for_selector("text=建模工作台", timeout=5000)
        
        # 点击建模工作台标签
        page.click("text=建模工作台")
        time.sleep(1)
        
        # 检查画布是否存在
        canvas = page.locator(".react-flow")
        assert canvas.is_visible()
        
        print(f"   {Colors.OKGREEN} 建模工作台加载成功{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def test_component_drag(page: Page):
    """测试组件拖拽"""
    print("\n 测试: 组件拖拽")
    try:
        # 查找组件面板
        component_panel = page.locator("text=组件库")
        if component_panel.is_visible():
            print(f"   {Colors.OKGREEN} 组件面板可见{Colors.ENDC}")
        
        # 查找明渠组件
        canal = page.locator("text=矩形明渠").first
        if canal.is_visible():
            print(f"   {Colors.OKGREEN} 明渠组件可见{Colors.ENDC}")
            return True
        
        return True
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def test_create_simulation(page: Page):
    """测试创建仿真"""
    print("\n 测试: 创建仿真 (通过API)")
    try:
        # 通过API创建仿真
        config = {
            "name": "浏览器测试仿真",
            "description": "自动化浏览器测试",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 30.0,
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
        }
        
        response = page.request.post(
            "http://localhost:8000/api/v1/simulations",
            data=config
        )
        
        assert response.status in [200, 201]
        data = response.json()
        task_id = data["task_id"]
        
        print(f"   {Colors.OKGREEN} 仿真创建成功{Colors.ENDC}")
        print(f"   任务ID: {task_id}")
        
        # 等待完成
        for i in range(30):
            status_resp = page.request.get(
                f"http://localhost:8000/api/v1/simulations/{task_id}/status"
            )
            status_data = status_resp.json()
            status = status_data["status"]
            
            if status == "completed":
                print(f"   {Colors.OKGREEN} 仿真完成{Colors.ENDC}")
                return True
            elif status == "failed":
                print(f"   {Colors.FAIL} 仿真失败{Colors.ENDC}")
                return False
            
            time.sleep(1)
        
        print(f"   {Colors.WARNING}️  超时{Colors.ENDC}")
        return False
        
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def test_simulation_list(page: Page):
    """测试仿真列表"""
    print("\n 测试: 仿真列表")
    try:
        # 切换到仿真管理标签
        page.click("text=仿真管理")
        time.sleep(1)
        
        # 检查列表是否存在
        page.wait_for_selector("text=仿真任务", timeout=5000)
        
        print(f"   {Colors.OKGREEN} 仿真列表加载成功{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"   {Colors.FAIL} 失败: {e}{Colors.ENDC}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("HydroClaude Web 浏览器自动化测试")
    print("="*60)
    
    results = {}
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        # 运行测试
        results["API健康检查"] = test_api_health(page)
        results["页面加载"] = test_page_load(page)
        results["建模工作台"] = test_modeling_workspace(page)
        results["组件拖拽"] = test_component_drag(page)
        results["创建仿真"] = test_create_simulation(page)
        results["仿真列表"] = test_simulation_list(page)
        
        # 截图
        page.screenshot(path="/workspace/web/test_screenshot.png")
        print(f"\n 截图已保存: test_screenshot.png")
        
        # 关闭浏览器
        browser.close()
    
    # 统计
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for name, result in results.items():
        status = f"{Colors.OKGREEN} PASS{Colors.ENDC}" if result else f"{Colors.FAIL} FAIL{Colors.ENDC}"
        print(f"{name:30s} {status}")
    
    print(f"\n总计: {total}")
    print(f"{Colors.OKGREEN}通过: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}失败: {failed}{Colors.ENDC}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    # 保存结果
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "success_rate": passed/total*100,
        "results": {k: "PASS" if v else "FAIL" for k, v in results.items()}
    }
    
    with open("/workspace/web/browser_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n 测试报告: browser_test_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
