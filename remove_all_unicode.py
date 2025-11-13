#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
彻底清除所有Unicode字符

Author: HydroClaude
Date: 2025-11-13
"""

import os

files_to_fix = [
    "physics/canal.py",
    "examples/advanced_examples/comprehensive_solver_audit.py",
    "examples/advanced_animation_generator.py",
    "examples/advanced_examples/compare_canal_solvers.py",
    "examples/advanced_examples/constrained_mpc_canal_demo.py",
]

# 完整的Unicode替换映射
unicode_map = {
    # 基础
    '\xb3': '^3', '\xb2': '^2', '\xb0': 'deg',
    # 符号
    '\u2022': '-', '\u2713': '[OK]', '\u2705': '[OK]', '\u274c': '[X]',
    '\u26a0': '[WARN]', '\u2139': '[INFO]',
    # 箭头
    '\u2192': '->', '\u2190': '<-', '\u2194': '<->',
    # Emoji
    '\U0001f4cb': '[LIST]', '\U0001f4ca': '[CHART]', '\U0001f3af': '[TARGET]',
    '\u2b50': '[STAR]', '\u2728': '[SPARK]',
    # 希伯来/其他特殊字符（直接删除）
    '\u05a7': '', '\u05f4': '', '\u0732': '', '\u02be': '', '\u0579': '',
    '\ufe0f': '',  # 变体选择器
}

print("="*70)
print("REMOVING ALL UNICODE")
print("="*70)
print()

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        print(f"[SKIP] {file_path} not found")
        continue
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        continue
    
    original = content
    
    # 应用所有替换
    for char, repl in unicode_map.items():
        content = content.replace(char, repl)
    
    # 额外：删除所有其他不可打印字符（保留常规字符）
    cleaned = ''
    for c in content:
        code = ord(c)
        # 保留：ASCII可打印、换行、制表、空格、汉字
        if (32 <= code <= 126) or code in (9, 10, 13) or (0x4e00 <= code <= 0x9fff):
            cleaned += c
    
    if cleaned != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            print(f"[OK] {file_path}")
        except Exception as e:
            print(f"[ERROR] {file_path}: {e}")
    else:
        print(f"[SKIP] {file_path} no changes")

print()
print("="*70)
print("Done")
print("="*70)

