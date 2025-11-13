#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析正在运行的测试 - 从日志文件实时提取统计
"""
import re
from pathlib import Path
from collections import defaultdict

def parse_running_test_log(log_file):
    """解析正在运行的测试日志"""
    if not Path(log_file).exists():
        print(f"[ERROR] Log file not found: {log_file}")
        return None
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取测试结果（更鲁棒的模式，不依赖中文）
    pass_pattern = r'\[(\d+)/541\].*?PASS'
    fail_pattern = r'\[(\d+)/541\].*?FAIL'
    
    passes = re.findall(pass_pattern, content, re.DOTALL)
    fails = re.findall(fail_pattern, content, re.DOTALL)
    
    # 找到最后一个测试索引
    last_test_pattern = r'\[(\d+)/541\]'
    all_tests = re.findall(last_test_pattern, content)
    
    current = int(all_tests[-1]) if all_tests else 0
    total_passed = len(passes)
    total_failed = len(fails)
    
    return {
        'current': current,
        'total': 541,
        'passed': total_passed,
        'failed': total_failed,
        'progress': current / 541 * 100,
        'pass_rate': total_passed / current * 100 if current > 0 else 0
    }

def main():
    log_file = "test_results/batch_test_output_v2.txt"
    
    print("="*70)
    print("正在运行的测试分析 - Running Test Analysis")
    print("="*70)
    
    stats = parse_running_test_log(log_file)
    
    if stats:
        print(f"\n当前进度: {stats['current']}/{stats['total']} ({stats['progress']:.1f}%)")
        print(f"已通过: {stats['passed']} 个")
        print(f"已失败: {stats['failed']} 个")
        print(f"通过率: {stats['pass_rate']:.1f}%")
        print(f"\n剩余: {stats['total'] - stats['current']} 个测试")
        
        # 预估
        if stats['current'] > 50:
            expected_pass = int(stats['total'] * stats['pass_rate'] / 100)
            print(f"\n预估最终结果:")
            print(f"  预计通过: {expected_pass} 个 ({stats['pass_rate']:.1f}%)")
            print(f"  预计失败: {stats['total'] - expected_pass} 个")
        
        print("\n" + "="*70)
        
        # 与第一轮对比
        print("\n对比第一轮测试:")
        print(f"  第一轮通过率: 19.6% (106/541)")
        print(f"  当前通过率: {stats['pass_rate']:.1f}% ({stats['passed']}/{stats['current']})")
        
        if stats['pass_rate'] > 19.6:
            improvement = stats['pass_rate'] - 19.6
            print(f"  改进: +{improvement:.1f}% [OK]")
        elif stats['pass_rate'] < 19.6:
            decline = 19.6 - stats['pass_rate']
            print(f"  下降: -{decline:.1f}% [WARN]")
        else:
            print(f"  持平 [INFO]")
    else:
        print("[ERROR] Could not parse log file")

if __name__ == '__main__':
    main()

