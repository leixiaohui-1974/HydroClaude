#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复导入错误"""

import os
import re
from pathlib import Path
import shutil

def fix_sys_path(content, file_path):
    """添加sys.path配置"""
    
    # 检查是否已有sys.path配置
    if 'sys.path.insert' in content or 'sys.path.append' in content:
        return content, []
    
    # 检查文件位置，确定需要添加几层父目录
    file_path = Path(file_path)
    
    if 'tests' in file_path.parts:
        levels = file_path.parts.index('tests')
        parent_path = '../' * (len(file_path.parts) - levels - 1)
    elif 'examples' in file_path.parts:
        levels = file_path.parts.index('examples')
        parent_path = '../' * (len(file_path.parts) - levels - 1)
    else:
        return content, []
    
    # 查找第一个import语句
    import_match = re.search(r'^\s*(?:from|import)\s+', content, re.MULTILINE)
    if not import_match:
        return content, []
    
    # 在第一个import前插入sys.path配置
    insert_pos = import_match.start()
    
    sys_path_block = f"""import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

"""
    
    # 检查是否已有import sys
    if 'import sys' not in content[:insert_pos]:
        content = content[:insert_pos] + sys_path_block + content[insert_pos:]
        return content, ['添加sys.path配置']
    
    return content, []

def fix_deprecated_solver_imports(content):
    """修复废弃的求解器导入"""
    
    changes = []
    original = content
    
    # SingleCanalSolver -> HydrostaticCanalSolver
    if 'from solvers.single_canal_solver import SingleCanalSolver' in content:
        content = content.replace(
            'from solvers.single_canal_solver import SingleCanalSolver',
            '# from solvers.single_canal_solver import SingleCanalSolver  # 已废弃\nfrom solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver'
        )
        changes.append('SingleCanalSolver -> HydrostaticCanalSolver')
    
    # CanalSolver -> HydrostaticCanalSolver
    if 'from solvers.canal_solver import CanalSolver' in content:
        content = content.replace(
            'from solvers.canal_solver import CanalSolver',
            '# from solvers.canal_solver import CanalSolver  # 已废弃\nfrom solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver'
        )
        changes.append('CanalSolver -> HydrostaticCanalSolver')
    
    return content, changes

def fix_file(file_path):
    """修复单个文件"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        all_changes = []
        
        # 1. 修复sys.path
        content, changes = fix_sys_path(content, file_path)
        all_changes.extend(changes)
        
        # 2. 修复废弃的求解器导入
        content, changes = fix_deprecated_solver_imports(content)
        all_changes.extend(changes)
        
        if content != original:
            # 备份
            backup = Path(file_path).with_suffix('.py.bak_imports')
            if not backup.exists():
                shutil.copy2(file_path, backup)
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, all_changes
        
        return False, []
    
    except Exception as e:
        print(f"[ERROR] {Path(file_path).name}: {e}")
        return False, []

def main():
    print("="*70)
    print("批量修复导入错误")
    print("="*70)
    
    # 扫描需要修复的文件
    test_files = []
    
    for root_dir in ['tests', 'examples']:
        if Path(root_dir).exists():
            for py_file in Path(root_dir).rglob('*.py'):
                if py_file.name not in ['__init__.py', 'conftest.py']:
                    test_files.append(py_file)
    
    print(f"\n扫描到 {len(test_files)} 个文件")
    print("开始修复...\n")
    
    fixed_count = 0
    change_counter = {}
    
    for i, file_path in enumerate(test_files, 1):
        if i % 50 == 0:
            print(f"[{i}/{len(test_files)}] 已处理...")
        
        success, changes = fix_file(file_path)
        
        if success:
            fixed_count += 1
            for change in changes:
                change_counter[change] = change_counter.get(change, 0) + 1
    
    print(f"\n修复完成: {fixed_count}/{len(test_files)} 个文件")
    
    if change_counter:
        print(f"\n修改统计:")
        for change, count in sorted(change_counter.items(), key=lambda x: -x[1]):
            print(f"  {change}: {count} 次")
    
    print("\n" + "="*70)
    print("预期效果:")
    print("  - 减少ModuleNotFoundError")
    print("  - 废弃求解器自动映射到HydrostaticCanalSolver")
    print("  - 提升整体通过率")
    print("="*70)

if __name__ == '__main__':
    main()

