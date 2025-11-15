#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速批量测试 - 分析失败原因
Quick Batch Test - Analyze Failures

对既有测试案例进行快速批量测试，收集失败原因

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def scan_test_files():
    """扫描测试文件"""
    scan_paths = [
        project_root / 'examples',
        project_root / 'tests',
        project_root / 'web' / 'backend' / 'examples'
    ]
    
    test_files = []
    for scan_path in scan_paths:
        if scan_path.exists():
            for py_file in scan_path.rglob('*.py'):
                # 排除__init__.py和明显不是测试的文件
                if py_file.name == '__init__.py':
                    continue
                if py_file.name.startswith('_'):
                    continue
                
                # 检查是否可执行
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    if 'if __name__' in content and ('main()' in content or 'run' in content):
                        test_files.append(py_file)
                except:
                    pass
    
    return test_files


def categorize_error(error_msg):
    """分类错误信息"""
    error_msg_lower = error_msg.lower()
    
    if 'modulenotfounderror' in error_msg_lower or 'no module named' in error_msg_lower:
        if 'pandas' in error_msg_lower:
            return 'missing_pandas'
        return 'missing_dependency'
    
    if 'syntaxerror' in error_msg_lower:
        return 'syntax_error'
    
    if 'timeout' in error_msg_lower or 'timed out' in error_msg_lower:
        return 'timeout'
    
    if 'filenotfounderror' in error_msg_lower or 'no such file' in error_msg_lower:
        return 'file_path_error'
    
    if 'typeerror' in error_msg_lower and '__init__' in error_msg_lower:
        return 'api_mismatch'
    
    if 'attributeerror' in error_msg_lower:
        return 'attribute_error'
    
    if 'importerror' in error_msg_lower:
        return 'import_error'
    
    if 'zerodivisionerror' in error_msg_lower:
        return 'zero_division'
    
    if 'convergence' in error_msg_lower or 'diverge' in error_msg_lower:
        return 'convergence_error'
    
    return 'other_error'


def run_batch_test(test_files, sample_size=50):
    """批量运行测试（采样）"""
    print(f"\n共扫描到 {len(test_files)} 个测试文件")
    print(f"采样测试 {min(sample_size, len(test_files))} 个文件...\n")
    
    # 采样
    import random
    random.seed(42)
    sampled_files = random.sample(test_files, min(sample_size, len(test_files)))
    
    results = {
        'total': len(sampled_files),
        'passed': 0,
        'failed': 0,
        'failures': [],
        'error_categories': defaultdict(int)
    }
    
    for i, test_file in enumerate(sampled_files, 1):
        print(f"\r[{i}/{len(sampled_files)}] 测试中...", end='', flush=True)
        
        try:
            result = subprocess.run(
                ['python3', str(test_file)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                results['passed'] += 1
            else:
                results['failed'] += 1
                
                # 分析错误
                error_msg = result.stderr + result.stdout
                error_category = categorize_error(error_msg)
                results['error_categories'][error_category] += 1
                
                # 保存详细信息
                results['failures'].append({
                    'file': str(test_file.relative_to(project_root)),
                    'category': error_category,
                    'error_snippet': error_msg[:500]
                })
                
        except subprocess.TimeoutExpired:
            results['failed'] += 1
            results['error_categories']['timeout'] += 1
            results['failures'].append({
                'file': str(test_file.relative_to(project_root)),
                'category': 'timeout',
                'error_snippet': '测试超时（30秒）'
            })
        except Exception as e:
            results['failed'] += 1
            results['error_categories']['other_error'] += 1
            results['failures'].append({
                'file': str(test_file.relative_to(project_root)),
                'category': 'other_error',
                'error_snippet': str(e)
            })
    
    print()  # 换行
    return results


def print_summary(results):
    """打印总结"""
    print("\n" + "="*80)
    print("测试结果总结".center(80))
    print("="*80)
    
    pass_rate = results['passed'] / results['total'] * 100 if results['total'] > 0 else 0
    
    print(f"\n总计: {results['passed']}/{results['total']} 通过 ({pass_rate:.1f}%)")
    print(f"  ✅ 通过: {results['passed']}")
    print(f"  ❌ 失败: {results['failed']}")
    
    print("\n失败原因分类:")
    print("-" * 80)
    
    # 按数量排序
    sorted_categories = sorted(
        results['error_categories'].items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    category_names = {
        'missing_pandas': '❌ 缺少pandas模块',
        'missing_dependency': '❌ 缺少其他依赖',
        'syntax_error': '❌ 语法错误',
        'timeout': '⏱️ 执行超时',
        'file_path_error': '📁 文件路径错误',
        'api_mismatch': '🔧 API不匹配',
        'attribute_error': '🔧 属性错误',
        'import_error': '📦 导入错误',
        'zero_division': '⚠️ 除零错误',
        'convergence_error': '⚠️ 收敛错误',
        'other_error': '❓ 其他错误'
    }
    
    for category, count in sorted_categories:
        name = category_names.get(category, category)
        percentage = count / results['failed'] * 100 if results['failed'] > 0 else 0
        print(f"  {name}: {count} ({percentage:.1f}%)")
    
    print("\n" + "="*80)
    print("修复建议".center(80))
    print("="*80)
    
    for category, count in sorted_categories[:5]:  # 只显示前5个
        print(f"\n{category_names.get(category, category)} ({count}个)")
        
        if category == 'missing_pandas':
            print("  ✅ 已修复：pandas已安装")
        elif category == 'missing_dependency':
            print("  🔧 建议：pip3 install <缺失的包>")
        elif category == 'syntax_error':
            print("  🔧 建议：检查Python 2→3语法问题")
        elif category == 'timeout':
            print("  🔧 建议：优化算法或增加超时时间")
        elif category == 'file_path_error':
            print("  🔧 建议：创建输出目录或修正路径")
        elif category == 'api_mismatch':
            print("  🔧 建议：更新API调用方式")
    
    return results


def save_results(results):
    """保存结果到JSON"""
    output_file = project_root / 'web' / 'batch_test_quick_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: {output_file}")


def main():
    print("\n" + "🔍"*40)
    print("快速批量测试 - 分析既有案例失败原因".center(80))
    print("🔍"*40)
    
    # 1. 扫描
    test_files = scan_test_files()
    
    # 2. 批量测试（采样50个）
    results = run_batch_test(test_files, sample_size=50)
    
    # 3. 打印总结
    print_summary(results)
    
    # 4. 保存结果
    save_results(results)
    
    print("\n" + "✅"*40)
    print("分析完成！".center(80))
    print("✅"*40)


if __name__ == '__main__':
    main()
