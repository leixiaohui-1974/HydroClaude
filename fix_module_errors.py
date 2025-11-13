#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复MODULE_NOT_FOUND错误

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

# 需要修复的文件（MODULE_NOT_FOUND）
files_to_fix = [
    'examples/advanced_examples/compare_canal_solvers.py',
    'examples/advanced_examples/debug_saint_venant.py',
    'examples/advanced_examples/diagnose_canal_boundary.py',
    'examples/advanced_examples/optimize_preissmann.py',
]

def fix_imports(file_path):
    """修复导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 1. 将错误的solvers.canal改回physics.canal
        if 'from solvers.canal' in content:
            content = content.replace('from solvers.canal', 'from physics.canal')
            changes.append("Reverted solvers.canal to physics.canal")
        
        if 'import solvers.canal' in content:
            content = content.replace('import solvers.canal', 'import physics.canal')
            changes.append("Reverted import solvers.canal")
        
        # 2. 或者，如果要使用HydrostaticCanalSolver，完全替换
        # （但先保持physics.canal，因为这些是旧代码）
        
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
    print("FIXING MODULE_NOT_FOUND ERRORS")
    print("="*70)
    print()
    
    fixed = 0
    
    for file_path in files_to_fix:
        basename = os.path.basename(file_path)
        print(f"{basename}")
        
        if not os.path.exists(file_path):
            print(f"  -> File not found!")
            continue
        
        success, changes = fix_imports(file_path)
        
        if success:
            print(f"  -> Fixed: {', '.join(changes)}")
            fixed += 1
        else:
            if changes:
                print(f"  -> {changes[0]}")
            else:
                print(f"  -> No changes needed")
    
    print()
    print("="*70)
    print(f"Fixed {fixed}/{len(files_to_fix)} files")
    print("="*70)

if __name__ == '__main__':
    main()

