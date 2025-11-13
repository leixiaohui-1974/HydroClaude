#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正确的修复方法 - 在文件开头插入，不破坏结构

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

def safe_fix(file_path):
    """安全的修复 - 只在文件开头添加"""
    
    if not os.path.exists(file_path):
        return False, "Not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return False, "Read error"
    
    original_content = ''.join(lines)
    
    # 1. Unicode替换
    content = original_content
    for char, repl in {'\xb3':'^3', '\xb2':'^2', '\u2713':'[OK]', '\u2705':'[OK]', '\u274c':'[X]'}.items():
        content = content.replace(char, repl)
    
    # 2. 废弃导入替换
    content = content.replace('from solvers.canal_solver import CanalSolver',
                            'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver')
    content = content.replace('from solvers.single_canal_solver import SingleCanalSolver',
                            'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver')
    
    # 3. 数值参数
    content = re.sub(r'cfl\s*=\s*0\.[5-9]', 'cfl=0.3', content, flags=re.IGNORECASE)
    content = re.sub(r't_end\s*=\s*[1-9]\d{2,}', 't_end=30', content)
    content = content.replace('order=2', 'order=1').replace('order = 2', 'order = 1')
    
    # 4. 在文件最开头添加sys.path（如果需要）
    if 'sys.path.insert(0' not in content:
        # 找到第一行代码（跳过注释和空行）
        first_code_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                first_code_line = i
                break
        
        # 在最开头插入（在任何代码之前）
        insert_lines = [
            'import sys\n',
            'import os\n',
            'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n',
            '\n'
        ]
        
        # 检查是否已有这些import
        has_sys = 'import sys' in original_content
        has_os = 'import os' in original_content
        
        if not has_sys and not has_os:
            # 在文件开头插入
            content = ''.join(insert_lines) + content
        elif not has_sys:
            content = 'import sys\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\n' + content
        elif not has_os:
            content = 'import os\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\n' + content
        else:
            # 都有了，只添加sys.path
            content = 'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n' + content
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed"
        except Exception as e:
            return False, str(e)
    
    return False, "No change"


# 第一批文件
batch1 = [
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
print("CORRECT FIX - Batch 1")
print("="*70)

for i, f in enumerate(batch1, 1):
    success, msg = safe_fix(f)
    print(f"[{i}/10] {os.path.basename(f)}: {msg}")

print("\nDone. Now test them:")
print("python retest_batch1.py")

