#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面测试所有仿真案例

基于成功经验，测试和修复所有仿真相关的测试文件

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path

def find_all_simulation_files():
    """查找所有仿真相关的Python文件"""
    examples_dir = Path('examples')
    
    # 排除这些目录/文件
    exclude_patterns = [
        '**/backups/**',
        '**/*.bak*',
        '**/__pycache__/**',
        '**/output_helper.py',
        '**/animation_utils.py',
    ]
    
    # 包含这些类型
    include_patterns = [
        '**/example_*.py',
        '**/demo_*.py',
        '**/case_*.py',
        '**/run_*.py',
        '**/*_v2.py',
        '**/scripts/*.py',
    ]
    
    all_files = []
    for pattern in include_patterns:
        files = list(examples_dir.glob(pattern))
        all_files.extend(files)
    
    # 去重并排除
    unique_files = []
    seen = set()
    for f in all_files:
        if f.is_file() and str(f) not in seen:
            # 检查是否在排除列表中
            exclude = False
            for exclude_pattern in exclude_patterns:
                if f.match(exclude_pattern):
                    exclude = True
                    break
            
            if not exclude:
                seen.add(str(f))
                unique_files.append(f)
    
    return sorted(unique_files)

def test_file(file_path, timeout=60):
    """测试单个文件"""
    try:
        start = time.time()
        result = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        elapsed = time.time() - start
        
        if result.returncode == 0:
            return 'PASS', elapsed, None
        else:
            # 提取错误信息
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            error_msg = 'Unknown error'
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    error_msg = line.strip()[:100]
                    break
            return 'FAIL', elapsed, error_msg
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, f'Timeout (>{timeout}s)'
    except Exception as e:
        return 'ERROR', 0, str(e)[:80]

def categorize_error(error_msg):
    """分类错误类型"""
    if not error_msg:
        return 'Unknown'
    
    error_lower = error_msg.lower()
    
    if 'modulenotfounderror' in error_lower or 'importerror' in error_lower:
        return 'Import'
    elif 'unicodeencodeerror' in error_lower or 'unicodedecodeerror' in error_lower:
        return 'Unicode'
    elif 'attributeerror' in error_lower:
        return 'Attribute'
    elif 'typeerror' in error_lower:
        return 'Type'
    elif 'valueerror' in error_lower:
        return 'Value'
    elif 'filenotfounderror' in error_lower:
        return 'FileNotFound'
    elif 'timeout' in error_lower:
        return 'Timeout'
    else:
        return 'Other'

def main():
    """主函数"""
    
    print("="*80)
    print("全面测试所有仿真案例")
    print("="*80)
    print()
    
    # 查找所有文件
    print("正在搜索仿真文件...")
    all_files = find_all_simulation_files()
    print(f"找到 {len(all_files)} 个文件")
    print()
    
    # 测试所有文件
    results = {}
    errors = []
    error_categories = {}
    
    print("开始测试...")
    print("-"*80)
    
    for i, file_path in enumerate(all_files, 1):
        rel_path = file_path.relative_to('examples')
        basename = file_path.name
        
        # 根据文件位置设置超时
        if 'scenario' in str(file_path):
            timeout = 120
        elif 'optimization' in str(file_path) or 'mpc' in str(file_path):
            timeout = 120
        elif 'benchmark' in str(file_path):
            timeout = 60
        else:
            timeout = 30
        
        print(f"[{i:3d}/{len(all_files)}] {str(rel_path):60s}", end=" ", flush=True)
        
        status, elapsed, error = test_file(file_path, timeout=timeout)
        print(f"[{status:7s}] ({elapsed:.1f}s)")
        
        results[str(rel_path)] = {
            'status': status,
            'elapsed': elapsed,
            'error': error
        }
        
        if status in ['FAIL', 'ERROR'] and error:
            error_cat = categorize_error(error)
            errors.append({
                'file': str(rel_path),
                'category': error_cat,
                'error': error
            })
            error_categories[error_cat] = error_categories.get(error_cat, 0) + 1
    
    print()
    print("="*80)
    print("测试结果汇总")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r['status'] == 'PASS')
    failed = sum(1 for r in results.values() if r['status'] == 'FAIL')
    timeout_count = sum(1 for r in results.values() if r['status'] == 'TIMEOUT')
    error_count = sum(1 for r in results.values() if r['status'] == 'ERROR')
    
    total = len(results)
    
    print(f"\n总计: {total} 个文件")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    print(f"超时: {timeout_count} ({timeout_count/total*100:.1f}%)")
    print(f"错误: {error_count} ({error_count/total*100:.1f}%)")
    
    print(f"\n通过率: {passed}/{total} = {passed/total*100:.1f}%")
    
    # 错误分类统计
    if error_categories:
        print(f"\n错误类型分布:")
        for cat, count in sorted(error_categories.items(), key=lambda x: -x[1]):
            print(f"  {cat:15s}: {count:3d}")
    
    # 保存结果
    output = {
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'timeout': timeout_count,
            'error': error_count,
            'pass_rate': passed / total * 100 if total > 0 else 0
        },
        'results': results,
        'errors': errors,
        'error_categories': error_categories
    }
    
    with open('all_simulations_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: all_simulations_test_results.json")
    
    # 显示前10个错误
    if errors:
        print(f"\n前10个错误:")
        print("-"*80)
        for err in errors[:10]:
            print(f"\n{err['file']}")
            print(f"  类型: {err['category']}")
            print(f"  错误: {err['error']}")
    
    print("\n" + "="*80)
    
    return passed, total

if __name__ == '__main__':
    passed, total = main()
    
    # 根据通过率给出评价
    pass_rate = passed / total * 100 if total > 0 else 0
    
    print(f"\n最终评价: ", end="")
    if pass_rate >= 95:
        print("优秀 ⭐⭐⭐⭐⭐")
    elif pass_rate >= 85:
        print("良好 ⭐⭐⭐⭐")
    elif pass_rate >= 75:
        print("合格 ⭐⭐⭐")
    elif pass_rate >= 60:
        print("需改进 ⭐⭐")
    else:
        print("不及格 ⭐")
