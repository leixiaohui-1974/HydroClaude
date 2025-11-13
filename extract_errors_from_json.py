#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从JSON结果中提取失败原因并分类

Author: HydroClaude
Date: 2025-11-13
"""

import json
import os
from collections import Counter

def main():
    """提取并分类错误"""
    
    json_file = 'test_results/batch_test_results.json'
    
    print("=" * 70)
    print(" " * 15 + "EXTRACT ERRORS FROM JSON")
    print("=" * 70)
    print()
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data['results']
    failed = [r for r in results if r['status'] == 'failed']
    
    print(f"Total failed: {len(failed)}")
    print()
    
    # 分类错误
    error_categories = {
        'UnicodeEncodeError': [],
        'ModuleNotFoundError': [],
        'ImportError': [],
        'Exit code 1 - Other': [],
        'Numerical Issues': [],
        'AttributeError': [],
        'Other': []
    }
    
    for r in failed:
        error = r.get('error_message', '')
        file_path = r.get('case_id', '')
        
        if 'UnicodeEncodeError' in error:
            char = ''
            if '\\x' in error:
                import re
                match = re.search(r"'\\x([0-9a-f]+)'", error)
                if match:
                    char = f"\\x{match.group(1)}"
            error_categories['UnicodeEncodeError'].append({
                'file': file_path,
                'char': char,
                'error': error[:200]
            })
        elif 'ModuleNotFoundError' in error:
            import re
            match = re.search(r"No module named '([^']+)'", error)
            module = match.group(1) if match else 'unknown'
            error_categories['ModuleNotFoundError'].append({
                'file': file_path,
                'module': module,
                'error': error[:200]
            })
        elif 'ImportError' in error:
            error_categories['ImportError'].append({
                'file': file_path,
                'error': error[:200]
            })
        elif 'AttributeError' in error:
            error_categories['AttributeError'].append({
                'file': file_path,
                'error': error[:200]
            })
        elif 'RuntimeWarning' in error and ('overflow' in error or 'invalid value' in error):
            error_categories['Numerical Issues'].append({
                'file': file_path,
                'error': error[:200]
            })
        elif 'Exit code: 1' in error:
            error_categories['Exit code 1 - Other'].append({
                'file': file_path,
                'error': error[:200]
            })
        else:
            error_categories['Other'].append({
                'file': file_path,
                'error': error[:200]
            })
    
    # 打印统计
    print("-" * 70)
    print("ERROR CATEGORIES:")
    print("-" * 70)
    
    for category, items in sorted(error_categories.items(), key=lambda x: len(x[1]), reverse=True):
        if len(items) > 0:
            percentage = len(items) / len(failed) * 100
            print(f"{category:30s}: {len(items):3d} ({percentage:5.1f}%)")
    
    print()
    print("-" * 70)
    print("FIXABLE ERRORS (Top Priority):")
    print("-" * 70)
    
    # Unicode错误
    if error_categories['UnicodeEncodeError']:
        print(f"\n1. UnicodeEncodeError: {len(error_categories['UnicodeEncodeError'])} cases")
        print("   Action: Replace Unicode characters")
        
        # 统计问题字符
        chars = [item['char'] for item in error_categories['UnicodeEncodeError'] if item['char']]
        char_counter = Counter(chars)
        print("   Problem characters:")
        for char, count in char_counter.most_common(10):
            print(f"     - {char}: {count} cases")
        
        # 保存文件列表
        with open('test_results/files_unicode_errors.txt', 'w', encoding='utf-8') as f:
            for item in error_categories['UnicodeEncodeError']:
                # 转换case_id为文件路径
                case_id = item['file']
                # 格式: "tests-xxx" -> "tests/xxx.py"
                if case_id.startswith('tests-'):
                    file_path = 'tests/' + case_id[6:] + '.py'
                elif '-' in case_id:
                    parts = case_id.split('-', 1)
                    file_path = parts[0] + '/' + parts[1].replace('-', '/') + '.py'
                else:
                    file_path = case_id + '.py'
                f.write(file_path + '\n')
        
        print("   Files saved to: test_results/files_unicode_errors.txt")
    
    # Module错误
    if error_categories['ModuleNotFoundError']:
        print(f"\n2. ModuleNotFoundError: {len(error_categories['ModuleNotFoundError'])} cases")
        print("   Action: Fix imports or add sys.path")
        
        # 统计缺失模块
        modules = [item['module'] for item in error_categories['ModuleNotFoundError']]
        module_counter = Counter(modules)
        print("   Missing modules:")
        for module, count in module_counter.most_common(10):
            print(f"     - {module}: {count} cases")
        
        # 保存文件列表
        with open('test_results/files_module_errors.txt', 'w', encoding='utf-8') as f:
            for item in error_categories['ModuleNotFoundError']:
                case_id = item['file']
                if case_id.startswith('tests-'):
                    file_path = 'tests/' + case_id[6:] + '.py'
                elif '-' in case_id:
                    parts = case_id.split('-', 1)
                    file_path = parts[0] + '/' + parts[1].replace('-', '/') + '.py'
                else:
                    file_path = case_id + '.py'
                f.write(file_path + '\n')
        
        print("   Files saved to: test_results/files_module_errors.txt")
    
    # 数值问题
    if error_categories['Numerical Issues']:
        print(f"\n3. Numerical Issues: {len(error_categories['Numerical Issues'])} cases")
        print("   Action: Optimize CFL, dt_max, convergence tolerance")
        
        with open('test_results/files_numerical_errors.txt', 'w', encoding='utf-8') as f:
            for item in error_categories['Numerical Issues']:
                case_id = item['file']
                if case_id.startswith('tests-'):
                    file_path = 'tests/' + case_id[6:] + '.py'
                elif '-' in case_id:
                    parts = case_id.split('-', 1)
                    file_path = parts[0] + '/' + parts[1].replace('-', '/') + '.py'
                else:
                    file_path = case_id + '.py'
                f.write(file_path + '\n')
        
        print("   Files saved to: test_results/files_numerical_errors.txt")
    
    # 其他Exit code 1
    if error_categories['Exit code 1 - Other']:
        print(f"\n4. Other Exit code 1: {len(error_categories['Exit code 1 - Other'])} cases")
        print("   Action: Manual investigation needed")
        
        with open('test_results/files_exit_code_1.txt', 'w', encoding='utf-8') as f:
            for item in error_categories['Exit code 1 - Other']:
                case_id = item['file']
                if case_id.startswith('tests-'):
                    file_path = 'tests/' + case_id[6:] + '.py'
                elif '-' in case_id:
                    parts = case_id.split('-', 1)
                    file_path = parts[0] + '/' + parts[1].replace('-', '/') + '.py'
                else:
                    file_path = case_id + '.py'
                f.write(file_path + '\n')
    
    print()
    print("=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    
    fixable = len(error_categories['UnicodeEncodeError']) + \
              len(error_categories['ModuleNotFoundError']) + \
              len(error_categories['Numerical Issues'])
    
    print(f"Total failed: {len(failed)}")
    print(f"Fixable (Unicode + Module + Numerical): {fixable} ({fixable/len(failed)*100:.1f}%)")
    print(f"Need investigation: {len(failed) - fixable} ({(len(failed)-fixable)/len(failed)*100:.1f}%)")
    print()
    print("Next action: Apply fixes to the fixable categories")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

