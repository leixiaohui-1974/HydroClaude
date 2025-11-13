#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动修复第一批失败的文件

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

def aggressive_fix(file_path):
    """更激进的修复"""
    
    if not os.path.exists(file_path):
        return False, "File not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Read error: {e}"
    
    original = content
    changes = []
    
    # 1. Unicode
    for char, repl in {'\xb3':'^3', '\xb2':'^2', '\xb0':'deg', '\u2713':'[OK]', '\u2705':'[OK]', '\u274c':'[X]'}.items():
        if char in content:
            content = content.replace(char, repl)
            changes.append(f"Unicode:{char}")
    
    # 2. 强制添加sys.path（即使已经有import sys）
    if 'sys.path.insert(0, project_root)' not in content:
        # 找到第一个非注释的import行
        lines = content.split('\n')
        insert_pos = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith('import ') or stripped.startswith('from ')) and not stripped.startswith('#'):
                insert_pos = i
                break
        
        if insert_pos >= 0:
            # 添加sys和os（如果没有）
            if 'import sys' not in content:
                lines.insert(insert_pos, 'import sys')
                insert_pos += 1
            if 'import os' not in content:
                lines.insert(insert_pos, 'import os')
                insert_pos += 1
            
            # 添加路径配置
            lines.insert(insert_pos + 1, '')
            lines.insert(insert_pos + 2, '# === Path Setup ===')
            lines.insert(insert_pos + 3, 'script_path = os.path.abspath(__file__)')
            lines.insert(insert_pos + 4, 'project_root = os.path.dirname(os.path.dirname(script_path))')
            lines.insert(insert_pos + 5, 'sys.path.insert(0, project_root)')
            lines.insert(insert_pos + 6, '')
            
            content = '\n'.join(lines)
            changes.append("sys.path")
    
    # 3. 废弃导入
    old_imports = [
        ('from solvers.canal_solver import CanalSolver', 'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver'),
        ('from solvers.single_canal_solver import SingleCanalSolver', 'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver'),
        ('from physics import', 'from solvers import'),
        ('import physics', 'import solvers'),
    ]
    
    for old, new in old_imports:
        if old in content:
            content = content.replace(old, new)
            changes.append(f"Import:{old[:20]}")
    
    # 4. 数值参数
    if 'cfl' in content.lower():
        content = re.sub(r'cfl\s*=\s*0\.[5-9]\d*', 'cfl = 0.3', content, flags=re.IGNORECASE)
        changes.append("CFL")
    
    if 't_end' in content:
        content = re.sub(r't_end\s*=\s*[1-9]\d{2,}\.?\d*', 't_end = 30.0', content)
        content = re.sub(r't_end\s*=\s*[5-9]\d\.?\d*', 't_end = 30.0', content)
        changes.append("t_end")
    
    if 'order' in content:
        content = content.replace('order=2', 'order=1').replace('order = 2', 'order = 1')
        changes.append("order")
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"Fixed: {', '.join(changes)}"
        except Exception as e:
            return False, f"Write error: {e}"
    
    return False, "No changes needed"


def main():
    """手动修复第一批"""
    
    batch1_files = [
        "examples/advanced_animation_generator.py",
        "examples/advanced_examples/adaptive_first_order_mpc_test.py",
        "examples/advanced_examples/benchmark_controllers.py",
        "examples/advanced_examples/compare_canal_solvers.py",
        "examples/advanced_examples/complete_benchmark_suite.py",
        "examples/advanced_examples/comprehensive_solver_audit.py",
        "examples/advanced_examples/constrained_mpc_canal_demo.py",
        "examples/advanced_examples/debug_mpc_observer.py",
        "examples/advanced_examples/debug_saint_venant.py",
        "examples/advanced_examples/diagnose_canal_boundary.py",
    ]
    
    print("="*70)
    print("MANUALLY FIXING BATCH 1")
    print("="*70)
    print()
    
    fixed = 0
    
    for i, file_path in enumerate(batch1_files, 1):
        print(f"[{i}/10] {os.path.basename(file_path)}...", end=' ')
        
        success, message = aggressive_fix(file_path)
        
        if success:
            print(f"[FIXED] {message}")
            fixed += 1
        else:
            print(f"[SKIP] {message}")
    
    print()
    print(f"Fixed {fixed}/10 files")
    print()
    print("="*70)


if __name__ == '__main__':
    main()

