#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量修复Examples导入问题

自动为16个失败的示例文件添加sys.path设置

作者: Claude
日期: 2025-10-22
"""

import os
from pathlib import Path
from typing import List, Tuple


# 需要修复的文件列表（相对于examples目录）
FILES_TO_FIX = [
    "example_02_pump_system/example_02_pump_system_enhanced.py",
    "example_02_spillway_cascade/example_02_spillway_system.py",
    "example_03_turbine_demo/example_03_turbine_comparison.py",
    "example_03_complex_network/code/example_03_complex_network.py",
    "example_04_hydropower_system/example_04_hydropower_plant.py",
    "example_05_transient_analysis/example_05_load_rejection.py",
    "example_06_complete_hydropower_system/example_06_complete_system.py",
    "example_07_multi_unit_agc/example_07_multi_unit_agc.py",
    "example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py",
    "example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py",
    "example_10_series_network/code/example_10_series_network.py",
    "example_11_tree_network/code/example_11_tree_network.py",
    "example_12_loop_network/code/example_12_loop_network.py",
    "example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py",
    "example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py",
    "example_15_rls_identification/example_15_rls_identification_enhanced.py",
]


# sys.path设置代码（需要根据文件所在层级调整）
def get_syspath_code(depth: int) -> str:
    """
    生成sys.path设置代码

    Args:
        depth: 文件相对于examples目录的深度
               1 = examples/xxx/file.py
               2 = examples/xxx/code/file.py

    Returns:
        str: sys.path设置代码
    """
    if depth == 1:
        # examples/example_xx/file.py
        parent_call = "os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    elif depth == 2:
        # examples/example_xx/code/file.py
        parent_call = "os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    else:
        parent_call = "os.path.dirname(os.path.abspath(__file__))"

    return f"""import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, {parent_call})

"""


def check_has_syspath(content: str) -> bool:
    """检查文件是否已经有sys.path设置"""
    return "sys.path.insert" in content or "sys.path.append" in content


def add_syspath_to_file(filepath: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    为文件添加sys.path设置

    Args:
        filepath: 文件路径
        dry_run: 如果为True，只检查不修改

    Returns:
        (success, message): 是否成功和消息
    """
    if not filepath.exists():
        return False, f"文件不存在: {filepath}"

    # 读取文件内容
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"读取失败: {e}"

    # 检查是否已经有sys.path设置
    if check_has_syspath(content):
        return True, "已有sys.path设置，跳过"

    # 确定文件深度
    rel_path = filepath.relative_to(Path('examples'))
    depth = len(rel_path.parts) - 1  # 减去文件名本身

    # 生成sys.path代码
    syspath_code = get_syspath_code(depth)

    # 找到插入位置
    lines = content.split('\n')
    insert_idx = 0

    # 跳过shebang和encoding声明
    for i, line in enumerate(lines):
        if line.startswith('#!') or line.startswith('# -*- coding'):
            insert_idx = i + 1
        elif line.startswith('"""') or line.startswith("'''"):
            # 跳过docstring
            # 找到docstring结束
            for j in range(i + 1, len(lines)):
                if '"""' in lines[j] or "'''" in lines[j]:
                    insert_idx = j + 1
                    break
            break
        elif line.strip() and not line.startswith('#'):
            # 遇到第一行非注释代码
            break

    # 插入sys.path代码
    lines.insert(insert_idx, syspath_code)
    new_content = '\n'.join(lines)

    if dry_run:
        return True, f"需要修复（深度={depth}）"

    # 写回文件
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True, f"✓ 已修复（深度={depth}）"
    except Exception as e:
        return False, f"写入失败: {e}"


def main():
    """主函数"""
    print("="*80)
    print("批量修复Examples导入问题")
    print("="*80)
    print()

    examples_dir = Path("examples")

    if not examples_dir.exists():
        print("错误: examples目录不存在")
        return 1

    # 首先进行dry run检查
    print("第1步: 检查需要修复的文件...")
    print("-"*80)

    files_to_process = []
    for rel_path in FILES_TO_FIX:
        filepath = examples_dir / rel_path
        success, message = add_syspath_to_file(filepath, dry_run=True)

        status = "✓" if success else "✗"
        print(f"  {status} {rel_path}")
        print(f"     {message}")

        if success and "需要修复" in message:
            files_to_process.append(filepath)

    print()
    print(f"发现 {len(files_to_process)} 个文件需要修复")
    print()

    if not files_to_process:
        print("所有文件已经正确配置!")
        return 0

    # 确认是否继续
    response = input(f"是否继续修复这 {len(files_to_process)} 个文件? (y/n): ")
    if response.lower() != 'y':
        print("取消修复")
        return 0

    # 执行修复
    print()
    print("第2步: 执行修复...")
    print("-"*80)

    success_count = 0
    fail_count = 0

    for filepath in files_to_process:
        rel_path = filepath.relative_to(examples_dir)
        success, message = add_syspath_to_file(filepath, dry_run=False)

        status = "✓" if success else "✗"
        print(f"  {status} {rel_path}: {message}")

        if success:
            success_count += 1
        else:
            fail_count += 1

    # 总结
    print()
    print("="*80)
    print("修复完成!")
    print("="*80)
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"总计: {success_count + fail_count}")
    print()

    if success_count > 0:
        print("建议:")
        print("  1. 运行 python test_all_examples.py 验证修复")
        print("  2. 检查修复后的文件确保格式正确")
        print()

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
