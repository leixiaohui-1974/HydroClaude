#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复剩余的导入错误

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

def fix_imports_in_file(file_path):
    """修复单个文件中的导入问题"""
    
    if not os.path.exists(file_path):
        return False, "File not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Read error: {e}"
    
    original = content
    changes = []
    
    # 1. 添加sys.path配置（如果还没有）
    if 'sys.path.insert' not in content and 'import sys' in content:
        # 找到import sys的位置
        lines = content.split('\n')
        insert_pos = -1
        for i, line in enumerate(lines):
            if re.match(r'^import sys\s*$', line.strip()) or re.match(r'^import sys,', line.strip()):
                insert_pos = i + 1
                break
        
        if insert_pos > 0:
            # 插入sys.path配置
            path_setup = [
                '',
                '# Add project root to path',
                'script_path = os.path.abspath(__file__)',
                'project_root = os.path.dirname(os.path.dirname(script_path))',
                'if project_root not in sys.path:',
                '    sys.path.insert(0, project_root)',
                ''
            ]
            
            # 确保有import os
            if 'import os' not in content:
                lines.insert(insert_pos, 'import os')
                insert_pos += 1
            
            for line in reversed(path_setup):
                lines.insert(insert_pos, line)
            
            content = '\n'.join(lines)
            changes.append("Added sys.path configuration")
    
    # 2. 替换废弃的导入
    replacements = {
        'from solvers.canal_solver import CanalSolver': 
            'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver',
        'from solvers.single_canal_solver import SingleCanalSolver':
            'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver',
        'from solvers.godunov_fvm_weno3 import':
            'from solvers.godunov_fvm_solver import',
    }
    
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            changes.append(f"Replaced deprecated import: {old.split()[1]}")
    
    # 3. 修复常见的导入错误
    # physics -> solvers
    if "from physics import" in content or "import physics" in content:
        content = content.replace("from physics import", "from solvers import")
        content = content.replace("import physics", "import solvers")
        changes.append("Fixed: physics -> solvers")
    
    # solvers.canal_solver -> solvers.hydrostatic_canal_solver
    if "solvers.canal_solver" in content:
        content = content.replace("solvers.canal_solver", "solvers.hydrostatic_canal_solver")
        changes.append("Fixed: solvers.canal_solver path")
    
    # 4. 修复缺少import sys, os的情况
    if 'sys.path' in content and 'import sys' not in content:
        # 在文件开头添加import sys
        lines = content.split('\n')
        # 找到第一个import语句的位置
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_pos = i
                break
        lines.insert(insert_pos, 'import sys')
        content = '\n'.join(lines)
        changes.append("Added 'import sys'")
    
    if 'os.path' in content or 'os.getcwd' in content or '__file__' in content:
        if 'import os' not in content:
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_pos = i
                    break
            lines.insert(insert_pos, 'import os')
            content = '\n'.join(lines)
            changes.append("Added 'import os'")
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"Fixed: {len(changes)} changes"
        except Exception as e:
            return False, f"Write error: {e}"
    
    return False, "No changes needed"


def main():
    """批量修复导入错误"""
    
    print("=" * 70)
    print(" " * 15 + "FIX REMAINING IMPORT ERRORS")
    print("=" * 70)
    print()
    
    # 读取文件列表
    file_list = 'test_results/files_module_errors.txt'
    
    if not os.path.exists(file_list):
        print(f"[ERROR] {file_list} not found!")
        return
    
    with open(file_list, 'r', encoding='utf-8') as f:
        files = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(files)} files with module errors")
    print()
    
    fixed = 0
    skipped = 0
    errors = 0
    
    for i, file_path in enumerate(files, 1):
        success, message = fix_imports_in_file(file_path)
        
        if success:
            print(f"[{i}/{len(files)}] FIXED: {file_path}")
            fixed += 1
        elif "not found" in message:
            print(f"[{i}/{len(files)}] SKIP: {file_path} (not found)")
            skipped += 1
        elif "No changes" in message:
            skipped += 1
        else:
            print(f"[{i}/{len(files)}] ERROR: {file_path} - {message}")
            errors += 1
    
    print()
    print("=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    print(f"Total files: {len(files)}")
    print(f"Fixed: {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

