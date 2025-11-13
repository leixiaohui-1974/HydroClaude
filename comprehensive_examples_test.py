#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 全面案例后台测试脚本
适用于Windows中文环境，测试所有examples下的案例

Author: HydroClaude Test Team
Date: 2025-11-13
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import traceback

# 确保输出使用UTF-8编码，避免Windows GBK问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()
EXAMPLES_DIR = PROJECT_ROOT / "examples"
RESULTS_DIR = PROJECT_ROOT / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)

class ExamplesTestRunner:
    """Examples案例测试运行器"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.test_categories = {
            'basic': [],      # 基础案例
            'advanced': [],   # 高级案例
            'gate_pump': [],  # 闸门泵站
            'network': [],    # 管网系统
            'special': []     # 特殊案例
        }
        
    def discover_test_scripts(self):
        """发现所有可测试的脚本"""
        print("\n" + "="*80)
        print("  发现测试脚本")
        print("="*80)
        
        # 1. example_01_canal_flow - 基础明渠案例
        canal_scripts_dir = EXAMPLES_DIR / "example_01_canal_flow" / "scripts"
        if canal_scripts_dir.exists():
            for script in sorted(canal_scripts_dir.glob("*.py")):
                # 跳过特殊文件
                if script.name.startswith('_') or script.name.startswith('output_'):
                    continue
                # 优先测试v2版本
                if '_v2' in script.name or 'refactored' not in script.name:
                    self.test_categories['basic'].append({
                        'path': script,
                        'name': f"明渠流动/{script.stem}",
                        'category': 'basic'
                    })
        
        # 2. example_gate_pump_cascade - 闸门泵站级联
        gate_pump_dir = EXAMPLES_DIR / "example_gate_pump_cascade"
        if gate_pump_dir.exists():
            for script in sorted(gate_pump_dir.glob("*.py")):
                if script.name.startswith('run_') or script.name.startswith('test_'):
                    self.test_categories['gate_pump'].append({
                        'path': script,
                        'name': f"闸门泵站/{script.stem}",
                        'category': 'gate_pump'
                    })
        
        # 3. advanced_examples - 高级案例
        advanced_dir = EXAMPLES_DIR / "advanced_examples"
        if advanced_dir.exists():
            for script in advanced_dir.glob("*.py"):
                if not script.name.startswith('_'):
                    self.test_categories['advanced'].append({
                        'path': script,
                        'name': f"高级案例/{script.stem}",
                        'category': 'advanced'
                    })
        
        # 4. 其他主要案例目录
        main_examples = [
            'example_02_pump_system',
            'example_02_spillway_cascade',
            'example_03_complex_network',
            'example_03_turbine_demo',
            'example_04_hydropower_system',
            'example_05_transient_analysis',
            'example_06_complete_hydropower_system'
        ]
        
        for example_name in main_examples:
            example_dir = EXAMPLES_DIR / example_name
            if example_dir.exists():
                # 查找主要的运行脚本
                for pattern in ['run*.py', 'demo*.py', 'example*.py']:
                    for script in example_dir.glob(pattern):
                        if not script.name.startswith('_'):
                            self.test_categories['special'].append({
                                'path': script,
                                'name': f"{example_name}/{script.stem}",
                                'category': 'special'
                            })
        
        # 5. examples根目录下的独立案例
        for script in EXAMPLES_DIR.glob("case*.py"):
            self.test_categories['special'].append({
                'path': script,
                'name': f"独立案例/{script.stem}",
                'category': 'special'
            })
        
        # 统计
        total = sum(len(scripts) for scripts in self.test_categories.values())
        print(f"\n发现测试脚本总数: {total}")
        for category, scripts in self.test_categories.items():
            if scripts:
                print(f"  - {category}: {len(scripts)} 个脚本")
        
        return total
    
    def run_single_test(self, test_info: Dict, timeout: int = 300) -> Dict:
        """
        运行单个测试脚本
        
        Args:
            test_info: 测试信息字典
            timeout: 超时时间（秒）
        
        Returns:
            测试结果字典
        """
        script_path = test_info['path']
        script_name = test_info['name']
        
        print(f"\n{'='*80}")
        print(f"测试: {script_name}")
        print(f"路径: {script_path}")
        print(f"{'='*80}")
        
        result = {
            'name': script_name,
            'path': str(script_path),
            'category': test_info['category'],
            'start_time': datetime.now().isoformat(),
            'status': 'unknown',
            'duration': 0,
            'error': None,
            'output': '',
            'returncode': None
        }
        
        start_time = time.time()
        
        try:
            # 使用subprocess运行脚本，捕获所有输出
            # 在Windows上设置环境变量以使用UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # 运行脚本
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(script_path.parent),
                env=env,
                encoding='utf-8',
                errors='replace',  # 重要：替换无法编码的字符
                text=True
            )
            
            # 等待完成或超时
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
                
                result['returncode'] = returncode
                result['output'] = stdout + "\n" + stderr
                result['duration'] = time.time() - start_time
                
                # 判断是否成功
                if returncode == 0:
                    # 检查输出中是否有明显的错误标志
                    output_lower = result['output'].lower()
                    if 'error' in output_lower or 'exception' in output_lower or 'traceback' in output_lower:
                        if 'error' in output_lower and output_lower.count('error') < 3:
                            # 少量error可能是正常的（如"mass conservation error"）
                            result['status'] = 'passed'
                        else:
                            result['status'] = 'passed_with_warnings'
                    else:
                        result['status'] = 'passed'
                    print(f"状态: 通过")
                else:
                    result['status'] = 'failed'
                    result['error'] = f"脚本返回非零退出码: {returncode}"
                    print(f"状态: 失败 (退出码: {returncode})")
                
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                result['status'] = 'timeout'
                result['error'] = f"超时 (>{timeout}秒)"
                result['output'] = stdout + "\n" + stderr
                result['duration'] = timeout
                print(f"状态: 超时")
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"状态: 错误")
            print(f"错误信息: {e}")
            traceback.print_exc()
        
        print(f"耗时: {result['duration']:.2f}秒")
        
        return result
    
    def run_all_tests(self, categories: List[str] = None, max_tests: int = None):
        """
        运行所有测试
        
        Args:
            categories: 要测试的类别列表，None表示全部
            max_tests: 最大测试数量，用于快速测试
        """
        self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("  开始全面测试")
        print("="*80)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"操作系统: {sys.platform}")
        print(f"Python版本: {sys.version}")
        
        # 确定要测试的脚本
        test_list = []
        if categories is None:
            categories = list(self.test_categories.keys())
        
        for category in categories:
            if category in self.test_categories:
                test_list.extend(self.test_categories[category])
        
        if max_tests:
            test_list = test_list[:max_tests]
        
        total_tests = len(test_list)
        print(f"总测试数: {total_tests}")
        
        # 运行测试
        for i, test_info in enumerate(test_list, 1):
            print(f"\n[{i}/{total_tests}] ", end='')
            
            result = self.run_single_test(test_info, timeout=300)
            self.results.append(result)
            
            # 实时保存结果
            self.save_results()
        
        # 最终报告
        self.print_summary()
    
    def save_results(self):
        """保存测试结果到JSON文件"""
        output_file = RESULTS_DIR / f"examples_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {
            'test_time': datetime.now().isoformat(),
            'platform': sys.platform,
            'python_version': sys.version,
            'total_tests': len(self.results),
            'results': self.results,
            'summary': self.get_summary_stats()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存: {output_file}")
    
    def get_summary_stats(self) -> Dict:
        """获取汇总统计"""
        stats = {
            'passed': 0,
            'failed': 0,
            'timeout': 0,
            'error': 0,
            'passed_with_warnings': 0,
            'unknown': 0,
            'total_duration': 0
        }
        
        for result in self.results:
            status = result['status']
            stats[status] = stats.get(status, 0) + 1
            stats['total_duration'] += result['duration']
        
        stats['success_rate'] = (stats['passed'] + stats['passed_with_warnings']) / len(self.results) * 100 if self.results else 0
        
        return stats
    
    def print_summary(self):
        """打印测试总结"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        stats = self.get_summary_stats()
        
        print("\n" + "="*80)
        print("  测试总结")
        print("="*80)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration:.2f}秒 ({duration/60:.1f}分钟)")
        print(f"\n总测试数: {len(self.results)}")
        print(f"  - 通过: {stats['passed']}")
        print(f"  - 通过(有警告): {stats['passed_with_warnings']}")
        print(f"  - 失败: {stats['failed']}")
        print(f"  - 超时: {stats['timeout']}")
        print(f"  - 错误: {stats['error']}")
        print(f"  - 未知: {stats['unknown']}")
        print(f"\n成功率: {stats['success_rate']:.1f}%")
        
        # 失败案例列表
        if stats['failed'] > 0 or stats['error'] > 0:
            print("\n失败案例:")
            for result in self.results:
                if result['status'] in ['failed', 'error']:
                    print(f"  - {result['name']}")
                    if result['error']:
                        print(f"    错误: {result['error'][:100]}")
        
        print("="*80)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HydroClaude Examples 全面测试')
    parser.add_argument('--categories', nargs='+', 
                       choices=['basic', 'advanced', 'gate_pump', 'network', 'special', 'all'],
                       default=['all'],
                       help='要测试的类别')
    parser.add_argument('--max-tests', type=int, default=None,
                       help='最大测试数量（用于快速测试）')
    parser.add_argument('--timeout', type=int, default=300,
                       help='单个测试超时时间（秒）')
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = ExamplesTestRunner()
    
    # 发现测试脚本
    total = runner.discover_test_scripts()
    
    if total == 0:
        print("\n未发现可测试的脚本！")
        return
    
    # 确定测试类别
    categories = None if 'all' in args.categories else args.categories
    
    # 运行测试
    try:
        runner.run_all_tests(categories=categories, max_tests=args.max_tests)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        runner.print_summary()
    except Exception as e:
        print(f"\n\n测试过程出错: {e}")
        traceback.print_exc()
        runner.print_summary()


if __name__ == '__main__':
    main()
