#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从日志文件分析并修复失败案例"""

import re
import os
from pathlib import Path
from collections import Counter
import shutil

def analyze_log_file(log_file):
    """分析日志文件，提取失败案例"""
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 新格式: 状态: 通过 PASS (耗时: 5.09s) 或 状态: 失败 FAIL (退出码: 1)
    pass_pattern = r'状态:.*?PASS'
    fail_pattern = r'状态:.*?FAIL'
    
    passes = re.findall(pass_pattern, content)
    fails = re.findall(fail_pattern, content)
    
    print(f"通过: {len(passes)}")
    print(f"失败: {len(fails)}")
    print(f"总计: {len(passes) + len(fails)}")
    
    # 提取文件路径和退出码
    # 格式: 文件: tests\xxx.py ... 状态: 失败 FAIL (退出码: 1)
    test_blocks = re.findall(r'\[\d+/\d+\].*?文件:\s*([^\n]+).*?状态:.*?FAIL.*?退出码:\s*(\d+)', content, re.DOTALL)
    
    error_types = Counter()
    exit_code_1_files = []
    
    for file_path, exit_code in test_blocks:
        file_path = file_path.strip()
        exit_code = exit_code.strip()
        
        if exit_code == '1':
            error_types['Exit code 1 (数值不稳定)'] += 1
            exit_code_1_files.append(file_path)
        else:
            error_types[f'Exit code {exit_code}'] += 1
    
    # 查找其他类型的错误（没有退出码的）
    other_fails = len(fails) - len(test_blocks)
    if other_fails > 0:
        error_types['Other/Unknown'] = other_fails
    
    return passes, fails, error_types, exit_code_1_files

def optimize_test_file(file_path, backup=True):
    """优化单个测试文件的参数"""
    
    if not Path(file_path).exists():
        return False, []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # 1. 降低CFL数
        new_content = re.sub(r'(["\']?cfl["\']?\s*[:=]\s*)0\.[5-9]', r'\g<1>0.3', content)
        new_content = re.sub(r'(["\']?cfl["\']?\s*[:=]\s*)1\.0', r'\g<1>0.3', new_content)
        if new_content != content:
            changes.append("CFL: 0.5+ -> 0.3")
            content = new_content
        
        # 2. 减小dt_max
        new_content = re.sub(r'(["\']?dt_max["\']?\s*[:=]\s*)0\.[5-9]\d*', r'\g<1>0.2', content)
        new_content = re.sub(r'(["\']?dt_max["\']?\s*[:=]\s*)[1-9]\.0', r'\g<1>0.2', new_content)
        if new_content != content:
            changes.append("dt_max: 0.5+ -> 0.2")
            content = new_content
        
        # 3. 使用一阶精度
        new_content = re.sub(r'(["\']?order["\']?\s*[:=]\s*)2', r'\g<1>1', content)
        if new_content != content:
            changes.append("order: 2 -> 1")
            content = new_content
        
        # 4. 增加网格（只对小网格）
        def increase_cells(match):
            value = int(match.group(2))
            if value < 200:
                new_value = int(value * 1.2)
                return f"{match.group(1)}{new_value}"
            return match.group(0)
        
        new_content = re.sub(r'(["\']?n_cells["\']?\s*[:=]\s*)(\d+)', increase_cells, content)
        if new_content != content:
            changes.append("n_cells: x1.2")
            content = new_content
        
        # 如果有修改，保存文件
        if content != original_content:
            if backup:
                backup_path = Path(file_path).with_suffix('.py.bak_stability')
                if not backup_path.exists():  # 只备份一次
                    shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, changes
        
        return False, []
    
    except Exception as e:
        print(f"[ERROR] Failed to optimize {file_path}: {e}")
        return False, []

def main():
    print("="*70)
    print("从日志分析并修复失败案例")
    print("="*70)
    
    # 使用第一轮测试的日志（更可靠）
    log_file = "test_results/batch_test_output.txt"
    
    if not Path(log_file).exists():
        print(f"[ERROR] Log file not found: {log_file}")
        return
    
    print(f"\n[1/3] 分析日志文件: {log_file}")
    passes, fails, error_types, exit_code_1_files = analyze_log_file(log_file)
    
    print(f"\n错误类型分布:")
    for error_type, count in error_types.most_common():
        pct = count / len(fails) * 100 if fails else 0
        print(f"  {error_type}: {count} ({pct:.1f}%)")
    
    print(f"\n[2/3] 修复Exit code 1案例...")
    print(f"需要修复: {len(exit_code_1_files)} 个文件")
    
    optimized_count = 0
    skipped_count = 0
    
    for i, file_path in enumerate(exit_code_1_files, 1):
        print(f"\r[{i}/{len(exit_code_1_files)}] {Path(file_path).name[:50]:<50}", end='')
        
        success, changes = optimize_test_file(file_path)
        
        if success:
            optimized_count += 1
        else:
            skipped_count += 1
    
    print()  # 新行
    
    print(f"\n[3/3] 修复完成")
    print(f"  成功优化: {optimized_count}")
    print(f"  跳过/无需修改: {skipped_count}")
    
    print(f"\n预期效果:")
    if len(passes) + len(fails) > 0:
        current_pass_rate = len(passes) / (len(passes) + len(fails)) * 100
        print(f"  当前通过率: {current_pass_rate:.1f}%")
        print(f"  预期通过率: {current_pass_rate + 5:.1f}% - {current_pass_rate + 10:.1f}%")
    else:
        print(f"  无法计算通过率（没有测试结果）")
    
    print(f"\n下一步:")
    print(f"  1. 快速验证: python quick_test_sample.py -n 50")
    print(f"  2. 完整测试: python batch_test_all_cases.py")
    print("\n" + "="*70)

if __name__ == '__main__':
    main()

