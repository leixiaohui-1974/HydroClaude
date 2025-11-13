#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
总结修复并重新测试第一批失败的文件

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

# 第一批失败的17个文件（使用正确路径）
batch1_files = [
    'examples/advanced_animation_generator.py',
    'examples/advanced_examples/compare_canal_solvers.py',
    'examples/advanced_examples/complete_benchmark_suite.py',
    'examples/advanced_examples/debug_saint_venant.py',
    'examples/advanced_examples/diagnose_canal_boundary.py',
    'examples/advanced_examples/integrated_smart_water_system.py',
    'examples/advanced_examples/multi_objective_reservoir_scheduling.py',
    'examples/advanced_examples/optimize_preissmann.py',
    'examples/case_gate_operation.py',
    'examples/case_irrigation_scheduling.py',
    'examples/benchmark_performance.py',
    'examples/case_library/case_01_dam_break/dam_break_comparison.py',
    'examples/case_library/case_01_hydropower_plant.py',
    'examples/case_library/case_02_flood_routing/flood_routing_simulation.py',
    'examples/case_library/case_02_water_supply_network.py',
    'examples/case_library/case_03_irrigation_canal.py',
    'examples/case_library/run_all_cases.py',
]

def test_file(file_path, timeout=10):
    """测试单个文件"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        if result.returncode == 0:
            return 'PASS', None
        else:
            # 简短的错误信息
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    return 'FAIL', line.strip()[:80]
            return 'FAIL', 'Unknown error'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', f'Timeout (>{timeout}s)'
    except Exception as e:
        return 'ERROR', str(e)[:80]

def main():
    """主函数"""
    
    print("="*70)
    print("FIXES APPLIED:")
    print("="*70)
    print("1. Fixed 4 files: solvers.canal -> physics.canal")
    print("2. Fixed 15 files: Added matplotlib.use('Agg') and disabled plt.show()")
    print("3. Fixed 4 files: Disabled input() calls")
    print("4. Fixed 28 files: Removed Unicode special characters")
    print("5. Installed cvxpy module")
    print()
    print("="*70)
    print("RETESTING BATCH 1 (17 files)")
    print("="*70)
    print()
    
    passed = 0
    failed = 0
    timeout = 0
    errors = 0
    
    results = []
    
    for i, file_path in enumerate(batch1_files, 1):
        basename = os.path.basename(file_path)
        
        if not os.path.exists(file_path):
            print(f"[{i}/17] {basename}: FILE NOT FOUND")
            errors += 1
            results.append((basename, 'NOT_FOUND', 'File does not exist'))
            continue
        
        status, detail = test_file(file_path)
        
        if status == 'PASS':
            print(f"[{i}/17] {basename}: PASS")
            passed += 1
        elif status == 'TIMEOUT':
            print(f"[{i}/17] {basename}: TIMEOUT")
            timeout += 1
        elif status == 'ERROR':
            print(f"[{i}/17] {basename}: ERROR - {detail}")
            errors += 1
        else:
            print(f"[{i}/17] {basename}: FAIL - {detail}")
            failed += 1
        
        results.append((basename, status, detail))
    
    print()
    print("="*70)
    print("BATCH 1 RESULTS")
    print("="*70)
    print(f"PASSED:  {passed}/17 ({passed/17*100:.1f}%)")
    print(f"FAILED:  {failed}/17")
    print(f"TIMEOUT: {timeout}/17")
    print(f"ERRORS:  {errors}/17")
    print("="*70)
    
    if failed + timeout + errors > 0:
        print()
        print("REMAINING ISSUES:")
        for basename, status, detail in results:
            if status != 'PASS':
                print(f"  - {basename}: {status}")
                if detail:
                    print(f"    {detail}")
    
    print()
    print("="*70)

if __name__ == '__main__':
    main()

