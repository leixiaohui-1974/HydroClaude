#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动修复所有仿真案例

基于成功经验的自动化修复脚本

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
from pathlib import Path

def needs_matplotlib_agg(content):
    """检查是否需要添加matplotlib.use('Agg')"""
    has_pyplot = ('import matplotlib.pyplot' in content or 
                  'from matplotlib import pyplot' in content)
    has_agg = "matplotlib.use('Agg')" in content or 'matplotlib.use("Agg")' in content
    return has_pyplot and not has_agg

def add_matplotlib_agg(content):
    """添加matplotlib.use('Agg')"""
    # 找到第一个matplotlib相关的import
    lines = content.split('\n')
    new_lines = []
    added = False
    
    for i, line in enumerate(lines):
        if not added and 'import matplotlib' in line and 'matplotlib.use' not in line:
            # 在这一行之前插入
            if i > 0 and lines[i-1].strip() == "import matplotlib":
                # 如果前一行已经是import matplotlib，在后面插入
                new_lines.append(line)
                new_lines.append("matplotlib.use('Agg')")
                added = True
            else:
                new_lines.append("import matplotlib")
                new_lines.append("matplotlib.use('Agg')")
                if 'import matplotlib.pyplot' in line:
                    new_lines.append("import matplotlib.pyplot as plt")
                else:
                    new_lines.append(line)
                added = True
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)

def needs_sys_path(content):
    """检查是否需要添加sys.path"""
    has_sys = 'import sys' in content
    has_path = 'sys.path.insert' in content
    return has_sys and not has_path

def add_sys_path(content):
    """添加sys.path配置"""
    lines = content.split('\n')
    new_lines = []
    added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if not added and 'import sys' in line:
            # 检查下一行是否已经有os import
            next_lines = lines[i+1:i+5]
            has_os = any('import os' in l for l in next_lines)
            
            if not has_os:
                new_lines.append('import os')
            
            new_lines.append('')
            new_lines.append('# 添加项目根目录到路径')
            new_lines.append('script_path = os.path.abspath(__file__)')
            new_lines.append('project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))')
            new_lines.append('sys.path.insert(0, project_root)')
            new_lines.append('')
            added = True
    
    return '\n'.join(new_lines)

def fix_plt_show(content):
    """注释plt.show()"""
    return content.replace('plt.show()', '# plt.show()  # Disabled for automated testing')

def fix_hardcoded_paths(content):
    """修复硬编码路径"""
    content = content.replace('/home/user/HydroClaude/', '')
    content = content.replace('/home/user/HydroClaude', '')
    content = content.replace('/workspace/', '')
    return content

def auto_fix_file(file_path):
    """自动修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            return False, ["READ_ERROR"]
    
    original = content
    changes = []
    
    # 1. matplotlib.use('Agg')
    if needs_matplotlib_agg(content):
        content = add_matplotlib_agg(content)
        changes.append("matplotlib_agg")
    
    # 2. 注释plt.show()
    if 'plt.show()' in content and '# plt.show()' not in content:
        content = fix_plt_show(content)
        changes.append("plt_show")
    
    # 3. sys.path
    if needs_sys_path(content):
        content = add_sys_path(content)
        changes.append("sys_path")
    
    # 4. 硬编码路径
    if '/home/user/HydroClaude' in content or '/workspace/' in content:
        content = fix_hardcoded_paths(content)
        changes.append("paths")
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        except Exception as e:
            return False, [f"WRITE_ERROR: {str(e)[:50]}"]
    
    return False, ["NO_CHANGE"]

def find_all_simulation_files():
    """查找所有仿真文件"""
    examples_dir = Path('examples')
    
    # 排除
    exclude_patterns = [
        '**/backups/**',
        '**/*.bak*',
        '**/__pycache__/**',
        '**/output_helper.py',
    ]
    
    # 包含
    include_patterns = [
        '**/example_*.py',
        '**/demo_*.py',
        '**/case_*.py',
        '**/run_*.py',
        '**/*_v2.py',
    ]
    
    all_files = []
    for pattern in include_patterns:
        files = list(examples_dir.glob(pattern))
        all_files.extend(files)
    
    # 去重并排除
    unique_files = []
    seen = set()
    for f in all_files:
        if f.is_file() and str(f) not in seen:
            exclude = False
            for exclude_pattern in exclude_patterns:
                if f.match(exclude_pattern):
                    exclude = True
                    break
            
            if not exclude:
                seen.add(str(f))
                unique_files.append(f)
    
    return sorted(unique_files)

def main():
    """主函数"""
    
    print("="*80)
    print("自动修复所有仿真案例 - Phase 1")
    print("="*80)
    print()
    
    # 查找文件
    print("正在搜索文件...")
    files = find_all_simulation_files()
    print(f"找到 {len(files)} 个文件")
    print()
    
    # 修复文件
    print("开始修复...")
    print("-"*80)
    
    fixed_count = 0
    change_stats = {}
    
    for i, file_path in enumerate(files, 1):
        rel_path = file_path.relative_to('examples')
        basename = file_path.name
        
        print(f"[{i:3d}/{len(files)}] {str(rel_path):60s}", end=" ", flush=True)
        
        fixed, changes = auto_fix_file(file_path)
        
        if fixed:
            fixed_count += 1
            changes_str = ', '.join(changes)
            print(f"[FIXED: {changes_str}]")
            
            for change in changes:
                change_stats[change] = change_stats.get(change, 0) + 1
        else:
            if changes[0] == "NO_CHANGE":
                print("[OK]")
            else:
                print(f"[{changes[0]}]")
    
    print()
    print("="*80)
    print("修复完成")
    print("="*80)
    print(f"\n修复文件数: {fixed_count}/{len(files)}")
    
    if change_stats:
        print(f"\n修复类型统计:")
        for change_type, count in sorted(change_stats.items(), key=lambda x: -x[1]):
            print(f"  {change_type:20s}: {count:3d}")
    
    print(f"\n下一步: python test_all_simulations.py")

if __name__ == '__main__':
    main()

