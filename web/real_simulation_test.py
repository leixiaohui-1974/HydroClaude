#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Web 真实仿真测试脚本
测试完整的仿真流程，包括提交、等待、结果验证

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class RealSimulationTest:
    """真实仿真测试"""
    
    def __init__(self):
        self.api_base = "http://localhost:8000/api/v1"
        self.test_results = []
        
    def log_header(self, message: str):
        """打印标题"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{message:^80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        
    def log_success(self, message: str):
        """打印成功消息"""
        print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")
        
    def log_error(self, message: str):
        """打印错误消息"""
        print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")
        
    def log_warning(self, message: str):
        """打印警告消息"""
        print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")
        
    def log_info(self, message: str):
        """打印信息消息"""
        print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")
        
    def test_backend_health(self) -> bool:
        """测试1: 后端健康检查"""
        self.log_header("测试1: 后端服务健康检查")
        
        try:
            response = requests.get(f"{self.api_base.replace('/api/v1', '')}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"后端服务运行正常")
                self.log_info(f"服务: {data.get('service')}")
                self.log_info(f"版本: {data.get('version')}")
                self.log_info(f"状态: {data.get('status')}")
                return True
            else:
                self.log_error(f"后端服务响应异常: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"后端服务无法访问: {str(e)}")
            return False
            
    def test_engine_info(self) -> bool:
        """测试2: 引擎信息"""
        self.log_header("测试2: 水力学引擎信息")
        
        try:
            response = requests.get(f"{self.api_base}/engine/info", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.log_success("引擎信息获取成功")
                self.log_info(f"引擎版本: {data.get('version', 'N/A')}")
                self.log_info(f"求解器: {data.get('solvers', [])}")
                return True
            else:
                self.log_error(f"引擎信息获取失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"引擎信息请求失败: {str(e)}")
            return False
            
    def run_simulation(self, config_name: str, config: Dict) -> Dict:
        """运行仿真"""
        self.log_header(f"运行仿真: {config_name}")
        
        try:
            # 1. 提交仿真
            self.log_info("提交仿真配置...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.api_base}/simulations",
                json=config,
                timeout=30
            )
            
            # 接受200和201状态码
            if response.status_code not in [200, 201]:
                self.log_error(f"仿真提交失败: {response.status_code}")
                self.log_error(f"响应: {response.text}")
                return {"success": False, "error": response.text}
            
            result = response.json()
            task_id = result.get('task_id')
            
            if not task_id:
                self.log_error("未获取到任务ID")
                return {"success": False, "error": "No task_id"}
            
            self.log_success(f"仿真已提交，任务ID: {task_id}")
            
            # 2. 轮询状态
            self.log_info("等待仿真完成...")
            max_wait = 60  # 最多等待60秒
            poll_interval = 2
            
            for i in range(max_wait // poll_interval):
                time.sleep(poll_interval)
                
                status_response = requests.get(
                    f"{self.api_base}/simulations/{task_id}/status",
                    timeout=5
                )
                
                if status_response.status_code != 200:
                    self.log_warning(f"状态查询失败: {status_response.status_code}")
                    continue
                
                status_data = status_response.json()
                status = status_data.get('status')
                
                if status == 'completed':
                    elapsed = time.time() - start_time
                    self.log_success(f"仿真完成！耗时: {elapsed:.2f}秒")
                    
                    # 3. 获取结果
                    self.log_info("获取仿真结果...")
                    results_response = requests.get(
                        f"{self.api_base}/simulations/{task_id}/results",
                        timeout=10
                    )
                    
                    if results_response.status_code != 200:
                        self.log_error("结果获取失败")
                        return {"success": False, "error": "Failed to get results"}
                    
                    results = results_response.json()
                    
                    # 4. 分析结果
                    self.analyze_results(config_name, results)
                    
                    return {
                        "success": True,
                        "task_id": task_id,
                        "results": results,
                        "elapsed": elapsed
                    }
                    
                elif status == 'failed':
                    error_msg = status_data.get('error', 'Unknown error')
                    self.log_error(f"仿真失败: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
                else:
                    # 仍在运行
                    elapsed = time.time() - start_time
                    self.log_info(f"状态: {status}, 已等待: {elapsed:.1f}秒")
            
            # 超时
            self.log_error(f"仿真超时（>{max_wait}秒）")
            return {"success": False, "error": "Timeout"}
            
        except Exception as e:
            self.log_error(f"仿真执行异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
            
    def analyze_results(self, name: str, results: Dict):
        """分析仿真结果"""
        self.log_info("\n" + "="*80)
        self.log_info(f"📊 仿真结果分析: {name}")
        self.log_info("="*80)
        
        # 基本信息
        task_id = results.get('task_id', 'N/A')
        status = results.get('status', 'unknown')
        
        print(f"\n{Colors.BOLD}基本信息:{Colors.ENDC}")
        print(f"  任务ID: {task_id}")
        print(f"  状态: {status}")
        
        # 计算指标
        if 'mass_conservation_error' in results:
            mass_error = results['mass_conservation_error']
            print(f"\n{Colors.BOLD}质量守恒:{Colors.ENDC}")
            
            if mass_error < 0.01:
                self.log_success(f"质量守恒误差: {mass_error:.6f}% - 优秀")
            elif mass_error < 0.1:
                self.log_info(f"质量守恒误差: {mass_error:.6f}% - 良好")
            else:
                self.log_warning(f"质量守恒误差: {mass_error:.6f}% - 需要改进")
        
        if 'compute_time' in results:
            compute_time = results['compute_time']
            print(f"\n{Colors.BOLD}性能指标:{Colors.ENDC}")
            
            if compute_time < 1.0:
                self.log_success(f"计算耗时: {compute_time:.3f}秒 - 快速")
            elif compute_time < 10.0:
                self.log_info(f"计算耗时: {compute_time:.3f}秒 - 正常")
            else:
                self.log_warning(f"计算耗时: {compute_time:.3f}秒 - 较慢")
        
        # 数据分析
        if 'x' in results and 'h' in results and 'Q' in results:
            import numpy as np
            
            x = np.array(results['x'])
            h_data = results['h']
            Q_data = results['Q']
            
            # 取最后时刻的数据
            if isinstance(h_data[0], list):
                h = np.array(h_data[-1])
                Q = np.array(Q_data[-1])
            else:
                h = np.array(h_data)
                Q = np.array(Q_data)
            
            print(f"\n{Colors.BOLD}水力学参数统计:{Colors.ENDC}")
            print(f"  网格数: {len(x)}")
            print(f"  渠道长度: {x[-1] - x[0]:.1f} m")
            print(f"  平均水深: {np.mean(h):.3f} m")
            print(f"  最大水深: {np.max(h):.3f} m")
            print(f"  最小水深: {np.min(h):.3f} m")
            print(f"  平均流量: {np.mean(Q):.3f} m³/s")
            print(f"  流量变化: {np.std(Q):.6f} m³/s")
            
            # 计算Froude数
            width = results.get('width', 5.0)
            velocity = Q / (width * h)
            g = 9.81
            froude = velocity / np.sqrt(g * h)
            
            print(f"\n{Colors.BOLD}流态分析:{Colors.ENDC}")
            print(f"  平均流速: {np.mean(velocity):.3f} m/s")
            print(f"  最大流速: {np.max(velocity):.3f} m/s")
            print(f"  平均Froude数: {np.mean(froude):.3f}")
            
            if np.mean(froude) < 1.0:
                self.log_success("流态: 缓流 (Subcritical)")
            else:
                self.log_warning("流态: 急流 (Supercritical)")
        
        print()
        
    def run_all_tests(self):
        """运行所有测试"""
        self.log_header("HydroClaude Web 真实仿真测试")
        
        # 测试1: 后端健康检查
        if not self.test_backend_health():
            self.log_error("后端服务未运行，测试终止")
            return False
        
        time.sleep(1)
        
        # 测试2: 引擎信息
        self.test_engine_info()
        
        time.sleep(1)
        
        # 测试3: 基础稳态流动
        config1 = {
            "name": "基础稳态流动测试",
            "description": "简单矩形渠道的稳态流动",
            "config": {
                "width": 5.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "bed_slope": 0.001,
                "t_end": 30.0,
                "cfl": 0.5,
                "order": 1,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 2.0,
                    "Q": 10.0
                },
                "boundary_conditions": {
                    "upstream": {
                        "type": "Q",
                        "value": 10.0
                    },
                    "downstream": {
                        "type": "h",
                        "value": 2.0
                    }
                }
            }
        }
        
        result1 = self.run_simulation("基础稳态流动", config1)
        self.test_results.append(result1)
        
        time.sleep(2)
        
        # 测试4: 快速测试案例
        config2 = {
            "name": "快速测试",
            "description": "快速验证计算",
            "config": {
                "width": 5.0,
                "length": 500.0,
                "n_cells": 50,
                "manning_n": 0.025,
                "bed_slope": 0.001,
                "t_end": 15.0,
                "cfl": 0.5,
                "order": 1,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 1.5,
                    "Q": 7.5
                },
                "boundary_conditions": {
                    "upstream": {
                        "type": "Q",
                        "value": 7.5
                    },
                    "downstream": {
                        "type": "h",
                        "value": 1.5
                    }
                }
            }
        }
        
        result2 = self.run_simulation("快速测试", config2)
        self.test_results.append(result2)
        
        # 生成总结报告
        self.generate_summary()
        
        return all(r.get('success', False) for r in self.test_results)
        
    def generate_summary(self):
        """生成测试总结"""
        self.log_header("测试总结")
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r.get('success', False))
        failed = total - success
        
        print(f"\n{Colors.BOLD}测试统计:{Colors.ENDC}")
        print(f"  总测试数: {total}")
        
        if success == total:
            self.log_success(f"全部通过: {success}/{total}")
        else:
            print(f"  {Colors.OKGREEN}通过: {success}{Colors.ENDC}")
            print(f"  {Colors.FAIL}失败: {failed}{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}详细结果:{Colors.ENDC}")
        for i, result in enumerate(self.test_results, 1):
            if result.get('success'):
                elapsed = result.get('elapsed', 0)
                self.log_success(f"测试 {i}: 成功 (耗时: {elapsed:.2f}秒)")
            else:
                error = result.get('error', 'Unknown')
                self.log_error(f"测试 {i}: 失败 ({error})")
        
        print()


def main():
    """主函数"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║              HydroClaude Web 真实仿真测试                                 ║")
    print("║              Real Simulation Testing                                     ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    tester = RealSimulationTest()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ 所有测试通过！系统运行正常！{Colors.ENDC}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}❌ 部分测试失败，请检查日志{Colors.ENDC}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
