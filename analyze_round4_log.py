#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析第四轮测试日志

Author: HydroClaude
Date: 2025-11-13
"""

import re
import os

def main():
    """分析第四轮测试日志"""
    
    log_file = 'test_results/batch_test_output_v4.txt'
    
    print("=" * 70)
    print(" " * 15 + "ROUND 4 LOG ANALYSIS")
    print("=" * 70)
    print()
    
    if not os.path.exists(log_file):
        print(f"[ERROR] {log_file} not found!")
        return
    
    # 获取文件信息
    file_size = os.path.getsize(log_file)
    print(f"Log file size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # 读取日志
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        # 尝试UTF-8
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            print(f"[ERROR] Failed to read log: {e}")
            return
    
    print(f"Content length: {len(content):,} characters")
    print()
    
    # 提取测试编号
    test_nums = re.findall(r'\[(\d+)/541\]', content)
    
    if test_nums:
        last_test = int(test_nums[-1])
        progress = last_test / 541 * 100
        
        print("-" * 70)
        print("TEST PROGRESS:")
        print("-" * 70)
        print(f"Tests processed: {last_test}/541 ({progress:.1f}%)")
        print(f"First test: {test_nums[0]}")
        print(f"Last test: {last_test}")
        print()
    else:
        print("[WARN] No test progress markers found")
        print()
    
    # 统计PASS/FAIL
    pass_count = content.count('PASS')
    fail_count = content.count('FAIL')
    total = pass_count + fail_count
    
    print("-" * 70)
    print("TEST RESULTS:")
    print("-" * 70)
    print(f"PASS count: {pass_count}")
    print(f"FAIL count: {fail_count}")
    print(f"Total counted: {total}")
    
    if total > 0:
        pass_rate = pass_count / total * 100
        fail_rate = fail_count / total * 100
        print(f"Pass rate: {pass_rate:.1f}%")
        print(f"Fail rate: {fail_rate:.1f}%")
        print()
        
        # 与第三轮对比
        round3_pass = 267
        round3_total = 541
        round3_rate = 49.4
        
        print("-" * 70)
        print("COMPARISON WITH ROUND 3:")
        print("-" * 70)
        print(f"Round 3: {round3_rate}% ({round3_pass}/{round3_total})")
        
        if test_nums and last_test > 0:
            # 估算完整通过率
            estimated_pass = int(pass_count * 541 / last_test)
            estimated_rate = estimated_pass / 541 * 100
            print(f"Round 4: {pass_rate:.1f}% ({pass_count}/{last_test}) - Partial")
            print(f"Estimated if completed: {estimated_rate:.1f}% ({estimated_pass}/541)")
            
            if estimated_rate > round3_rate:
                improvement = estimated_rate - round3_rate
                print(f"\nEstimated improvement: +{improvement:.1f}%")
                print(f"Estimated new passes: +{estimated_pass - round3_pass}")
            elif estimated_rate < round3_rate:
                decline = round3_rate - estimated_rate
                print(f"\nEstimated decline: -{decline:.1f}%")
            else:
                print(f"\nNo significant change")
        else:
            print(f"Round 4: {pass_rate:.1f}% ({pass_count}/{total})")
    
    print()
    
    # 检查最后几行，看是否有异常
    lines = content.split('\n')
    
    print("-" * 70)
    print("LAST 20 LINES OF LOG:")
    print("-" * 70)
    for line in lines[-20:]:
        if line.strip():
            print(line[:120])  # 截断长行
    
    print()
    print("=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    
    if test_nums:
        last = int(test_nums[-1])
        if last < 541:
            print(f"Test was INTERRUPTED at {last}/541 ({progress:.1f}%)")
            print(f"Reason: User terminated after 1+ hour")
        else:
            print("Test COMPLETED all 541 cases")
    
    if total > 0 and test_nums:
        print(f"Partial results: {pass_count} passed, {fail_count} failed")
        print(f"Pass rate so far: {pass_rate:.1f}%")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

