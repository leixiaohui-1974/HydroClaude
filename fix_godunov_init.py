#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复GodunvFVMSolver的initialize_steady_state调用"""

import re
from pathlib import Path

files = [
    "examples/phase1_mega_scenarios.py",
    "examples/case_parameter_sensitivity.py",
    "examples/case_flood_control_steady.py",
    "examples/case_library/case_01_dam_break/dam_break_comparison.py",
    "examples/case_gate_operation.py",
    "examples/pressurized_examples/water_supply_network.py",
    "examples/config_driven/simulate.py",
    "examples/test_weno3_dambreak.py",
    "examples/phase1_steady_scenarios.py",
    "examples/phase1_simple_gate_control.py",
    "examples/phase1_flood_routing.py",
    "examples/phase1_extended_scenarios.py",
    "examples/case02_flood_risk_assessment.py",
]

def fix_file(filepath):
    """修复单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(filepath, 'r', encoding='gbk') as f:
            content = f.read()
    
    original = content
    
    # 模式1: solver.initialize_steady_state(h_init, Q_init, bc_left, bc_right)
    pattern1 = r'(\s+)(solver\.initialize_steady_state)\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)'
    
    def replace_func(match):
        indent = match.group(1)
        h_var = match.group(3).strip()
        Q_var = match.group(4).strip()
        bc_left_var = match.group(5).strip()
        bc_right_var = match.group(6).strip()
        
        return f'''{indent}# GodunvFVMSolver需要手动初始化
{indent}solver.h = {h_var}.copy()
{indent}solver.Q = {Q_var}.copy()
{indent}solver.bc_left = {bc_left_var}
{indent}solver.bc_right = {bc_right_var}'''
    
    content = re.sub(pattern1, replace_func, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return True
    return False

print("="*80)
print("批量修复GodunvFVMSolver初始化问题")
print("="*80)
print()

fixed_count = 0
for filepath in files:
    basename = Path(filepath).name
    print(f"{basename:50s}", end=" ", flush=True)
    
    if fix_file(filepath):
        print("[FIXED]")
        fixed_count += 1
    else:
        print("[NO_CHANGE]")

print()
print(f"修复完成: {fixed_count}/{len(files)} 个文件")

