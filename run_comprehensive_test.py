#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 综合测试脚本
执行完整的后台算法和Web界面测试，生成详细报告和截图

Author: HydroClaude Team
Date: 2025-11-12
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import traceback

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class ComprehensiveTestRunner:
    """综合测试运行器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            'summary': {},
            'backend_tests': {},
            'web_api_tests': {},
            'web_ui_tests': {},
            'e2e_tests': {},
            'screenshots': []
        }
        self.screenshots_dir = PROJECT_ROOT / 'test_screenshots'
        self.screenshots_dir.mkdir(exist_ok=True)
        
    def print_header(self, text: str, level: int = 1):
        """打印格式化的标题"""
        if level == 1:
            print('\n' + '=' * 80)
            print(f'  {text}')
            print('=' * 80 + '\n')
        elif level == 2:
            print('\n' + '-' * 80)
            print(f'  {text}')
            print('-' * 80 + '\n')
        else:
            print(f'\n>>> {text}\n')
    
    def run_backend_algorithm_tests(self) -> Dict[str, Any]:
        """Phase 1: 后台算法测试"""
        self.print_header('Phase 1: 后台算法测试', 1)
        
        results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0}
        }
        
        # 1.1 测试GodunvFVMSolver
        self.print_header('1.1 测试GodunvFVMSolver', 2)
        godunov_result = self._test_godunov_solver()
        results['tests'].append(godunov_result)
        
        # 1.2 测试HydrostaticCanalSolver
        self.print_header('1.2 测试HydrostaticCanalSolver', 2)
        hydrostatic_result = self._test_hydrostatic_solver()
        results['tests'].append(hydrostatic_result)
        
        # 1.3 测试水力学工具
        self.print_header('1.3 测试水力学工具', 2)
        utils_result = self._test_canal_utils()
        results['tests'].append(utils_result)
        
        # 1.4 测试ResultValidator
        self.print_header('1.4 测试ResultValidator', 2)
        validator_result = self._test_result_validator()
        results['tests'].append(validator_result)
        
        # 统计
        results['summary']['total'] = len(results['tests'])
        results['summary']['passed'] = sum(1 for t in results['tests'] if t['status'] == 'passed')
        results['summary']['failed'] = results['summary']['total'] - results['summary']['passed']
        results['end_time'] = datetime.now().isoformat()
        
        return results
    
    def _test_godunov_solver(self) -> Dict[str, Any]:
        """测试GodunvFVMSolver"""
        try:
            from solvers.godunov_fvm_solver import GodunvFVMSolver
            import numpy as np
            
            # 创建求解器
            solver = GodunvFVMSolver(
                width=10.0,
                length=1000.0,
                n_cells=100,
                manning_n=0.025,
                slope=0.001,
                order=1
            )
            
            # 初始化
            h_init = np.ones(100) * 2.0
            Q_init = np.ones(100) * 50.0
            bc_left = {'type': 'Q', 'value': 50.0}
            bc_right = {'type': 'h', 'value': 2.0}
            solver.initialize(h_init, Q_init, bc_left, bc_right)
            
            # 运行几步
            for _ in range(10):
                solver.step()
            
            # 检查质量守恒
            mass_error = solver.get_mass_conservation_error()
            
            return {
                'name': 'GodunvFVMSolver',
                'status': 'passed' if mass_error < 5.0 else 'failed',
                'message': f'质量守恒误差: {mass_error:.6f}%',
                'metrics': {
                    'mass_error': mass_error,
                    'steps': solver.step_count,
                    'time': solver.t
                }
            }
        except Exception as e:
            return {
                'name': 'GodunvFVMSolver',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_hydrostatic_solver(self) -> Dict[str, Any]:
        """测试HydrostaticCanalSolver"""
        try:
            from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
            from utils.canal_utils import compute_steady_uniform_flow
            import numpy as np
            
            # 创建求解器
            solver = HydrostaticCanalSolver(
                length=10000.0,
                nx=201,
                B=10.0,
                S0=0.0005,
                n=0.025
            )
            
            # 初始化
            h_uniform = compute_steady_uniform_flow(10.0, 10.0, 0.0005, 0.025)
            solver.h[:] = h_uniform
            solver.hu[:] = 10.0 / 10.0
            
            # 稳态求解
            result = solver.solve_steady_state(
                Q_target=10.0,
                h_downstream=h_uniform,
                max_iterations=100,
                convergence_tol=0.1,
                verbose=False
            )
            
            return {
                'name': 'HydrostaticCanalSolver',
                'status': 'passed' if result['converged'] and result['Q_error_percent'] < 0.01 else 'failed',
                'message': f"收敛: {result['converged']}, 流量误差: {result['Q_error_percent']:.6f}%",
                'metrics': {
                    'converged': result['converged'],
                    'iterations': result['iterations'],
                    'Q_error_percent': result['Q_error_percent']
                }
            }
        except Exception as e:
            return {
                'name': 'HydrostaticCanalSolver',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_canal_utils(self) -> Dict[str, Any]:
        """测试水力学工具函数"""
        try:
            from utils.canal_utils import (
                compute_steady_uniform_flow,
                compute_critical_depth,
                compute_froude_number
            )
            
            # 测试均匀流计算
            h_uniform = compute_steady_uniform_flow(10.0, 10.0, 0.001, 0.025)
            
            # 测试临界水深
            h_c = compute_critical_depth(10.0, 10.0)
            
            # 测试Froude数
            Fr = compute_froude_number(h_uniform, 1.0)
            
            # 验证结果合理性
            checks = [
                h_uniform > 0,
                h_c > 0,
                Fr > 0,
                0.5 < h_uniform < 2.0,  # 合理范围
                0.3 < h_c < 0.8
            ]
            
            return {
                'name': 'canal_utils',
                'status': 'passed' if all(checks) else 'failed',
                'message': f'均匀流水深={h_uniform:.4f}m, 临界水深={h_c:.4f}m, Fr={Fr:.4f}',
                'metrics': {
                    'h_uniform': float(h_uniform),
                    'h_critical': float(h_c),
                    'froude': float(Fr)
                }
            }
        except Exception as e:
            return {
                'name': 'canal_utils',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_result_validator(self) -> Dict[str, Any]:
        """测试ResultValidator"""
        try:
            from utils.result_validator import ResultValidator
            import numpy as np
            
            validator = ResultValidator()
            
            # 测试流量守恒验证
            Q_computed = np.ones(100) * 10.0
            Q_target = 10.0
            
            result = validator.validate_flow_conservation(
                Q_computed=Q_computed,
                Q_target=Q_target,
                label="Test Flow"
            )
            
            return {
                'name': 'ResultValidator',
                'status': 'passed' if result['grade'] in ['优秀 (Excellent)', '良好 (Good)'] else 'failed',
                'message': f"等级: {result['grade']}, 误差: {result['error_percent']:.6f}%",
                'metrics': {
                    'grade': result['grade'],
                    'error_percent': result['error_percent']
                }
            }
        except Exception as e:
            return {
                'name': 'ResultValidator',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def run_web_api_tests(self) -> Dict[str, Any]:
        """Phase 2: Web API测试"""
        self.print_header('Phase 2: Web API测试', 1)
        
        results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0}
        }
        
        # 检查服务是否运行
        if not self._check_backend_running():
            print('️  后端服务未运行，尝试启动...')
            if not self._start_backend_service():
                results['tests'].append({
                    'name': 'Backend Service',
                    'status': 'failed',
                    'message': '无法启动后端服务'
                })
                return results
        
        # 2.1 健康检查
        self.print_header('2.1 健康检查', 2)
        health_result = self._test_health_endpoint()
        results['tests'].append(health_result)
        
        # 2.2 引擎信息
        self.print_header('2.2 引擎信息', 2)
        engine_result = self._test_engine_info()
        results['tests'].append(engine_result)
        
        # 2.3 仿真API
        self.print_header('2.3 仿真API', 2)
        sim_result = self._test_simulation_api()
        results['tests'].append(sim_result)
        
        # 统计
        results['summary']['total'] = len(results['tests'])
        results['summary']['passed'] = sum(1 for t in results['tests'] if t['status'] == 'passed')
        results['summary']['failed'] = results['summary']['total'] - results['summary']['passed']
        results['end_time'] = datetime.now().isoformat()
        
        return results
    
    def _check_backend_running(self) -> bool:
        """检查后端服务是否运行"""
        try:
            import requests
            response = requests.get('http://localhost:8000/health', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _start_backend_service(self) -> bool:
        """启动后端服务"""
        try:
            web_dir = PROJECT_ROOT / 'web'
            start_script = web_dir / 'start_servers.sh'
            
            if start_script.exists():
                subprocess.Popen(['bash', str(start_script)], cwd=str(web_dir))
                print('等待服务启动...')
                time.sleep(20)
                return self._check_backend_running()
            return False
        except Exception as e:
            print(f'启动失败: {e}')
            return False
    
    def _test_health_endpoint(self) -> Dict[str, Any]:
        """测试健康检查端点"""
        try:
            import requests
            
            response = requests.get('http://localhost:8000/health', timeout=5)
            data = response.json()
            
            return {
                'name': 'Health Check',
                'status': 'passed' if response.status_code == 200 and data.get('status') == 'healthy' else 'failed',
                'message': f"状态码: {response.status_code}, 响应: {data.get('status')}",
                'response': data
            }
        except Exception as e:
            return {
                'name': 'Health Check',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_engine_info(self) -> Dict[str, Any]:
        """测试引擎信息端点"""
        try:
            import requests
            
            response = requests.get('http://localhost:8000/api/v1/engine/info', timeout=5)
            data = response.json()
            
            return {
                'name': 'Engine Info',
                'status': 'passed' if response.status_code == 200 else 'failed',
                'message': f"引擎: {data.get('engine_name')}, 版本: {data.get('version')}",
                'response': data
            }
        except Exception as e:
            return {
                'name': 'Engine Info',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_simulation_api(self) -> Dict[str, Any]:
        """测试仿真API"""
        try:
            import requests
            
            # 创建测试配置
            config = {
                'name': 'Test Simulation',
                'canal_params': {
                    'length': 10000.0,
                    'width': 10.0,
                    'slope': 0.0005,
                    'manning_n': 0.025,
                    'flow_rate': 10.0
                },
                'solver_params': {
                    'nx': 201,
                    'convergence_tol': 0.1,
                    'max_iterations': 100
                }
            }
            
            response = requests.post(
                'http://localhost:8000/api/v1/simulations/run',
                json=config,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'name': 'Simulation API',
                    'status': 'passed',
                    'message': f"仿真ID: {data.get('simulation_id')}, 状态: {data.get('status')}",
                    'response': data
                }
            else:
                return {
                    'name': 'Simulation API',
                    'status': 'failed',
                    'message': f"状态码: {response.status_code}",
                    'response': response.text
                }
        except Exception as e:
            return {
                'name': 'Simulation API',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def run_web_ui_tests(self) -> Dict[str, Any]:
        """Phase 3: Web UI测试（带截图）"""
        self.print_header('Phase 3: Web UI测试（带截图）', 1)
        
        results = {
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0},
            'screenshots': []
        }
        
        # 检查前端是否运行
        if not self._check_frontend_running():
            print('️  前端服务未运行，跳过UI测试')
            results['tests'].append({
                'name': 'Frontend Service',
                'status': 'skipped',
                'message': '前端服务未运行'
            })
            return results
        
        # 启动浏览器测试
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            
            try:
                # 3.1 首页加载
                self.print_header('3.1 测试首页加载', 2)
                homepage_result = self._test_homepage(driver)
                results['tests'].append(homepage_result)
                if homepage_result.get('screenshot'):
                    results['screenshots'].append(homepage_result['screenshot'])
                
                # 3.2 模型编辑器
                self.print_header('3.2 测试模型编辑器', 2)
                editor_result = self._test_model_editor(driver)
                results['tests'].append(editor_result)
                if editor_result.get('screenshot'):
                    results['screenshots'].append(editor_result['screenshot'])
                
                # 3.3 测试功能按钮
                self.print_header('3.3 测试功能按钮', 2)
                button_result = self._test_ui_buttons(driver)
                results['tests'].append(button_result)
                if button_result.get('screenshot'):
                    results['screenshots'].append(button_result['screenshot'])
                
            finally:
                driver.quit()
            
            # 统计
            results['summary']['total'] = len(results['tests'])
            results['summary']['passed'] = sum(1 for t in results['tests'] if t['status'] == 'passed')
            results['summary']['failed'] = results['summary']['total'] - results['summary']['passed']
            
        except Exception as e:
            results['tests'].append({
                'name': 'Browser Tests',
                'status': 'failed',
                'message': f'浏览器测试失败: {str(e)}',
                'error': traceback.format_exc()
            })
        
        results['end_time'] = datetime.now().isoformat()
        return results
    
    def _check_frontend_running(self) -> bool:
        """检查前端服务是否运行"""
        try:
            import requests
            response = requests.get('http://localhost:5173', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _test_homepage(self, driver) -> Dict[str, Any]:
        """测试首页加载"""
        try:
            driver.get('http://localhost:5173')
            time.sleep(3)  # 等待页面加载
            
            # 截图
            screenshot_path = self.screenshots_dir / '01_homepage.png'
            driver.save_screenshot(str(screenshot_path))
            
            # 检查标题
            title = driver.title
            
            return {
                'name': 'Homepage Load',
                'status': 'passed' if 'HydroClaude' in title or len(title) > 0 else 'failed',
                'message': f'页面标题: {title}',
                'screenshot': str(screenshot_path)
            }
        except Exception as e:
            return {
                'name': 'Homepage Load',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_model_editor(self, driver) -> Dict[str, Any]:
        """测试模型编辑器"""
        try:
            # 等待页面元素
            time.sleep(2)
            
            # 截图
            screenshot_path = self.screenshots_dir / '02_model_editor.png'
            driver.save_screenshot(str(screenshot_path))
            
            # 检查是否有输入框
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            
            return {
                'name': 'Model Editor',
                'status': 'passed' if len(inputs) > 0 else 'failed',
                'message': f'发现 {len(inputs)} 个输入框',
                'screenshot': str(screenshot_path)
            }
        except Exception as e:
            return {
                'name': 'Model Editor',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def _test_ui_buttons(self, driver) -> Dict[str, Any]:
        """测试UI按钮"""
        try:
            # 查找按钮
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            
            # 截图
            screenshot_path = self.screenshots_dir / '03_ui_buttons.png'
            driver.save_screenshot(str(screenshot_path))
            
            return {
                'name': 'UI Buttons',
                'status': 'passed' if len(buttons) > 0 else 'failed',
                'message': f'发现 {len(buttons)} 个按钮',
                'screenshot': str(screenshot_path)
            }
        except Exception as e:
            return {
                'name': 'UI Buttons',
                'status': 'failed',
                'message': f'错误: {str(e)}',
                'error': traceback.format_exc()
            }
    
    def generate_report(self):
        """生成测试报告"""
        self.print_header('生成测试报告', 1)
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # 汇总统计
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for phase in ['backend_tests', 'web_api_tests', 'web_ui_tests']:
            if phase in self.results and 'summary' in self.results[phase]:
                summary = self.results[phase]['summary']
                total_tests += summary.get('total', 0)
                passed_tests += summary.get('passed', 0)
                failed_tests += summary.get('failed', 0)
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'pass_rate': round(passed_tests / total_tests * 100, 2) if total_tests > 0 else 0,
            'duration_seconds': round(duration, 2),
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        # 保存JSON报告
        report_path = PROJECT_ROOT / 'comprehensive_test_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f' JSON报告已保存: {report_path}')
        
        # 生成Markdown报告
        self._generate_markdown_report()
        
        # 打印摘要
        self._print_summary()
    
    def _generate_markdown_report(self):
        """生成Markdown格式报告"""
        report_path = PROJECT_ROOT / 'COMPREHENSIVE_TEST_REPORT.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('# HydroClaude 综合测试报告\n\n')
            f.write(f'**测试日期**: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            f.write(f'**测试时长**: {self.results["summary"]["duration_seconds"]:.2f} 秒\n\n')
            
            # 总体统计
            f.write('##  总体统计\n\n')
            summary = self.results['summary']
            f.write(f'- **总测试数**: {summary["total_tests"]}\n')
            f.write(f'- **通过**: {summary["passed"]} \n')
            f.write(f'- **失败**: {summary["failed"]} \n')
            f.write(f'- **通过率**: {summary["pass_rate"]}%\n\n')
            
            # 后台测试
            if 'backend_tests' in self.results:
                f.write('##  后台算法测试\n\n')
                for test in self.results['backend_tests'].get('tests', []):
                    status_icon = '' if test['status'] == 'passed' else ''
                    f.write(f'### {status_icon} {test["name"]}\n\n')
                    f.write(f'- **状态**: {test["status"]}\n')
                    f.write(f'- **信息**: {test["message"]}\n\n')
            
            # Web API测试
            if 'web_api_tests' in self.results:
                f.write('##  Web API测试\n\n')
                for test in self.results['web_api_tests'].get('tests', []):
                    status_icon = '' if test['status'] == 'passed' else ''
                    f.write(f'### {status_icon} {test["name"]}\n\n')
                    f.write(f'- **状态**: {test["status"]}\n')
                    f.write(f'- **信息**: {test["message"]}\n\n')
            
            # Web UI测试
            if 'web_ui_tests' in self.results:
                f.write('## ️ Web UI测试\n\n')
                for test in self.results['web_ui_tests'].get('tests', []):
                    status_icon = '' if test['status'] == 'passed' else ''
                    f.write(f'### {status_icon} {test["name"]}\n\n')
                    f.write(f'- **状态**: {test["status"]}\n')
                    f.write(f'- **信息**: {test["message"]}\n')
                    if 'screenshot' in test:
                        f.write(f'- **截图**: `{test["screenshot"]}`\n')
                    f.write('\n')
            
            # 截图列表
            if self.results['web_ui_tests'].get('screenshots'):
                f.write('##  测试截图\n\n')
                for screenshot in self.results['web_ui_tests']['screenshots']:
                    f.write(f'- {screenshot}\n')
                f.write('\n')
            
            f.write('---\n\n')
            f.write('**报告生成时间**: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
        
        print(f' Markdown报告已保存: {report_path}')
    
    def _print_summary(self):
        """打印测试摘要"""
        self.print_header('测试摘要', 1)
        
        summary = self.results['summary']
        
        print(f'总测试数: {summary["total_tests"]}')
        print(f'通过: {summary["passed"]} ')
        print(f'失败: {summary["failed"]} ')
        print(f'通过率: {summary["pass_rate"]}%')
        print(f'测试时长: {summary["duration_seconds"]:.2f} 秒')
        
        # 判断整体结果
        if summary['pass_rate'] >= 95:
            print('\n 测试结果: 优秀！')
        elif summary['pass_rate'] >= 80:
            print('\n 测试结果: 良好')
        elif summary['pass_rate'] >= 60:
            print('\n️  测试结果: 一般，需要改进')
        else:
            print('\n 测试结果: 较差，需要重点修复')
        
        print(f'\n 详细报告: {PROJECT_ROOT}/COMPREHENSIVE_TEST_REPORT.md')
        print(f' JSON数据: {PROJECT_ROOT}/comprehensive_test_report.json')
        print(f' 截图目录: {self.screenshots_dir}')
    
    def run_all_tests(self):
        """运行所有测试"""
        print('\n' + '=' * 80)
        print('  HydroClaude 综合测试套件')
        print('=' * 80 + '\n')
        print(f'开始时间: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'测试输出: {PROJECT_ROOT}')
        print(f'截图目录: {self.screenshots_dir}\n')
        
        try:
            # Phase 1: 后台算法测试
            self.results['backend_tests'] = self.run_backend_algorithm_tests()
            
            # Phase 2: Web API测试
            self.results['web_api_tests'] = self.run_web_api_tests()
            
            # Phase 3: Web UI测试
            self.results['web_ui_tests'] = self.run_web_ui_tests()
            
            # 生成报告
            self.generate_report()
            
        except KeyboardInterrupt:
            print('\n\n️  测试被用户中断')
            self.generate_report()
        except Exception as e:
            print(f'\n\n 测试过程中发生错误: {e}')
            traceback.print_exc()
            self.generate_report()


def main():
    """主函数"""
    runner = ComprehensiveTestRunner()
    runner.run_all_tests()


if __name__ == '__main__':
    main()







