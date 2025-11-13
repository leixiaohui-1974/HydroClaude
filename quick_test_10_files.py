#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试10个文件"""

import subprocess
import sys
import os
import time

files = [
    "examples/advanced_examples/run_first_order_mpc_benchmark.py",
    "examples/case_channel_renovation.py",
    "examples/case_flood_control.py",
    "examples/case_gate_operation.py",
    "examples/case_irrigation_scheduling.py",
    "examples/case_library/case_01_hydropower_plant.py",
    "examples/case_library/case_02_water_supply_network.py",
    "examples/case_library/case_03_irrigation_canal.py",
    "examples/example_01_canal_flow/run_all.py",
    "examples/example_01_canal_flow/scripts/01_basic_v2.py",
]

print("="*80)
print("快速测试10个文件（Windows中文环境）")
print("="*80)
print()

passed = 0
failed = 0

for i, file in enumerate(files, 1):
    basename = os.path.basename(file)
    print(f"[{i:2d}/10] {basename:50s}", end=" ", flush=True)
    
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, file],
            capture_output=True,
            timeout=30,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        if result.returncode == 0:
            print("[PASS]")
            passed += 1
        else:
            print("[FAIL]")
            failed += 1
            # 显示错误
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            for line in lines[-10:]:
                if line.strip() and ('Error' in line or 'Exception' in line):
                    print(f"  → {line.strip()[:100]}")
    except subprocess.TimeoutExpired:
        print("[TIMEOUT]")
        failed += 1
    except Exception as e:
        print(f"[ERROR: {str(e)[:30]}]")
        failed += 1

print()
print("="*80)
print(f"结果: {passed}/10 通过 ({passed/10*100:.0f}%)")
print(f"通过: {passed}, 失败: {failed}")
print("="*80)

