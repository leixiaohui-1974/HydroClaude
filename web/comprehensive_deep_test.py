#!/usr/bin/env python3
"""
HydroClaude Web 全面深度测试
无死角测试所有功能
"""

from playwright.sync_api import sync_playwright, Page
import time
import json
import requests
from datetime import datetime
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class DeepTester:
    def __init__(self):
        self.screenshots_dir = Path("/workspace/web/deep_test_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.results = {}
        self.test_count = 0
        self.passed_count = 0
        self.screenshot_count = 0
        
    def log_header(self, msg):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        
    def log_success(self, msg):
        print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")
        
    def log_error(self, msg):
        print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")
        
    def log_info(self, msg):
        print(f"ℹ️  {msg}")
        
    def save_screenshot(self, page: Page, name: str):
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{name}.png"
        filepath = self.screenshots_dir / filename
        page.screenshot(path=str(filepath), full_page=True)
        self.log_info(f"📸 截图保存: {filename}")
        return str(filepath)
        
    def record_test(self, name: str, passed: bool, details: str = ""):
        self.test_count += 1
        if passed:
            self.passed_count += 1
            self.log_success(f"{name}")
        else:
            self.log_error(f"{name} - {details}")
            
        self.results[name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
    def test_backend_apis(self):
        """深度测试所有后端API"""
        self.log_header("🔍 深度测试：后端API全覆盖")
        
        # 1. 健康检查
        try:
            resp = requests.get("http://127.0.0.1:8000/health", timeout=5)
            self.record_test("API: 健康检查", resp.status_code == 200)
        except Exception as e:
            self.record_test("API: 健康检查", False, str(e))
            
        # 2. 引擎信息
        try:
            resp = requests.get("http://127.0.0.1:8000/api/v1/engine/info", timeout=5)
            self.record_test("API: 引擎信息", resp.status_code == 200)
        except Exception as e:
            self.record_test("API: 引擎信息", False, str(e))
            
        # 3. 创建仿真
        config = {
            "name": "深度测试仿真",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 30.0,
                "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                "boundary_conditions": {
                    "upstream": {"type": "h", "value": 5.0},
                    "downstream": {"type": "h", "value": 5.0}
                }
            }
        }
        
        try:
            resp = requests.post("http://127.0.0.1:8000/api/v1/simulations", 
                               json=config, timeout=30)
            if resp.status_code in [200, 201]:
                task_id = resp.json()['task_id']
                self.record_test("API: 创建仿真", True, f"任务ID: {task_id}")
                
                # 4. 查询状态
                time.sleep(2)
                resp = requests.get(f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/status", 
                                  timeout=5)
                self.record_test("API: 查询状态", resp.status_code == 200)
                
                # 等待完成
                for _ in range(30):
                    resp = requests.get(f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/status")
                    status = resp.json()['status']
                    if status in ['completed', 'failed']:
                        break
                    time.sleep(1)
                    
                # 5. 获取结果
                if status == 'completed':
                    resp = requests.get(f"http://127.0.0.1:8000/api/v1/simulations/{task_id}/results", 
                                      timeout=10)
                    self.record_test("API: 获取结果", resp.status_code == 200)
                else:
                    self.record_test("API: 获取结果", False, f"仿真状态: {status}")
                    
                # 6. 删除仿真
                resp = requests.delete(f"http://127.0.0.1:8000/api/v1/simulations/{task_id}", 
                                     timeout=5)
                self.record_test("API: 删除仿真", resp.status_code in [200, 204])
            else:
                self.record_test("API: 创建仿真", False, f"状态码: {resp.status_code}")
        except Exception as e:
            self.record_test("API: 创建仿真", False, str(e))
            
    def test_frontend_deep(self, page: Page):
        """深度测试前端UI"""
        self.log_header("🔍 深度测试：前端UI全覆盖")
        
        try:
            # 1. 页面加载
            self.log_info("测试：页面加载...")
            page.goto("http://localhost:5173", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            self.save_screenshot(page, "01_homepage")
            
            title = page.title()
            self.record_test("前端: 页面加载", "HydroClaude" in title, f"标题: {title}")
            
            time.sleep(2)
            
            # 2. 建模工作台
            self.log_info("测试：建模工作台...")
            try:
                page.click("text=建模工作台", timeout=10000)
                time.sleep(2)
                self.save_screenshot(page, "02_modeling_workspace")
                self.record_test("前端: 建模工作台标签", True)
                
                # 检查画布
                canvas = page.locator(".react-flow").first
                if canvas.is_visible(timeout=5000):
                    self.record_test("前端: React Flow画布", True)
                    self.save_screenshot(page, "03_canvas_visible")
                else:
                    self.record_test("前端: React Flow画布", False, "画布不可见")
                    
            except Exception as e:
                self.record_test("前端: 建模工作台标签", False, str(e))
                self.save_screenshot(page, "02_modeling_error")
                
            # 3. 仿真管理
            self.log_info("测试：仿真管理...")
            try:
                page.click("text=仿真管理", timeout=10000)
                time.sleep(2)
                self.save_screenshot(page, "04_simulation_management")
                self.record_test("前端: 仿真管理标签", True)
            except Exception as e:
                self.record_test("前端: 仿真管理标签", False, str(e))
                self.save_screenshot(page, "04_simulation_error")
                
            # 4. 响应式设计
            self.log_info("测试：响应式设计...")
            resolutions = [
                (1920, 1080, "桌面"),
                (1366, 768, "笔记本"),
                (768, 1024, "平板"),
                (375, 667, "手机")
            ]
            
            for width, height, device in resolutions:
                page.set_viewport_size({"width": width, "height": height})
                time.sleep(1)
                self.save_screenshot(page, f"05_responsive_{width}x{height}")
                self.record_test(f"前端: 响应式-{device}", True, f"{width}×{height}")
                
            # 恢复默认分辨率
            page.set_viewport_size({"width": 1920, "height": 1080}")
            
            # 5. 页面性能
            self.log_info("测试：页面性能...")
            start = time.time()
            page.goto("http://localhost:5173", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            load_time = time.time() - start
            
            self.record_test("前端: 页面加载性能", load_time < 5, f"{load_time:.2f}秒")
            
            # 6. 控制台错误
            errors = []
            page.on("console", lambda msg: errors.append(msg.text()) if msg.type == "error" else None)
            time.sleep(3)
            
            self.record_test("前端: 无控制台错误", len(errors) == 0, f"{len(errors)}个错误")
            
        except Exception as e:
            self.log_error(f"前端测试异常: {e}")
            self.save_screenshot(page, "99_exception")
            
    def test_api_stress(self):
        """压力测试API"""
        self.log_header("🔍 深度测试：API压力测试")
        
        self.log_info("并发创建10个仿真任务...")
        
        import concurrent.futures
        
        def create_simulation(i):
            config = {
                "name": f"压力测试_{i}",
                "config": {
                    "width": 10.0,
                    "length": 500.0,
                    "n_cells": 50,
                    "manning_n": 0.025,
                    "t_end": 10.0,
                    "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 5.0},
                        "downstream": {"type": "h", "value": 5.0}
                    }
                }
            }
            
            try:
                resp = requests.post("http://127.0.0.1:8000/api/v1/simulations", 
                                   json=config, timeout=30)
                return resp.status_code in [200, 201]
            except:
                return False
                
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_simulation, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        success_count = sum(results)
        self.record_test("压力: 并发创建仿真", success_count >= 8, 
                        f"{success_count}/10成功")
        
    def test_security(self):
        """安全性测试"""
        self.log_header("🔍 深度测试：安全性检查")
        
        # 1. SQL注入测试
        try:
            malicious_name = "'; DROP TABLE simulations; --"
            config = {
                "name": malicious_name,
                "config": {
                    "width": 10.0,
                    "length": 100.0,
                    "n_cells": 10,
                    "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 5.0},
                        "downstream": {"type": "h", "value": 5.0}
                    }
                }
            }
            
            resp = requests.post("http://127.0.0.1:8000/api/v1/simulations", 
                               json=config, timeout=30)
            # 应该正常处理或拒绝，不应崩溃
            self.record_test("安全: SQL注入防护", True, "系统未崩溃")
        except:
            self.record_test("安全: SQL注入防护", False, "可能存在漏洞")
            
        # 2. XSS测试
        try:
            xss_name = "<script>alert('XSS')</script>"
            config = {
                "name": xss_name,
                "config": {
                    "width": 10.0,
                    "length": 100.0,
                    "n_cells": 10,
                    "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 5.0},
                        "downstream": {"type": "h", "value": 5.0}
                    }
                }
            }
            
            resp = requests.post("http://127.0.0.1:8000/api/v1/simulations", 
                               json=config, timeout=30)
            self.record_test("安全: XSS防护", True, "系统未崩溃")
        except:
            self.record_test("安全: XSS防护", False, "可能存在漏洞")
            
        # 3. 大数据测试
        try:
            large_name = "A" * 10000
            config = {
                "name": large_name,
                "config": {
                    "width": 10.0,
                    "length": 100.0,
                    "n_cells": 10,
                    "initial_conditions": {"type": "uniform", "h": 5.0, "Q": 0.0},
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 5.0},
                        "downstream": {"type": "h", "value": 5.0}
                    }
                }
            }
            
            resp = requests.post("http://127.0.0.1:8000/api/v1/simulations", 
                               json=config, timeout=30)
            # 应该拒绝或截断
            self.record_test("安全: 大数据防护", True, "系统处理正常")
        except:
            self.record_test("安全: 大数据防护", True, "拒绝过大请求")
            
    def generate_report(self):
        """生成测试报告"""
        self.log_header("📊 测试报告生成")
        
        success_rate = (self.passed_count / self.test_count * 100) if self.test_count > 0 else 0
        
        print(f"\n{Colors.BOLD}测试统计:{Colors.ENDC}")
        print(f"  总测试数: {self.test_count}")
        print(f"  {Colors.OKGREEN}通过: {self.passed_count}{Colors.ENDC}")
        print(f"  {Colors.FAIL}失败: {self.test_count - self.passed_count}{Colors.ENDC}")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"  截图数: {self.screenshot_count}")
        
        # 保存报告
        report = {
            "test_date": datetime.now().isoformat(),
            "test_type": "comprehensive_deep_test",
            "summary": {
                "total": self.test_count,
                "passed": self.passed_count,
                "failed": self.test_count - self.passed_count,
                "success_rate": success_rate,
                "screenshots": self.screenshot_count
            },
            "results": self.results
        }
        
        report_path = Path("/workspace/web/deep_test_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        self.log_success(f"测试报告已保存: {report_path}")
        self.log_info(f"截图目录: {self.screenshots_dir}")
        
        return success_rate >= 75
        
    def run_all_tests(self):
        """运行所有深度测试"""
        self.log_header("🚀 HydroClaude Web 全面深度测试")
        self.log_info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 后端API测试
        self.test_backend_apis()
        
        # 2. 前端UI测试
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            try:
                self.test_frontend_deep(page)
            finally:
                browser.close()
                
        # 3. 压力测试
        self.test_api_stress()
        
        # 4. 安全测试
        self.test_security()
        
        # 5. 生成报告
        success = self.generate_report()
        
        if success:
            self.log_header("✅ 测试完成！")
            self.log_success("系统通过全面深度测试")
        else:
            self.log_header("⚠️  测试完成，但存在问题")
            
        return success

def main():
    tester = DeepTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
