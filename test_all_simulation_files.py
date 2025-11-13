#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试所有模拟案例文件

Author: HydroClaude
Date: 2025-11-13
"""

import subprocess
import sys
import os
from pathlib import Path
import json

def test_file(file_path, timeout=15):
    """测试单个文件"""
    try:
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        if result.returncode == 0:
            return 'PASS'
        else:
            # 提取错误类型
            err = result.stderr if result.stderr else result.stdout
            if 'ModuleNotFoundError' in err:
                return 'MODULE_ERROR'
            elif 'ImportError' in err:
                return 'IMPORT_ERROR'
            elif 'AttributeError' in err:
                return 'ATTR_ERROR'
            elif 'IndentationError' in err or 'SyntaxError' in err:
                return 'SYNTAX_ERROR'
            elif 'ValueError' in err:
                return 'VALUE_ERROR'
            elif 'FileNotFoundError' in err:
                return 'FILE_ERROR'
            else:
                return 'FAIL'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except Exception:
        return 'ERROR'

def main():
    """主函数"""
    
    print("="*70)
    print("TESTING ALL SIMULATION FILES")
    print("="*70)
    print()
    
    # 找到所有Python文件
    all_files = []
    for path in Path('examples').rglob('*.py'):
        if path.is_file() and path.name != '__init__.py':
            all_files.append(str(path))
    
    print(f"Found {len(all_files)} Python files")
    print("Testing...")
    print()
    
    # 统计
    results = {
        'PASS': [],
        'FAIL': [],
        'TIMEOUT': [],
        'MODULE_ERROR': [],
        'IMPORT_ERROR': [],
        'ATTR_ERROR': [],
        'SYNTAX_ERROR': [],
        'VALUE_ERROR': [],
        'FILE_ERROR': [],
        'ERROR': []
    }
    
    for i, file_path in enumerate(all_files, 1):
        status = test_file(file_path)
        results[status].append(file_path)
        
        # 显示进度
        if i % 10 == 0 or status != 'PASS':
            rel_path = os.path.relpath(file_path)
            print(f"[{i:3d}/{len(all_files)}] {status:15s} {rel_path}")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total files: {len(all_files)}")
    print()
    for status, files in sorted(results.items()):
        if files:
            print(f"{status:15s}: {len(files):3d} ({len(files)/len(all_files)*100:5.1f}%)")
    
    print()
    print("="*70)
    print(f"PASS RATE: {len(results['PASS'])}/{len(all_files)} = {len(results['PASS'])/len(all_files)*100:.1f}%")
    print("="*70)
    
    # 保存结果
    with open('full_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nResults saved to full_test_results.json")

if __name__ == '__main__':
    main()

