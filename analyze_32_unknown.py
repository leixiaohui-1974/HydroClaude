#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析32个未知状态的测试

Author: HydroClaude
Date: 2025-11-13
"""

import re
import os

def main():
    """分析32个未知状态测试"""
    
    log_file = 'test_results/batch_test_output_v3.txt'
    
    print("=" * 70)
    print(" " * 15 + "ANALYZE 32 UNKNOWN TESTS")
    print("=" * 70)
    print()
    
    # 读取日志
    try:
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
    except Exception as e:
        print(f"[ERROR] Failed to read: {e}")
        return
    
    # 解析测试块
    test_blocks = []
    lines = content.split('\n')
    
    current_test = None
    current_block = []
    current_name = ""
    current_file = ""
    
    for line in lines:
        # 检查是否是新测试的开始
        match = re.match(r'\[(\d+)/541\]', line)
        if match:
            # 保存前一个测试块
            if current_test is not None:
                test_blocks.append({
                    'num': current_test,
                    'name': current_name,
                    'file': current_file,
                    'content': '\n'.join(current_block)
                })
            # 开始新测试块
            current_test = int(match.group(1))
            # 提取测试名称
            name_match = re.search(r'\[(\d+)/541\].*?:\s*(.+)', line)
            if name_match:
                current_name = name_match.group(2).strip()
            else:
                current_name = "Unknown"
            current_block = [line]
            current_file = ""
        else:
            if current_test is not None:
                current_block.append(line)
                # 提取文件路径
                if '文件:' in line:
                    file_match = re.search(r'文件:\s*(.+)', line)
                    if file_match:
                        current_file = file_match.group(1).strip()
    
    # 保存最后一个测试块
    if current_test is not None:
        test_blocks.append({
            'num': current_test,
            'name': current_name,
            'file': current_file,
            'content': '\n'.join(current_block)
        })
    
    print(f"Total test blocks parsed: {len(test_blocks)}")
    
    # 筛选未知状态的测试（既没有PASS也没有FAIL）
    unknown_tests = []
    for test in test_blocks:
        if 'PASS' not in test['content'] and 'FAIL' not in test['content']:
            unknown_tests.append(test)
    
    print(f"Unknown status tests found: {len(unknown_tests)}")
    print()
    
    if len(unknown_tests) == 0:
        print("[INFO] No unknown tests found. All tests have clear status.")
        return
    
    print("-" * 70)
    print("UNKNOWN TESTS LIST:")
    print("-" * 70)
    
    for i, test in enumerate(unknown_tests, 1):
        print(f"{i:2d}. [{test['num']}] {test['name']}")
        print(f"    File: {test['file']}")
        
        # 尝试找出为什么没有状态
        content = test['content']
        
        if '超时' in content or 'timeout' in content.lower():
            reason = "Timeout"
        elif '错误' in content or 'error' in content.lower():
            reason = "Error occurred but no clear PASS/FAIL"
        elif len(content) < 100:
            reason = "Test block too short - may be interrupted"
        else:
            reason = "Unknown - needs manual investigation"
        
        print(f"    Possible reason: {reason}")
        print()
    
    # 保存详细结果
    output_file = 'test_results/32_unknown_analysis.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write(f"ANALYSIS OF {len(unknown_tests)} UNKNOWN STATUS TESTS\n")
        f.write("=" * 70 + "\n\n")
        
        for i, test in enumerate(unknown_tests, 1):
            f.write(f"\n[{i}] Test #{test['num']}: {test['name']}\n")
            f.write(f"File: {test['file']}\n")
            f.write("-" * 70 + "\n")
            f.write(test['content'][:500])  # 前500字符
            if len(test['content']) > 500:
                f.write("\n... (truncated)")
            f.write("\n" + "=" * 70 + "\n")
    
    print(f"Detailed analysis saved to: {output_file}")
    
    # 保存文件列表
    files_output = 'test_results/unknown_test_files.txt'
    with open(files_output, 'w', encoding='utf-8') as f:
        for test in unknown_tests:
            f.write(f"{test['file']}\n")
    
    print(f"File list saved to: {files_output}")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

