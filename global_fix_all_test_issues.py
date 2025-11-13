#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局修复所有测试文件的常见问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
from pathlib import Path

def fix_file_all_issues(file_path):
    """修复单个文件的所有问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 问题1: 修复错误的plt import插入（导致的语法错误）
        # 例如: matplotlib.use("Agg")  # 非交互模式.pyplot as plt
        pattern1 = r'matplotlib\.use\(["\']Agg["\']\)\s*#[^#\n]*\.pyplot as plt'
        if re.search(pattern1, content):
            content = re.sub(pattern1, 'matplotlib.use("Agg")  # Non-interactive mode', content)
            # 然后在下一行添加plt import
            if 'import matplotlib.pyplot as plt' not in content:
                content = re.sub(
                    r'(matplotlib\.use\(["\']Agg["\']\)[^\n]*\n)',
                    r'\1import matplotlib.pyplot as plt\n',
                    content,
                    count=1
                )
            changes.append("Fixed matplotlib.pyplot import")
        
        # 问题2: 缺少plt import但使用了plt
        if 'plt.' in content and 'import matplotlib.pyplot as plt' not in content:
            # 在matplotlib import后添加
            if 'import matplotlib' in content:
                lines = content.split('\n')
                new_lines = []
                added = False
                
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if not added and 'import matplotlib' in line and 'pyplot' not in line:
                        # 检查下一行是否是matplotlib.use
                        if i + 1 < len(lines) and 'matplotlib.use' in lines[i + 1]:
                            new_lines.append(lines[i + 1])
                            new_lines.append('import matplotlib.pyplot as plt')
                            i += 1
                            added = True
                            # 跳过原来的下一行
                            continue
                        else:
                            new_lines.append('import matplotlib.pyplot as plt')
                            added = True
                
                if added:
                    content = '\n'.join(new_lines)
                    changes.append("Added missing plt import")
        
        # 问题3: .initialize( 应该是 .initialize_steady_state(
        if '.initialize(' in content:
            content = re.sub(r'\.initialize\(', '.initialize_steady_state(', content)
            changes.append("Fixed initialize method")
        
        # 问题4: 错误的导入 GodunvFVMWENO3 (拼写错误)
        if 'GodunvFVMWENO3' in content:
            content = content.replace('GodunvFVMWENO3', 'GodunovFVMWENO3')
            changes.append("Fixed GodunvFVMWENO3 typo")
        
        # 问题5: 文件路径 /workspace/ (Linux路径，应该是相对路径)
        if '/workspace/' in content:
            content = content.replace('/workspace/', './')
            changes.append("Fixed /workspace/ path")
        
        # 问题6: Unicode字符 (再次清理)
        unicode_chars = {
            '→': '->',
            '•': '*',
            '✓': 'OK',
            '✗': 'X',
            '—': '--',
            '–': '-',
            '°': 'deg',
            '±': '+/-',
            '≠': '!=',
            '≤': '<=',
            '≥': '>=',
        }
        for old, new in unicode_chars.items():
            if old in content:
                content = content.replace(old, new)
                if 'Fixed Unicode' not in changes:
                    changes.append("Fixed Unicode")
        
        # 问题7: 确保有matplotlib.use('Agg')如果使用了plt.show()
        if 'plt.show()' in content and 'matplotlib.use' not in content:
            # 在第一个import matplotlib后添加
            content = re.sub(
                r'(import matplotlib\n)',
                r'\1matplotlib.use("Agg")\n',
                content,
                count=1
            )
            changes.append("Added matplotlib.use('Agg')")
        
        # 问题8: 注释掉plt.show()
        if 'plt.show()' in content and '# plt.show()' not in content:
            content = content.replace('plt.show()', '# plt.show()  # Disabled for testing')
            changes.append("Disabled plt.show()")
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {str(e)[:50]}"]

def main():
    """主函数"""
    
    print("="*70)
    print("GLOBAL FIX FOR ALL TEST FILES")
    print("="*70)
    print()
    
    # 找到所有Python测试文件
    all_files = []
    for path in Path('examples').rglob('*.py'):
        if path.is_file() and path.name != '__init__.py':
            all_files.append(str(path))
    
    print(f"Found {len(all_files)} Python files")
    print("Processing...")
    print()
    
    # 统计
    fixed_count = 0
    all_changes = {}
    
    for i, file_path in enumerate(all_files, 1):
        success, changes = fix_file_all_issues(file_path)
        
        if success:
            fixed_count += 1
            rel_path = os.path.relpath(file_path)
            print(f"[{i:3d}/{len(all_files)}] {rel_path}")
            for change in changes:
                print(f"           - {change}")
                all_changes[change] = all_changes.get(change, 0) + 1
        
        # 每100个显示进度
        if i % 100 == 0 and not success:
            print(f"Progress: {i}/{len(all_files)} scanned...")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total files: {len(all_files)}")
    print(f"Files fixed: {fixed_count}")
    print()
    print("Changes applied:")
    for change, count in sorted(all_changes.items()):
        print(f"  - {change}: {count} files")
    print("="*70)

if __name__ == '__main__':
    main()

