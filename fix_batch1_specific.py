#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
针对性修复Batch 1的具体问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

fixes = {
    # 问题1: plt未定义 - 需要添加import matplotlib.pyplot as plt
    'plt_undefined': [
        'examples/case_irrigation_scheduling.py',
        'examples/case_library/case_01_hydropower_plant.py',
        'examples/case_library/case_02_water_supply_network.py',
        'examples/case_library/case_03_irrigation_canal.py',
    ],
    
    # 问题2: physics.canal的ValueError - 可能需要改为HydrostaticCanalSolver
    'physics_canal_error': [
        'examples/advanced_examples/compare_canal_solvers.py',
        'examples/advanced_examples/debug_saint_venant.py',
        'examples/advanced_examples/diagnose_canal_boundary.py',
    ],
    
    # 问题3: HydrostaticCanalSolver没有initialize方法
    'no_initialize': [
        'examples/case_gate_operation.py',
    ],
}

def fix_plt_undefined(file_path):
    """修复plt未定义问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已有import
        if 'import matplotlib.pyplot as plt' in content:
            return False, "Already has plt import"
        
        # 在import section添加
        lines = content.split('\n')
        import_idx = -1
        
        # 找到最后一个import语句的位置
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_idx = i
        
        if import_idx >= 0:
            # 在最后一个import后添加
            lines.insert(import_idx + 1, 'import matplotlib.pyplot as plt')
            content = '\n'.join(lines)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Added plt import"
        
        return False, "Could not find import section"
        
    except Exception as e:
        return False, f"Error: {e}"

def fix_no_initialize(file_path):
    """修复initialize方法问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换 .initialize( 为 .initialize_steady_state(
        if '.initialize(' in content:
            content = content.replace('.initialize(', '.initialize_steady_state(')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed initialize method"
        
        return False, "No initialize call found"
        
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """主函数"""
    
    print("="*70)
    print("FIXING BATCH 1 SPECIFIC ISSUES")
    print("="*70)
    print()
    
    # 修复plt未定义
    print("1. Fixing 'plt' not defined (4 files):")
    for file_path in fixes['plt_undefined']:
        if os.path.exists(file_path):
            success, msg = fix_plt_undefined(file_path)
            basename = os.path.basename(file_path)
            print(f"  {basename}: {msg}")
        else:
            print(f"  {os.path.basename(file_path)}: File not found")
    
    print()
    
    # 修复initialize问题
    print("2. Fixing 'initialize' method (1 file):")
    for file_path in fixes['no_initialize']:
        if os.path.exists(file_path):
            success, msg = fix_no_initialize(file_path)
            basename = os.path.basename(file_path)
            print(f"  {basename}: {msg}")
        else:
            print(f"  {os.path.basename(file_path)}: File not found")
    
    print()
    
    # physics.canal问题需要更仔细地分析，先跳过
    print("3. physics.canal ValueError issues (3 files):")
    print("  These files use physics.canal which may need manual review")
    print("  - compare_canal_solvers.py")
    print("  - debug_saint_venant.py")
    print("  - diagnose_canal_boundary.py")
    
    print()
    print("="*70)
    print("DONE")
    print("="*70)

if __name__ == '__main__':
    main()

