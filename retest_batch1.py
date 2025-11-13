#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重新测试第一批

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

batch1_files = [
    "examples/advanced_animation_generator.py",
    "examples/advanced_examples/adaptive_first_order_mpc_test.py",
    "examples/advanced_examples/benchmark_controllers.py",
    "examples/advanced_examples/compare_canal_solvers.py",
    "examples/advanced_examples/complete_benchmark_suite.py",
    "examples/advanced_examples/comprehensive_solver_audit.py",
    "examples/advanced_examples/constrained_mpc_canal_demo.py",
    "examples/advanced_examples/debug_mpc_observer.py",
    "examples/advanced_examples/debug_saint_venant.py",
    "examples/advanced_examples/diagnose_canal_boundary.py",
]

print("="*70)
print("RETEST BATCH 1 (After fixes)")
print("="*70)
print()

passed = 0
failed = 0

for i, file_path in enumerate(batch1_files, 1):
    print(f"[{i}/10] {os.path.basename(file_path)}...", end=' ', flush=True)
    
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=20,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print('[OK]')
            passed += 1
        else:
            print('[FAIL]')
            failed += 1
    except subprocess.TimeoutExpired:
        print('[TIMEOUT]')
        failed += 1
    except Exception as e:
        print(f'[ERROR: {e}]')
        failed += 1

print()
print("="*70)
print(f"RESULTS: {passed}/10 passed, {failed}/10 failed")
print(f"Pass rate: {passed/10*100:.0f}%")
print()
print("BEFORE fixes: 1/10 passed (10%)")
print(f"AFTER fixes: {passed}/10 passed ({passed/10*100:.0f}%)")
if passed > 1:
    print(f"Improvement: +{passed-1} tests")
print("="*70)

