#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局修复所有测试案例的常见问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
from pathlib import Path

def fix_file(file_path):
    """修复单个文件的常见问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 问题1: 错误的 solvers.canal 导入 -> 改回 physics.canal
        if 'from solvers.canal' in content or 'import solvers.canal' in content:
            content = content.replace('from solvers.canal', 'from physics.canal')
            content = content.replace('import solvers.canal', 'import physics.canal')
            changes.append("solvers.canal->physics.canal")
        
        # 问题2: plt.show() 导致timeout -> 添加 matplotlib.use('Agg')
        if 'plt.show()' in content and 'matplotlib.use' not in content:
            # 在import matplotlib后添加use('Agg')
            if 'import matplotlib.pyplot' in content:
                # 找到第一个import matplotlib的位置
                lines = content.split('\n')
                new_lines = []
                added = False
                
                for line in lines:
                    new_lines.append(line)
                    if not added and 'import matplotlib.pyplot' in line:
                        # 在这行后面添加use('Agg')
                        indent = len(line) - len(line.lstrip())
                        new_lines.insert(-1, ' ' * indent + 'import matplotlib')
                        new_lines.append(' ' * indent + 'matplotlib.use(\'Agg\')')
                        added = True
                
                if added:
                    content = '\n'.join(new_lines)
                    changes.append("Added matplotlib.use('Agg')")
            
            # 替换 plt.show() 为 plt.savefig()
            # 找到所有plt.show()并替换
            if 'plt.show()' in content:
                # 简单策略：注释掉plt.show()
                content = content.replace('plt.show()', '# plt.show()  # Disabled for automated testing')
                changes.append("Disabled plt.show()")
        
        # 问题3: 缺少sys.path设置（某些文件可能需要）
        # 先不修改，因为可能破坏代码结构
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {e}"]

def find_all_python_files(root_dir='examples'):
    """找到所有Python测试文件"""
    python_files = []
    for path in Path(root_dir).rglob('*.py'):
        if path.is_file():
            # 排除__init__.py等
            if path.name != '__init__.py':
                python_files.append(str(path))
    return python_files

def main():
    """主函数"""
    
    print("="*70)
    print("GLOBAL FIX FOR ALL TEST CASES")
    print("="*70)
    print()
    
    # 找到所有Python文件
    all_files = find_all_python_files('examples')
    print(f"Found {len(all_files)} Python files in examples/")
    print()
    
    # 统计
    fixed_count = 0
    issue_counts = {
        'solvers.canal->physics.canal': 0,
        'Added matplotlib.use(\'Agg\')': 0,
        'Disabled plt.show()': 0,
    }
    
    print("Fixing files...")
    for i, file_path in enumerate(all_files, 1):
        success, changes = fix_file(file_path)
        
        if success:
            fixed_count += 1
            rel_path = os.path.relpath(file_path)
            print(f"[{i}/{len(all_files)}] {rel_path}")
            for change in changes:
                print(f"  - {change}")
                if change in issue_counts:
                    issue_counts[change] += 1
        
        # 每100个文件打印进度
        if i % 100 == 0:
            print(f"Progress: {i}/{len(all_files)} files scanned...")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total files scanned: {len(all_files)}")
    print(f"Files fixed: {fixed_count}")
    print()
    print("Issues fixed:")
    for issue, count in issue_counts.items():
        if count > 0:
            print(f"  - {issue}: {count} files")
    print("="*70)

if __name__ == '__main__':
    main()

