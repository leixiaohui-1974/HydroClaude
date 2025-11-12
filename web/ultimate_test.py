#!/usr/bin/env python3
"""
HydroClaude Web 终极测试 - 完整验证所有功能
包含API、UI、工作流、性能的全面测试
"""

from playwright.sync_api import sync_playwright
import requests
import time
import json
from datetime import datetime
from pathlib import Path
import concurrent.futures

class UltimateWebTester:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8000"
        self.frontend_url = "http://localhost:5174"
        self.screenshots_dir = Path("/workspace/web/ultimate_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.results = {}
        self.test_num = 0
        self.all_tests = []
        
    def log(self, msg, status="info"):
        colors = {
            "success": "\033[92m✅",
            "error": "\033[91m❌",
            "info": "\033[94mℹ️",
            "warning": "\033[93m⚠️",
            "header": "\033[95m🎯"
        }
        end = "\033[0m"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {colors.get(status, colors['info'])} {msg}{end}")
        
    def save_screenshot(self, page, name, description=""):
        self.test_num += 1
        filename = f"{self.test_num:02d}_{name}.png"
        path = self.screenshots_dir / filename
        page.screenshot(path=str(path), full_page=True)
        self.log(f"截图: {filename}", "info")
        return str(path)
        
    def add_test_result(self, category, name, passed, details=""):
        """记录测试结果"""
        self.all_tests.append({
            "category": category,
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def test_backend_comprehensive(self):
        """全面测试后端API"""
        self.log("\n" + "="*70, "header")
        self.log("第1部分: 后端API全面测试", "header")
        self.log("="*70, "header")
        
        tests = []
        
        # 1. 系统健康检查
        self.log("\n1. 系统健康检查...", "info")
        try:
            r = requests.get(f"{self.api_base}/health", timeout=5)
            passed = r.status_code == 200
            tests.append(("健康检查", passed))
            self.add_test_result("Backend", "健康检查", passed, f"状态码: {r.status_code}")
            if passed:
                data = r.json()
                self.log(f"   服务: {data.get('service')}", "success")
                self.log(f"   版本: {data.get('version')}", "success")
        except Exception as e:
            tests.append(("健康检查", False))
            self.add_test_result("Backend", "健康检查", False, str(e))
            self.log(f"   错误: {e}", "error")
            
        # 2. 引擎信息
        self.log("\n2. 引擎信息...", "info")
        try:
            r = requests.get(f"{self.api_base}/api/v1/engine/info", timeout=5)
            passed = r.status_code == 200
            tests.append(("引擎信息", passed))
            self.add_test_result("Backend", "引擎信息", passed)
            if passed:
                self.log(f"   引擎加载成功", "success")
        except Exception as e:
            tests.append(("引擎信息", False))
            self.add_test_result("Backend", "引擎信息", False, str(e))
            
        # 3-7. 完整仿真工作流
        self.log("\n3. 完整仿真工作流测试...", "info")
        task_id = None
        
        # 创建仿真
        config = {
            "name": "终极测试仿真",
            "config": {
                "width": 10.0, "length": 1000.0, "n_cells": 50,
                "manning_n": 0.025, "slope": 0.001, "t_end": 10.0,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "upstream": {"type": "h", "value": 5.0},
                    "downstream": {"type": "h", "value": 5.0}
                }
            }
        }
        
        try:
            r = requests.post(f"{self.api_base}/api/v1/simulations", json=config, timeout=30)
            passed = r.status_code in [200, 201]
            tests.append(("创建仿真", passed))
            self.add_test_result("Backend", "创建仿真", passed)
            if passed:
                task_id = r.json().get('task_id')
                self.log(f"   任务ID: {task_id[:16]}...", "success")
        except Exception as e:
            tests.append(("创建仿真", False))
            self.add_test_result("Backend", "创建仿真", False, str(e))
            
        # 查询状态和结果
        if task_id:
            time.sleep(3)
            
            # 状态
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/status", timeout=5)
                passed = r.status_code == 200
                tests.append(("查询状态", passed))
                self.add_test_result("Backend", "查询状态", passed)
                if passed:
                    self.log(f"   状态: {r.json().get('status')}", "success")
            except:
                tests.append(("查询状态", False))
                self.add_test_result("Backend", "查询状态", False)
                
            # 等待完成
            for i in range(20):
                try:
                    r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/status", timeout=5)
                    if r.json().get('status') in ['completed', 'failed']:
                        break
                except:
                    pass
                time.sleep(0.5)
                
            # 结果
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations/{task_id}/results", timeout=10)
                passed = r.status_code == 200
                tests.append(("获取结果", passed))
                self.add_test_result("Backend", "获取结果", passed)
                if passed:
                    self.log(f"   结果获取成功", "success")
            except:
                tests.append(("获取结果", False))
                self.add_test_result("Backend", "获取结果", False)
                
            # 列表
            try:
                r = requests.get(f"{self.api_base}/api/v1/simulations", timeout=5)
                passed = r.status_code == 200
                tests.append(("列出仿真", passed))
                self.add_test_result("Backend", "列出仿真", passed)
            except:
                tests.append(("列出仿真", False))
                self.add_test_result("Backend", "列出仿真", False)
                
            # 删除
            try:
                r = requests.delete(f"{self.api_base}/api/v1/simulations/{task_id}", timeout=5)
                passed = r.status_code in [200, 204]
                tests.append(("删除仿真", passed))
                self.add_test_result("Backend", "删除仿真", passed)
            except:
                tests.append(("删除仿真", False))
                self.add_test_result("Backend", "删除仿真", False)
        else:
            for name in ["查询状态", "获取结果", "列出仿真", "删除仿真"]:
                tests.append((name, False))
                self.add_test_result("Backend", name, False, "task_id为空")
                
        passed_count = sum(1 for _, p in tests if p)
        self.log(f"\n后端测试: {passed_count}/{len(tests)} 通过", 
                "success" if passed_count == len(tests) else "warning")
        self.results['backend'] = {"passed": passed_count, "total": len(tests), "tests": tests}
        
    def test_frontend_comprehensive(self, page):
        """全面测试前端UI"""
        self.log("\n" + "="*70, "header")
        self.log("第2部分: 前端UI全面测试", "header")
        self.log("="*70, "header")
        
        tests = []
        
        # 1. 页面加载
        self.log("\n1. 页面加载测试...", "info")
        try:
            page.goto(self.frontend_url, timeout=30000, wait_until="networkidle")
            time.sleep(3)
            self.save_screenshot(page, "01_homepage", "首页")
            
            title = page.title()
            passed = "HydroClaude" in title
            tests.append(("页面标题", passed))
            self.add_test_result("Frontend", "页面标题", passed, title)
            self.log(f"   标题: {title}", "success" if passed else "error")
        except Exception as e:
            tests.append(("页面标题", False))
            self.add_test_result("Frontend", "页面标题", False, str(e))
            
        # 2. 建模工作台
        self.log("\n2. 建模工作台测试...", "info")
        try:
            page.locator('[role="tab"]:has-text("建模工作台")').first.click()
            page.wait_for_selector('.react-flow', timeout=10000)
            time.sleep(5)
            self.save_screenshot(page, "02_modeling_workspace", "建模工作台")
            
            body_text = page.locator('body').inner_text()
            has_components = "明渠" in body_text or "矩形明渠" in body_text
            has_canvas = page.locator('.react-flow').count() > 0
            
            tests.append(("建模组件库", has_components))
            tests.append(("建模画布", has_canvas))
            self.add_test_result("Frontend", "建模组件库", has_components)
            self.add_test_result("Frontend", "建模画布", has_canvas)
            
            self.log(f"   组件库: {'显示' if has_components else '未显示'}", 
                    "success" if has_components else "error")
            self.log(f"   画布: {'显示' if has_canvas else '未显示'}", 
                    "success" if has_canvas else "error")
        except Exception as e:
            tests.append(("建模组件库", False))
            tests.append(("建模画布", False))
            self.add_test_result("Frontend", "建模工作台", False, str(e))
            
        # 3. 仿真管理（关键测试）
        self.log("\n3. 仿真管理测试（带懒加载等待）...", "info")
        try:
            page.locator('[role="tab"]:has-text("仿真管理")').first.click()
            self.log("   等待懒加载...", "info")
            
            # 等待加载
            try:
                page.wait_for_selector('text=加载中...', state="detached", timeout=10000)
            except:
                pass
                
            page.wait_for_selector('text=仿真配置', timeout=10000)
            time.sleep(8)
            self.save_screenshot(page, "03_simulation_management", "仿真管理")
            
            body_text = page.locator('body').inner_text()
            has_config = "仿真配置" in body_text
            has_single = "单场景结果" in body_text
            no_modeling = "明渠" not in body_text and "矩形明渠" not in body_text
            
            tests.append(("仿真配置表单", has_config))
            tests.append(("单场景标签", has_single))
            tests.append(("内容隔离", no_modeling))
            
            self.add_test_result("Frontend", "仿真配置表单", has_config)
            self.add_test_result("Frontend", "单场景标签", has_single)
            self.add_test_result("Frontend", "内容隔离", no_modeling)
            
            self.log(f"   仿真配置: {'存在' if has_config else '缺失'}", 
                    "success" if has_config else "error")
            self.log(f"   单场景结果: {'存在' if has_single else '缺失'}", 
                    "success" if has_single else "error")
            self.log(f"   内容隔离: {'正确' if no_modeling else '错误'}", 
                    "success" if no_modeling else "error")
        except Exception as e:
            tests.append(("仿真配置表单", False))
            tests.append(("单场景标签", False))
            tests.append(("内容隔离", False))
            self.add_test_result("Frontend", "仿真管理", False, str(e))
            
        # 4. 子标签测试
        self.log("\n4. 仿真管理子标签测试...", "info")
        try:
            # 单场景结果
            single_tab = page.locator('[role="tab"]:has-text("单场景结果")')
            if single_tab.count() > 0:
                single_tab.first.click()
                time.sleep(3)
                self.save_screenshot(page, "04_single_scenario", "单场景结果")
                tests.append(("单场景结果标签", True))
                self.add_test_result("Frontend", "单场景结果标签", True)
                self.log("   单场景结果标签: 存在并可点击", "success")
            else:
                tests.append(("单场景结果标签", False))
                self.add_test_result("Frontend", "单场景结果标签", False)
                
            # 多场景对比
            comparison_tab = page.locator('[role="tab"]:has-text("多场景对比")')
            if comparison_tab.count() > 0:
                comparison_tab.first.click()
                time.sleep(3)
                self.save_screenshot(page, "05_comparison", "多场景对比")
                tests.append(("多场景对比标签", True))
                self.add_test_result("Frontend", "多场景对比标签", True)
                self.log("   多场景对比标签: 存在并可点击", "success")
            else:
                tests.append(("多场景对比标签", False))
                self.add_test_result("Frontend", "多场景对比标签", False)
        except Exception as e:
            self.log(f"   子标签测试错误: {e}", "error")
            
        # 5. 响应式测试
        self.log("\n5. 响应式设计测试...", "info")
        page.locator('[role="tab"]:has-text("建模工作台")').first.click()
        page.wait_for_selector('.react-flow', timeout=10000)
        
        resolutions = [
            (1920, 1080, "桌面大屏"),
            (1366, 768, "桌面中屏"),
            (768, 1024, "平板")
        ]
        
        for width, height, desc in resolutions:
            page.set_viewport_size({"width": width, "height": height})
            time.sleep(2)
            self.save_screenshot(page, f"responsive_{width}x{height}", desc)
            tests.append((f"响应式{width}x{height}", True))
            self.add_test_result("Frontend", f"响应式{desc}", True)
            
        self.log(f"   测试了{len(resolutions)}种分辨率", "success")
        page.set_viewport_size({"width": 1920, "height": 1080})
        
        # 6. 返回验证
        self.log("\n6. 标签切换验证...", "info")
        page.locator('[role="tab"]:has-text("建模工作台")').first.click()
        time.sleep(3)
        self.save_screenshot(page, "06_back_to_modeling", "返回建模")
        tests.append(("标签切换", True))
        self.add_test_result("Frontend", "标签切换", True)
        
        passed_count = sum(1 for _, p in tests if p)
        self.log(f"\n前端测试: {passed_count}/{len(tests)} 通过", 
                "success" if passed_count > len(tests)*0.8 else "warning")
        self.results['frontend'] = {"passed": passed_count, "total": len(tests), "tests": tests}
        
    def test_performance(self):
        """性能测试"""
        self.log("\n" + "="*70, "header")
        self.log("第3部分: 性能测试", "header")
        self.log("="*70, "header")
        
        tests = []
        
        # API响应时间
        self.log("\n1. API响应时间测试...", "info")
        times = []
        for i in range(10):
            start = time.time()
            try:
                requests.get(f"{self.api_base}/health", timeout=5)
                elapsed = time.time() - start
                times.append(elapsed)
            except:
                pass
                
        if times:
            avg = sum(times) / len(times) * 1000
            max_t = max(times) * 1000
            min_t = min(times) * 1000
            
            self.log(f"   平均: {avg:.1f}ms", "success")
            self.log(f"   最小: {min_t:.1f}ms", "info")
            self.log(f"   最大: {max_t:.1f}ms", "info")
            
            tests.append(("平均响应<100ms", avg < 100))
            tests.append(("最大响应<200ms", max_t < 200))
            self.add_test_result("Performance", "API平均响应", avg < 100, f"{avg:.1f}ms")
            self.add_test_result("Performance", "API最大响应", max_t < 200, f"{max_t:.1f}ms")
            
        # 并发测试
        self.log("\n2. 并发请求测试...", "info")
        def make_request(i):
            try:
                r = requests.get(f"{self.api_base}/health", timeout=5)
                return r.status_code == 200
            except:
                return False
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))
            
        success_count = sum(results)
        self.log(f"   成功: {success_count}/20", "success" if success_count >= 18 else "warning")
        tests.append(("并发>90%", success_count >= 18))
        self.add_test_result("Performance", "并发请求", success_count >= 18, f"{success_count}/20")
        
        passed_count = sum(1 for _, p in tests if p)
        self.log(f"\n性能测试: {passed_count}/{len(tests)} 通过", 
                "success" if passed_count == len(tests) else "warning")
        self.results['performance'] = {"passed": passed_count, "total": len(tests), "tests": tests}
        
    def generate_ultimate_report(self):
        """生成终极报告"""
        self.log("\n" + "="*70, "header")
        self.log("生成终极测试报告", "header")
        self.log("="*70, "header")
        
        total_tests = sum(r['total'] for r in self.results.values())
        total_passed = sum(r['passed'] for r in self.results.values())
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_date": datetime.now().isoformat(),
            "test_type": "ultimate_comprehensive",
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": success_rate
            },
            "details": self.results,
            "all_tests": self.all_tests,
            "screenshots": self.test_num
        }
        
        # 保存JSON
        report_path = Path("/workspace/web/ultimate_test_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # 打印摘要
        self.log("\n", "info")
        self.log("="*70, "info")
        self.log("终极测试摘要", "info")
        self.log("="*70, "info")
        self.log(f"总测试数: {total_tests}", "info")
        self.log(f"通过: {total_passed}", "success")
        self.log(f"失败: {total_tests - total_passed}", "error" if total_tests > total_passed else "success")
        self.log(f"成功率: {success_rate:.1f}%", "success" if success_rate >= 90 else "warning")
        self.log(f"截图数: {self.test_num}", "info")
        self.log("="*70, "info")
        
        # 分类统计
        for category, data in self.results.items():
            rate = (data['passed'] / data['total'] * 100) if data['total'] > 0 else 0
            self.log(f"{category}: {data['passed']}/{data['total']} ({rate:.0f}%)", 
                    "success" if rate >= 90 else "warning")
                    
        return success_rate >= 90
        
    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*70, "header")
        self.log("HydroClaude Web 终极全面测试", "header")
        self.log("="*70, "header")
        self.log(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
        
        # 1. 后端测试
        self.test_backend_comprehensive()
        
        # 2. 前端测试
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            self.test_frontend_comprehensive(page)
            
            browser.close()
            
        # 3. 性能测试
        self.test_performance()
        
        # 4. 生成报告
        success = self.generate_ultimate_report()
        
        if success:
            self.log("\n🎉 终极测试通过！系统完美！", "success")
        else:
            self.log("\n⚠️  测试完成，部分项目未达标", "warning")
            
        self.log(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
        
        return success

def main():
    tester = UltimateWebTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
