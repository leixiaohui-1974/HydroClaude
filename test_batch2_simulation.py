#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch 2测试 - 仿真相关案例（下一批20个文件）

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time
import json

# Batch 2: 仿真相关案例（从examples/下选择）
batch2_files = [
    ('example_01_canal_flow/scripts/01_basic_v2.py', 30),
    ('example_01_canal_flow/scripts/02_dam_break_v2.py', 30),
    ('example_01_canal_flow/scripts/03_weir_v2.py', 30),
    ('example_01_canal_flow/scripts/04_boundary_conditions_v2.py', 30),
    ('example_01_canal_flow/scripts/05_sloped_channel_v2.py', 30),
    ('example_01_canal_flow/scripts/06_subcritical_supercritical_v2.py', 30),
    ('example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py', 30),
    ('example_01_canal_flow/scripts/08_channel_junction_v2.py', 30),
    ('example_01_canal_flow/scripts/09_multi_structure_v2.py', 30),
    ('example_01_canal_flow/scripts/10_steady_solver_comparison_v2.py', 30),
    ('example_01_canal_flow/scripts/11_two_gates_v2.py', 30),
    ('example_01_canal_flow/scripts/12_advanced_optimized_v2.py', 30),
    ('example_02_reservoir_operation/scripts/01_single_reservoir_basic.py', 30),
    ('example_02_reservoir_operation/scripts/02_flood_control.py', 30),
    ('example_02_reservoir_operation/scripts/03_multi_objective_operation.py', 60),
    ('example_03_network_simulation/scripts/01_series_network.py', 30),
    ('example_03_network_simulation/scripts/02_tree_network.py', 30),
    ('example_03_network_simulation/scripts/03_loop_network.py', 30),
    ('example_04_control_demo/scripts/01_pid_control_demo.py', 30),
    ('example_04_control_demo/scripts/02_mpc_control_demo.py', 60),
]

def test_file(file_path, timeout=60):
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
            return 'PASS', elapsed, None
        else:
            # 提取错误信息
            err = result.stderr if result.stderr else result.stdout
            lines = err.split('\n')
            error_msg = 'Unknown error'
            for line in lines:
                if 'Error' in line or 'Exception' in line:
                    error_msg = line.strip()[:80]
                    break
            return 'FAIL', elapsed, error_msg
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, f'Timeout (>{timeout}s)'
    except Exception as e:
        return 'ERROR', 0, str(e)[:80]

def main():
    """主函数"""
    
    print("="*70)
    print("BATCH 2 TEST - SIMULATION CASES (20 FILES)")
    print("="*70)
    print()
    
    results = {}
    total_time = 0
    errors = []
    
    for i, (rel_path, timeout) in enumerate(batch2_files, 1):
        file_path = os.path.join('examples', rel_path)
        basename = os.path.basename(file_path)
        
        if not os.path.exists(file_path):
            print(f"[{i:2d}/20] {basename:50s} [NOT_FOUND]")
            results[basename] = 'NOT_FOUND'
            continue
        
        print(f"[{i:2d}/20] {basename:50s}", end=" ", flush=True)
        status, elapsed, error = test_file(file_path, timeout=timeout)
        print(f"[{status:7s}] ({elapsed:.1f}s)")
        
        results[basename] = status
        total_time += elapsed
        
        if status == 'FAIL' and error:
            errors.append({'file': basename, 'error': error})
    
    print()
    print("="*70)
    
    passed = sum(1 for s in results.values() if s == 'PASS')
    failed = sum(1 for s in results.values() if s == 'FAIL')
    timeout_count = sum(1 for s in results.values() if s == 'TIMEOUT')
    not_found = sum(1 for s in results.values() if s == 'NOT_FOUND')
    
    total_tested = len(results) - not_found
    
    print(f"PASS:      {passed}/{total_tested}")
    print(f"FAIL:      {failed}/{total_tested}")
    print(f"TIMEOUT:   {timeout_count}/{total_tested}")
    print(f"NOT_FOUND: {not_found}/{len(results)}")
    print(f"\nTotal time: {total_time:.1f}s ({total_time/60:.1f}min)")
    
    if total_tested > 0:
        pass_rate = passed / total_tested * 100
        print(f"\nBATCH 2 PASS RATE: {passed}/{total_tested} = {pass_rate:.1f}%")
    
    print("="*70)
    
    # 保存结果
    with open('batch2_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'results': results,
            'errors': errors,
            'summary': {
                'passed': passed,
                'failed': failed,
                'timeout': timeout_count,
                'not_found': not_found,
                'total_tested': total_tested,
                'pass_rate': passed / total_tested * 100 if total_tested > 0 else 0
            }
        }, f, indent=2)
    
    print("\nResults saved to batch2_results.json")
    
    # 显示错误摘要
    if errors:
        print(f"\nERROR SUMMARY ({len(errors)} failures):")
        print("-"*70)
        for err in errors[:5]:  # 只显示前5个
            print(f"  {err['file']}")
            print(f"    {err['error']}")
    
    return passed, total_tested

if __name__ == '__main__':
    passed, total = main()

