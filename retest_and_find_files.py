#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重测修复的文件并找到缺失文件的正确路径

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
from pathlib import Path

# 刚修复的文件
fixed_files = [
    'examples/advanced_examples/compare_canal_solvers.py',
    'examples/advanced_examples/debug_saint_venant.py',
    'examples/advanced_examples/diagnose_canal_boundary.py',
    'examples/advanced_examples/optimize_preissmann.py',
]

# 缺失的文件名
missing_files = [
    'advanced_animation_generator.py',
    'case_gate_operation.py',
    'case_irrigation_scheduling.py',
    'benchmark_performance.py',
    'dam_break_comparison.py',
    'case_01_hydropower_plant.py',
    'flood_routing_simulation.py',
    'case_02_water_supply_network.py',
    'case_03_irrigation_canal.py',
    'run_all_cases.py',
]

def test_file(file_path):
    """测试单个文件"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def find_file(filename, root_dir='examples'):
    """在项目中查找文件"""
    matches = []
    for path in Path(root_dir).rglob(filename):
        if path.is_file():
            matches.append(str(path))
    return matches

def main():
    """主函数"""
    
    print("="*70)
    print("PART 1: RETEST FIXED FILES")
    print("="*70)
    print()
    
    passed = 0
    for file_path in fixed_files:
        basename = os.path.basename(file_path)
        result = test_file(file_path)
        status = "PASS" if result else "FAIL"
        print(f"{basename}: {status}")
        if result:
            passed += 1
    
    print(f"\nFixed files: {passed}/{len(fixed_files)} passed")
    
    print()
    print("="*70)
    print("PART 2: FIND MISSING FILES")
    print("="*70)
    print()
    
    found_count = 0
    found_paths = []
    
    for filename in missing_files:
        print(f"Searching for: {filename}")
        matches = find_file(filename)
        
        if matches:
            found_count += 1
            for match in matches:
                print(f"  -> Found: {match}")
                found_paths.append(match)
        else:
            print(f"  -> NOT FOUND")
        print()
    
    print("="*70)
    print(f"Found {found_count}/{len(missing_files)} missing files")
    print("="*70)
    
    # 保存找到的路径
    if found_paths:
        with open('found_file_paths.txt', 'w', encoding='utf-8') as f:
            for path in found_paths:
                f.write(path + '\n')
        print(f"\nSaved {len(found_paths)} paths to found_file_paths.txt")

if __name__ == '__main__':
    main()

