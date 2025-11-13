#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
真实的失败原因分析 - 不夸大，不掩盖

Author: HydroClaude
Date: 2025-11-13
"""

import json
import os
from collections import Counter

def main():
    """分析真实的失败情况"""
    
    print("=" * 60)
    print(" " * 15 + "REAL FAILURE ANALYSIS")
    print("=" * 60)
    print()
    
    # 读取测试结果
    results_file = 'test_results/batch_test_results.json'
    if not os.path.exists(results_file):
        print(f"[ERROR] {results_file} not found!")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # 统计
    total = len(results)
    passed = [r for r in results if r['status'] == 'passed']
    failed = [r for r in results if r['status'] == 'failed']
    
    print(f"Total tests: {total}")
    print(f"Passed: {len(passed)} ({len(passed)/total*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/total*100:.1f}%)")
    print()
    
    # 分析失败原因
    print("-" * 60)
    print("FAILURE REASONS (Top 15):")
    print("-" * 60)
    
    error_types = []
    for r in failed:
        error = r.get('error', 'Unknown')
        # 提取关键错误类型
        if 'Exit code' in error:
            error_types.append('Exit code 1')
        elif 'ModuleNotFoundError' in error:
            module = error.split("'")[1] if "'" in error else 'unknown'
            error_types.append(f'ModuleNotFoundError: {module}')
        elif 'ImportError' in error:
            error_types.append('ImportError')
        elif 'Timeout' in error:
            error_types.append('Timeout')
        elif 'UnicodeEncodeError' in error:
            error_types.append('UnicodeEncodeError')
        elif error:
            # 截取前50个字符
            error_types.append(error[:50])
        else:
            error_types.append('Unknown error')
    
    error_counter = Counter(error_types)
    
    for i, (error, count) in enumerate(error_counter.most_common(15), 1):
        percentage = count / len(failed) * 100
        print(f"{i:2d}. [{count:3d} cases, {percentage:5.1f}%] {error}")
    
    print()
    print("-" * 60)
    print("EXIT CODE 1 DETAILS:")
    print("-" * 60)
    
    exit_code_failures = [r for r in failed if 'Exit code' in r.get('error', '')]
    print(f"Total Exit code 1 failures: {len(exit_code_failures)}")
    print(f"Percentage of all failures: {len(exit_code_failures)/len(failed)*100:.1f}%")
    print()
    
    if exit_code_failures:
        print("Sample Exit code 1 failures (first 10):")
        for i, r in enumerate(exit_code_failures[:10], 1):
            file_name = os.path.basename(r['file'])
            print(f"{i:2d}. {file_name}")
    
    print()
    print("-" * 60)
    print("MODULE NOT FOUND DETAILS:")
    print("-" * 60)
    
    module_failures = [r for r in failed if 'ModuleNotFoundError' in r.get('error', '')]
    print(f"Total ModuleNotFoundError failures: {len(module_failures)}")
    print(f"Percentage of all failures: {len(module_failures)/len(failed)*100:.1f}%")
    print()
    
    if module_failures:
        modules = []
        for r in module_failures:
            error = r.get('error', '')
            if "'" in error:
                module = error.split("'")[1]
                modules.append(module)
        
        module_counter = Counter(modules)
        print("Missing modules:")
        for module, count in module_counter.most_common(10):
            print(f"  - {module}: {count} cases")
    
    print()
    print("-" * 60)
    print("REALISTIC ASSESSMENT:")
    print("-" * 60)
    print(f"Pass rate: {len(passed)/total*100:.1f}%")
    print(f"Fail rate: {len(failed)/total*100:.1f}%")
    print(f"Gap to 100%: {100 - len(passed)/total*100:.1f}%")
    print(f"Tests need to fix: {len(failed)}")
    print()
    print("Current status: PROBLEMATIC")
    print("Reason: Nearly 50% failure rate")
    print("Action needed: Deep analysis of failures")
    print()
    
    # 保存详细失败列表
    output_file = 'test_results/detailed_failures.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DETAILED FAILURE LIST\n")
        f.write("=" * 80 + "\n\n")
        
        for i, r in enumerate(failed, 1):
            f.write(f"[{i}/{len(failed)}] {os.path.basename(r['file'])}\n")
            f.write(f"Error: {r.get('error', 'Unknown')}\n")
            f.write("-" * 80 + "\n")
    
    print(f"Detailed failure list saved to: {output_file}")
    print()
    print("=" * 60)
    print("CONCLUSION: Need to fix {0} failures to reach 100%".format(len(failed)))
    print("=" * 60)


if __name__ == '__main__':
    main()

