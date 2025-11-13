#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断超时案例 - 增加超时时间并查看进展

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import threading

timeout_files = [
    'examples/advanced_animation_generator.py',
    'examples/advanced_examples/complete_benchmark_suite.py',
    'examples/advanced_examples/integrated_smart_water_system.py',
    'examples/advanced_examples/multi_objective_reservoir_scheduling.py',
    'examples/advanced_examples/optimize_preissmann.py',
    'examples/case_library/case_02_flood_routing/flood_routing_simulation.py',
    'examples/case_library/run_all_cases.py',
]

def test_with_longer_timeout(file_path, timeout=30):
    """使用更长的超时时间测试"""
    try:
        print(f"  Testing with {timeout}s timeout...")
        
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
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    return 'FAIL', line.strip()[:80]
            return 'FAIL', 'Unknown error'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', f'Still timeout after {timeout}s'
    except Exception as e:
        return 'ERROR', str(e)[:80]

def main():
    """主函数"""
    
    print("="*70)
    print("DIAGNOSING 7 TIMEOUT CASES")
    print("="*70)
    print()
    
    results = {}
    
    for i, file_path in enumerate(timeout_files, 1):
        basename = os.path.basename(file_path)
        print(f"[{i}/7] {basename}")
        
        if not os.path.exists(file_path):
            print(f"  FILE NOT FOUND")
            print()
            continue
        
        # 先用30秒超时测试
        status, detail = test_with_longer_timeout(file_path, timeout=30)
        results[basename] = status
        
        print(f"  Status: {status}")
        if detail:
            print(f"  Detail: {detail}")
        print()
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(1 for s in results.values() if s == 'PASS')
    timeout = sum(1 for s in results.values() if s == 'TIMEOUT')
    print(f"PASS:    {passed}/7")
    print(f"TIMEOUT: {timeout}/7")
    print("="*70)
    
    if passed > 0:
        print("\nGood news! Some tests passed with longer timeout:")
        for name, status in results.items():
            if status == 'PASS':
                print(f"  - {name}")

if __name__ == '__main__':
    main()

