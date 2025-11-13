#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""彻底修复所有Unicode编码问题"""

import os
import re
from pathlib import Path
import shutil

def fix_file_thoroughly(file_path):
    """彻底修复文件中的Unicode问题"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替换所有常见的Unicode符号
        replacements = {
            # 上标/下标
            '\xb2': '^2',  # ²
            '\xb3': '^3',  # ³
            '\xb9': '^1',  # ¹
            # 特殊符号
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
            '\u00b0': ' deg',      # °
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # 还原被错误转换的[U+XXXX]格式（只在字符串中）
        # 这个模式匹配 print(...[U+XXXX]...) 并尝试还原
        def restore_chinese_in_strings(match):
            """尝试还原字符串中的中文"""
            string_content = match.group(1)
            # 替换 [U+XXXX] 为对应的中文字符
            def hex_to_char(m):
                try:
                    code = int(m.group(1), 16)
                    # 如果是中文范围，还原；否则保持
                    if 0x4E00 <= code <= 0x9FFF:  # 中文范围
                        return chr(code)
                    else:
                        return m.group(0)  # 保持原样
                except:
                    return m.group(0)
            
            string_content = re.sub(r'\[U\+([0-9A-F]{4})\]', hex_to_char, string_content)
            return f'"{string_content}"'
        
        # 在双引号字符串中还原
        content = re.sub(r'"([^"]*\[U\+[0-9A-F]{4}\][^"]*)"', restore_chinese_in_strings, content)
        # 在f-string中还原
        content = re.sub(r'f"([^"]*\[U\+[0-9A-F]{4}\][^"]*)"', lambda m: f'f"{restore_chinese_in_strings(m).strip(chr(34))}"', content)
        
        if content != original_content:
            # 备份
            backup_path = Path(file_path).with_suffix('.py.bak_unicode_thorough')
            if not backup_path.exists():
                shutil.copy2(file_path, backup_path)
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        return False
    
    except Exception as e:
        print(f"[ERROR] {Path(file_path).name}: {e}")
        return False

def main():
    print("="*70)
    print("彻底修复Unicode编码问题")
    print("="*70)
    
    # 核心测试文件
    core_files = [
        'tests/core_functionality_verification_v2.py',
        'tests/test_lake_at_rest_wb.py',
        'examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py',
        'examples/example_01_canal_flow/scripts/01_basic_v2.py',
        'examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py',
    ]
    
    fixed_count = 0
    
    print(f"\n处理 {len(core_files)} 个核心文件...")
    
    for file_path in core_files:
        if not Path(file_path).exists():
            print(f"[SKIP] {file_path}")
            continue
        
        print(f"修复: {Path(file_path).name}...", end=' ')
        
        if fix_file_thoroughly(file_path):
            print("[OK]")
            fixed_count += 1
        else:
            print("[SKIP]")
    
    print(f"\n修复完成: {fixed_count} 个文件")
    print("="*70)

if __name__ == '__main__':
    main()

