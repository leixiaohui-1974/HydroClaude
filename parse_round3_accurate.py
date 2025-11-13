#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
准确解析第三轮测试结果 - 获取真实数据

Author: HydroClaude
Date: 2025-11-13
"""

import re
import os

def main():
    """准确解析第三轮测试日志"""
    
    log_file = 'test_results/batch_test_output_v3.txt'
    
    if not os.path.exists(log_file):
        print(f"[ERROR] {log_file} not found!")
        return
    
    print("=" * 70)
    print(" " * 15 + "ROUND 3 ACCURATE ANALYSIS")
    print("=" * 70)
    print()
    
    # 读取日志
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        print(f"[ERROR] Failed to read: {e}")
        return
    
    # 方法1: 统计测试块
    test_blocks = re.split(r'\n(?=\[测试 \d+/541\])', content)
    print(f"Method 1 - Test blocks found: {len(test_blocks)}")
    
    # 方法2: 找所有的[测试 X/541]
    test_nums = re.findall(r'\[测试 (\d+)/541\]', content)
    print(f"Method 2 - Test numbers found: {len(test_nums)}")
    if test_nums:
        print(f"  First test: {test_nums[0]}")
        print(f"  Last test: {test_nums[-1]}")
    
    # 方法3: 统计状态行
    pass_matches = list(re.finditer(r'状态:.*?通过.*?PASS', content))
    fail_matches = list(re.finditer(r'状态:.*?失败.*?FAIL', content))
    
    print(f"\nMethod 3 - Status lines:")
    print(f"  PASS lines: {len(pass_matches)}")
    print(f"  FAIL lines: {len(fail_matches)}")
    print(f"  Total: {len(pass_matches) + len(fail_matches)}")
    
    # 方法4: 详细解析每个测试
    print(f"\nMethod 4 - Detailed parsing:")
    
    # 使用正则表达式提取每个测试的信息
    pattern = r'\[测试 (\d+)/541\].*?(?:状态:.*?(通过|失败).*?(?:PASS|FAIL))'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    print(f"  Matched tests: {len(matches)}")
    
    passed_count = 0
    failed_count = 0
    
    for match in matches:
        test_num = match.group(1)
        status = match.group(2)
        
        if status == '通过':
            passed_count += 1
        elif status == '失败':
            failed_count += 1
    
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total parsed: {passed_count + failed_count}")
    
    # 计算通过率
    if passed_count + failed_count > 0:
        total_parsed = passed_count + failed_count
        pass_rate = passed_count / total_parsed * 100
        
        print()
        print("-" * 70)
        print("ROUND 3 RESULTS:")
        print("-" * 70)
        print(f"Total tests run: {total_parsed}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Pass rate: {pass_rate:.1f}%")
        print()
        
        # 与第一轮对比
        round1_pass_rate = 19.6
        round1_passed = 106
        
        print("-" * 70)
        print("COMPARISON WITH ROUND 1:")
        print("-" * 70)
        print(f"Round 1: {round1_pass_rate}% ({round1_passed}/541)")
        print(f"Round 3: {pass_rate:.1f}% ({passed_count}/{total_parsed})")
        print()
        
        if pass_rate > round1_pass_rate:
            improvement = pass_rate - round1_pass_rate
            multiplier = pass_rate / round1_pass_rate
            print(f"Improvement: +{improvement:.1f}%")
            print(f"Multiplier: {multiplier:.2f}x")
            print(f"Status: IMPROVED")
        elif pass_rate < round1_pass_rate:
            decline = round1_pass_rate - pass_rate
            print(f"Decline: -{decline:.1f}%")
            print(f"Status: DECLINED")
        else:
            print(f"Status: NO CHANGE")
        
        print()
        print("-" * 70)
        print("HONEST ASSESSMENT:")
        print("-" * 70)
        
        if pass_rate >= 90:
            assessment = "EXCELLENT - Close to target"
        elif pass_rate >= 70:
            assessment = "GOOD - Significant progress"
        elif pass_rate >= 50:
            assessment = "MODERATE - Some progress"
        elif pass_rate >= 30:
            assessment = "POOR - Limited progress"
        else:
            assessment = "CRITICAL - Minimal progress"
        
        print(f"Assessment: {assessment}")
        print(f"Gap to 100%: {100 - pass_rate:.1f}%")
        print(f"Tests still failing: {failed_count}")
        print()
        
        # 保存结果
        output_file = 'test_results/round3_accurate_results.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ROUND 3 ACCURATE RESULTS\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Total tests run: {total_parsed}\n")
            f.write(f"Passed: {passed_count}\n")
            f.write(f"Failed: {failed_count}\n")
            f.write(f"Pass rate: {pass_rate:.1f}%\n\n")
            f.write(f"Round 1: {round1_pass_rate}% ({round1_passed}/541)\n")
            f.write(f"Round 3: {pass_rate:.1f}% ({passed_count}/{total_parsed})\n\n")
            if pass_rate > round1_pass_rate:
                f.write(f"Improvement: +{pass_rate - round1_pass_rate:.1f}%\n")
                f.write(f"Multiplier: {pass_rate / round1_pass_rate:.2f}x\n")
            f.write(f"\nAssessment: {assessment}\n")
            f.write(f"Gap to 100%: {100 - pass_rate:.1f}%\n")
        
        print(f"Results saved to: {output_file}")
    else:
        print("[ERROR] No tests could be parsed!")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

