#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复所有测试文件的Unicode问题"""

import os
import re
from pathlib import Path
import shutil

def fix_unicode_thoroughly(content):
    """彻底修复Unicode字符"""
    
    # 上标/下标
    content = content.replace('\xb2', '^2')
    content = content.replace('\xb3', '^3')
    content = content.replace('\xb9', '^1')
    content = content.replace('\xb0', ' deg')
    content = content.replace('\xb6', '[PARA]')
    
    # 特殊符号
    replacements = {
        '\u2713': '[OK]', '\u2714': '[OK]', '\u2705': '[OK]',
        '\u274c': '[FAIL]', '\u2717': '[FAIL]',
        '\u26a0': '[WARN]', '\u26a0\ufe0f': '[WARN]',
        '\u2139': '[INFO]', '\u2139\ufe0f': '[INFO]',
        '\U0001f4ca': '[CHART]', '\U0001f3af': '[TARGET]',
        '\u2192': '->', '\u2190': '<-',
        '\u2022': '-', '\u00d7': 'x',
        '\u00b1': '+/-', '\u2248': '~=',
        '\u2264': '<=', '\u2265': '>=',
        '\u2030': '[permille]',  # ‰
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 还原被转换的中文[U+XXXX]
    def restore_chinese(match):
        try:
            code = int(match.group(1), 16)
            if 0x4E00 <= code <= 0x9FFF:  # 中文范围
                return chr(code)
            else:
                return f'[U+{code:04X}]'  # 保留非中文
        except:
            return match.group(0)
    
    content = re.sub(r'\[U\+([0-9A-F]{4})\]', restore_chinese, content)
    
    return content

def fix_file(file_path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = fix_unicode_thoroughly(content)
        
        if content != original:
            backup = Path(file_path).with_suffix('.py.bak_unicode_batch')
            if not backup.exists():
                shutil.copy2(file_path, backup)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        return False
    except Exception as e:
        print(f"[ERROR] {Path(file_path).name}: {e}")
        return False

def main():
    print("="*70)
    print("批量修复所有测试文件的Unicode问题")
    print("="*70)
    
    # 扫描所有Python文件
    test_files = []
    
    for root_dir in ['tests', 'examples']:
        if Path(root_dir).exists():
            for py_file in Path(root_dir).rglob('*.py'):
                if py_file.name not in ['__init__.py', 'conftest.py']:
                    test_files.append(py_file)
    
    print(f"\n找到 {len(test_files)} 个Python文件")
    print("开始修复...\n")
    
    fixed_count = 0
    
    for i, file_path in enumerate(test_files, 1):
        if i % 50 == 0:
            print(f"[{i}/{len(test_files)}] 已处理...")
        
        if fix_file(file_path):
            fixed_count += 1
    
    print(f"\n修复完成: {fixed_count}/{len(test_files)} 个文件")
    print("="*70)

if __name__ == '__main__':
    main()

