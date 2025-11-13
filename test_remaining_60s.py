#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用60秒超时测试剩余5个案例

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

remaining_timeouts = [
    'examples/advanced_animation_generator.py',
    'examples/advanced_examples/integrated_smart_water_system.py',
    'examples/advanced_examples/multi_objective_reservoir_scheduling.py',
    'examples/advanced_examples/optimize_preissmann.py',
    'examples/case_library/run_all_cases.py',
]

def test_file(file_path, timeout=60):
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
            return 'PASS'
        else:
            return 'FAIL'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except Exception:
        return 'ERROR'

def main():
    """主函数"""
    
    print("="*70)
    print("TESTING REMAINING 5 WITH 60S TIMEOUT")
    print("="*70)
    print()
    
    results = {}
    
    for i, file_path in enumerate(remaining_timeouts, 1):
        basename = os.path.basename(file_path)
        
        if not os.path.exists(file_path):
            print(f"[{i}/5] {basename:50s} [NOT_FOUND]")
            continue
        
        print(f"[{i}/5] {basename:50s}", end=" ", flush=True)
        status = test_file(file_path, timeout=60)
        print(f"[{status}]")
        
        results[basename] = status
    
    print()
    print("="*70)
    passed = sum(1 for s in results.values() if s == 'PASS')
    print(f"PASS:    {passed}/5")
    print(f"TIMEOUT: {sum(1 for s in results.values() if s == 'TIMEOUT')}/5")
    print()
    print(f"New total: {12 + passed}/17 = {(12 + passed)/17*100:.1f}%")
    print("="*70)

if __name__ == '__main__':
    main()

