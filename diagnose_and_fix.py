#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断并修复 - 不废话，直接干

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

batch1 = [
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

print("DIAGNOSING BATCH 1...\n")

for i, file_path in enumerate(batch1, 1):
    print(f"[{i}/10] {os.path.basename(file_path)}")
    
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=20,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("  STATUS: PASS\n")
        else:
            # 提取关键错误
            error = result.stderr or result.stdout
            lines = error.split('\n')
            
            # 找关键错误行
            for line in lines:
                if 'Error' in line or 'Traceback' in line or 'File' in line:
                    print(f"  {line[:100]}")
            print()
            
    except subprocess.TimeoutExpired:
        print("  STATUS: TIMEOUT\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")

