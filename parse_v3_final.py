#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终准确解析第三轮测试结果

Author: HydroClaude
Date: 2025-11-13
"""

import re
import os

def main():
    """准确解析第三轮测试"""
    
    log_file = 'test_results/batch_test_output_v3.txt'
    
    print("=" * 70)
    print(" " * 10 + "ROUND 3 FINAL ACCURATE ANALYSIS")
    print("=" * 70)
    print()
    
    # 读取日志（UTF-16-LE编码）
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        print(f"[ERROR] Failed to read: {e}")
        return
    
    print("Log file loaded successfully")
    print(f"Total characters: {len(content)}")
    print()
    
    # 找到所有测试编号
    test_nums = re.findall(r'\[(\d+)/541\]', content)
    print(f"Total test entries found: {len(test_nums)}")
    if test_nums:
        print(f"  First: {test_nums[0]}")
        print(f"  Last: {test_nums[-1]}")
    print()
    
    # 统计PASS和FAIL
    # 模式: "状态: 通过 PASS" 或 "状态: 失败 FAIL"
    pass_pattern = r'PASS'
    fail_pattern = r'FAIL'
    
    pass_count = len(re.findall(pass_pattern, content))
    fail_count = len(re.findall(fail_pattern, content))
    
    print(f"PASS occurrences: {pass_count}")
    print(f"FAIL occurrences: {fail_count}")
    print(f"Total: {pass_count + fail_count}")
    print()
    
    # 更准确的统计：每个测试只计数一次
    # 找到每个测试块
    test_blocks = []
    lines = content.split('\n')
    
    current_test = None
    current_block = []
    
    for line in lines:
        # 检查是否是新测试的开始
        match = re.match(r'\[(\d+)/541\]', line)
        if match:
            # 保存前一个测试块
            if current_test is not None:
                test_blocks.append((current_test, '\n'.join(current_block)))
            # 开始新测试块
            current_test = int(match.group(1))
            current_block = [line]
        else:
            if current_test is not None:
                current_block.append(line)
    
    # 保存最后一个测试块
    if current_test is not None:
        test_blocks.append((current_test, '\n'.join(current_block)))
    
    print(f"Parsed test blocks: {len(test_blocks)}")
    print()
    
    # 分析每个测试块的状态
    passed = 0
    failed = 0
    timeout = 0
    unknown = 0
    
    for test_num, block in test_blocks:
        if 'PASS' in block:
            passed += 1
        elif 'FAIL' in block:
            failed += 1
        elif 'timeout' in block.lower() or '超时' in block:
            timeout += 1
            failed += 1  # 超时也算失败
        else:
            unknown += 1
    
    total_parsed = len(test_blocks)
    
    print("-" * 70)
    print("DETAILED RESULTS:")
    print("-" * 70)
    print(f"Total tests parsed: {total_parsed}")
    print(f"Passed (PASS): {passed}")
    print(f"Failed (FAIL): {failed - timeout}")
    print(f"Timeout: {timeout}")
    print(f"Unknown: {unknown}")
    print(f"Total failed: {failed}")
    print()
    
    if total_parsed > 0:
        pass_rate = passed / total_parsed * 100
        fail_rate = failed / total_parsed * 100
        
        print(f"Pass rate: {pass_rate:.1f}%")
        print(f"Fail rate: {fail_rate:.1f}%")
        print()
        
        # 与第一轮对比
        round1_passed = 106
        round1_failed = 434
        round1_total = 541
        round1_pass_rate = 19.6
        
        print("-" * 70)
        print("COMPARISON WITH ROUND 1:")
        print("-" * 70)
        print(f"Round 1: {round1_pass_rate}% ({round1_passed}/{round1_total})")
        print(f"Round 3: {pass_rate:.1f}% ({passed}/{total_parsed})")
        print()
        
        if pass_rate > round1_pass_rate:
            improvement = pass_rate - round1_pass_rate
            multiplier = pass_rate / round1_pass_rate
            new_passes = passed - round1_passed
            print(f"Improvement: +{improvement:.1f}%")
            print(f"Multiplier: {multiplier:.2f}x")
            print(f"Additional passes: +{new_passes}")
            print(f"Status: ✓ IMPROVED")
        elif pass_rate < round1_pass_rate:
            decline = round1_pass_rate - pass_rate
            print(f"Decline: -{decline:.1f}%")
            print(f"Status: ✗ DECLINED")
        else:
            print(f"Status: = NO CHANGE")
        
        print()
        print("-" * 70)
        print("HONEST ASSESSMENT:")
        print("-" * 70)
        
        if pass_rate >= 90:
            assessment = "EXCELLENT"
            rating = "⭐⭐⭐⭐⭐"
        elif pass_rate >= 70:
            assessment = "GOOD"
            rating = "⭐⭐⭐⭐"
        elif pass_rate >= 50:
            assessment = "MODERATE"
            rating = "⭐⭐⭐"
        elif pass_rate >= 30:
            assessment = "POOR"
            rating = "⭐⭐"
        else:
            assessment = "CRITICAL"
            rating = "⭐"
        
        print(f"Assessment: {assessment} {rating}")
        print(f"Gap to target (100%): {100 - pass_rate:.1f}%")
        print(f"Tests still need fixing: {failed}")
        print()
        
        # 实事求是的结论
        print("-" * 70)
        print("REALISTIC CONCLUSION:")
        print("-" * 70)
        
        if pass_rate < 50:
            print("Status: PROBLEMATIC")
            print("- Less than half of tests pass")
            print("- Significant work still needed")
            print("- 100% target is distant")
        elif pass_rate < 70:
            print("Status: MODERATE PROGRESS")
            print("- More than half tests pass")
            print("- Good foundation established")
            print("- More work needed for 100%")
        elif pass_rate < 90:
            print("Status: GOOD PROGRESS")
            print("- Most tests pass")
            print("- Strong foundation")
            print("- 100% is achievable")
        else:
            print("Status: EXCELLENT PROGRESS")
            print("- Nearly all tests pass")
            print("- Very close to target")
            print("- 100% is within reach")
        
        print()
        
        # 保存结果
        output_file = 'test_results/ROUND3_REAL_RESULTS.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ROUND 3 REAL RESULTS (Honest Analysis)\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Total tests: {total_parsed}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Pass rate: {pass_rate:.1f}%\n")
            f.write(f"Fail rate: {fail_rate:.1f}%\n\n")
            f.write("Comparison with Round 1:\n")
            f.write(f"  Round 1: {round1_pass_rate}% ({round1_passed}/{round1_total})\n")
            f.write(f"  Round 3: {pass_rate:.1f}% ({passed}/{total_parsed})\n\n")
            if pass_rate > round1_pass_rate:
                f.write(f"  Improvement: +{pass_rate - round1_pass_rate:.1f}%\n")
                f.write(f"  Multiplier: {pass_rate / round1_pass_rate:.2f}x\n")
            f.write(f"\nAssessment: {assessment}\n")
            f.write(f"Gap to 100%: {100 - pass_rate:.1f}%\n")
        
        print(f"Results saved to: {output_file}")
    else:
        print("[ERROR] No tests could be parsed!")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

