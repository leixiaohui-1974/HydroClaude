#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
监控第四轮测试进度

Author: HydroClaude
Date: 2025-11-13
"""

import time
import os

def monitor():
    """实时监控测试进度"""
    
    log_file = 'test_results/batch_test_output_v4.txt'
    
    print("=" * 70)
    print(" " * 15 + "MONITOR ROUND 4 TEST")
    print("=" * 70)
    print()
    
    last_size = 0
    check_count = 0
    
    while True:
        check_count += 1
        
        if not os.path.exists(log_file):
            print(f"[{check_count}] Waiting for test to start...")
            time.sleep(5)
            continue
        
        # 读取文件
        try:
            with open(log_file, 'rb') as f:
                content = f.read().decode('utf-16-le', errors='ignore')
        except:
            print(f"[{check_count}] Reading log file...")
            time.sleep(5)
            continue
        
        # 提取进度
        import re
        test_nums = re.findall(r'\[(\d+)/541\]', content)
        
        if test_nums:
            current = int(test_nums[-1])
            progress = current / 541 * 100
            
            # 统计PASS/FAIL
            passes = content.count('PASS')
            fails = content.count('FAIL')
            total = passes + fails
            
            pass_rate = passes / total * 100 if total > 0 else 0
            
            print(f"\r[{check_count}] Progress: {current}/541 ({progress:.0f}%) | "
                  f"Pass: {passes} Fail: {fails} Rate: {pass_rate:.1f}%", end='', flush=True)
            
            if current >= 541:
                print("\n\nTest completed!")
                print()
                print(f"Final: {passes} passed, {fails} failed")
                print(f"Pass rate: {pass_rate:.1f}%")
                break
        else:
            print(f"[{check_count}] Test starting...")
        
        time.sleep(10)  # 每10秒检查一次
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    monitor()

