#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析具体失败案例
Analyze Specific Failures

详细分析失败测试的具体原因

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def analyze_file_path_errors():
    """分析文件路径错误"""
    print("\n" + "="*80)
    print("文件路径错误详细分析".center(80))
    print("="*80)
    
    result_file = project_root / 'web' / 'batch_test_quick_results.json'
    if not result_file.exists():
        print("  ❌ 结果文件不存在")
        return []
    
    with open(result_file) as f:
        data = json.load(f)
    
    path_errors = [f for f in data['failures'] if f['category'] == 'file_path_error']
    
    print(f"\n发现 {len(path_errors)} 个文件路径错误")
    print("-"*80)
    
    missing_dirs = set()
    for i, failure in enumerate(path_errors, 1):
        print(f"\n【错误 {i}】")
        print(f"文件: {failure['file']}")
        
        # 提取缺失的路径
        error = failure['error_snippet']
        if 'No such file or directory' in error:
            lines = error.split('\n')
            for line in lines:
                if 'No such file or directory' in line:
                    # 尝试提取路径
                    if "'" in line:
                        path = line.split("'")[1]
                        missing_dirs.add(str(Path(path).parent))
                    print(f"  缺失路径: {line.strip()}")
                    break
    
    if missing_dirs:
        print("\n建议创建的目录:")
        print("-"*80)
        for d in sorted(missing_dirs):
            print(f"  mkdir -p {d}")
    
    return list(missing_dirs)


def analyze_other_errors():
    """分析其他运行时错误"""
    print("\n" + "="*80)
    print("其他错误详细分析".center(80))
    print("="*80)
    
    result_file = project_root / 'web' / 'batch_test_quick_results.json'
    if not result_file.exists():
        print("  ❌ 结果文件不存在")
        return {}
    
    with open(result_file) as f:
        data = json.load(f)
    
    other_errors = [f for f in data['failures'] if f['category'] == 'other_error']
    
    print(f"\n发现 {len(other_errors)} 个其他错误")
    print("-"*80)
    
    error_patterns = {}
    
    for i, failure in enumerate(other_errors, 1):
        print(f"\n【错误 {i}】")
        print(f"文件: {failure['file']}")
        
        # 提取关键错误信息
        error = failure['error_snippet']
        lines = error.split('\n')
        
        # 找最后的错误行
        for line in reversed(lines):
            line = line.strip()
            if 'Error:' in line or 'Exception:' in line:
                error_type = line.split(':')[0].strip()
                error_msg = ':'.join(line.split(':')[1:]).strip()
                print(f"  类型: {error_type}")
                print(f"  信息: {error_msg[:100]}")
                
                # 统计错误类型
                if error_type not in error_patterns:
                    error_patterns[error_type] = []
                error_patterns[error_type].append(failure['file'])
                break
        else:
            # 如果没找到标准错误格式，找包含Error的行
            for line in reversed(lines):
                if 'Error' in line or 'error' in line.lower():
                    print(f"  错误: {line.strip()[:150]}")
                    break
    
    print("\n错误类型统计:")
    print("-"*80)
    for error_type, files in error_patterns.items():
        print(f"  {error_type}: {len(files)}个")
    
    return error_patterns


def analyze_timeout_errors():
    """分析超时错误"""
    print("\n" + "="*80)
    print("超时错误分析".center(80))
    print("="*80)
    
    result_file = project_root / 'web' / 'batch_test_quick_results.json'
    if not result_file.exists():
        print("  ❌ 结果文件不存在")
        return []
    
    with open(result_file) as f:
        data = json.load(f)
    
    timeout_errors = [f for f in data['failures'] if f['category'] == 'timeout']
    
    print(f"\n发现 {len(timeout_errors)} 个超时测试")
    print("-"*80)
    
    for i, failure in enumerate(timeout_errors, 1):
        print(f"  {i}. {failure['file']}")
    
    print("\n建议:")
    print("-"*80)
    print("  • 超时测试通常是算法收敛慢或计算量大")
    print("  • 短期内可以跳过，专注于其他问题")
    print("  • 长期需要算法优化")
    
    return [f['file'] for f in timeout_errors]


def generate_fix_plan():
    """生成修复计划"""
    print("\n" + "="*80)
    print("修复计划".center(80))
    print("="*80)
    
    print("\n优先级1: 文件路径错误 (3个)")
    print("-"*80)
    print("  预期效果: +3个通过")
    print("  当前通过率: 62.0%")
    print("  目标通过率: 68.0%")
    print("  操作: 创建缺失目录")
    
    print("\n优先级2: 其他错误 (7个)")
    print("-"*80)
    print("  预期效果: 至少+2个通过")
    print("  目标通过率: 70.0%+")
    print("  操作: 逐个调试修复")
    
    print("\n优先级3: 超时错误 (5个)")
    print("-"*80)
    print("  预期效果: 长期优化")
    print("  建议: 暂时跳过")
    print("  操作: 算法优化（长期工作）")


def main():
    print("\n" + "🔍"*40)
    print("失败案例详细分析".center(80))
    print("🔍"*40)
    
    missing_dirs = analyze_file_path_errors()
    error_patterns = analyze_other_errors()
    timeout_files = analyze_timeout_errors()
    generate_fix_plan()
    
    print("\n" + "="*80)
    print("分析完成！".center(80))
    print("="*80)
    
    print("\n下一步:")
    print("-"*80)
    print("  1. 创建缺失目录")
    print("  2. 重新运行批量测试")
    print("  3. 验证通过率提升")
    print("  4. 针对性修复其他错误")
    
    return {
        'missing_dirs': missing_dirs,
        'error_patterns': error_patterns,
        'timeout_files': timeout_files
    }


if __name__ == '__main__':
    main()
