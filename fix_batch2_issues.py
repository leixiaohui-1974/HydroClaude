#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复Batch 2的常见问题
应用Batch 1的成功经验

Author: HydroClaude
Date: 2025-11-13
"""

import os
import re

# 需要修复的文件
files_to_fix = [
    'examples/example_03_turbine_demo/example_03_turbine_with_anim.py',
    'examples/example_05_transient_analysis/example_05_load_rejection.py',
    'examples/example_16_weirs_application/weirs_irrigation_system.py',
    'examples/example_22_water_hammer/demo_water_hammer.py',
    'examples/example_23_control_comparison/demo_control_comparison.py',
    'examples/example_gate_pump_cascade/run_scenario_01.py',
    'examples/example_gate_pump_cascade/run_scenario_02.py',
    'examples/example_gate_pump_cascade/run_scenario_03.py',
    'examples/example_unsteady/run_time_varying_bc.py',
]

def fix_file(file_path):
    """修复单个文件"""
    if not os.path.exists(file_path):
        return f"NOT_FOUND"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception as e:
            return f"READ_ERROR: {str(e)[:50]}"
    
    original_content = content
    changes = []
    
    # Fix 1: 添加sys.path设置（如果缺少）
    if 'import sys' in content and 'sys.path.insert' not in content:
        # 找到import sys的位置
        import_pos = content.find('import sys')
        if import_pos > 0:
            # 在下一行插入sys.path配置
            next_line_pos = content.find('\n', import_pos) + 1
            insert_code = """import os

# 添加项目根目录到路径
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.insert(0, project_root)

"""
            content = content[:next_line_pos] + insert_code + content[next_line_pos:]
            changes.append("Added sys.path configuration")
    
    # Fix 2: 替换硬编码的/home/user/HydroClaude路径
    if '/home/user/HydroClaude' in content:
        # 替换为相对路径
        content = content.replace('/home/user/HydroClaude/', '')
        content = content.replace('/home/user/HydroClaude', '')
        changes.append("Removed /home/user paths")
    
    # Fix 3: 修复total_length参数（如果存在）
    if 'total_length=' in content:
        content = content.replace('total_length=', 'length=')
        changes.append("Fixed total_length parameter")
    
    # Fix 4: 添加matplotlib.use('Agg')
    if 'import matplotlib' in content and "matplotlib.use('Agg')" not in content and "matplotlib.use(\"Agg\")" not in content:
        content = content.replace('import matplotlib.pyplot', 
                                 "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot")
        changes.append("Added matplotlib.use('Agg')")
    
    # Fix 5: 注释掉plt.show()
    if 'plt.show()' in content:
        content = content.replace('plt.show()', '# plt.show()  # Disabled for automated testing')
        changes.append("Disabled plt.show()")
    
    # Fix 6: 修复文件读取的编码问题
    if "open(" in content and "encoding=" not in content:
        # 这个比较复杂，跳过自动修复
        pass
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"FIXED: {', '.join(changes)}"
        except Exception as e:
            return f"WRITE_ERROR: {str(e)[:50]}"
    else:
        return "NO_CHANGE"

def main():
    """主函数"""
    print("="*70)
    print("FIXING BATCH 2 ISSUES")
    print("="*70)
    print()
    
    fixed_count = 0
    
    for i, file_path in enumerate(files_to_fix, 1):
        basename = os.path.basename(file_path)
        print(f"[{i:2d}/9] {basename:50s}", end=" ", flush=True)
        
        result = fix_file(file_path)
        print(f"[{result}]")
        
        if result.startswith("FIXED"):
            fixed_count += 1
    
    print()
    print("="*70)
    print(f"Fixed {fixed_count}/{len(files_to_fix)} files")
    print("="*70)
    print("\nRe-test with: python test_batch2_real.py")

if __name__ == '__main__':
    main()

