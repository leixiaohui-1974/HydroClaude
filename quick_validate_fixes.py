#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速验证修复效果 - 测试少量之前失败的案例

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time

def run_test(file_path):
    """运行单个测试"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            return True, "PASS", None
        else:
            # 提取错误信息
            error = result.stderr[:200] if result.stderr else result.stdout[:200]
            return False, "FAIL", error
            
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "Test exceeded 30 seconds"
    except Exception as e:
        return False, "ERROR", str(e)


def main():
    """快速验证修复"""
    
    print("=" * 70)
    print(" " * 15 + "QUICK VALIDATION OF FIXES")
    print("=" * 70)
    print()
    
    # 选择之前失败的测试案例进行验证
    # Unicode错误案例
    unicode_tests = [
        'tests/analyze_well_balanced_details.py',
        'tests/benchmark_riemann_solvers.py',
        'tests/dam_break_high_res_numba.py',
        'examples/case02_flood_risk_assessment.py',
        'examples/example_01_canal_flow/scripts/02_methods_comparison.py',
    ]
    
    # 导入错误案例
    import_tests = [
        'tests/benchmark_newton_vs_iterative.py',
        'tests/test_controllers.py',
        'examples/example_01_canal_flow/scripts/01_basic.py',
        'examples/advanced_examples/run_mpc_benchmark.py',
    ]
    
    all_tests = unicode_tests + import_tests
    
    print(f"Testing {len(all_tests)} cases:")
    print(f"  - {len(unicode_tests)} previously had Unicode errors")
    print(f"  - {len(import_tests)} previously had import errors")
    print()
    print("-" * 70)
    
    passed = 0
    failed = 0
    errors = {}
    
    for i, test_file in enumerate(all_tests, 1):
        if not os.path.exists(test_file):
            print(f"[{i}/{len(all_tests)}] SKIP: {test_file} (not found)")
            continue
        
        print(f"[{i}/{len(all_tests)}] Testing: {os.path.basename(test_file)}...", end=' ', flush=True)
        
        success, status, error = run_test(test_file)
        
        if success:
            print("[OK] PASS")
            passed += 1
        else:
            print(f"[X] {status}")
            failed += 1
            
            # 分类错误
            if error:
                if 'UnicodeEncodeError' in error:
                    errors.setdefault('Unicode', []).append(test_file)
                elif 'ModuleNotFoundError' in error or 'ImportError' in error:
                    errors.setdefault('Import', []).append(test_file)
                elif 'Timeout' in status:
                    errors.setdefault('Timeout', []).append(test_file)
                else:
                    errors.setdefault('Other', []).append(test_file)
    
    print()
    print("=" * 70)
    print("VALIDATION RESULTS:")
    print("=" * 70)
    print(f"Passed: {passed}/{len(all_tests)} ({passed/len(all_tests)*100:.0f}%)")
    print(f"Failed: {failed}/{len(all_tests)} ({failed/len(all_tests)*100:.0f}%)")
    print()
    
    if errors:
        print("-" * 70)
        print("ERROR BREAKDOWN:")
        print("-" * 70)
        for error_type, files in errors.items():
            print(f"{error_type}: {len(files)} cases")
    
    print()
    print("=" * 70)
    print("ASSESSMENT:")
    print("=" * 70)
    
    if passed / len(all_tests) > 0.7:
        print("Status: GOOD - Fixes are working well")
        print("Recommendation: Run full test (expect significant improvement)")
    elif passed / len(all_tests) > 0.5:
        print("Status: MODERATE - Some fixes working")
        print("Recommendation: Can run full test (expect moderate improvement)")
    elif passed / len(all_tests) > 0.3:
        print("Status: POOR - Limited effectiveness")
        print("Recommendation: Analyze remaining issues before full test")
    else:
        print("Status: CRITICAL - Fixes not working")
        print("Recommendation: Don't run full test, investigate issues")
    
    print()
    
    # 基于验证结果估算完整测试的预期
    if failed > 0:
        print("-" * 70)
        print("ESTIMATED FULL TEST RESULT:")
        print("-" * 70)
        
        # 第三轮基准
        round3_pass = 267
        round3_total = 541
        
        # 如果这些修复的测试通过了，估算能增加多少
        # 假设修复的82个文件中，按相同比例通过
        estimated_new_passes = int(82 * (passed / len(all_tests)))
        estimated_total_pass = round3_pass + estimated_new_passes
        estimated_rate = estimated_total_pass / round3_total * 100
        
        print(f"Current (Round 3): {round3_pass}/541 (49.4%)")
        print(f"Estimated new passes: +{estimated_new_passes}")
        print(f"Estimated total: {estimated_total_pass}/541 ({estimated_rate:.1f}%)")
        
        if estimated_rate > 55:
            print("\n→ Improvement expected, worth running full test")
        elif estimated_rate > 51:
            print("\n→ Modest improvement, consider running full test")
        else:
            print("\n→ Limited improvement, may not be worth 1.5 hours")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

