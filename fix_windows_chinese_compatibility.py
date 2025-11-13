#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复Windows中文环境兼容性问题

自动修复所有可能导致Windows中文环境下失败的问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
from pathlib import Path

def fix_file_operations(content):
    """修复文件操作，添加encoding='utf-8'"""
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # 匹配open()调用但没有encoding参数的
        if 'open(' in line and 'encoding=' not in line:
            # 检查是否是简单的open调用
            if re.search(r"open\(['\"].*?['\"].*?\)", line):
                # 在关闭括号前添加encoding
                line = re.sub(r"\)", r", encoding='utf-8')", line, count=1)
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def remove_problematic_unicode(content):
    """移除可能导致编码问题的Unicode字符"""
    # 移除emoji和特殊Unicode字符
    problematic_chars = [
        '\ufe0f',  # variation selector
        '️',      # emoji variation
        '⚠️',     # warning
        '✅',     # check mark
        '❌',     # cross mark
        '🔥',     # fire
        '⭐',     # star
        '📊',     # chart
        '🎯',     # target
    ]
    
    for char in problematic_chars:
        if char in content:
            # 替换为ASCII等价物或移除
            replacements = {
                '\ufe0f': '',
                '️': '',
                '⚠️': '[警告]',
                '✅': '[成功]',
                '❌': '[失败]',
                '🔥': '[重要]',
                '⭐': '*',
                '📊': '[图表]',
                '🎯': '[目标]',
            }
            content = content.replace(char, replacements.get(char, ''))
    
    return content

def add_encoding_header(content):
    """确保文件有正确的编码声明"""
    lines = content.split('\n')
    
    # 检查前3行是否有编码声明
    has_encoding = False
    for i in range(min(3, len(lines))):
        if 'coding' in lines[i] or 'encoding' in lines[i]:
            has_encoding = True
            break
    
    if not has_encoding:
        # 在shebang后添加
        if lines[0].startswith('#!'):
            lines.insert(1, '# -*- coding: utf-8 -*-')
        else:
            lines.insert(0, '# -*- coding: utf-8 -*-')
    
    return '\n'.join(lines)

def fix_print_statements(content):
    """修复可能有编码问题的print语句"""
    # 这个比较复杂，暂时只做简单处理
    # 移除print中的emoji
    content = remove_problematic_unicode(content)
    return content

def fix_exec_encoding(content):
    """修复exec()调用，添加encoding"""
    # exec(open('file.py').read()) -> exec(open('file.py', encoding='utf-8').read())
    content = re.sub(
        r"exec\(open\(['\"]([^'\"]+)['\"]\)\.read\(\)\)",
        r"exec(open('\1', encoding='utf-8').read())",
        content
    )
    return content

def add_pythonioencoding_warning(content):
    """在主函数开始处添加环境检查"""
    if '__main__' in content and 'if __name__' in content:
        # 不修改，只在测试脚本中设置环境变量
        pass
    return content

def fix_windows_chinese_compat(file_path):
    """修复单个文件的Windows中文兼容性"""
    try:
        # 尝试UTF-8读取
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试GBK
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
    except Exception as e:
        return False, [f"READ_ERROR: {str(e)[:50]}"]
    
    original = content
    changes = []
    
    # 1. 添加编码头
    content = add_encoding_header(content)
    if content != original:
        changes.append("encoding_header")
        original = content
    
    # 2. 修复文件操作
    content = fix_file_operations(content)
    if content != original:
        changes.append("file_encoding")
        original = content
    
    # 3. 移除问题Unicode字符
    content = remove_problematic_unicode(content)
    if content != original:
        changes.append("unicode_chars")
        original = content
    
    # 4. 修复exec调用
    content = fix_exec_encoding(content)
    if content != original:
        changes.append("exec_encoding")
        original = content
    
    # 5. 修复print语句
    content = fix_print_statements(content)
    if content != original:
        changes.append("print_fix")
        original = content
    
    # 保存（如果有修改）
    if changes:
        try:
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            return True, changes
        except Exception as e:
            return False, [f"WRITE_ERROR: {str(e)[:50]}"]
    
    return False, ["NO_CHANGE"]

def find_all_python_files():
    """查找所有Python文件"""
    examples_dir = Path('examples')
    
    # 排除
    exclude_patterns = [
        '**/backups/**',
        '**/*.bak*',
        '**/__pycache__/**',
    ]
    
    # 所有.py文件
    all_files = list(examples_dir.glob('**/*.py'))
    
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
    print("修复Windows中文环境兼容性")
    print("="*80)
    print()
    
    # 查找文件
    print("正在搜索Python文件...")
    files = find_all_python_files()
    print(f"找到 {len(files)} 个文件")
    print()
    
    # 修复文件
    print("开始修复...")
    print("-"*80)
    
    fixed_count = 0
    change_stats = {}
    
    for i, file_path in enumerate(files, 1):
        try:
            rel_path = file_path.relative_to('examples')
        except:
            rel_path = file_path
        
        print(f"[{i:3d}/{len(files)}] {str(rel_path):60s}", end=" ", flush=True)
        
        fixed, changes = fix_windows_chinese_compat(file_path)
        
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
            desc = {
                'encoding_header': '编码头声明',
                'file_encoding': '文件操作编码',
                'unicode_chars': 'Unicode字符',
                'exec_encoding': 'exec编码',
                'print_fix': 'print修复'
            }
            print(f"  {desc.get(change_type, change_type):20s}: {count:3d}")
    
    print(f"\n下一步: python test_windows_chinese_env.py")
    print("\n建议:")
    print("  1. 确保所有文件以UTF-8编码保存")
    print("  2. 测试时设置环境变量: PYTHONIOENCODING=utf-8")
    print("  3. 避免在代码中使用emoji和特殊Unicode字符")

if __name__ == '__main__':
    main()

