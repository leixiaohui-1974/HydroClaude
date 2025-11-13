#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能增量测试 - 只测试失败的案例

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
from pathlib import Path
import json

# 已知通过的文件（Batch 1中的3个）
KNOWN_PASS = {
    'examples/benchmark_performance.py',
    'examples/case_library/case_03_irrigation_canal.py',
    'examples/case_library/case_01_hydropower_plant.py',  # 刚修复的
}

# Batch 1中失败和超时的文件
BATCH1_FAILURES = [
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
    'examples/case_library/case_01_dam_break/dam_break_comparison.py',
    'examples/case_library/case_02_flood_routing/flood_routing_simulation.py',
    'examples/case_library/case_02_water_supply_network.py',
    'examples/case_library/run_all_cases.py',
]

def test_file(file_path, timeout=30):
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
            # 提取错误信息
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    return 'FAIL', line.strip()[:80]
            return 'FAIL', 'Unknown error'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', f'Timeout (>30s)'
    except Exception as e:
        return 'ERROR', str(e)[:80]

def main():
    """主函数"""
    
    print("="*70)
    print("SMART INCREMENTAL TEST - BATCH 1 FAILURES ONLY")
    print("="*70)
    print()
    print(f"Skipping {len(KNOWN_PASS)} known passing files")
    print(f"Testing {len(BATCH1_FAILURES)} failing files")
    print()
    
    passed = 0
    failed = 0
    timeout = 0
    
    results = []
    
    for i, file_path in enumerate(BATCH1_FAILURES, 1):
        basename = os.path.basename(file_path)
        
        if not os.path.exists(file_path):
            print(f"[{i:2d}/{len(BATCH1_FAILURES)}] {basename:50s} FILE_NOT_FOUND")
            continue
        
        status, detail = test_file(file_path)
        
        if status == 'PASS':
            print(f"[{i:2d}/{len(BATCH1_FAILURES)}] {basename:50s} [PASS]")
            passed += 1
        elif status == 'TIMEOUT':
            print(f"[{i:2d}/{len(BATCH1_FAILURES)}] {basename:50s} [TIMEOUT]")
            timeout += 1
        else:
            print(f"[{i:2d}/{len(BATCH1_FAILURES)}] {basename:50s} [FAIL]")
            if detail:
                print(f"     {detail}")
            failed += 1
        
        results.append({
            'file': file_path,
            'status': status,
            'detail': detail
        })
    
    print()
    print("="*70)
    print("RESULTS")
    print("="*70)
    print(f"PASS:    {passed:3d} / {len(BATCH1_FAILURES)} ({passed/len(BATCH1_FAILURES)*100:5.1f}%)")
    print(f"FAIL:    {failed:3d} / {len(BATCH1_FAILURES)} ({failed/len(BATCH1_FAILURES)*100:5.1f}%)")
    print(f"TIMEOUT: {timeout:3d} / {len(BATCH1_FAILURES)} ({timeout/len(BATCH1_FAILURES)*100:5.1f}%)")
    print()
    print(f"Total pass rate: {passed + len(KNOWN_PASS)}/{len(BATCH1_FAILURES) + len(KNOWN_PASS)} = {(passed + len(KNOWN_PASS))/(len(BATCH1_FAILURES) + len(KNOWN_PASS))*100:.1f}%")
    print("="*70)
    
    # 保存结果
    with open('batch1_retest_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'known_pass': list(KNOWN_PASS),
            'tested': results,
            'summary': {
                'pass': passed,
                'fail': failed,
                'timeout': timeout,
                'total': len(BATCH1_FAILURES)
            }
        }, f, indent=2, ensure_ascii=False)
    
    print("\nResults saved to batch1_retest_results.json")

if __name__ == '__main__':
    main()

