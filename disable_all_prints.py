#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
禁用所有Python文件中的print语句
用于解决Windows编码问题
"""

import os
import re

TARGET_FILES = [
    'solvers/godunov_fvm_solver.py',
    'web/backend/core/hydraulic_engine.py',
]

def disable_prints_in_file(filepath):
    """在文件中注释掉所有print语句"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 匹配print语句（不包括已经被注释的）
        # 简单的替换：在行首添加#
        lines = content.split('\n')
        modified_lines = []
        count = 0
        
        for line in lines:
            stripped = line.lstrip()
            # 如果行中有print且不是注释
            if 'print(' in line and not stripped.startswith('#'):
                # 计算缩进
                indent = len(line) - len(stripped)
                # 添加注释
                modified_lines.append(' ' * indent + '# ' + stripped + '  # Auto-disabled for Windows compatibility')
                count += 1
            else:
                modified_lines.append(line)
        
        new_content = '\n'.join(modified_lines)
        
        if count > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[OK] {filepath}: Disabled {count} print statements")
            return count
        else:
            print(f"[--] {filepath}: No print statements found")
            return 0
            
    except Exception as e:
        print(f"[!] Error processing {filepath}: {e}")
        return 0

def main():
    print("="*60)
    print(" Disable All Print Statements")
    print("="*60)
    
    total_disabled = 0
    
    for filepath in TARGET_FILES:
        if os.path.exists(filepath):
            count = disable_prints_in_file(filepath)
            total_disabled += count
        else:
            print(f"[!] File not found: {filepath}")
    
    print("="*60)
    print(f" Total print statements disabled: {total_disabled}")
    print("="*60)

if __name__ == "__main__":
    main()






