#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断剩余失败案例的具体错误

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os

remaining_fails = [
    'examples/advanced_examples/compare_canal_solvers.py',
    'examples/advanced_examples/debug_saint_venant.py',
    'examples/advanced_examples/diagnose_canal_boundary.py',
    'examples/case_irrigation_scheduling.py',
    'examples/case_library/case_02_flood_routing/flood_routing_simulation.py',
]

def diagnose_file(file_path):
    """诊断单个文件的详细错误"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        if result.returncode == 0:
            return 'PASS', None
        
        # 获取完整错误输出
        output = result.stderr if result.stderr else result.stdout
        
        # 提取关键错误行
        lines = output.split('\n')
        error_lines = []
        for i, line in enumerate(lines):
            if 'Error' in line or 'Exception' in line or 'Traceback' in line:
                # 获取前后几行上下文
                start = max(0, i-2)
                end = min(len(lines), i+3)
                error_lines.extend(lines[start:end])
                break
        
        return 'FAIL', '\n'.join(error_lines)
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 'Timeout after 10s'
    except Exception as e:
        return 'ERROR', str(e)

def main():
    """主函数"""
    
    print("="*70)
    print("DIAGNOSING REMAINING 5 FAILURES")
    print("="*70)
    print()
    
    for i, file_path in enumerate(remaining_fails, 1):
        basename = os.path.basename(file_path)
        print(f"[{i}/5] {basename}")
        print("-"*70)
        
        if not os.path.exists(file_path):
            print("FILE NOT FOUND")
            print()
            continue
        
        status, detail = diagnose_file(file_path)
        
        print(f"Status: {status}")
        if detail:
            print(f"\nError details:\n{detail}")
        print()
        print("="*70)
        print()

if __name__ == '__main__':
    main()

