#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分批增量测试 - 每批10个，快速反馈

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path

def find_all_test_files():
    """查找所有测试文件"""
    
    test_files = []
    
    # tests/目录
    tests_dir = Path('tests')
    if tests_dir.exists():
        test_files.extend([str(f) for f in tests_dir.glob('*.py')])
    
    # examples/目录
    examples_dir = Path('examples')
    if examples_dir.exists():
        for f in examples_dir.rglob('*.py'):
            if '__pycache__' not in str(f):
                test_files.append(str(f))
    
    # validation_cases/目录
    validation_dir = Path('validation_cases')
    if validation_dir.exists():
        for f in validation_dir.rglob('*.py'):
            if '__pycache__' not in str(f):
                test_files.append(str(f))
    
    return sorted(test_files)


def run_test(file_path):
    """运行单个测试"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            return 'PASS', None
        else:
            error = result.stderr[:150] if result.stderr else result.stdout[:150]
            return 'FAIL', error
            
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Exceeded 30 seconds'
    except Exception as e:
        return 'ERROR', str(e)


def run_batch(files, batch_num, total_batches):
    """运行一批测试"""
    
    print(f"\n{'='*70}")
    print(f"BATCH {batch_num}/{total_batches} - Testing {len(files)} files")
    print(f"{'='*70}")
    
    results = []
    passed = 0
    failed = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {file_path}...", end=' ', flush=True)
        
        status, error = run_test(file_path)
        
        if status == 'PASS':
            print('[OK]')
            passed += 1
        else:
            print(f'[{status}]')
            failed += 1
        
        results.append({
            'file': file_path,
            'status': status,
            'error': error
        })
    
    print(f"\nBatch {batch_num} results: {passed} passed, {failed} failed")
    print(f"Pass rate: {passed/len(files)*100:.1f}%")
    
    return results, passed, failed


def main():
    """分批测试主函数"""
    
    print("="*70)
    print(" "*15 + "INCREMENTAL BATCH TESTING")
    print("="*70)
    print()
    
    # 查找所有测试文件
    print("Finding all test files...")
    all_files = find_all_test_files()
    
    print(f"Found {len(all_files)} test files")
    print()
    
    # 分批
    batch_size = 10
    batches = [all_files[i:i+batch_size] for i in range(0, len(all_files), batch_size)]
    
    print(f"Split into {len(batches)} batches of {batch_size} files each")
    print()
    
    # 运行测试
    all_results = []
    total_passed = 0
    total_failed = 0
    
    start_time = time.time()
    
    for batch_num, batch in enumerate(batches, 1):
        batch_results, passed, failed = run_batch(batch, batch_num, len(batches))
        
        all_results.extend(batch_results)
        total_passed += passed
        total_failed += failed
        
        # 显示累计统计
        total_tested = total_passed + total_failed
        cumulative_rate = total_passed / total_tested * 100
        
        print(f"\n{'='*70}")
        print(f"CUMULATIVE STATS (After {batch_num}/{len(batches)} batches)")
        print(f"{'='*70}")
        print(f"Tested: {total_tested}/{len(all_files)} ({total_tested/len(all_files)*100:.1f}%)")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Pass rate: {cumulative_rate:.1f}%")
        
        elapsed = time.time() - start_time
        avg_time_per_batch = elapsed / batch_num
        remaining_batches = len(batches) - batch_num
        estimated_remaining = avg_time_per_batch * remaining_batches
        
        print(f"\nElapsed: {elapsed/60:.1f} minutes")
        print(f"Estimated remaining: {estimated_remaining/60:.1f} minutes")
        print(f"{'='*70}")
        
        # 每5批保存一次结果
        if batch_num % 5 == 0:
            with open(f'test_results/incremental_results_batch_{batch_num}.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'batches_completed': batch_num,
                    'total_batches': len(batches),
                    'total_tested': total_tested,
                    'total_passed': total_passed,
                    'total_failed': total_failed,
                    'pass_rate': cumulative_rate,
                    'results': all_results
                }, f, indent=2)
    
    # 最终总结
    total_time = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Total files: {len(all_files)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Pass rate: {total_passed/len(all_files)*100:.1f}%")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"{'='*70}")
    
    # 保存最终结果
    with open('test_results/incremental_results_final.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_files': len(all_files),
            'total_passed': total_passed,
            'total_failed': total_failed,
            'pass_rate': total_passed/len(all_files)*100,
            'total_time': total_time,
            'results': all_results
        }, f, indent=2)
    
    print("\nResults saved to: test_results/incremental_results_final.json")
    
    # 与第三轮对比
    print(f"\n{'='*70}")
    print("COMPARISON WITH ROUND 3:")
    print(f"{'='*70}")
    print(f"Round 3: 49.4% (267/541)")
    print(f"Round 5 (incremental): {total_passed/len(all_files)*100:.1f}% ({total_passed}/{len(all_files)})")
    
    if total_passed/len(all_files) > 0.494:
        improvement = total_passed/len(all_files)*100 - 49.4
        print(f"Improvement: +{improvement:.1f}%")
        print(f"New passes: +{total_passed - 267}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

