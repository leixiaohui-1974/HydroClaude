#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows中文环境完整测试脚本
测试后端API的所有功能，包括中文字符支持

使用方法:
    python Windows中文环境测试脚本.py
"""

import sys
import os
import io
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Any

# ========== Windows UTF-8 设置 ==========
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# API配置
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

# 颜色输出（Windows兼容）
def print_success(msg: str):
    """成功消息"""
    print(f"✅ {msg}")

def print_error(msg: str):
    """错误消息"""
    print(f"❌ {msg}")

def print_info(msg: str):
    """信息消息"""
    print(f"ℹ️  {msg}")

def print_warning(msg: str):
    """警告消息"""
    print(f"⚠️  {msg}")

def print_header(msg: str):
    """标题"""
    print("\n" + "="*70)
    print(f"  {msg}")
    print("="*70)


class WindowsCompatibleTestRunner:
    """Windows兼容的测试运行器"""
    
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def check_backend_health(self) -> bool:
        """检查后端健康状态"""
        print_header("步骤 1: 检查后端服务")
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success(f"后端服务正常运行")
                print_info(f"  服务: {data.get('service', 'N/A')}")
                print_info(f"  版本: {data.get('version', 'N/A')}")
                print_info(f"  时间: {data.get('timestamp', 'N/A')}")
                return True
            else:
                print_error(f"后端返回异常状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print_error("无法连接到后端服务！")
            print_warning("请先运行: 启动后端_Windows.bat")
            return False
        except Exception as e:
            print_error(f"健康检查失败: {str(e)}")
            return False
    
    def test_chinese_simulation(self) -> Dict[str, Any]:
        """测试中文名称的仿真"""
        print_header("步骤 2: 测试中文名称仿真")
        
        test_config = {
            "name": "均匀流测试_中文环境",
            "description": "这是一个包含中文描述的测试用例，用于验证系统对中文的支持。",
            "config": {
                "width": 10.0,
                "length": 1000.0,
                "n_cells": 100,
                "manning_n": 0.025,
                "slope": 0.001,
                "t_end": 10.0,
                "dt_max": 0.1,
                "cfl": 0.5,
                "order": 1,
                "output_interval": 0.5,
                "initial_conditions": {
                    "type": "uniform",
                    "h": 5.0,
                    "Q": 10.0
                },
                "boundary_conditions": {
                    "upstream": {"type": "Q", "value": 10.0},
                    "downstream": {"type": "h", "value": 5.0}
                }
            }
        }
        
        try:
            self.results['total'] += 1
            
            # 提交仿真
            print_info("正在提交仿真任务...")
            response = requests.post(
                f"{self.api_url}/api/v1/simulations",
                json=test_config,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                print_error(f"提交失败: {response.status_code}")
                print_error(f"响应: {response.text}")
                self.results['failed'] += 1
                self.results['errors'].append("中文仿真提交失败")
                return None
            
            result = response.json()
            task_id = result['task_id']
            print_success(f"任务已提交: {task_id}")
            print_info(f"  名称: {result.get('name', 'N/A')}")
            
            # 等待完成
            print_info("正在等待仿真完成...")
            max_wait = 30  # 最多等待30秒
            
            for i in range(max_wait):
                time.sleep(1)
                status_response = requests.get(
                    f"{self.api_url}/api/v1/simulations/{task_id}/status",
                    timeout=5
                )
                
                if status_response.status_code != 200:
                    print_error(f"状态查询失败: {status_response.status_code}")
                    break
                
                status_data = status_response.json()
                status = status_data['status']
                
                # 显示进度
                progress_bar = "█" * (i % 10) + "░" * (10 - (i % 10))
                print(f"\r  进度: [{progress_bar}] 状态: {status} ({i+1}s)", end='', flush=True)
                
                if status == 'completed':
                    print()  # 换行
                    print_success("仿真完成！")
                    
                    # 获取结果
                    results_response = requests.get(
                        f"{self.api_url}/api/v1/simulations/{task_id}/results",
                        timeout=10
                    )
                    
                    if results_response.status_code == 200:
                        results_data = results_response.json()
                        metrics = results_data['metrics']
                        
                        print_info("仿真结果:")
                        print(f"    - 质量守恒误差: {metrics['mass_conservation_error']:.8f}%")
                        print(f"    - 最大水深: {metrics['max_depth']:.3f} m")
                        print(f"    - 平均水深: {metrics['mean_depth_final']:.3f} m")
                        print(f"    - 最大流速: {metrics['max_velocity']:.3f} m/s")
                        print(f"    - 收敛状态: {'✅ 已收敛' if metrics['converged'] else '❌ 未收敛'}")
                        print(f"    - 计算耗时: {results_data['duration']:.3f} 秒")
                        
                        # 验证结果
                        if metrics['mass_conservation_error'] < 0.001 and metrics['converged']:
                            print_success("✅ 测试通过！")
                            self.results['passed'] += 1
                        else:
                            print_warning("⚠️  结果异常")
                            self.results['failed'] += 1
                            self.results['errors'].append("仿真结果不符合预期")
                        
                        return results_data
                    else:
                        print_error(f"获取结果失败: {results_response.status_code}")
                        self.results['failed'] += 1
                        self.results['errors'].append("无法获取仿真结果")
                        return None
                
                elif status == 'failed':
                    print()  # 换行
                    error_msg = status_data.get('error', '未知错误')
                    print_error(f"仿真失败: {error_msg}")
                    self.results['failed'] += 1
                    self.results['errors'].append(f"仿真失败: {error_msg}")
                    return None
            
            # 超时
            print()
            print_warning("等待超时")
            self.results['failed'] += 1
            self.results['errors'].append("仿真超时")
            return None
            
        except Exception as e:
            print_error(f"测试异常: {str(e)}")
            self.results['failed'] += 1
            self.results['errors'].append(f"异常: {str(e)}")
            return None
    
    def test_api_list(self):
        """测试API列表功能"""
        print_header("步骤 3: 测试仿真列表API")
        
        try:
            self.results['total'] += 1
            
            response = requests.get(f"{self.api_url}/api/v1/simulations", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('simulations', []))
                print_success(f"获取列表成功: 共 {count} 个仿真任务")
                self.results['passed'] += 1
            else:
                print_error(f"获取列表失败: {response.status_code}")
                self.results['failed'] += 1
                self.results['errors'].append("列表API失败")
                
        except Exception as e:
            print_error(f"测试异常: {str(e)}")
            self.results['failed'] += 1
            self.results['errors'].append(f"列表API异常: {str(e)}")
    
    def print_summary(self):
        """打印测试总结"""
        print_header("测试总结")
        
        total = self.results['total']
        passed = self.results['passed']
        failed = self.results['failed']
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"成功率: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n错误列表:")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"  {i}. {error}")
        
        print("\n" + "="*70)
        
        if failed == 0:
            print_success("🎉 所有测试通过！")
        else:
            print_warning(f"⚠️  有 {failed} 个测试失败")
        
        print("="*70 + "\n")
        
        return failed == 0


def main():
    """主函数"""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*15 + "HydroClaude Web Windows中文环境测试" + " "*18 + "║")
    print("╚" + "═"*68 + "╝\n")
    
    print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Python版本: {sys.version.split()[0]}")
    print_info(f"平台: {sys.platform}")
    print_info(f"编码: {sys.stdout.encoding}")
    print_info(f"API地址: {API_URL}")
    
    # 创建测试运行器
    runner = WindowsCompatibleTestRunner(API_URL)
    
    # 运行测试
    if not runner.check_backend_health():
        print_error("\n后端服务未运行，测试终止！")
        print_info("请执行以下步骤:")
        print_info("  1. 打开新的命令行窗口")
        print_info("  2. 运行: 启动后端_Windows.bat")
        print_info("  3. 等待服务器启动完成")
        print_info("  4. 重新运行此测试脚本")
        return 1
    
    # 执行测试
    runner.test_chinese_simulation()
    runner.test_api_list()
    
    # 打印总结
    success = runner.print_summary()
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        input("\n按回车键退出...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n严重错误: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        sys.exit(1)
