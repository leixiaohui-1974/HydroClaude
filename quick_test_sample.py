#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Test Sample - 快速测试样本
先测试一小部分案例来验证系统

Author: HydroClaude Team
Date: 2025-11-13
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

CATALOG_FILE = PROJECT_ROOT / "web" / "backend" / "data" / "test_cases_catalog.json"

def quick_test(num_samples=10):
    """快速测试指定数量的样本案例"""
    print("="*80)
    print(" 快速测试样本 - Quick Test Sample ".center(80))
    print("="*80)
    print()
    
    # 加载目录
    with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    test_cases = catalog.get('testCases', [])
    total = len(test_cases)
    
    print(f"总共 {total} 个测试案例")
    print(f"随机抽取 {num_samples} 个进行快速测试\n")
    
    # 随机选择案例
    import random
    random.seed(42)  # 固定随机种子以便复现
    samples = random.sample(test_cases, min(num_samples, total))
    
    passed = 0
    failed = 0
    errors = 0
    
    for idx, test_case in enumerate(samples, 1):
        metadata = test_case.get('metadata', {})
        case_name = metadata.get('name', 'Unknown')
        file_path = test_case.get('sourcePath', '')
        
        print(f"[{idx}/{num_samples}] {case_name}")
        print(f"    文件: {file_path}")
        
        if not file_path:
            print(f"    状态: 错误 - 无源文件")
            errors += 1
            print()
            continue
        
        full_path = PROJECT_ROOT / file_path
        
        if not full_path.exists():
            print(f"    状态: 错误 - 文件不存在")
            errors += 1
            print()
            continue
        
        # 运行测试
        try:
            start = time.time()
            process = subprocess.Popen(
                [sys.executable, str(full_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=30)
                returncode = process.returncode
                duration = time.time() - start
                
                if returncode == 0:
                    print(f"    状态: 通过 PASS ({duration:.2f}s)")
                    passed += 1
                else:
                    print(f"    状态: 失败 FAIL (错误码: {returncode})")
                    if stderr:
                        print(f"    错误: {stderr[:200]}")
                    failed += 1
            
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"    状态: 失败 - 超时")
                failed += 1
        
        except Exception as e:
            print(f"    状态: 错误 - {str(e)}")
            errors += 1
        
        print()
    
    # 总结
    print("="*80)
    print(" 测试完成 ".center(80))
    print("="*80)
    print()
    print(f"总计: {num_samples}")
    print(f"通过: {passed} ({passed/num_samples*100:.1f}%)")
    print(f"失败: {failed} ({failed/num_samples*100:.1f}%)")
    print(f"错误: {errors} ({errors/num_samples*100:.1f}%)")
    print()
    
    if passed == num_samples:
        print("[PASS] 所有测试通过！可以进行完整测试。")
        return True
    else:
        print(f"[WARN] 有 {failed + errors} 个测试未通过。建议先修复问题。")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='快速测试样本案例')
    parser.add_argument('-n', '--num', type=int, default=10, help='测试案例数量（默认10）')
    args = parser.parse_args()
    
    success = quick_test(args.num)
    sys.exit(0 if success else 1)

