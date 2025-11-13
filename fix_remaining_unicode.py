#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复剩余的Unicode错误

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

def fix_unicode_in_file(file_path):
    """修复单个文件中的Unicode字符"""
    
    if not os.path.exists(file_path):
        return False, "File not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Read error: {e}"
    
    original = content
    changes = []
    
    # 扩展的Unicode字符替换表
    replacements = {
        # 已有的
        '\u2022': '-',
        '\u2713': '[OK]',
        '\u2705': '[OK]',
        '\u274c': '[FAIL]',
        '\u26a0\ufe0f': '[WARN]',
        '\u26a0': '[WARN]',
        '\u2139\ufe0f': '[INFO]',
        '\u2139': '[INFO]',
        '\U0001f4ca': '[CHART]',
        '\U0001f3af': '[TARGET]',
        '\xb3': '^3',
        '\xb2': '^2',
        '\xb0': ' deg',
        '\u0732': '',
        '\u05f4': '',
        '\u02be': '',
        '\u0579': '',
        # 新增常见的
        '\u2192': '->',
        '\u2190': '<-',
        '\u2194': '<->',
        '\u2260': '!=',
        '\u2264': '<=',
        '\u2265': '>=',
        '\u00d7': 'x',
        '\u00f7': '/',
        '\u221a': 'sqrt',
        '\u03c0': 'pi',
        '\u0394': 'Delta',
        '\u03b1': 'alpha',
        '\u03b2': 'beta',
        '\u03b3': 'gamma',
        '\u03b8': 'theta',
        '\u03bb': 'lambda',
        '\u03bc': 'mu',
        '\u03c1': 'rho',
        '\u03c3': 'sigma',
        '\u03c4': 'tau',
        '\u2208': 'in',
        '\u2211': 'sum',
        '\u221e': 'inf',
        '\ufe0f': '',  # 变体选择器
    }
    
    for char, replacement in replacements.items():
        if char in content:
            content = content.replace(char, replacement)
            changes.append(f"Replaced '{char}' with '{replacement}'")
    
    # 移除其他不可打印字符（保留常规空白）
    content_clean = ''
    for char in content:
        code = ord(char)
        # 保留：ASCII可打印字符、常规空白（换行、制表、空格）、汉字范围
        if (32 <= code <= 126) or code in (9, 10, 13) or (0x4e00 <= code <= 0x9fff):
            content_clean += char
        elif code > 127:  # 其他Unicode字符转为?或删除
            changes.append(f"Removed char U+{code:04X}")
    
    content = content_clean
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"Fixed: {len(changes)} changes"
        except Exception as e:
            return False, f"Write error: {e}"
    
    return False, "No changes needed"


def main():
    """批量修复Unicode错误"""
    
    print("=" * 70)
    print(" " * 15 + "FIX REMAINING UNICODE ERRORS")
    print("=" * 70)
    print()
    
    # 读取文件列表
    file_list = 'test_results/files_unicode_errors.txt'
    
    if not os.path.exists(file_list):
        print(f"[ERROR] {file_list} not found!")
        print("Run extract_errors_from_json.py first")
        return
    
    with open(file_list, 'r', encoding='utf-8') as f:
        files = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(files)} files with Unicode errors")
    print()
    
    fixed = 0
    skipped = 0
    errors = 0
    
    for i, file_path in enumerate(files, 1):
        success, message = fix_unicode_in_file(file_path)
        
        if success:
            print(f"[{i}/{len(files)}] FIXED: {file_path}")
            fixed += 1
        elif "not found" in message:
            print(f"[{i}/{len(files)}] SKIP: {file_path} (not found)")
            skipped += 1
        elif "No changes" in message:
            print(f"[{i}/{len(files)}] OK: {file_path} (already fixed)")
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

