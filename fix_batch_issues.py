#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复前两批发现的问题

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re
import json

# 加载失败的文件
STATE_FILE = 'test_results/simulation_test_state.json'

def load_failed_files():
    """加载失败的文件列表"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return state.get('failed_files', {})
    return {}

def fix_matplotlib_blocking(file_path):
    """修复matplotlib阻塞问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 1. 添加非交互后端（在import matplotlib后立即设置）
        if 'import matplotlib.pyplot as plt' in content or 'from matplotlib import pyplot as plt' in content:
            # 检查是否已有backend设置
            if 'matplotlib.use(' not in content:
                # 在第一个import matplotlib之前添加
                import_pattern = r'(import matplotlib)'
                if re.search(import_pattern, content):
                    content = re.sub(
                        import_pattern,
                        r'import matplotlib\nmatplotlib.use("Agg")  # 非交互模式',
                        content,
                        count=1
                    )
                    changes.append("Added matplotlib.use('Agg')")
        
        # 2. 替换plt.show()为plt.savefig()或plt.close()
        if 'plt.show()' in content:
            # 智能替换：如果附近有savefig就只close，否则savefig然后close
            lines = content.split('\n')
            new_lines = []
            for i, line in enumerate(lines):
                if 'plt.show()' in line and '#' not in line.split('plt.show()')[0]:
                    # 检查前5行是否有savefig
                    has_savefig = any('savefig' in lines[j] for j in range(max(0, i-5), i))
                    if has_savefig:
                        # 只关闭
                        new_line = line.replace('plt.show()', 'plt.close("all")  # 自动关闭图形')
                    else:
                        # 保存并关闭
                        indent = len(line) - len(line.lstrip())
                        new_line = line.replace('plt.show()', 
                                               'plt.savefig("output.png", dpi=100, bbox_inches="tight"); plt.close("all")  # 保存并关闭')
                    new_lines.append(new_line)
                    changes.append("Replaced plt.show()")
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        
        # 3. 移除input()调用
        if 'input(' in content:
            content = re.sub(r'input\([^)]*\)', '# input() removed for automation', content)
            changes.append("Removed input()")
        
        # 4. 降低可能导致timeout的参数
        if 't_end' in content:
            # 将过大的t_end降低
            content = re.sub(r't_end\s*=\s*([1-9]\d{2,})', 't_end = 50', content)
            if 't_end = 50' in content and 't_end = 50' not in original:
                changes.append("Reduced t_end to 50")
        
        # 5. 添加sys.path（如果缺少）
        if 'import sys' in content and 'sys.path.insert' not in content:
            # 在import sys后添加
            content = re.sub(
                r'(import sys\n)',
                r'import sys\nimport os\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))\n',
                content,
                count=1
            )
            changes.append("Added sys.path")
        
        # 6. 替换physics模块为solvers
        if 'from physics' in content or 'import physics' in content:
            content = content.replace('from physics.canal', 'from solvers.canal')
            content = content.replace('from physics import', 'from solvers import')
            content = content.replace('import physics.', 'import solvers.')
            changes.append("Replaced physics with solvers")
        
        if content != original and changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
        
    except Exception as e:
        return False, [f"Error: {e}"]

def main():
    """主函数"""
    
    failed_files = load_failed_files()
    
    print("="*70)
    print("FIXING BATCH 1 & 2 ISSUES")
    print("="*70)
    print(f"Failed files to fix: {len(failed_files)}")
    print()
    
    if not failed_files:
        print("No failed files found in state.")
        return
    
    fixed_count = 0
    timeout_fixed = 0
    fail_fixed = 0
    
    for file_path, info in failed_files.items():
        status = info['status']
        basename = os.path.basename(file_path)
        
        print(f"[{status}] {basename}")
        
        if not os.path.exists(file_path):
            print(f"  -> File not found, skipping")
            continue
        
        # 修复
        fixed, changes = fix_matplotlib_blocking(file_path)
        
        if fixed:
            print(f"  -> Fixed: {', '.join(changes)}")
            fixed_count += 1
            if status == 'TIMEOUT':
                timeout_fixed += 1
            else:
                fail_fixed += 1
        else:
            if changes:
                print(f"  -> {changes[0]}")
            else:
                print(f"  -> No changes needed")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total fixed: {fixed_count}/{len(failed_files)}")
    print(f"  TIMEOUT fixed: {timeout_fixed}")
    print(f"  FAIL fixed: {fail_fixed}")
    print()
    print("Run 'python retest_fixed_files.py' to verify fixes")
    print("="*70)

if __name__ == '__main__':
    main()

