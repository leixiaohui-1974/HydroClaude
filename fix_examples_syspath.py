#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复所有示例文件的sys.path设置

问题：有些示例文件的sys.path设置不正确，导致无法导入模块
解决：根据文件所在深度，自动计算正确的向上级数
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_example_python_files() -> List[Path]:
    """查找所有示例Python文件"""

    examples_dir = Path("examples")
    if not examples_dir.exists():
        print(f"错误: examples目录不存在")
        return []

    # 递归查找所有.py文件
    py_files = list(examples_dir.rglob("*.py"))

    # 排除__init__.py
    py_files = [f for f in py_files if f.name != "__init__.py"]

    print(f"找到 {len(py_files)} 个示例Python文件")

    return py_files

def calculate_depth(file_path: Path, project_root: Path) -> int:
    """计算文件相对于项目根目录的深度"""

    # 确保使用绝对路径
    file_path = file_path.resolve()
    project_root = project_root.resolve()

    # 获取相对路径
    try:
        rel_path = file_path.relative_to(project_root)
    except ValueError:
        print(f"  警告: {file_path} 不在项目根目录 {project_root} 下")
        return 0

    # 计算向上层数（包括文件所在目录）
    # rel_path.parts包含所有目录和文件名
    # 例如: ['examples', 'example_01', 'code', 'file.py']
    # 从file.py到root需要向上len(parts)级
    depth = len(rel_path.parts)

    return depth

def get_correct_syspath_code(depth: int) -> str:
    """根据深度生成正确的sys.path代码"""

    if depth == 0:
        # 文件在项目根目录
        return None
    elif depth == 1:
        # examples/file.py
        return "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))"
    elif depth == 2:
        # examples/example_01/file.py
        return "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    elif depth == 3:
        # examples/example_01/code/file.py
        return "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))"
    else:
        # 更深层次（极少见）
        dirname_chain = "os.path.abspath(__file__)"
        for _ in range(depth):
            dirname_chain = f"os.path.dirname({dirname_chain})"
        return f"sys.path.insert(0, {dirname_chain})"

def fix_syspath_in_file(file_path: Path, dry_run: bool = False) -> bool:
    """修复单个文件的sys.path设置"""

    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"   无法读取文件: {e}")
        return False

    # 计算正确的深度
    project_root = Path.cwd()
    depth = calculate_depth(file_path, project_root)

    # 生成正确的sys.path代码
    correct_code = get_correct_syspath_code(depth)

    if correct_code is None:
        # 文件在根目录，不需要sys.path
        return False

    # 查找现有的sys.path设置
    syspath_pattern = re.compile(r'sys\.path\.(insert|append)\s*\([^)]+\)')

    modified = False
    new_lines = []
    syspath_found = False
    import_sys_found = False

    for i, line in enumerate(lines):
        # 检查是否导入了sys
        if 'import sys' in line:
            import_sys_found = True

        # 检查是否有sys.path设置
        if syspath_pattern.search(line):
            syspath_found = True

            # 替换为正确的代码
            indent = len(line) - len(line.lstrip())
            new_line = ' ' * indent + correct_code + '\n'

            if line.strip() != new_line.strip():
                new_lines.append(new_line)
                modified = True
                print(f"   修复第 {i+1} 行")
                print(f"    原: {line.strip()}")
                print(f"    新: {new_line.strip()}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 如果没有找到sys.path设置，需要添加
    if not syspath_found:
        # 找到合适的插入位置（在import语句之后）
        insert_pos = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                # 跳过docstring
                continue
            if 'import' in line:
                insert_pos = i + 1
                break

        # 如果没有导入sys，先添加import sys
        if not import_sys_found:
            new_lines.insert(insert_pos, "import sys, os\n")
            new_lines.insert(insert_pos + 1, correct_code + "\n")
            new_lines.insert(insert_pos + 2, "\n")
            print(f"   添加sys.path设置（第 {insert_pos+1} 行）")
        else:
            new_lines.insert(insert_pos, correct_code + "\n")
            print(f"   添加sys.path设置（第 {insert_pos+1} 行）")

        modified = True

    # 写回文件
    if modified and not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        except Exception as e:
            print(f"   无法写入文件: {e}")
            return False

    return modified

def main():
    """主函数"""

    print("="*80)
    print("示例文件sys.path批量修复工具")
    print("="*80)
    print()

    # 查找所有示例文件
    py_files = find_example_python_files()

    if not py_files:
        print("没有找到示例文件")
        return 1

    print("\n开始修复...")
    print("="*80)

    # 修复每个文件
    fixed_count = 0
    unchanged_count = 0
    failed_count = 0

    for file_path in py_files:
        print(f"\n处理: {file_path}")

        try:
            if fix_syspath_in_file(file_path, dry_run=False):
                fixed_count += 1
            else:
                unchanged_count += 1
        except Exception as e:
            print(f"   修复失败: {e}")
            failed_count += 1

    # 打印总结
    print("\n" + "="*80)
    print("修复完成!")
    print("="*80)
    print(f"总文件数: {len(py_files)}")
    print(f"已修复: {fixed_count}")
    print(f"未改变: {unchanged_count}")
    print(f"失败: {failed_count}")
    print("="*80)

    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
