#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Web系统全面测试脚本
对Web系统的前端、后端、API、数据库进行全面测试

Author: HydroClaude Team
Date: 2025-11-12
"""

import sys
import os
import json
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_section(text):
    """打印章节"""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{'─'*80}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{'─'*80}{Colors.ENDC}")

def print_success(text):
    """成功消息"""
    print(f"{Colors.OKGREEN} {text}{Colors.ENDC}")

def print_error(text):
    """错误消息"""
    print(f"{Colors.FAIL} {text}{Colors.ENDC}")

def print_warning(text):
    """警告消息"""
    print(f"{Colors.WARNING}️  {text}{Colors.ENDC}")

def print_info(text):
    """信息消息"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_test(name, passed, details=""):
    """打印测试结果"""
    status = f"{Colors.OKGREEN} PASS{Colors.ENDC}" if passed else f"{Colors.FAIL} FAIL{Colors.ENDC}"
    print(f"  {name:60s} {status}")
    if details and not passed:
        print(f"     {Colors.FAIL}↳ {details}{Colors.ENDC}")


class WebSystemTester:
    """Web系统测试器"""
    
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.api_v1 = f"{self.api_base}/api/v1"
        self.frontend_url = "http://localhost:5173"
        self.results = {}
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        
    def run_all_tests(self):
        """运行所有测试"""
        print_header("HydroClaude Web系统全面测试")
        print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API地址: {self.api_base}")
        print_info(f"前端地址: {self.frontend_url}")
        
        # 1. 环境检查
        self.test_environment()
        
        # 2. 后端测试
        self.test_backend()
        
        # 3. API测试
        self.test_api()
        
        # 4. 数据库测试
        self.test_database()
        
        # 5. 核心引擎测试
        self.test_engine()
        
        # 6. 集成测试
        self.test_integration()
        
        # 7. 性能测试
        self.test_performance()
        
        # 8. 生成报告
        self.generate_report()
        
    def test_environment(self):
        """测试环境检查"""
        print_section("1. 环境检查")
        
        # Python版本
        python_version = sys.version.split()[0]
        self.record_test(
            "Python版本 >= 3.10",
            python_version >= "3.10",
            f"当前版本: {python_version}"
        )
        
        # 依赖检查
        dependencies = [
            'fastapi', 'uvicorn', 'numpy', 'scipy', 
            'matplotlib', 'pydantic', 'sqlalchemy'
        ]
        
        for dep in dependencies:
            try:
                __import__(dep)
                self.record_test(f"依赖: {dep}", True)
            except ImportError as e:
                self.record_test(f"依赖: {dep}", False, str(e))
        
        # HydroClaude核心模块
        try:
            sys.path.insert(0, '/workspace')
            from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
            self.record_test("HydroClaude核心模块", True)
        except Exception as e:
            self.record_test("HydroClaude核心模块", False, str(e))
            
    def test_backend(self):
        """测试后端服务"""
        print_section("2. 后端服务测试")
        
        # 健康检查
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            self.record_test(
                "后端健康检查",
                response.status_code == 200,
                f"状态码: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                print_info(f"服务: {data.get('service')}")
                print_info(f"版本: {data.get('version')}")
        except Exception as e:
            self.record_test("后端健康检查", False, str(e))
            print_warning("后端服务未运行，跳过后续API测试")
            return False
            
        # API文档
        try:
            response = requests.get(f"{self.api_base}/api/docs", timeout=5)
            self.record_test(
                "API文档可访问",
                response.status_code == 200
            )
        except Exception as e:
            self.record_test("API文档可访问", False, str(e))
            
        return True
        
    def test_api(self):
        """测试API端点"""
        print_section("3. API端点测试")
        
        # 引擎信息
        try:
            response = requests.get(f"{self.api_v1}/engine/info", timeout=5)
            passed = response.status_code == 200
            self.record_test("GET /api/v1/engine/info", passed)
            
            if passed:
                data = response.json()
                print_info(f"引擎版本: {data.get('engine_version')}")
                print_info(f"Numba加速: {data.get('features', {}).get('numba_acceleration')}")
        except Exception as e:
            self.record_test("GET /api/v1/engine/info", False, str(e))
            
        # 创建仿真
        test_config = {
            "name": "API测试仿真",
            "description": "自动化测试用例",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 30.0,
                "dt_max": 1.0,
                "output_interval": 1.0,
                "cfl": 0.5,
                "order": 2,
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
        
        task_id = None
        try:
            response = requests.post(
                f"{self.api_v1}/simulations",
                json=test_config,
                timeout=30
            )
            passed = response.status_code in [200, 201]
            self.record_test("POST /api/v1/simulations", passed)
            
            if passed:
                data = response.json()
                task_id = data.get('task_id')
                print_info(f"任务ID: {task_id}")
        except Exception as e:
            self.record_test("POST /api/v1/simulations", False, str(e))
            
        # 查询状态
        if task_id:
            time.sleep(2)  # 等待任务开始
            try:
                response = requests.get(
                    f"{self.api_v1}/simulations/{task_id}/status",
                    timeout=5
                )
                passed = response.status_code == 200
                self.record_test("GET /api/v1/simulations/{id}/status", passed)
                
                if passed:
                    data = response.json()
                    print_info(f"状态: {data.get('status')}")
            except Exception as e:
                self.record_test("GET /api/v1/simulations/{id}/status", False, str(e))
                
            # 等待完成
            max_wait = 30
            for i in range(max_wait):
                try:
                    response = requests.get(
                        f"{self.api_v1}/simulations/{task_id}/status",
                        timeout=5
                    )
                    if response.status_code == 200:
                        status = response.json().get('status')
                        if status == 'completed':
                            print_info(f"仿真完成 (耗时 {i*1}秒)")
                            break
                        elif status == 'failed':
                            print_error("仿真失败")
                            break
                    time.sleep(1)
                except:
                    break
                    
            # 获取结果
            try:
                response = requests.get(
                    f"{self.api_v1}/simulations/{task_id}/results",
                    timeout=10
                )
                passed = response.status_code == 200
                self.record_test("GET /api/v1/simulations/{id}/results", passed)
                
                if passed:
                    data = response.json()
                    if 'results' in data:
                        results = data['results']
                        print_info(f"时间步数: {len(results.get('time', []))}")
                        print_info(f"空间点数: {len(results.get('x', []))}")
                        
                        # 检查质量守恒
                        if 'metrics' in results:
                            metrics = results['metrics']
                            mass_error = metrics.get('mass_conservation_error', 0)
                            print_info(f"质量守恒误差: {mass_error:.2e}")
            except Exception as e:
                self.record_test("GET /api/v1/simulations/{id}/results", False, str(e))
                
            # 列出仿真
            try:
                response = requests.get(f"{self.api_v1}/simulations", timeout=5)
                passed = response.status_code == 200
                self.record_test("GET /api/v1/simulations (列表)", passed)
                
                if passed:
                    data = response.json()
                    print_info(f"仿真任务总数: {len(data)}")
            except Exception as e:
                self.record_test("GET /api/v1/simulations (列表)", False, str(e))
                
            # 删除仿真
            try:
                response = requests.delete(
                    f"{self.api_v1}/simulations/{task_id}",
                    timeout=5
                )
                passed = response.status_code in [200, 204]
                self.record_test("DELETE /api/v1/simulations/{id}", passed)
            except Exception as e:
                self.record_test("DELETE /api/v1/simulations/{id}", False, str(e))
                
    def test_database(self):
        """测试数据库"""
        print_section("4. 数据库测试")
        
        try:
            sys.path.insert(0, '/workspace/web/backend')
            from shared.database import init_db, get_db
            
            # 初始化数据库
            init_db()
            self.record_test("数据库初始化", True)
            
            # 测试连接
            db = next(get_db())
            self.record_test("数据库连接", True)
            db.close()
            
        except Exception as e:
            self.record_test("数据库测试", False, str(e))
            
    def test_engine(self):
        """测试核心引擎"""
        print_section("5. 核心引擎测试")
        
        try:
            sys.path.insert(0, '/workspace/web/backend/api_gateway')
            from core.hydraulic_engine import HydraulicEngine
            
            engine = HydraulicEngine()
            
            # 获取引擎信息
            info = engine.get_engine_info()
            self.record_test(
                "引擎信息获取",
                'engine_version' in info
            )
            
            # 测试简单仿真
            test_config = {
                "width": 10.0,
                "length": 500.0,
                "n_cells": 50,
                "manning_n": 0.0,
                "slope": 0.0,
                "t_end": 10.0,
                "dt_max": 0.1,
                "output_interval": 1.0,
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
            
            result = engine.run_canal_simulation("test_001", test_config)
            self.record_test(
                "引擎运行仿真",
                result.status == 'completed'
            )
            
            if result.status == 'completed':
                metrics = result.metrics
                mass_error = abs(metrics.get('mass_conservation_error', 0))
                self.record_test(
                    "质量守恒 (误差 < 1e-8)",
                    mass_error < 1e-8,
                    f"误差: {mass_error:.2e}"
                )
                
                print_info(f"计算时间: {result.duration:.3f}秒")
                print_info(f"时间步数: {len(result.time)}")
                
        except Exception as e:
            self.record_test("核心引擎测试", False, str(e))
            
    def test_integration(self):
        """集成测试"""
        print_section("6. 集成测试")
        
        # 测试完整工作流
        test_cases = [
            {
                "name": "静态均匀流",
                "config": {
                    "width": 10.0,
                    "length": 1000.0,
                    "n_cells": 100,
                    "manning_n": 0.0,
                    "slope": 0.0,
                    "t_end": 10.0,
                    "initial_conditions": {
                        "type": "uniform",
                        "h": 5.0,
                        "Q": 0.0
                    },
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 5.0},
                        "downstream": {"type": "h", "value": 5.0}
                    }
                },
                "expected_mass_error": 1e-10
            },
            {
                "name": "浅水均匀流",
                "config": {
                    "width": 10.0,
                    "length": 500.0,
                    "n_cells": 50,
                    "manning_n": 0.0,
                    "slope": 0.0,
                    "t_end": 5.0,
                    "initial_conditions": {
                        "type": "uniform",
                        "h": 1.0,
                        "Q": 0.0
                    },
                    "boundary_conditions": {
                        "upstream": {"type": "h", "value": 1.0},
                        "downstream": {"type": "h", "value": 1.0}
                    }
                },
                "expected_mass_error": 1e-10
            }
        ]
        
        for test_case in test_cases:
            try:
                # 通过API运行
                request_data = {
                    "name": test_case["name"],
                    "config": test_case["config"]
                }
                
                response = requests.post(
                    f"{self.api_v1}/simulations",
                    json=request_data,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    task_id = response.json()['task_id']
                    
                    # 等待完成
                    for _ in range(30):
                        status_resp = requests.get(
                            f"{self.api_v1}/simulations/{task_id}/status",
                            timeout=5
                        )
                        if status_resp.status_code == 200:
                            status = status_resp.json()['status']
                            if status == 'completed':
                                # 检查结果
                                results_resp = requests.get(
                                    f"{self.api_v1}/simulations/{task_id}/results",
                                    timeout=10
                                )
                                if results_resp.status_code == 200:
                                    results = results_resp.json()['results']
                                    mass_error = abs(
                                        results['metrics'].get('mass_conservation_error', 0)
                                    )
                                    passed = mass_error < test_case['expected_mass_error']
                                    self.record_test(
                                        f"集成测试: {test_case['name']}",
                                        passed,
                                        f"质量误差: {mass_error:.2e}"
                                    )
                                break
                            elif status == 'failed':
                                self.record_test(
                                    f"集成测试: {test_case['name']}",
                                    False,
                                    "仿真失败"
                                )
                                break
                        time.sleep(1)
                    
                    # 清理
                    requests.delete(f"{self.api_v1}/simulations/{task_id}")
                else:
                    self.record_test(
                        f"集成测试: {test_case['name']}",
                        False,
                        f"创建失败: {response.status_code}"
                    )
                    
            except Exception as e:
                self.record_test(
                    f"集成测试: {test_case['name']}",
                    False,
                    str(e)
                )
                
    def test_performance(self):
        """性能测试"""
        print_section("7. 性能测试")
        
        # API响应时间
        endpoints = [
            ("/health", "健康检查"),
            ("/api/v1/engine/info", "引擎信息"),
        ]
        
        for endpoint, name in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                elapsed = (time.time() - start) * 1000  # ms
                
                passed = response.status_code == 200 and elapsed < 1000
                self.record_test(
                    f"{name} 响应时间 < 1s",
                    passed,
                    f"{elapsed:.1f}ms"
                )
                
                if passed:
                    print_info(f"响应时间: {elapsed:.1f}ms")
                    
            except Exception as e:
                self.record_test(f"{name} 响应时间", False, str(e))
                
        # 仿真性能测试
        grid_sizes = [50, 100, 200]
        
        for n_cells in grid_sizes:
            try:
                sys.path.insert(0, '/workspace/web/backend/api_gateway')
                from core.hydraulic_engine import HydraulicEngine
                
                engine = HydraulicEngine()
                config = {
                    "width": 10.0,
                    "length": 1000.0,
                    "n_cells": n_cells,
                    "manning_n": 0.0,
                    "slope": 0.0,
                    "t_end": 10.0,
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
                
                start = time.time()
                result = engine.run_canal_simulation(f"perf_{n_cells}", config)
                elapsed = time.time() - start
                
                passed = result.status == 'completed' and elapsed < 5.0
                self.record_test(
                    f"仿真性能 ({n_cells}单元) < 5s",
                    passed,
                    f"{elapsed:.3f}s"
                )
                
                if passed:
                    print_info(f"网格: {n_cells}, 时间: {elapsed:.3f}s")
                    
            except Exception as e:
                self.record_test(f"仿真性能 ({n_cells}单元)", False, str(e))
                
    def record_test(self, name, passed, details=""):
        """记录测试结果"""
        self.test_count += 1
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
            
        print_test(name, passed, details)
        
        self.results[name] = {
            "passed": passed,
            "details": details
        }
        
    def generate_report(self):
        """生成测试报告"""
        print_section("8. 测试报告")
        
        # 统计
        success_rate = (self.passed_count / self.test_count * 100) if self.test_count > 0 else 0
        
        print(f"\n{Colors.BOLD}测试统计:{Colors.ENDC}")
        print(f"  总测试数: {self.test_count}")
        print(f"  {Colors.OKGREEN}通过: {self.passed_count}{Colors.ENDC}")
        print(f"  {Colors.FAIL}失败: {self.failed_count}{Colors.ENDC}")
        print(f"  成功率: {success_rate:.1f}%")
        
        # 生成JSON报告
        report = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "total": self.test_count,
                "passed": self.passed_count,
                "failed": self.failed_count,
                "success_rate": success_rate
            },
            "results": self.results
        }
        
        report_path = Path(__file__).parent / "web_test_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"\n{Colors.OKGREEN}详细报告已保存: {report_path}{Colors.ENDC}")
        
        # 生成Markdown报告
        self.generate_markdown_report()
        
        # 最终结论
        print_header("测试结论")
        
        if success_rate >= 90:
            print_success(" 系统测试通过！系统运行良好，可以进行生产使用。")
        elif success_rate >= 70:
            print_warning("️  系统基本可用，但存在一些问题需要修复。")
        else:
            print_error(" 系统存在严重问题，需要进行修复。")
            
    def generate_markdown_report(self):
        """生成Markdown格式的测试报告"""
        report_path = Path(__file__).parent / "WEB_TEST_REPORT.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# HydroClaude Web系统测试报告\n\n")
            f.write(f"**测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**测试版本**: v1.0.0\n\n")
            
            f.write("## 测试摘要\n\n")
            f.write(f"- 总测试数: {self.test_count}\n")
            f.write(f"-  通过: {self.passed_count}\n")
            f.write(f"-  失败: {self.failed_count}\n")
            success_rate = (self.passed_count / self.test_count * 100) if self.test_count > 0 else 0
            f.write(f"- 成功率: {success_rate:.1f}%\n\n")
            
            f.write("## 详细结果\n\n")
            
            categories = [
                "环境检查",
                "后端服务",
                "API端点",
                "数据库",
                "核心引擎",
                "集成测试",
                "性能测试"
            ]
            
            for category in categories:
                f.write(f"### {category}\n\n")
                f.write("| 测试项 | 状态 | 详情 |\n")
                f.write("|--------|------|------|\n")
                
                for name, result in self.results.items():
                    if category.lower() in name.lower() or \
                       (category == "环境检查" and any(x in name for x in ["Python", "依赖", "模块"])):
                        status = " PASS" if result['passed'] else " FAIL"
                        details = result.get('details', '')
                        f.write(f"| {name} | {status} | {details} |\n")
                        
                f.write("\n")
                
            f.write("## 建议\n\n")
            
            if success_rate >= 90:
                f.write("-  系统运行良好，可以进行生产部署\n")
                f.write("- 建议进行浏览器兼容性测试\n")
                f.write("- 建议进行压力测试\n")
            elif success_rate >= 70:
                f.write("- ️  修复失败的测试项\n")
                f.write("- 重新运行完整测试\n")
            else:
                f.write("-  优先修复关键错误\n")
                f.write("- 检查环境配置\n")
                f.write("- 验证依赖安装\n")
                
        print(f"{Colors.OKGREEN}Markdown报告已保存: {report_path}{Colors.ENDC}")


def main():
    """主函数"""
    tester = WebSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
