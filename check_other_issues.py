#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查其他潜在问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
from pathlib import Path
import re

def check_file(file_path):
    """检查文件是否有潜在问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # 问题1: 使用了cvxpy但可能未安装
        if 'import cvxpy' in content or 'from cvxpy' in content:
            issues.append('cvxpy')
        
        # 问题2: 使用了废弃的SingleCanalSolver
        if 'SingleCanalSolver' in content or 'from solvers.single_canal_solver' in content:
            issues.append('SingleCanalSolver')
        
        # 问题3: 使用了CanalSolver (废弃)
        if 'from solvers.canal_solver import CanalSolver' in content:
            issues.append('CanalSolver')
        
        # 问题4: 缺少sys.path设置
        if 'from solvers.' in content or 'from physics.' in content or 'from utils.' in content:
            if 'sys.path' not in content:
                issues.append('missing_syspath')
        
        # 问题5: input() 会阻塞
        if 'input(' in content:
            issues.append('input_blocking')
        
        # 问题6: 可能还有Unicode字符
        # 检查是否有非ASCII字符在print或注释中
        for line in content.split('\n'):
            if 'print' in line or '#' in line:
                if any(ord(c) > 127 for c in line):
                    # 排除中文注释（这些是正常的）
                    if not any(0x4e00 <= ord(c) <= 0x9fff for c in line):
                        issues.append('unicode_chars')
                        break
        
        return issues
        
    except Exception as e:
        return [f'read_error']

def main():
    """主函数"""
    
    print("="*70)
    print("CHECKING FOR OTHER POTENTIAL ISSUES")
    print("="*70)
    print()
    
    # 找到所有Python文件
    all_files = []
    for path in Path('examples').rglob('*.py'):
        if path.is_file() and path.name != '__init__.py':
            all_files.append(str(path))
    
    print(f"Scanning {len(all_files)} files...")
    print()
    
    # 统计问题
    issue_files = {
        'cvxpy': [],
        'SingleCanalSolver': [],
        'CanalSolver': [],
        'missing_syspath': [],
        'input_blocking': [],
        'unicode_chars': [],
        'read_error': [],
    }
    
    for file_path in all_files:
        issues = check_file(file_path)
        for issue in issues:
            if issue in issue_files:
                issue_files[issue].append(file_path)
    
    # 显示结果
    print("ISSUE SUMMARY")
    print("="*70)
    
    for issue, files in issue_files.items():
        if files:
            print(f"\n{issue.upper()} ({len(files)} files):")
            for f in files[:10]:  # 只显示前10个
                print(f"  - {os.path.relpath(f)}")
            if len(files) > 10:
                print(f"  ... and {len(files)-10} more")
    
    print()
    print("="*70)
    print("PRIORITY FIXES NEEDED:")
    print("="*70)
    
    # 优先级排序
    if issue_files['cvxpy']:
        print(f"1. CVXPY: {len(issue_files['cvxpy'])} files need cvxpy module")
    
    if issue_files['SingleCanalSolver'] or issue_files['CanalSolver']:
        total = len(issue_files['SingleCanalSolver']) + len(issue_files['CanalSolver'])
        print(f"2. DEPRECATED SOLVERS: {total} files use deprecated solvers")
    
    if issue_files['missing_syspath']:
        print(f"3. MISSING SYSPATH: {len(issue_files['missing_syspath'])} files may need sys.path fix")
    
    if issue_files['input_blocking']:
        print(f"4. INPUT BLOCKING: {len(issue_files['input_blocking'])} files use input()")
    
    if issue_files['unicode_chars']:
        print(f"5. UNICODE: {len(issue_files['unicode_chars'])} files have Unicode issues")
    
    print("="*70)

if __name__ == '__main__':
    main()

