#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取真实的测试统计数据

Author: HydroClaude
Date: 2025-11-13
"""

import json
import os
from collections import Counter

def main():
    """获取真实统计"""
    
    print("=" * 70)
    print(" " * 20 + "REAL TEST STATISTICS")
    print("=" * 70)
    print()
    
    # 读取JSON结果
    results_file = 'test_results/batch_test_results.json'
    
    if not os.path.exists(results_file):
        print(f"[ERROR] {results_file} not found!")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查数据类型
    print(f"Data type: {type(data)}")
    
    if isinstance(data, list):
        print(f"Total entries: {len(data)}")
        print()
        
        # 检查第一个条目
        if len(data) > 0:
            print("First entry structure:")
            first = data[0]
            print(f"  Type: {type(first)}")
            if isinstance(first, dict):
                print("  Keys:", list(first.keys()))
                for key in first.keys():
                    print(f"    {key}: {first[key]}")
            else:
                print(f"  Value: {first}")
        print()
        
        # 统计状态
        if len(data) > 0 and isinstance(data[0], dict):
            statuses = [item.get('status', 'unknown') for item in data]
            status_counter = Counter(statuses)
            
            print("-" * 70)
            print("STATUS DISTRIBUTION:")
            print("-" * 70)
            for status, count in status_counter.most_common():
                percentage = count / len(data) * 100
                print(f"{status:15s}: {count:3d} ({percentage:5.1f}%)")
            
            print()
            print("-" * 70)
            print("REAL NUMBERS:")
            print("-" * 70)
            
            passed = sum(1 for item in data if item.get('status') == 'passed')
            failed = sum(1 for item in data if item.get('status') == 'failed')
            total = len(data)
            
            print(f"Total tests: {total}")
            print(f"Passed: {passed}")
            print(f"Failed: {failed}")
            print(f"Pass rate: {passed/total*100:.1f}%")
            print(f"Fail rate: {failed/total*100:.1f}%")
            print()
            
            # 与目标对比
            print("-" * 70)
            print("GAP TO TARGET:")
            print("-" * 70)
            print(f"Current pass rate: {passed/total*100:.1f}%")
            print(f"Target: 100.0%")
            print(f"Gap: {100 - passed/total*100:.1f}%")
            print(f"Need to fix: {failed} tests")
            print()
            
            # 分析失败原因
            print("-" * 70)
            print("FAILURE ANALYSIS:")
            print("-" * 70)
            
            failed_items = [item for item in data if item.get('status') == 'failed']
            
            error_types = []
            for item in failed_items:
                error = item.get('error', 'Unknown')
                if 'Exit code' in error:
                    error_types.append('Exit code 1')
                elif 'ModuleNotFoundError' in error:
                    error_types.append('ModuleNotFoundError')
                elif 'ImportError' in error:
                    error_types.append('ImportError')
                elif 'Timeout' in error:
                    error_types.append('Timeout')
                elif 'UnicodeEncodeError' in error:
                    error_types.append('UnicodeEncodeError')
                elif error:
                    error_types.append(error[:30] + '...' if len(error) > 30 else error)
                else:
                    error_types.append('Unknown')
            
            error_counter = Counter(error_types)
            
            print("Top 10 failure reasons:")
            for i, (error, count) in enumerate(error_counter.most_common(10), 1):
                percentage = count / len(failed_items) * 100 if failed_items else 0
                print(f"{i:2d}. [{count:3d}, {percentage:5.1f}%] {error}")
            
            print()
            print("-" * 70)
            print("HONEST CONCLUSION:")
            print("-" * 70)
            
            if passed/total >= 0.90:
                status = "EXCELLENT"
            elif passed/total >= 0.75:
                status = "GOOD"
            elif passed/total >= 0.50:
                status = "MODERATE"
            elif passed/total >= 0.25:
                status = "POOR"
            else:
                status = "CRITICAL"
            
            print(f"Overall status: {status}")
            print(f"Pass rate: {passed/total*100:.1f}%")
            print(f"This means: {failed} out of {total} tests are failing")
            print(f"Work remaining: SIGNIFICANT" if failed > 100 else "MODERATE" if failed > 50 else "MINOR")
            print()
            
    elif isinstance(data, dict):
        print("Data is a dictionary")
        print("Keys:", list(data.keys()))
    else:
        print(f"Unexpected data type: {type(data)}")
    
    print("=" * 70)


if __name__ == '__main__':
    main()

