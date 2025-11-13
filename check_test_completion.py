#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查测试是否真正完成

Author: HydroClaude
Date: 2025-11-13
"""

import os

def main():
    """检查测试完成情况"""
    
    log_file = 'test_results/batch_test_output_v3.txt'
    
    if not os.path.exists(log_file):
        print(f"[ERROR] {log_file} not found!")
        return
    
    print("=" * 60)
    print(" " * 15 + "TEST COMPLETION CHECK")
    print("=" * 60)
    print()
    
    # 读取日志文件
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        print(f"[ERROR] Failed to read log file: {e}")
        return
    
    # 查找最后的测试编号
    import re
    matches = re.findall(r'\[(\d+)/541\]', content)
    
    if matches:
        last_test = int(matches[-1])
        print(f"Last test number found: {last_test}/541")
        print(f"Progress: {last_test/541*100:.1f}%")
        print()
        
        if last_test == 541:
            print("[OK] All 541 tests have been processed")
        else:
            print(f"[WARN] Only {last_test} out of 541 tests processed")
            print(f"Missing: {541 - last_test} tests")
    else:
        print("[ERROR] No test progress found in log")
    
    # 统计PASS/FAIL
    pass_count = content.count('PASS')
    fail_count = content.count('FAIL')
    total_counted = pass_count + fail_count
    
    print()
    print(f"PASS count: {pass_count}")
    print(f"FAIL count: {fail_count}")
    print(f"Total counted: {total_counted}")
    
    if total_counted > 0:
        print(f"Pass rate: {pass_count/total_counted*100:.1f}%")
        print(f"Fail rate: {fail_count/total_counted*100:.1f}%")
    
    print()
    
    # 检查是否有"completed"或"finished"字样
    if 'completed' in content.lower() or 'finished' in content.lower():
        print("[OK] Test appears to be completed")
    else:
        print("[WARN] No completion marker found")
    
    # 获取最后几行
    lines = content.split('\n')
    print()
    print("-" * 60)
    print("Last 10 lines of log:")
    print("-" * 60)
    for line in lines[-10:]:
        if line.strip():
            print(line[:100])  # 截断很长的行
    
    print()
    print("=" * 60)


if __name__ == '__main__':
    main()

