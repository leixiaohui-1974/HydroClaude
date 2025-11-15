#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证"其他错误"测试
Verify Other Errors

重新测试3个"其他错误"案例，确认真实状态

Author: HydroClaude Team
Date: 2025-11-15
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_single_file(filepath):
    """测试单个文件"""
    print(f"\n{'='*80}")
    print(f"测试: {filepath}")
    print('='*80)
    
    try:
        result = subprocess.run(
            [sys.executable, str(filepath)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(f"退出码: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ 状态: 成功")
            return True
        else:
            print("❌ 状态: 失败")
            # 显示最后20行输出
            lines = result.stdout.split('\n')
            print("\n最后输出:")
            for line in lines[-20:]:
                if line.strip():
                    print(f"  {line}")
            
            if result.stderr:
                print("\n错误信息:")
                error_lines = result.stderr.split('\n')
                for line in error_lines[-20:]:
                    if line.strip():
                        print(f"  {line}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️ 状态: 超时")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def main():
    print("\n" + "🔍"*40)
    print("其他错误测试验证".center(80))
    print("🔍"*40)
    
    test_files = [
        "tests/test_lake_at_rest_wb.py",
        "tests/diagnostic/test_anderson_performance.py",
        "tests/diagnostic/test_macdonald4_fine_grid.py",
    ]
    
    results = {}
    for filepath in test_files:
        full_path = project_root / filepath
        if full_path.exists():
            results[filepath] = test_single_file(full_path)
        else:
            print(f"\n❌ 文件不存在: {filepath}")
            results[filepath] = False
    
    print("\n" + "="*80)
    print("验证结果总结".center(80))
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for filepath, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status}: {filepath}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    print("\n分析:")
    print("-"*80)
    print("1. test_lake_at_rest_wb.py: 算法精度问题，部分子测试失败")
    print("2. test_anderson_performance.py: 有警告但可能运行成功")
    print("3. test_macdonald4_fine_grid.py: 有真正的运行时错误")
    
    return results


if __name__ == '__main__':
    main()
