#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细分析242个失败测试的原因

Author: HydroClaude
Date: 2025-11-13
"""

import re
import os
from collections import Counter

def extract_error_type(block):
    """从测试块中提取错误类型"""
    
    # Exit code 1
    if '错误码: 1' in block or 'Exit code: 1' in block:
        # 尝试提取更具体的错误信息
        if 'ModuleNotFoundError' in block:
            match = re.search(r"No module named '([^']+)'", block)
            if match:
                return f"ModuleNotFoundError: {match.group(1)}"
            return "ModuleNotFoundError"
        elif 'ImportError' in block:
            return "ImportError"
        elif 'UnicodeEncodeError' in block:
            match = re.search(r"'\\x([0-9a-f]+)'", block)
            if match:
                return f"UnicodeEncodeError: \\x{match.group(1)}"
            return "UnicodeEncodeError"
        elif 'AttributeError' in block:
            return "AttributeError"
        elif 'ValueError' in block:
            return "ValueError"
        elif 'RuntimeWarning' in block and 'overflow' in block:
            return "Numerical overflow"
        elif 'RuntimeWarning' in block and 'invalid value' in block:
            return "Numerical NaN/Inf"
        elif 'AssertionError' in block:
            return "AssertionError"
        elif 'TypeError' in block:
            return "TypeError"
        elif 'KeyError' in block:
            return "KeyError"
        elif 'IndexError' in block:
            return "IndexError"
        else:
            return "Exit code 1 (unknown reason)"
    
    # Timeout
    if '超时' in block or 'timeout' in block.lower():
        return "Timeout"
    
    # Unknown
    return "Unknown error"

def main():
    """分析242个失败测试"""
    
    log_file = 'test_results/batch_test_output_v3.txt'
    
    print("=" * 70)
    print(" " * 15 + "ANALYZE 242 FAILURES")
    print("=" * 70)
    print()
    
    # 读取日志
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        print(f"[ERROR] Failed to read: {e}")
        return
    
    # 解析测试块
    test_blocks = []
    lines = content.split('\n')
    
    current_test = None
    current_block = []
    current_name = ""
    current_file = ""
    
    for line in lines:
        # 检查是否是新测试的开始
        match = re.match(r'\[(\d+)/541\]\s+.*?:\s*(.+)', line)
        if match:
            # 保存前一个测试块
            if current_test is not None:
                test_blocks.append({
                    'num': current_test,
                    'name': current_name,
                    'file': current_file,
                    'content': '\n'.join(current_block)
                })
            # 开始新测试块
            current_test = int(match.group(1))
            current_name = match.group(2).strip()
            current_block = [line]
            current_file = ""
        else:
            if current_test is not None:
                current_block.append(line)
                # 提取文件路径
                if '文件:' in line:
                    file_match = re.search(r'文件:\s*(.+)', line)
                    if file_match:
                        current_file = file_match.group(1).strip()
    
    # 保存最后一个测试块
    if current_test is not None:
        test_blocks.append({
            'num': current_test,
            'name': current_name,
            'file': current_file,
            'content': '\n'.join(current_block)
        })
    
    print(f"Total test blocks parsed: {len(test_blocks)}")
    
    # 筛选失败的测试
    failed_tests = []
    for test in test_blocks:
        if 'FAIL' in test['content'] or '失败' in test['content']:
            if 'PASS' not in test['content'] or test['content'].index('FAIL') < test['content'].index('PASS'):
                failed_tests.append(test)
    
    print(f"Failed tests found: {len(failed_tests)}")
    print()
    
    # 分析失败原因
    print("-" * 70)
    print("FAILURE REASONS BREAKDOWN:")
    print("-" * 70)
    
    error_types = []
    error_details = {}
    
    for test in failed_tests:
        error_type = extract_error_type(test['content'])
        error_types.append(error_type)
        
        if error_type not in error_details:
            error_details[error_type] = []
        
        error_details[error_type].append({
            'num': test['num'],
            'name': test['name'],
            'file': test['file']
        })
    
    error_counter = Counter(error_types)
    
    for i, (error, count) in enumerate(error_counter.most_common(20), 1):
        percentage = count / len(failed_tests) * 100
        print(f"{i:2d}. [{count:3d} cases, {percentage:5.1f}%] {error}")
    
    print()
    print("-" * 70)
    print("DETAILED BREAKDOWN BY CATEGORY:")
    print("-" * 70)
    
    # 分类统计
    categories = {
        'Module/Import Errors': 0,
        'Unicode Errors': 0,
        'Numerical Issues': 0,
        'Assertion Errors': 0,
        'Timeout': 0,
        'Other Exit code 1': 0,
        'Unknown': 0
    }
    
    for error_type in error_types:
        if 'ModuleNotFoundError' in error_type or 'ImportError' in error_type:
            categories['Module/Import Errors'] += 1
        elif 'UnicodeEncodeError' in error_type:
            categories['Unicode Errors'] += 1
        elif 'overflow' in error_type or 'NaN' in error_type or 'Inf' in error_type:
            categories['Numerical Issues'] += 1
        elif 'AssertionError' in error_type:
            categories['Assertion Errors'] += 1
        elif 'Timeout' in error_type:
            categories['Timeout'] += 1
        elif 'Exit code 1' in error_type:
            categories['Other Exit code 1'] += 1
        else:
            categories['Unknown'] += 1
    
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            percentage = count / len(failed_tests) * 100
            print(f"{category:25s}: {count:3d} ({percentage:5.1f}%)")
    
    print()
    print("-" * 70)
    print("ACTIONABLE INSIGHTS:")
    print("-" * 70)
    
    # 可操作的洞察
    total = len(failed_tests)
    
    if categories['Module/Import Errors'] > 0:
        pct = categories['Module/Import Errors'] / total * 100
        print(f"1. Module/Import: {categories['Module/Import Errors']} ({pct:.1f}%)")
        print(f"   Action: Check sys.path configuration, verify imports")
    
    if categories['Unicode Errors'] > 0:
        pct = categories['Unicode Errors'] / total * 100
        print(f"2. Unicode: {categories['Unicode Errors']} ({pct:.1f}%)")
        print(f"   Action: Replace remaining Unicode characters")
    
    if categories['Numerical Issues'] > 0:
        pct = categories['Numerical Issues'] / total * 100
        print(f"3. Numerical: {categories['Numerical Issues']} ({pct:.1f}%)")
        print(f"   Action: Optimize CFL, dt_max, convergence tolerance")
    
    if categories['Assertion Errors'] > 0:
        pct = categories['Assertion Errors'] / total * 100
        print(f"4. Assertions: {categories['Assertion Errors']} ({pct:.1f}%)")
        print(f"   Action: Check test expectations, verify algorithm")
    
    if categories['Timeout'] > 0:
        pct = categories['Timeout'] / total * 100
        print(f"5. Timeout: {categories['Timeout']} ({pct:.1f}%)")
        print(f"   Action: Reduce t_end, optimize parameters")
    
    if categories['Other Exit code 1'] > 0:
        pct = categories['Other Exit code 1'] / total * 100
        print(f"6. Other Exit 1: {categories['Other Exit code 1']} ({pct:.1f}%)")
        print(f"   Action: Manual investigation needed")
    
    print()
    
    # 保存详细结果
    output_file = 'test_results/242_failures_analysis.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("DETAILED ANALYSIS OF 242 FAILED TESTS\n")
        f.write("=" * 70 + "\n\n")
        
        for error_type in error_counter.most_common():
            f.write(f"\n{'=' * 70}\n")
            f.write(f"{error_type[0]} ({error_type[1]} cases)\n")
            f.write(f"{'=' * 70}\n\n")
            
            for test in error_details[error_type[0]][:10]:  # 只列出前10个
                f.write(f"[{test['num']}] {test['name']}\n")
                f.write(f"    File: {test['file']}\n")
            
            if len(error_details[error_type[0]]) > 10:
                f.write(f"\n... and {len(error_details[error_type[0]]) - 10} more\n")
    
    print(f"Detailed analysis saved to: {output_file}")
    print()
    
    # 保存每个类别的文件列表
    for category, count in categories.items():
        if count > 0:
            safe_name = category.replace('/', '_').replace(' ', '_')
            category_file = f'test_results/failures_{safe_name.lower()}.txt'
            
            with open(category_file, 'w', encoding='utf-8') as f:
                f.write(f"{category}: {count} cases\n")
                f.write("=" * 70 + "\n\n")
                
                for error_type, tests in error_details.items():
                    # 检查是否属于这个类别
                    if (category == 'Module/Import Errors' and ('Module' in error_type or 'Import' in error_type)) or \
                       (category == 'Unicode Errors' and 'Unicode' in error_type) or \
                       (category == 'Numerical Issues' and ('overflow' in error_type or 'NaN' in error_type)) or \
                       (category == 'Assertion Errors' and 'Assertion' in error_type) or \
                       (category == 'Timeout' and 'Timeout' in error_type) or \
                       (category == 'Other Exit code 1' and 'Exit code 1 (unknown' in error_type):
                        
                        for test in tests:
                            f.write(f"{test['file']}\n")
    
    print("Category files saved to test_results/failures_*.txt")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

