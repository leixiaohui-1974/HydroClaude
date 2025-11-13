#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量测试模拟案例（每批20个）

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import json

def is_control_related(file_path):
    """判断是否是控制相关"""
    control_keywords = ['mpc', 'controller', 'control', 'cvxpy', 'pid', 'agc']
    basename = os.path.basename(file_path).lower()
    # 排除包含控制关键词的文件
    return any(kw in basename for kw in control_keywords)

def find_all_test_files():
    """找到所有Python测试文件"""
    files = []
    search_dirs = ['examples', 'tests']
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, filenames in os.walk(search_dir):
            for f in filenames:
                if f.endswith('.py') and '__pycache__' not in root and '__init__' not in f:
                    full_path = os.path.join(root, f)
                    # 验证文件确实存在
                    if os.path.isfile(full_path):
                        files.append(full_path)
    return files

def run_test(file_path):
    """运行测试"""
    if not os.path.exists(file_path):
        return 'NOT_FOUND', f'File not found: {file_path}'
    
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=15,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        if result.returncode == 0:
            return 'PASS', None
        else:
            error = (result.stderr or result.stdout)[:300]
            return 'FAIL', error
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Exceeded 15s'
    except Exception as e:
        return 'ERROR', str(e)

def main():
    """主函数"""
    
    # 找到所有测试文件
    all_files = find_all_test_files()
    
    # 分类
    simulation_files = [f for f in all_files if not is_control_related(f)]
    control_files = [f for f in all_files if is_control_related(f)]
    
    print("="*70)
    print("SIMULATION TEST - BATCH TESTING")
    print("="*70)
    print(f"Total files: {len(all_files)}")
    print(f"Simulation files: {len(simulation_files)}")
    print(f"Control files (skipped): {len(control_files)}")
    print()
    
    # 分批测试（每批20个）
    batch_size = 20
    total_batches = (len(simulation_files) + batch_size - 1) // batch_size
    
    print(f"Will test {len(simulation_files)} simulation files in {total_batches} batches")
    print(f"(Batch size: {batch_size})")
    print()
    
    # 只测试第一批
    batch_num = 1
    start_idx = (batch_num - 1) * batch_size
    end_idx = min(start_idx + batch_size, len(simulation_files))
    batch = simulation_files[start_idx:end_idx]
    
    print(f"BATCH {batch_num}/{total_batches} ({len(batch)} files)")
    print("="*70)
    print()
    
    results = []
    passed = 0
    failed = 0
    timeout = 0
    
    for i, f in enumerate(batch, 1):
        basename = os.path.basename(f)
        print(f"[{i}/{len(batch)}] {basename}...", end=' ', flush=True)
        
        status, error = run_test(f)
        results.append({
            'file': f,
            'basename': basename,
            'status': status,
            'error': error
        })
        
        if status == 'PASS':
            print("[OK]")
            passed += 1
        elif status == 'TIMEOUT':
            print("[TIMEOUT]")
            timeout += 1
            failed += 1
        else:
            print(f"[{status}]")
            failed += 1
    
    # 统计
    pass_rate = passed / len(batch) * 100
    
    print()
    print("="*70)
    print(f"RESULTS - BATCH {batch_num}")
    print("="*70)
    print(f"Passed: {passed}/{len(batch)} ({pass_rate:.1f}%)")
    print(f"Failed: {failed}/{len(batch)}")
    print(f"  - Timeout: {timeout}")
    print(f"  - Error: {failed - timeout}")
    print()
    
    # 显示失败的文件
    if failed > 0:
        print("FAILED FILES:")
        print("-"*70)
        for r in results:
            if r['status'] != 'PASS':
                print(f"  [{r['status']}] {r['basename']}")
                if r['error'] and r['status'] != 'TIMEOUT':
                    # 提取关键错误行
                    error_lines = r['error'].split('\n')
                    for line in error_lines:
                        if 'Error' in line and 'Traceback' not in line:
                            print(f"         {line.strip()}")
                            break
        print()
    
    # 保存结果
    output_file = f'test_results/simulation_batch{batch_num}_results.json'
    os.makedirs('test_results', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'batch': batch_num,
            'total_batches': total_batches,
            'passed': passed,
            'failed': failed,
            'timeout': timeout,
            'pass_rate': pass_rate,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")
    print("="*70)
    
    return passed, len(batch)

if __name__ == '__main__':
    main()

