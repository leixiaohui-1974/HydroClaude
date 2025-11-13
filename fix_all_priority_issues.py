#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复所有优先级问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
from pathlib import Path

def fix_file_comprehensive(file_path):
    """全面修复文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 1. 注释掉input()调用（防止阻塞）
        if 'input(' in content:
            content = re.sub(r'\s*input\([^)]*\)', '# input() disabled for automated testing', content)
            changes.append("Disabled input()")
        
        # 2. 移除或替换Unicode特殊字符（除了中文）
        # 常见问题字符
        unicode_replacements = {
            '\u2192': '->',      # →
            '\u2022': '*',       # •
            '\u2713': 'OK',      # ✓
            '\u2717': 'X',       # ✗
            '\u2014': '--',      # —
            '\u2013': '-',       # –
            '\u05a7': '',        # 神秘字符
            '\u00b0': 'deg',     # °
            '\u00b1': '+/-',     # ±
            '\u03b1': 'alpha',   # α
            '\u03b2': 'beta',    # β
            '\u2260': '!=',      # ≠
            '\u2264': '<=',      # ≤
            '\u2265': '>=',      # ≥
        }
        
        has_unicode = False
        for old_char, new_char in unicode_replacements.items():
            if old_char in content:
                content = content.replace(old_char, new_char)
                has_unicode = True
        
        if has_unicode:
            changes.append("Fixed Unicode chars")
        
        # 3. 替换废弃的SingleCanalSolver（如果使用）
        if 'SingleCanalSolver' in content:
            # 替换import
            if 'from solvers.single_canal_solver import SingleCanalSolver' in content:
                content = content.replace(
                    'from solvers.single_canal_solver import SingleCanalSolver',
                    'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver'
                )
                changes.append("SingleCanalSolver->HydrostaticCanalSolver")
        
        # 4. 替换废弃的CanalSolver
        if 'from solvers.canal_solver import CanalSolver' in content:
            content = content.replace(
                'from solvers.canal_solver import CanalSolver',
                'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver'
            )
            changes.append("CanalSolver->HydrostaticCanalSolver")
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {e}"]

def main():
    """主函数"""
    
    print("="*70)
    print("COMPREHENSIVE FIX FOR ALL PRIORITY ISSUES")
    print("="*70)
    print()
    
    # 找到所有Python文件
    all_files = []
    for path in Path('examples').rglob('*.py'):
        if path.is_file() and path.name != '__init__.py':
            all_files.append(str(path))
    
    print(f"Processing {len(all_files)} files...")
    print()
    
    # 统计
    fixed_count = 0
    issue_counts = {
        'Disabled input()': 0,
        'Fixed Unicode chars': 0,
        'SingleCanalSolver->HydrostaticCanalSolver': 0,
        'CanalSolver->HydrostaticCanalSolver': 0,
    }
    
    for i, file_path in enumerate(all_files, 1):
        success, changes = fix_file_comprehensive(file_path)
        
        if success:
            fixed_count += 1
            rel_path = os.path.relpath(file_path)
            print(f"[{i}/{len(all_files)}] {rel_path}")
            for change in changes:
                print(f"  - {change}")
                if change in issue_counts:
                    issue_counts[change] += 1
        
        # 进度提示
        if i % 50 == 0:
            print(f"\nProgress: {i}/{len(all_files)} files scanned...\n")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total files scanned: {len(all_files)}")
    print(f"Files fixed: {fixed_count}")
    print()
    print("Issues fixed:")
    total_issues = 0
    for issue, count in issue_counts.items():
        if count > 0:
            print(f"  - {issue}: {count} files")
            total_issues += count
    print()
    print(f"Total issues resolved: {total_issues}")
    print("="*70)

if __name__ == '__main__':
    main()

