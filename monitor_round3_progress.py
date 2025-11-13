#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""监控第三轮测试进度"""

import time
from pathlib import Path
import re

def check_progress():
    """检查测试进度"""
    
    log_file = Path("test_results/batch_test_output_v3.txt")
    
    if not log_file.exists():
        return None, None, None
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 查找进度标记 [X/541]
        progress_matches = re.findall(r'\[(\d+)/541\]', content)
        if progress_matches:
            current = int(progress_matches[-1])
        else:
            current = 0
        
        # 统计通过和失败
        passes = len(re.findall(r'通过 PASS', content))
        fails = len(re.findall(r'失败 FAIL', content))
        
        return current, passes, fails
    
    except Exception as e:
        return None, None, None

def main():
    print("="*70)
    print("第三轮测试进度监控")
    print("="*70)
    print("\n修复内容:")
    print("  - Unicode编码问题: 410个文件")
    print("  - 数值稳定性优化: 45个文件")
    print("\n预期通过率: 60%+ (基于快速测试)")
    print("\n" + "="*70)
    
    last_current = 0
    
    while True:
        current, passes, fails = check_progress()
        
        if current is None:
            print("\n[等待] 测试尚未开始...")
            time.sleep(5)
            continue
        
        if current > last_current:
            total = passes + fails
            pass_rate = (passes / total * 100) if total > 0 else 0
            
            print(f"\r[{current}/541] 通过: {passes} | 失败: {fails} | 通过率: {pass_rate:.1f}%    ", end='', flush=True)
            last_current = current
        
        if current >= 541:
            print("\n\n[完成] 测试已完成!")
            break
        
        time.sleep(3)
    
    # 最终统计
    print("\n" + "="*70)
    print("第三轮测试最终结果")
    print("="*70)
    print(f"总计: 541")
    print(f"通过: {passes}")
    print(f"失败: {fails}")
    print(f"通过率: {passes/541*100:.2f}%")
    
    # 对比
    print(f"\n通过率对比:")
    print(f"  第一轮: 19.6%")
    print(f"  第二轮: 18.9%")
    print(f"  第三轮: {passes/541*100:.2f}%")
    
    improvement = passes/541*100 - 19.6
    print(f"  提升: {improvement:+.1f}%")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[中断] 监控已停止")

