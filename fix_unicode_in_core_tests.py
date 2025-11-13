#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复核心测试文件中的Unicode字符"""

import os
import re
from pathlib import Path
import shutil

# Unicode字符替换表
UNICODE_REPLACEMENTS = {
    '\u2713': '[OK]',      # ✓
    '\u2714': '[OK]',  
    '\u2705': '[OK]',      # ✅
    '\u274c': '[FAIL]',    # ❌
    '\u2717': '[FAIL]',    # ✗
    '\u26a0': '[WARN]',    # ⚠
    '\u26a0\ufe0f': '[WARN]',
    '\u2139': '[INFO]',    # ℹ
    '\u2139\ufe0f': '[INFO]',
    '\U0001f4ca': '[CHART]',  # 📊
    '\U0001f3af': '[TARGET]', # 🎯
    '\u2192': '->',        # →
    '\u2190': '<-',        # ←
    '\u2022': '-',         # •
    '\u00d7': 'x',         # ×
    '\u00b1': '+/-',       # ±
    '\u2248': '~=',        # ≈
    '\u2264': '<=',        # ≤
    '\u2265': '>=',        # >=
}

def fix_unicode_in_file(file_path):
    """修复单个文件中的Unicode字符"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替换已知的Unicode字符
        for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
            content = content.replace(unicode_char, replacement)
        
        # 查找并替换其他可能有问题的Unicode字符（U+0100以上的字符）
        def replace_high_unicode(match):
            char = match.group(0)
            code = ord(char)
            if code > 0x00FF:  # 非ASCII/扩展ASCII
                return f"[U+{code:04X}]"
            return char
        
        # 在字符串中查找高Unicode字符
        content = re.sub(r'[^\x00-\x7F\u00A0-\u00FF]', replace_high_unicode, content)
        
        if content != original_content:
            # 备份原文件
            backup_path = Path(file_path).with_suffix('.py.bak_unicode')
            if not backup_path.exists():
                shutil.copy2(file_path, backup_path)
            
            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        return False
    
    except Exception as e:
        print(f"[ERROR] {Path(file_path).name}: {e}")
        return False

def main():
    print("="*70)
    print("修复核心测试文件的Unicode编码问题")
    print("="*70)
    
    # 核心测试文件列表
    core_files = [
        'tests/core_functionality_verification_v2.py',
        'tests/test_lake_at_rest_wb.py',
        'examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py',
        'examples/example_01_canal_flow/scripts/01_basic_v2.py',
        'examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py',
    ]
    
    fixed_count = 0
    
    print(f"\n处理 {len(core_files)} 个核心测试文件...")
    
    for file_path in core_files:
        if not Path(file_path).exists():
            print(f"[SKIP] {file_path} (不存在)")
            continue
        
        print(f"处理: {Path(file_path).name}...", end=' ')
        
        if fix_unicode_in_file(file_path):
            print("[OK] 已修复")
            fixed_count += 1
        else:
            print("[SKIP] 无需修改")
    
    print(f"\n修复完成: {fixed_count} 个文件")
    print("\n" + "="*70)
    
    return 0

if __name__ == '__main__':
    exit(main())

