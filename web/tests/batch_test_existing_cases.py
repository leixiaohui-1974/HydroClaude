#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量测试已有案例 - Web端到端测试
Batch Test Existing Cases - Web E2E Testing

扫描并测试所有已完成的后端测试案例

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# 项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class BatchTestExecutor:
    """批量测试执行器"""
    
    def __init__(self):
        self.test_results = []
        self.total_cases = 0
        self.passed_cases = 0
        self.failed_cases = 0
        self.skipped_cases = 0
        
        # 扫描路径
        self.scan_paths = [
            project_root / 'examples',
            project_root / 'tests',
            project_root / 'web' / 'backend' / 'examples'
        ]
    
    def scan_test_cases(self) -> List[Path]:
        """扫描所有测试案例"""
        print("\n" + "="*80)
        print("扫描测试案例...")
        print("="*80)
        
        test_files = []
        
        for scan_path in self.scan_paths:
            if not scan_path.exists():
                continue
            
            # 查找所有Python文件
            for py_file in scan_path.rglob("*.py"):
                # 排除备份文件和__init__文件
                if any(x in str(py_file) for x in ['.bak', '__pycache__', '__init__']):
                    continue
                
                # 检查是否是可执行的测试/示例
                if self._is_executable_case(py_file):
                    test_files.append(py_file)
        
        print(f"\n✅ 扫描完成，找到 {len(test_files)} 个测试案例")
        return test_files
    
    def _is_executable_case(self, file_path: Path) -> bool:
        """判断是否是可执行的测试案例"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查是否有main函数
                return 'if __name__' in content and 'main' in content
        except:
            return False
    
    def categorize_cases(self, test_files: List[Path]) -> Dict[str, List[Path]]:
        """分类测试案例"""
        categories = {
            'canal_flow': [],
            'pump_system': [],
            'hydropower': [],
            'network': [],
            'gate_weir': [],
            'reservoir': [],
            'numerical': [],
            'integration': [],
            'other': []
        }
        
        for file_path in test_files:
            file_str = str(file_path).lower()
            
            if 'canal' in file_str or 'channel' in file_str:
                categories['canal_flow'].append(file_path)
            elif 'pump' in file_str:
                categories['pump_system'].append(file_path)
            elif 'turbine' in file_str or 'hydropower' in file_str:
                categories['hydropower'].append(file_path)
            elif 'network' in file_str:
                categories['network'].append(file_path)
            elif 'gate' in file_str or 'weir' in file_str:
                categories['gate_weir'].append(file_path)
            elif 'reservoir' in file_str:
                categories['reservoir'].append(file_path)
            elif 'numerical' in file_str or 'convergence' in file_str:
                categories['numerical'].append(file_path)
            elif 'integration' in file_str or 'workflow' in file_str:
                categories['integration'].append(file_path)
            else:
                categories['other'].append(file_path)
        
        return categories
    
    def run_test_case(self, file_path: Path, timeout: int = 60) -> Tuple[bool, str, float]:
        """运行单个测试案例"""
        start_time = time.time()
        
        try:
            # 运行Python文件
            result = subprocess.run(
                [sys.executable, str(file_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(file_path.parent)
            )
            
            elapsed_time = time.time() - start_time
            
            # 判断是否成功
            if result.returncode == 0:
                # 检查输出是否有错误标记
                output = result.stdout + result.stderr
                if any(x in output.lower() for x in ['error', 'exception', 'traceback', 'failed']):
                    if 'test passed' in output.lower() or 'success' in output.lower():
                        return True, "PASS", elapsed_time
                    else:
                        return False, f"输出包含错误: {output[:200]}", elapsed_time
                else:
                    return True, "PASS", elapsed_time
            else:
                error_msg = result.stderr[:500] if result.stderr else "未知错误"
                return False, f"退出码{result.returncode}: {error_msg}", elapsed_time
                
        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            return False, f"超时({timeout}秒)", elapsed_time
        except Exception as e:
            elapsed_time = time.time() - start_time
            return False, f"异常: {str(e)[:200]}", elapsed_time
    
    def batch_test_category(self, category: str, test_files: List[Path], 
                           sample_size: int = 10) -> Dict:
        """批量测试某个类别"""
        print(f"\n{'='*80}")
        print(f"测试类别: {category}")
        print(f"案例总数: {len(test_files)}")
        print(f"抽样测试: {min(sample_size, len(test_files))} 个")
        print(f"{'='*80}")
        
        # 抽样测试
        import random
        if len(test_files) > sample_size:
            sampled_files = random.sample(test_files, sample_size)
        else:
            sampled_files = test_files
        
        category_results = {
            'category': category,
            'total': len(test_files),
            'tested': len(sampled_files),
            'passed': 0,
            'failed': 0,
            'cases': []
        }
        
        for i, file_path in enumerate(sampled_files, 1):
            print(f"\n[{i}/{len(sampled_files)}] 测试: {file_path.name}")
            
            success, message, elapsed = self.run_test_case(file_path)
            
            case_result = {
                'file': str(file_path.relative_to(project_root)),
                'name': file_path.stem,
                'success': success,
                'message': message,
                'time': elapsed
            }
            
            category_results['cases'].append(case_result)
            
            if success:
                category_results['passed'] += 1
                self.passed_cases += 1
                print(f"  ✅ PASS ({elapsed:.2f}s)")
            else:
                category_results['failed'] += 1
                self.failed_cases += 1
                print(f"  ❌ FAIL ({elapsed:.2f}s): {message[:100]}")
            
            self.total_cases += 1
        
        return category_results
    
    def run_all_tests(self, sample_per_category: int = 10):
        """运行所有测试"""
        print("\n" + "🎯"*40)
        print("批量测试已有案例 - Web端到端测试".center(80))
        print("🎯"*40)
        
        # 1. 扫描测试案例
        test_files = self.scan_test_cases()
        
        if not test_files:
            print("\n❌ 没有找到测试案例")
            return
        
        # 2. 分类
        categories = self.categorize_cases(test_files)
        
        print("\n" + "="*80)
        print("测试案例分类统计")
        print("="*80)
        for category, files in categories.items():
            if files:
                print(f"  {category:<20} {len(files):>3} 个案例")
        
        # 3. 批量测试每个类别
        all_results = []
        
        for category, files in categories.items():
            if not files:
                continue
            
            result = self.batch_test_category(category, files, sample_per_category)
            all_results.append(result)
            self.test_results.append(result)
        
        # 4. 生成报告
        self.generate_report(all_results)
    
    def generate_report(self, all_results: List[Dict]):
        """生成测试报告"""
        print("\n" + "="*80)
        print("测试报告".center(80))
        print("="*80)
        
        # 总体统计
        print(f"\n总体统计:")
        print(f"  总测试案例: {self.total_cases}")
        print(f"  通过: {self.passed_cases} ({self.passed_cases/self.total_cases*100:.1f}%)")
        print(f"  失败: {self.failed_cases} ({self.failed_cases/self.total_cases*100:.1f}%)")
        
        # 分类统计
        print(f"\n分类统计:")
        print(f"{'类别':<20} {'测试数':<10} {'通过':<10} {'失败':<10} {'通过率':<10}")
        print("-"*80)
        
        for result in all_results:
            category = result['category']
            tested = result['tested']
            passed = result['passed']
            failed = result['failed']
            rate = f"{passed/tested*100:.1f}%" if tested > 0 else "N/A"
            
            print(f"{category:<20} {tested:<10} {passed:<10} {failed:<10} {rate:<10}")
        
        print("-"*80)
        
        # 失败案例详情
        if self.failed_cases > 0:
            print(f"\n失败案例详情:")
            print("-"*80)
            
            for result in all_results:
                failed_cases = [c for c in result['cases'] if not c['success']]
                if failed_cases:
                    print(f"\n{result['category']}:")
                    for case in failed_cases[:5]:  # 只显示前5个
                        print(f"  ❌ {case['name']}")
                        print(f"     {case['message'][:100]}")
        
        # 保存详细结果
        output_file = 'batch_test_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': self.total_cases,
                    'passed': self.passed_cases,
                    'failed': self.failed_cases,
                    'pass_rate': self.passed_cases/self.total_cases if self.total_cases > 0 else 0
                },
                'categories': all_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 详细结果已保存到: {output_file}")
        
        # 最终结论
        print("\n" + "🎉"*40)
        if self.failed_cases == 0:
            print("✅ 所有测试通过！".center(80))
        else:
            print(f"⚠️  {self.failed_cases}/{self.total_cases} 个测试失败".center(80))
        print("🎉"*40)


if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='批量测试已有案例')
    parser.add_argument('--sample', type=int, default=10, 
                       help='每个类别抽样测试的数量（默认10）')
    parser.add_argument('--all', action='store_true',
                       help='测试所有案例（不抽样）')
    
    args = parser.parse_args()
    
    sample_size = 999999 if args.all else args.sample
    
    # 执行批量测试
    executor = BatchTestExecutor()
    executor.run_all_tests(sample_per_category=sample_size)
