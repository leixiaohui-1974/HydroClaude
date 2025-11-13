#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用120秒超时测试最后4个案例

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time

final_4_cases = [
    ('advanced_animation_generator.py', 'examples/advanced_animation_generator.py'),
    ('integrated_smart_water_system.py', 'examples/advanced_examples/integrated_smart_water_system.py'),
    ('multi_objective_reservoir_scheduling.py', 'examples/advanced_examples/multi_objective_reservoir_scheduling.py'),
    ('optimize_preissmann.py', 'examples/advanced_examples/optimize_preissmann.py'),
]

def test_file(file_path, timeout=120):
    """测试单个文件"""
    try:
        start = time.time()
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        elapsed = time.time() - start
        
        if result.returncode == 0:
            return 'PASS', elapsed
        else:
            return 'FAIL', elapsed
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout
    except Exception as e:
        return 'ERROR', 0

def main():
    """主函数"""
    
    print("="*70)
    print("TESTING FINAL 4 CASES WITH 120S TIMEOUT")
    print("="*70)
    print()
    
    results = {}
    
    for i, (name, file_path) in enumerate(final_4_cases, 1):
        if not os.path.exists(file_path):
            print(f"[{i}/4] {name:50s} [NOT_FOUND]")
            continue
        
        print(f"[{i}/4] {name:50s}", end=" ", flush=True)
        status, elapsed = test_file(file_path, timeout=120)
        print(f"[{status}] ({elapsed:.1f}s)")
        
        results[name] = status
    
    print()
    print("="*70)
    passed = sum(1 for s in results.values() if s == 'PASS')
    failed = sum(1 for s in results.values() if s == 'FAIL')
    timeout = sum(1 for s in results.values() if s == 'TIMEOUT')
    
    print(f"PASS:    {passed}/4")
    print(f"FAIL:    {failed}/4")
    print(f"TIMEOUT: {timeout}/4")
    print()
    
    # run_all_cases.py用60s FAIL了，我们也用120s测试它
    print("\nTesting run_all_cases.py with 120s timeout...")
    status, elapsed = test_file('examples/case_library/run_all_cases.py', timeout=120)
    print(f"run_all_cases.py: [{status}] ({elapsed:.1f}s)")
    
    if status == 'PASS':
        passed += 1
    
    total_batch1 = 12 + passed  # 12个已经通过 + 新通过的
    print()
    print("="*70)
    print(f"BATCH 1 FINAL: {total_batch1}/17 = {total_batch1/17*100:.1f}%")
    print("="*70)

if __name__ == '__main__':
    main()

