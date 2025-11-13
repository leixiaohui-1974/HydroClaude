#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断失败的模拟测试

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys

failed_files = [
    'examples/advanced_examples/advanced_animation_generator.py',
    'examples/advanced_examples/benchmark_examples.py',
    'examples/advanced_examples/calibration_example.py',
    'examples/advanced_examples/case_gate_operation.py',
    'examples/advanced_examples/case_irrigation_scheduling.py',
    'examples/climate_change/climate_change_assessment.py',
]

print("="*70)
print("DIAGNOSING FAILED SIMULATION TESTS")
print("="*70)
print()

for i, f in enumerate(failed_files, 1):
    print(f"[{i}/{len(failed_files)}] {f}")
    
    try:
        result = subprocess.run(
            [sys.executable, f],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("  STATUS: PASS")
        else:
            # 提取关键错误
            stderr = result.stderr or result.stdout
            lines = stderr.split('\n')
            
            # 找ModuleNotFoundError
            for line in lines:
                if 'ModuleNotFoundError' in line:
                    print(f"  ERROR: {line.strip()}")
                    break
            # 找ImportError
            for line in lines:
                if 'ImportError' in line:
                    print(f"  ERROR: {line.strip()}")
                    break
            # 找AttributeError
            for line in lines:
                if 'AttributeError' in line:
                    print(f"  ERROR: {line.strip()}")
                    break
            # 找其他错误
            for line in lines:
                if 'Error' in line and 'Traceback' not in line:
                    print(f"  ERROR: {line.strip()}")
                    break
    
    except subprocess.TimeoutExpired:
        print("  STATUS: TIMEOUT (>10s)")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print()

print("="*70)

