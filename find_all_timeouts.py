#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
找出所有timeout的测试

Author: HydroClaude
Date: 2025-11-13
"""

import json
import re
import os

def main():
    """找出所有timeout测试"""
    
    print("=" * 70)
    print("FINDING ALL TIMEOUT TESTS")
    print("=" * 70)
    print()
    
    timeout_files = []
    
    # 方法1: 从第三轮日志中找
    log_file = 'test_results/batch_test_output_v3.txt'
    if os.path.exists(log_file):
        with open(log_file, 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
        
        # 找所有包含"超时"或"timeout"的测试块
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '超时' in line or 'timeout' in line.lower():
                # 往前找测试名称
                for j in range(max(0, i-10), i):
                    if '文件:' in lines[j]:
                        match = re.search(r'文件:\s*(.+\.py)', lines[j])
                        if match:
                            file_path = match.group(1).strip()
                            if file_path not in timeout_files:
                                timeout_files.append(file_path)
                        break
    
    print(f"Found {len(timeout_files)} timeout tests from v3 log")
    
    # 保存到文件
    with open('test_results/files_timeout.txt', 'w', encoding='utf-8') as f:
        for file_path in timeout_files:
            f.write(file_path + '\n')
    
    print("Saved to: test_results/files_timeout.txt")
    print()
    
    # 显示列表
    if timeout_files:
        print("Timeout tests:")
        for i, f in enumerate(timeout_files, 1):
            print(f"{i:2d}. {f}")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

