#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复Batch 1剩余问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

# 需要修复的文件及其问题
issues = {
    # 问题1: GodunvFVMSolver没有initialize_steady_state方法
    'godunov_init': [
        'examples/case_irrigation_scheduling.py',
        'examples/case_library/case_02_flood_routing/flood_routing_simulation.py',
    ],
    
    # 问题2: HydrostaticCanalSolver.initialize_ste (应该完整删除或改为其他初始化方法)
    'hydrostatic_init': [
        'examples/case_gate_operation.py',
    ],
    
    # 问题3: GodunovFVMWENO3拼写错误
    'godunov_typo': [
        'examples/case_library/case_01_dam_break/dam_break_comparison.py',
    ],
}

def fix_godunov_init(file_path):
    """修复Godunov求解器的初始化问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # GodunvFVMSolver通常不需要initialize_steady_state
        # 可以直接删除这个调用或注释掉
        if '.initialize_steady_state(' in content:
            # 注释掉这行
            content = re.sub(
                r'(\s+)(\w+\.initialize_steady_state\([^)]*\))',
                r'\1# \2  # Not needed for Godunov solver',
                content
            )
            changes.append("Commented out initialize_steady_state")
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {e}"]

def fix_hydrostatic_init(file_path):
    """修复HydrostaticCanalSolver的初始化问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 检查是否有.initialize_steady_state的调用
        # 可能被截断了或有拼写错误
        if '.initialize_ste' in content or '.initialize_steady_state(' in content:
            # 注释掉所有initialize相关调用
            content = re.sub(
                r'(\s+)(\w+\.initialize[^(]*\([^)]*\))',
                r'\1# \2  # Manual initialization preferred',
                content
            )
            changes.append("Commented out initialize calls")
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {e}"]

def fix_godunov_typo(file_path):
    """修复GodunovFVMWENO3拼写错误 (已经修复过了，再检查一遍)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 检查模块名拼写
        if 'from solvers.godunov_fvm_solve import' in content:
            # 应该是godunov_fvm_solver (多了r)
            content = content.replace(
                'from solvers.godunov_fvm_solve import',
                'from solvers.godunov_fvm_solver import'
            )
            changes.append("Fixed module name: godunov_fvm_solve -> godunov_fvm_solver")
        
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
    print("FIXING REMAINING BATCH 1 ISSUES")
    print("="*70)
    print()
    
    fixed_count = 0
    
    # 修复Godunov初始化问题
    print("1. Fixing Godunov initialization (2 files):")
    for file_path in issues['godunov_init']:
        if os.path.exists(file_path):
            success, changes = fix_godunov_init(file_path)
            basename = os.path.basename(file_path)
            if success:
                print(f"   {basename}: {', '.join(changes)}")
                fixed_count += 1
            else:
                print(f"   {basename}: No changes needed")
        else:
            print(f"   {os.path.basename(file_path)}: Not found")
    
    print()
    
    # 修复Hydrostatic初始化问题
    print("2. Fixing Hydrostatic initialization (1 file):")
    for file_path in issues['hydrostatic_init']:
        if os.path.exists(file_path):
            success, changes = fix_hydrostatic_init(file_path)
            basename = os.path.basename(file_path)
            if success:
                print(f"   {basename}: {', '.join(changes)}")
                fixed_count += 1
            else:
                print(f"   {basename}: No changes needed")
        else:
            print(f"   {os.path.basename(file_path)}: Not found")
    
    print()
    
    # 修复Godunov拼写错误
    print("3. Fixing Godunov typo (1 file):")
    for file_path in issues['godunov_typo']:
        if os.path.exists(file_path):
            success, changes = fix_godunov_typo(file_path)
            basename = os.path.basename(file_path)
            if success:
                print(f"   {basename}: {', '.join(changes)}")
                fixed_count += 1
            else:
                print(f"   {basename}: No changes needed")
        else:
            print(f"   {os.path.basename(file_path)}: Not found")
    
    print()
    print("="*70)
    print(f"Fixed {fixed_count} files")
    print("="*70)

if __name__ == '__main__':
    main()

