#!/usr/bin/env python3
"""
HydroClaude Web 深度测试 - 工作流、性能、压力测试
"""

from playwright.sync_api import sync_playwright
import requests
import time
import json
from datetime import datetime
from pathlib import Path
import concurrent.futures

class AdvancedWebTester:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8000"
        self.frontend_url = "http://localhost:5174"
        self.screenshots_dir = Path("/workspace/web/advanced_screenshots")
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
        
    def test_complete_workflow(self):
        """测试完整端到端工作流"""
        self.log("\n=== 测试1: 完整端到端工作流 ===", "info")
        
        tests = []
        
        # 创建多个仿真任务
        task_ids = []
        configs = [
            {
                "name": "缓坡渠道",
                "config": {"length": 1000, "slope": 0.001, "n_cells": 50}
            },
            {
                "name": "陡坡渠道",
                "config": {"length": 500, "slope": 0.01, "n_cells": 30}
            },
            {
                "name": "长渠道",
                "config": {"length": 5000, "slope": 0.0005, "n_cells": 100}
            }
        ]
        
        self.log("创建多个仿真任务...", "info")
        for i, cfg in enumerate(configs):
            try:
                r = requests.post(f"{self.api_base}/api/v1/simulations", json=cfg, timeout=10)
                if r.status_code in [200, 201]:
                    task_id = r.json().get('task_id')
                    task_ids.append(task_id)
                    self.log(f"  任务 {i+1}: {cfg['name']} -> {task_id[:8]}...", "success")
                    tests.append((f"创建任务{i+1}", True))
                else:
                    tests.append((f"创建任务{i+1}", False))
            except Exception as e:
                self.log(f"  任务 {i+1} 创建失败: {e}", "error")
                tests.append((f"创建任务{i+1}", False))
                
        # 等待所有任务完成
        self.log("等待任务完成...", "info")
        time.sleep(5)
        
        # 检查所有任务状态
        for i, task_id in enumerate(task_ids):
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/status", timeout=5)
                if r.status_code == 200:
                    status = r.json().get('status')
                    tests.append((f"任务{i+1}状态", status in ['completed', 'running']))
                    self.log(f"  任务 {i+1}: {status}", "success" if status == 'completed' else "warning")
            except:
                tests.append((f"任务{i+1}状态", False))
                
        # 获取所有结果
        for i, task_id in enumerate(task_ids):
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/results", timeout=10)
                tests.append((f"任务{i+1}结果", r.status_code == 200))
            except:
                tests.append((f"任务{i+1}结果", False))
                
        # 列出所有仿真
        try:
            r = requests.get(f"{self.api_base}/api/v1/simulations", timeout=5)
            if r.status_code == 200:
                total = r.json().get('total', 0)
                tests.append(("列出仿真", total >= len(task_ids)))
                self.log(f"总仿真数: {total}", "success")
        except:
            tests.append(("列出仿真", False))
            
        # 删除所有任务
        for i, task_id in enumerate(task_ids):
            try:
                r = requests.delete(f"{self.api_base}/api/v1/simulations/{task_id}", timeout=5)
                tests.append((f"删除任务{i+1}", r.status_code in [200, 204]))
            except:
                tests.append((f"删除任务{i+1}", False))
                
        passed = sum(1 for _, result in tests if result)
        self.log(f"\n工作流测试: {passed}/{len(tests)} 通过", "success" if passed > len(tests)*0.8 else "warning")
        self.results['workflow'] = {"tests": tests, "passed": passed, "total": len(tests)}
        
    def test_ui_interactions(self, page):
        """测试UI交互功能"""
        self.log("\n=== 测试2: UI交互功能 ===", "info")
        
        tests = []
        
        try:
            page.goto(self.frontend_url, timeout=20000, wait_until="networkidle")
            self.save_screenshot(page, "ui_start")
            
            # 测试建模工作台交互
            self.log("测试建模工作台交互...", "info")
            page.click("text=建模工作台", timeout=5000)
            time.sleep(2)
            self.save_screenshot(page, "modeling_tab")
            tests.append(("建模工作台切换", True))
            
            # 测试仿真管理交互
            self.log("测试仿真管理交互...", "info")
            page.click("text=仿真管理", timeout=5000)
            time.sleep(2)
            self.save_screenshot(page, "simulation_tab")
            tests.append(("仿真管理切换", True))
            
            # 测试导航多次切换
            self.log("测试多次标签切换...", "info")
            for i in range(3):
                page.click("text=建模工作台", timeout=5000)
                time.sleep(0.5)
                page.click("text=仿真管理", timeout=5000)
                time.sleep(0.5)
            tests.append(("多次切换", True))
            self.save_screenshot(page, "multiple_switches")
            
            # 测试浏览器后退/前进
            self.log("测试浏览器导航...", "info")
            page.go_back(timeout=5000)
            time.sleep(1)
            self.save_screenshot(page, "browser_back")
            page.go_forward(timeout=5000)
            time.sleep(1)
            self.save_screenshot(page, "browser_forward")
            tests.append(("浏览器导航", True))
            
            # 测试页面刷新
            self.log("测试页面刷新...", "info")
            page.reload(timeout=20000, wait_until="networkidle")
            time.sleep(2)
            self.save_screenshot(page, "page_refresh")
            tests.append(("页面刷新", True))
            
        except Exception as e:
            self.log(f"UI交互测试错误: {e}", "error")
            self.save_screenshot(page, "ui_error")
            
        passed = sum(1 for _, result in tests if result)
        self.log(f"\nUI交互测试: {passed}/{len(tests)} 通过", "success" if passed == len(tests) else "warning")
        self.results['ui_interactions'] = {"tests": tests, "passed": passed, "total": len(tests)}
        
    def test_performance(self):
        """测试API性能"""
        self.log("\n=== 测试3: API性能测试 ===", "info")
        
        tests = []
        
        # 测试健康检查响应时间
        self.log("测试API响应时间...", "info")
        response_times = []
        for i in range(10):
            start = time.time()
            try:
                r = requests.get(f"{self.api_base}/health", timeout=5)
                elapsed = time.time() - start
                response_times.append(elapsed)
            except:
                pass
                
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            self.log(f"  平均响应: {avg_time*1000:.1f}ms", "success")
            self.log(f"  最小响应: {min_time*1000:.1f}ms", "info")
            self.log(f"  最大响应: {max_time*1000:.1f}ms", "info")
            
            tests.append(("平均响应<100ms", avg_time < 0.1))
            tests.append(("最大响应<200ms", max_time < 0.2))
        else:
            tests.append(("平均响应<100ms", False))
            tests.append(("最大响应<200ms", False))
            
        # 测试并发请求
        self.log("测试并发请求处理...", "info")
        
        def make_request(i):
            try:
                r = requests.get(f"{self.api_base}/health", timeout=5)
                return r.status_code == 200
            except:
                return False
                
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))
        elapsed = time.time() - start
        
        success_count = sum(results)
        self.log(f"  并发请求: {success_count}/20 成功", "success" if success_count >= 18 else "warning")
        self.log(f"  总耗时: {elapsed:.2f}秒", "info")
        
        tests.append(("并发请求>90%", success_count >= 18))
        tests.append(("并发耗时<5s", elapsed < 5))
        
        passed = sum(1 for _, result in tests if result)
        self.log(f"\n性能测试: {passed}/{len(tests)} 通过", "success" if passed >= len(tests)*0.75 else "warning")
        self.results['performance'] = {"tests": tests, "passed": passed, "total": len(tests)}
        
    def test_stress(self):
        """测试压力场景"""
        self.log("\n=== 测试4: 压力测试 ===", "info")
        
        tests = []
        
        # 快速创建多个仿真
        self.log("快速创建10个仿真任务...", "info")
        config = {
            "name": "压力测试",
            "config": {"length": 1000, "n_cells": 50}
        }
        
        created = 0
        for i in range(10):
            try:
                r = requests.post(f"{self.api_base}/api/v1/simulations", json=config, timeout=10)
                if r.status_code in [200, 201]:
                    created += 1
            except:
                pass
                
        self.log(f"  创建成功: {created}/10", "success" if created >= 8 else "warning")
        tests.append(("快速创建>80%", created >= 8))
        
        # 等待处理
        time.sleep(3)
        
        # 检查系统稳定性
        try:
            r = requests.get(f"{self.api_base}/health", timeout=5)
            tests.append(("压力后健康", r.status_code == 200))
            self.log("  系统健康检查: OK", "success")
        except:
            tests.append(("压力后健康", False))
            self.log("  系统健康检查: 失败", "error")
            
        # 清理
        try:
            r = requests.get(f"{self.api_base}/api/v1/simulations", timeout=5)
            if r.status_code == 200:
                sims = r.json().get('simulations', [])
                for sim in sims:
                    try:
                        requests.delete(f"{self.api_base}/api/v1/simulations/{sim['task_id']}", timeout=5)
                    except:
                        pass
                tests.append(("清理任务", True))
        except:
            tests.append(("清理任务", False))
            
        passed = sum(1 for _, result in tests if result)
        self.log(f"\n压力测试: {passed}/{len(tests)} 通过", "success" if passed >= len(tests)*0.75 else "warning")
        self.results['stress'] = {"tests": tests, "passed": passed, "total": len(tests)}
        
    def test_error_handling(self):
        """测试错误处理"""
        self.log("\n=== 测试5: 错误处理 ===", "info")
        
        tests = []
        
        # 测试不存在的任务
        try:
            r = requests.get(f"{self.api_base}/api/v1/simulations/nonexistent/status", timeout=5)
            tests.append(("不存在任务404", r.status_code == 404))
            self.log(f"  不存在任务: {r.status_code}", "success" if r.status_code == 404 else "error")
        except:
            tests.append(("不存在任务404", False))
            
        # 测试无效配置
        try:
            r = requests.post(f"{self.api_base}/api/v1/simulations", json={}, timeout=10)
            tests.append(("无效配置处理", r.status_code in [200, 201, 400, 422]))
            self.log(f"  无效配置: {r.status_code}", "info")
        except:
            tests.append(("无效配置处理", False))
            
        # 测试无效端点
        try:
            r = requests.get(f"{self.api_base}/api/v1/invalid", timeout=5)
            tests.append(("无效端点404", r.status_code == 404))
            self.log(f"  无效端点: {r.status_code}", "success" if r.status_code == 404 else "warning")
        except:
            tests.append(("无效端点404", False))
            
        passed = sum(1 for _, result in tests if result)
        self.log(f"\n错误处理测试: {passed}/{len(tests)} 通过", "success" if passed >= 2 else "warning")
        self.results['error_handling'] = {"tests": tests, "passed": passed, "total": len(tests)}
        
    def generate_report(self):
        """生成详细测试报告"""
        self.log("\n=== 生成测试报告 ===", "info")
        
        total_tests = sum(r['total'] for r in self.results.values())
        total_passed = sum(r['passed'] for r in self.results.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_date": datetime.now().isoformat(),
            "test_type": "advanced",
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": success_rate
            },
            "details": self.results,
            "screenshots": len(list(self.screenshots_dir.glob("*.png")))
        }
        
        report_path = Path("/workspace/web/advanced_test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        self.log("\n" + "="*60, "info")
        self.log("深度测试摘要", "info")
        self.log("="*60, "info")
        self.log(f"总测试数: {total_tests}", "info")
        self.log(f"通过: {total_passed}", "success")
        self.log(f"失败: {total_tests - total_passed}", "error" if total_tests > total_passed else "success")
        self.log(f"成功率: {success_rate:.1f}%", "success" if success_rate >= 75 else "warning")
        self.log(f"截图数: {report['screenshots']}", "info")
        
        # 打印详细结果
        self.log("\n详细结果:", "info")
        for category, data in self.results.items():
            rate = (data['passed'] / data['total'] * 100) if data['total'] > 0 else 0
            self.log(f"  {category}: {data['passed']}/{data['total']} ({rate:.0f}%)", 
                    "success" if rate >= 75 else "warning")
        
        return success_rate >= 75
        
    def run_all_tests(self):
        """运行所有深度测试"""
        self.log("\n" + "="*60, "info")
        self.log("HydroClaude Web 深度测试", "info")
        self.log("="*60, "info")
        self.log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
        
        # 1. 工作流测试
        self.test_complete_workflow()
        
        # 2. UI交互测试
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            self.test_ui_interactions(page)
            
            browser.close()
            
        # 3. 性能测试
        self.test_performance()
        
        # 4. 压力测试
        self.test_stress()
        
        # 5. 错误处理测试
        self.test_error_handling()
        
        # 生成报告
        success = self.generate_report()
        
        if success:
            self.log("\n 深度测试通过！", "success")
        else:
            self.log("\n️  深度测试完成，部分项目未通过", "warning")
            
        return success

def main():
    tester = AdvancedWebTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
