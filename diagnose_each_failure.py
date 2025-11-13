#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
逐个诊断失败文件的真实错误

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

failed_files = [
    'examples/advanced_examples/advanced_animation_generator.py',
    'examples/advanced_examples/compare_canal_solvers.py',
    'examples/advanced_examples/complete_benchmark_suite.py',
    'examples/advanced_examples/debug_saint_venant.py',
    'examples/advanced_examples/diagnose_canal_boundary.py',
    'examples/advanced_examples/integrated_smart_water_system.py',
    'examples/advanced_examples/multi_objective_reservoir_scheduling.py',
    'examples/advanced_examples/optimize_preissmann.py',
    'examples/advanced_examples/case_gate_operation.py',
    'examples/advanced_examples/case_irrigation_scheduling.py',
    'examples/real_world_cases/benchmark_performance.py',
    'examples/dam_break/dam_break_comparison.py',
    'examples/pressurized_flow/case_01_hydropower_plant.py',
    'examples/structures/flood_routing_simulation.py',
    'examples/pressurized_flow/case_02_water_supply_network.py',
    'examples/pressurized_flow/case_03_irrigation_canal.py',
    'examples/pressurized_flow/run_all_cases.py',
]

def diagnose_file(file_path):
    """详细诊断单个文件"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        output = result.stderr if result.stderr else result.stdout
        
        # 分析错误类型
        if result.returncode == 0:
            return 'PASS', None
        
        error_type = 'UNKNOWN'
        error_detail = ''
        
        # 检查各种错误
        if 'ModuleNotFoundError' in output:
            error_type = 'MODULE_NOT_FOUND'
            for line in output.split('\n'):
                if 'ModuleNotFoundError' in line:
                    error_detail = line.strip()
                    break
        elif 'ImportError' in output:
            error_type = 'IMPORT_ERROR'
            for line in output.split('\n'):
                if 'ImportError' in line:
                    error_detail = line.strip()
                    break
        elif 'AttributeError' in output:
            error_type = 'ATTRIBUTE_ERROR'
            for line in output.split('\n'):
                if 'AttributeError' in line:
                    error_detail = line.strip()
                    break
        elif 'FileNotFoundError' in output:
            error_type = 'FILE_NOT_FOUND'
            for line in output.split('\n'):
                if 'FileNotFoundError' in line:
                    error_detail = line.strip()
                    break
        elif 'TypeError' in output:
            error_type = 'TYPE_ERROR'
            for line in output.split('\n'):
                if 'TypeError' in line:
                    error_detail = line.strip()
                    break
        elif 'ValueError' in output:
            error_type = 'VALUE_ERROR'
            for line in output.split('\n'):
                if 'ValueError' in line:
                    error_detail = line.strip()
                    break
        elif 'NameError' in output:
            error_type = 'NAME_ERROR'
            for line in output.split('\n'):
                if 'NameError' in line:
                    error_detail = line.strip()
                    break
        elif 'KeyError' in output:
            error_type = 'KEY_ERROR'
            for line in output.split('\n'):
                if 'KeyError' in line:
                    error_detail = line.strip()
                    break
        elif 'IndexError' in output:
            error_type = 'INDEX_ERROR'
            for line in output.split('\n'):
                if 'IndexError' in line:
                    error_detail = line.strip()
                    break
        elif 'ZeroDivisionError' in output:
            error_type = 'ZERO_DIVISION'
            error_detail = 'Division by zero'
        elif 'AssertionError' in output:
            error_type = 'ASSERTION_ERROR'
            for line in output.split('\n'):
                if 'AssertionError' in line:
                    error_detail = line.strip()
                    break
        else:
            # 尝试找到最后一个错误行
            lines = output.split('\n')
            for line in reversed(lines):
                if line.strip() and not line.startswith(' '):
                    error_detail = line.strip()[:100]
                    break
        
        return error_type, error_detail
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Real timeout (>10s)'
    except Exception as e:
        return 'EXCEPTION', str(e)

def main():
    """主函数"""
    
    print("="*70)
    print("DETAILED FAILURE DIAGNOSIS")
    print("="*70)
    print()
    
    results = {}
    
    for i, file_path in enumerate(failed_files, 1):
        basename = os.path.basename(file_path)
        print(f"[{i}/{len(failed_files)}] {basename}")
        
        if not os.path.exists(file_path):
            print(f"  ERROR: File not found")
            results[basename] = ('FILE_NOT_FOUND', 'File does not exist')
            print()
            continue
        
        error_type, error_detail = diagnose_file(file_path)
        results[basename] = (error_type, error_detail)
        
        print(f"  TYPE: {error_type}")
        if error_detail:
            print(f"  DETAIL: {error_detail[:100]}")
        print()
    
    # 按错误类型分组统计
    print("="*70)
    print("ERROR SUMMARY")
    print("="*70)
    
    error_groups = {}
    for filename, (error_type, _) in results.items():
        if error_type not in error_groups:
            error_groups[error_type] = []
        error_groups[error_type].append(filename)
    
    for error_type, files in sorted(error_groups.items()):
        print(f"\n{error_type} ({len(files)}):")
        for f in files:
            print(f"  - {f}")
    
    print()
    print("="*70)

if __name__ == '__main__':
    main()

