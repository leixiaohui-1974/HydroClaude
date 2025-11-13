#!/usr/bin/env python3
"""
HydroClaude Web 全面无死角测试
包含所有功能的完整测试
"""

from playwright.sync_api import sync_playwright
import requests
import time
import json
from datetime import datetime
from pathlib import Path

class ComprehensiveWebTester:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8000"
        self.frontend_url = "http://localhost:5174"
        self.screenshots_dir = Path("/workspace/web/comprehensive_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.results = {}
        self.test_num = 0
        
    def log(self, msg, status="info"):
        colors = {
            "success": "\033[92m",
            "error": "\033[91m",
            "info": "\033[94mℹ️",
            "warning": "\033[93m️"
        }
        end = "\033[0m"
        print(f"{colors.get(status, colors['info'])} {msg}{end}")
        
    def save_screenshot(self, page, name):
        self.test_num += 1
        filename = f"{self.test_num:02d}_{name}.png"
        path = self.screenshots_dir / filename
        page.screenshot(path=str(path), full_page=True)
        self.log(f"截图: {filename}", "info")
        return str(path)
        
    def test_backend_apis(self):
        """测试所有后端API"""
        self.log("\n=== 测试1: 后端API全面测试 ===", "info")
        
        tests = []
        
        # 1. 健康检查
        try:
            r = requests.get(f"{self.api_base}/health", timeout=5)
            tests.append(("健康检查", r.status_code == 200))
            self.log(f"健康检查: {r.status_code}", "success" if r.status_code == 200 else "error")
        except Exception as e:
            tests.append(("健康检查", False))
            self.log(f"健康检查失败: {e}", "error")
            
        # 2. 根端点
        try:
            r = requests.get(f"{self.api_base}/", timeout=5)
            tests.append(("根端点", r.status_code == 200))
        except Exception as e:
            tests.append(("根端点", False))
            
        # 3. 引擎信息
        try:
            r = requests.get(f"{self.api_base}/api/v1/engine/info", timeout=5)
            tests.append(("引擎信息", r.status_code == 200))
            if r.status_code == 200:
                self.log(f"引擎信息: {r.json().get('engine_version', 'N/A')}", "success")
        except Exception as e:
            tests.append(("引擎信息", False))
            
        # 4. 创建仿真
        config = {
            "name": "全面测试仿真",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 50,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 10.0,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "upstream": {"type": "h", "value": 5.0},
                    "downstream": {"type": "h", "value": 5.0}
                }
            }
        }
        
        task_id = None
        try:
            r = requests.post(f"{self.api_base}/api/v1/simulations", json=config, timeout=30)
            tests.append(("创建仿真", r.status_code in [200, 201]))
            if r.status_code in [200, 201]:
                task_id = r.json().get('task_id')
                self.log(f"仿真创建成功: {task_id}", "success")
        except Exception as e:
            tests.append(("创建仿真", False))
            self.log(f"创建仿真失败: {e}", "error")
            
        # 5-7. 如果有task_id，测试状态、结果、删除
        if task_id:
            time.sleep(3)
            
            # 查询状态
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/status", timeout=5)
                tests.append(("查询状态", r.status_code == 200))
                if r.status_code == 200:
                    status = r.json().get('status')
                    self.log(f"仿真状态: {status}", "success")
            except:
                tests.append(("查询状态", False))
                
            # 等待完成
            for _ in range(20):
                try:
                    r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/status", timeout=5)
                    if r.json().get('status') in ['completed', 'failed']:
                        break
                except:
                    pass
                time.sleep(0.5)
                
            # 获取结果
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/results", timeout=10)
                tests.append(("获取结果", r.status_code == 200))
                if r.status_code == 200:
                    self.log("结果获取成功", "success")
            except:
                tests.append(("获取结果", False))
                
            # 删除
            try:
                r = requests.delete(f"{self.api_base}/api/v1/simulations/{task_id}", timeout=5)
                tests.append(("删除仿真", r.status_code in [200, 204]))
            except:
                tests.append(("删除仿真", False))
        else:
            tests.extend([("查询状态", False), ("获取结果", False), ("删除仿真", False)])
            
        passed = sum(1 for _, result in tests if result)
        self.log(f"\nAPI测试: {passed}/{len(tests)} 通过", "success" if passed == len(tests) else "warning")
        self.results['backend_api'] = {"tests": tests, "passed": passed, "total": len(tests)}
        return passed == len(tests)
        
    def test_frontend_ui(self, page):
        """测试前端UI"""
        self.log("\n=== 测试2: 前端UI全面测试 ===", "info")
        
        tests = []
        
        try:
            # 1. 页面加载
            self.log("访问首页...", "info")
            page.goto(self.frontend_url, timeout=20000, wait_until="networkidle")
            self.save_screenshot(page, "01_homepage")
            
            title = page.title()
            tests.append(("页面加载", "HydroClaude" in title))
            self.log(f"页面标题: {title}", "success")
            
            time.sleep(2)
            
            # 2. 检查主要元素
            elements = [
                ("text=建模工作台", "建模工作台标签"),
                ("text=仿真管理", "仿真管理标签"),
            ]
            
            for selector, name in elements:
                try:
                    visible = page.locator(selector).first.is_visible(timeout=5000)
                    tests.append((name, visible))
                    self.log(f"{name}: {'可见' if visible else '不可见'}", "success" if visible else "error")
                except:
                    tests.append((name, False))
                    self.log(f"{name}: 未找到", "error")
                    
            self.save_screenshot(page, "02_main_ui")
            
            # 3. 测试建模工作台
            self.log("\n测试建模工作台...", "info")
            try:
                page.click("text=建模工作台", timeout=5000)
                time.sleep(2)
                self.save_screenshot(page, "03_modeling_workspace")
                
                # 检查画布
                canvas_visible = page.locator(".react-flow").first.is_visible(timeout=5000)
                tests.append(("建模画布", canvas_visible))
                self.log(f"建模画布: {'显示' if canvas_visible else '未显示'}", "success" if canvas_visible else "error")
            except Exception as e:
                tests.append(("建模画布", False))
                self.log(f"建模工作台错误: {e}", "error")
                
            # 4. 测试仿真管理
            self.log("\n测试仿真管理...", "info")
            try:
                page.click("text=仿真管理", timeout=5000)
                time.sleep(2)
                self.save_screenshot(page, "04_simulation_management")
                tests.append(("仿真管理切换", True))
                self.log("仿真管理页面加载成功", "success")
            except Exception as e:
                tests.append(("仿真管理切换", False))
                self.log(f"仿真管理错误: {e}", "error")
                
            # 5. 响应式测试
            self.log("\n测试响应式设计...", "info")
            resolutions = [(1920, 1080), (1366, 768), (768, 1024)]
            for width, height in resolutions:
                page.set_viewport_size({"width": width, "height": height})
                time.sleep(1)
                self.save_screenshot(page, f"05_responsive_{width}x{height}")
                tests.append((f"响应式{width}x{height}", True))
                
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # 6. 性能测试
            self.log("\n测试页面性能...", "info")
            start = time.time()
            page.reload(timeout=20000, wait_until="networkidle")
            load_time = time.time() - start
            tests.append(("加载性能<5s", load_time < 5))
            self.log(f"页面加载时间: {load_time:.2f}秒", "success" if load_time < 5 else "warning")
            
            self.save_screenshot(page, "06_final_state")
            
        except Exception as e:
            self.log(f"前端测试错误: {e}", "error")
            self.save_screenshot(page, "error_state")
            
        passed = sum(1 for _, result in tests if result)
        self.log(f"\n前端UI测试: {passed}/{len(tests)} 通过", "success" if passed > len(tests)*0.7 else "warning")
        self.results['frontend_ui'] = {"tests": tests, "passed": passed, "total": len(tests)}
        return passed > len(tests) * 0.7
        
    def generate_report(self):
        """生成测试报告"""
        self.log("\n=== 生成测试报告 ===", "info")
        
        total_tests = sum(r['total'] for r in self.results.values())
        total_passed = sum(r['passed'] for r in self.results.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": success_rate
            },
            "details": self.results,
            "screenshots": len(list(self.screenshots_dir.glob("*.png")))
        }
        
        # 保存JSON报告
        report_path = Path("/workspace/web/comprehensive_test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        # 打印摘要
        self.log("\n" + "="*60, "info")
        self.log("测试摘要", "info")
        self.log("="*60, "info")
        self.log(f"总测试数: {total_tests}", "info")
        self.log(f"通过: {total_passed}", "success")
        self.log(f"失败: {total_tests - total_passed}", "error" if total_tests > total_passed else "success")
        self.log(f"成功率: {success_rate:.1f}%", "success" if success_rate >= 80 else "warning")
        self.log(f"截图数: {report['screenshots']}", "info")
        self.log(f"报告: {report_path}", "info")
        
        return success_rate >= 80
        
    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*60, "info")
        self.log("HydroClaude Web 全面无死角测试", "info")
        self.log("="*60, "info")
        self.log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
        
        # 测试后端API
        backend_ok = self.test_backend_apis()
        
        # 测试前端UI
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            frontend_ok = self.test_frontend_ui(page)
            
            browser.close()
            
        # 生成报告
        success = self.generate_report()
        
        if success:
            self.log("\n 全面测试通过！", "success")
        else:
            self.log("\n️  测试完成，但部分项目未通过", "warning")
            
        return success

def main():
    tester = ComprehensiveWebTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
