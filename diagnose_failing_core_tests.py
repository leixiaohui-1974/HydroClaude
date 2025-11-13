#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断失败的核心测试"""

import sys
import os
import subprocess
from pathlib import Path

# 设置UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 失败的测试
FAILING_TESTS = [
    {
        'name': 'Lake at Rest',
        'path': 'tests/test_lake_at_rest_wb.py',
        'timeout': 120
    },
    {
        'name': '单闸门流动V2',
        'path': 'examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py',
        'timeout': 180
    },
]

def run_test_detailed(test_info):
    """运行测试并捕获详细输出"""
    
    test_path = Path(test_info['path'])
    
    if not test_path.exists():
        print(f"[ERROR] 文件不存在: {test_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"测试: {test_info['name']}")
    print(f"文件: {test_path}")
    print(f"{'='*70}\n")
    
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=test_info['timeout'],
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nExit code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"\n[分析] 测试失败，退出码: {result.returncode}")
            
            # 查找具体错误
            output = result.stdout + result.stderr
            
            if 'Traceback' in output:
                print("\n[错误] 发现Python异常")
                # 提取traceback
                lines = output.split('\n')
                in_traceback = False
                for line in lines:
                    if 'Traceback' in line:
                        in_traceback = True
                    if in_traceback:
                        print(f"  {line}")
                        if line.strip() and not line.startswith(' ') and 'Traceback' not in line:
                            in_traceback = False
            
            if 'AssertionError' in output:
                print("\n[错误] 断言失败")
            
            if 'NaN' in output or 'nan' in output:
                print("\n[错误] 检测到NaN值")
            
            if 'Inf' in output or 'inf' in output:
                print("\n[错误] 检测到Inf值")
        
        else:
            print(f"\n[OK] 测试通过")
    
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] 测试超时 (>{test_info['timeout']}s)")
    except Exception as e:
        print(f"\n[ERROR] 运行失败: {e}")

def main():
    print("="*70)
    print("诊断失败的核心测试")
    print("="*70)
    
    for i, test in enumerate(FAILING_TESTS, 1):
        print(f"\n[{i}/{len(FAILING_TESTS)}]")
        run_test_detailed(test)
        print("\n" + "="*70)

if __name__ == '__main__':
    main()

