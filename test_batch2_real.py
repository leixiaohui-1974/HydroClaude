#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch 2测试 - 基于实际存在的example文件

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time
import json

# Batch 2: 实际存在的example文件
batch2_files = [
    # example_01_canal_flow - v2版本（已知使用HydrostaticCanalSolver）
    ('examples/example_01_canal_flow/scripts/01_basic_v2.py', 30),
    ('examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py', 120),  # 增加超时
    ('examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py', 30),
    ('examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py', 30),
    
    # example_02_pump_system
    ('examples/example_02_pump_system/example_02_pump_system_enhanced.py', 30),
    
    # example_03_turbine_demo
    ('examples/example_03_turbine_demo/example_03_turbine_with_anim.py', 30),
    
    # example_05_transient_analysis
    ('examples/example_05_transient_analysis/example_05_load_rejection.py', 30),
    
    # example_08_preissmann_vs_fvm
    ('examples/example_08_preissmann_vs_fvm/example_08_preissmann_demo.py', 30),
    
    # example_09_pipe_rk4
    ('examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py', 120),  # 增加超时
    
    # example_16_weirs
    ('examples/example_16_weirs_application/weirs_irrigation_system.py', 30),
    
    # example_22_water_hammer
    ('examples/example_22_water_hammer/demo_water_hammer.py', 30),
    
    # example_23_control_comparison
    ('examples/example_23_control_comparison/demo_control_comparison.py', 60),
    
    # example_gate_pump_cascade
    ('examples/example_gate_pump_cascade/run_scenario_01.py', 120),  # 增加超时
    ('examples/example_gate_pump_cascade/run_scenario_02.py', 120),  # 增加超时
    ('examples/example_gate_pump_cascade/run_scenario_03.py', 120),  # 增加超时
    
    # example_unsteady
    ('examples/example_unsteady/run_time_varying_bc.py', 30),
    
    # complex network examples
    ('examples/example_03_complex_network/code/example_03_complex_network.py', 30),
    ('examples/example_10_series_network/code/example_10_series_network.py', 30),
    ('examples/example_11_tree_network/code/example_11_tree_network.py', 30),
    ('examples/example_12_loop_network/code/example_12_loop_network.py', 30),
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
                    error_msg = line.strip()[:100]
                    break
            return 'FAIL', elapsed, error_msg
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, f'Timeout (>{timeout}s)'
    except Exception as e:
        return 'ERROR', 0, str(e)[:80]

def main():
    """主函数"""
    
    print("="*70)
    print(f"BATCH 2 TEST - REAL EXAMPLE FILES ({len(batch2_files)} files)")
    print("="*70)
    print()
    
    results = {}
    total_time = 0
    errors = []
    
    for i, (file_path, timeout) in enumerate(batch2_files, 1):
        basename = os.path.basename(file_path)
        
        if not os.path.exists(file_path):
            print(f"[{i:2d}/{len(batch2_files)}] {basename:50s} [NOT_FOUND]")
            results[basename] = 'NOT_FOUND'
            continue
        
        print(f"[{i:2d}/{len(batch2_files)}] {basename:50s}", end=" ", flush=True)
        status, elapsed, error = test_file(file_path, timeout=timeout)
        print(f"[{status:7s}] ({elapsed:.1f}s)")
        
        results[basename] = status
        total_time += elapsed
        
        if status in ['FAIL', 'TIMEOUT'] and error:
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
    with open('batch2_real_results.json', 'w', encoding='utf-8') as f:
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
    
    print("\nResults saved to batch2_real_results.json")
    
    # 显示错误摘要
    if errors:
        print(f"\nERROR SUMMARY ({len(errors)} failures):")
        print("-"*70)
        for err in errors[:10]:  # 显示前10个
            print(f"  {err['file']}")
            print(f"    {err['error']}")
    
    return passed, total_tested

if __name__ == '__main__':
    passed, total = main()

