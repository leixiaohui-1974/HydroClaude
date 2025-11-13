#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本迁移工具 - 将旧求解器迁移到HydrostaticCanalSolver

自动转换使用SingleCanalSolver或CanalSolver的脚本到HydrostaticCanalSolver

Author: Claude
Date: 2025-10-23
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple


class SolverMigrator:
    """求解器迁移工具"""

    def __init__(self, backup_dir: str = "backups"):
        """
        初始化迁移器

        Args:
            backup_dir: 备份目录
        """
        self.backup_dir = backup_dir
        self.conversion_log = []

    def backup_file(self, filepath: str) -> str:
        """
        备份文件

        Args:
            filepath: 文件路径

        Returns:
            备份文件路径
        """
        os.makedirs(self.backup_dir, exist_ok=True)
        filename = os.path.basename(filepath)
        backup_path = os.path.join(self.backup_dir, filename + '.bak')
        shutil.copy2(filepath, backup_path)
        print(f"   备份: {filepath} -> {backup_path}")
        return backup_path

    def convert_imports(self, content: str) -> Tuple[str, List[str]]:
        """
        转换导入语句

        Args:
            content: 文件内容

        Returns:
            (转换后内容, 变更日志)
        """
        changes = []

        # SingleCanalSolver -> HydrostaticCanalSolver
        if 'from solvers.single_canal_solver import SingleCanalSolver' in content:
            content = content.replace(
                'from solvers.single_canal_solver import SingleCanalSolver',
                'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver'
            )
            changes.append("导入: SingleCanalSolver -> HydrostaticCanalSolver")

        # CanalSolver -> HydrostaticCanalSolver (更谨慎)
        if 'from solvers.canal_solver import CanalSolver' in content:
            content = content.replace(
                'from solvers.canal_solver import CanalSolver',
                'from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver'
            )
            changes.append("导入: CanalSolver -> HydrostaticCanalSolver")

        return content, changes

    def convert_constructor_calls(self, content: str) -> Tuple[str, List[str]]:
        """
        转换构造函数调用

        Args:
            content: 文件内容

        Returns:
            (转换后内容, 变更日志)
        """
        changes = []

        # SingleCanalSolver(...) -> HydrostaticCanalSolver(...)
        if 'SingleCanalSolver(' in content:
            # 需要转换参数名称
            # total_length -> length
            # nx_total -> nx
            # structures=[] -> internal_structures=[(pos, obj), ...]

            content = content.replace('SingleCanalSolver(', 'HydrostaticCanalSolver(')
            content = content.replace('total_length=', 'length=')
            content = content.replace('nx_total=', 'nx=')

            # structures参数需要手动转换为元组格式
            # 这个比较复杂，需要添加注释提示
            if 'structures=[' in content:
                changes.append(" 警告: structures参数格式需要手动转换为 internal_structures=[(pos, obj), ...]")

            changes.append("构造: SingleCanalSolver -> HydrostaticCanalSolver")

        # CanalSolver(...) -> HydrostaticCanalSolver(...)
        if 'CanalSolver(' in content:
            content = content.replace('CanalSolver(', 'HydrostaticCanalSolver(')
            changes.append("构造: CanalSolver -> HydrostaticCanalSolver")

        return content, changes

    def add_result_validation(self, content: str, script_name: str) -> Tuple[str, List[str]]:
        """
        添加结果验证代码

        Args:
            content: 文件内容
            script_name: 脚本名称

        Returns:
            (转换后内容, 变更日志)
        """
        changes = []

        # 检查是否已经导入了result_validator
        if 'from utils.result_validator import' not in content:
            # 在导入部分添加
            import_section = re.search(r'(import.*?\n)+', content)
            if import_section:
                insert_pos = import_section.end()
                validation_import = "from utils.result_validator import ResultValidator, quick_validate_steady_state\n"
                content = content[:insert_pos] + validation_import + content[insert_pos:]
                changes.append("添加: result_validator导入")

        return content, changes

    def convert_method_calls(self, content: str) -> Tuple[str, List[str]]:
        """
        转换方法调用

        Args:
            content: 文件内容

        Returns:
            (转换后内容, 变更日志)
        """
        changes = []

        # solve_steady_with_structures -> solve_steady_state
        if 'solve_steady_with_structures(' in content:
            content = content.replace('solve_steady_with_structures(', 'solve_steady_state(')
            # 添加h_downstream参数提示
            changes.append(" 注意: solve_steady_state()需要h_downstream参数")
            changes.append("方法: solve_steady_with_structures -> solve_steady_state")

        # compute_steady_uniform_flow返回值处理
        if 'h_uniform, _ = compute_steady_uniform_flow(' in content:
            content = content.replace(
                'h_uniform, _ = compute_steady_uniform_flow(',
                'h_uniform = compute_steady_uniform_flow('
            )
            changes.append("修复: compute_steady_uniform_flow返回值解包")

        return content, changes

    def migrate_script(self, filepath: str, dry_run: bool = False) -> bool:
        """
        迁移单个脚本

        Args:
            filepath: 脚本路径
            dry_run: 是否只是试运行（不实际修改文件）

        Returns:
            是否成功
        """
        print(f"\n{'='*80}")
        print(f"迁移脚本: {filepath}")
        print(f"{'='*80}")

        # 读取文件
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"   读取失败: {e}")
            return False

        # 检查是否需要迁移
        needs_migration = any([
            'SingleCanalSolver' in content,
            'from solvers.canal_solver import CanalSolver' in content
        ])

        if not needs_migration:
            print(f"  ℹ 跳过: 已使用HydrostaticCanalSolver或无需迁移")
            return True

        # 备份
        if not dry_run:
            self.backup_file(filepath)

        # 应用转换
        all_changes = []
        original_content = content

        content, changes = self.convert_imports(content)
        all_changes.extend(changes)

        content, changes = self.convert_constructor_calls(content)
        all_changes.extend(changes)

        content, changes = self.convert_method_calls(content)
        all_changes.extend(changes)

        content, changes = self.add_result_validation(content, os.path.basename(filepath))
        all_changes.extend(changes)

        # 显示变更
        if all_changes:
            print("\n变更内容:")
            for change in all_changes:
                print(f"  • {change}")

        # 写入文件
        if not dry_run and content != original_content:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"\n   迁移成功")
                self.conversion_log.append((filepath, True, all_changes))
                return True
            except Exception as e:
                print(f"\n   写入失败: {e}")
                self.conversion_log.append((filepath, False, [str(e)]))
                return False
        elif dry_run:
            print(f"\n  ℹ 试运行模式 - 未修改文件")
            return True
        else:
            print(f"\n  ℹ 无需修改")
            return True

    def migrate_directory(self, directory: str, pattern: str = "*.py", dry_run: bool = False):
        """
        迁移目录下的所有脚本

        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            dry_run: 是否只是试运行
        """
        print(f"\n{'#'*80}")
        print(f"批量迁移目录: {directory}")
        print(f"匹配模式: {pattern}")
        print(f"模式: {'试运行' if dry_run else '实际迁移'}")
        print(f"{'#'*80}")

        # 查找所有Python文件
        script_files = list(Path(directory).glob(pattern))
        print(f"\n找到 {len(script_files)} 个脚本文件")

        success_count = 0
        for script_file in sorted(script_files):
            if self.migrate_script(str(script_file), dry_run=dry_run):
                success_count += 1

        # 总结
        print(f"\n{'#'*80}")
        print(f"迁移完成")
        print(f"{'#'*80}")
        print(f"  总计: {len(script_files)} 个文件")
        print(f"  成功: {success_count} 个文件")
        print(f"  失败: {len(script_files) - success_count} 个文件")

        if self.conversion_log:
            print(f"\n转换日志:")
            for filepath, success, changes in self.conversion_log:
                status = "" if success else ""
                print(f"  {status} {filepath}")
                for change in changes:
                    print(f"      {change}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="迁移脚本到HydrostaticCanalSolver")
    parser.add_argument('directory', help="脚本目录")
    parser.add_argument('--pattern', default='*.py', help="文件匹配模式")
    parser.add_argument('--dry-run', action='store_true', help="试运行（不修改文件）")
    parser.add_argument('--backup-dir', default='backups', help="备份目录")

    args = parser.parse_args()

    migrator = SolverMigrator(backup_dir=args.backup_dir)
    migrator.migrate_directory(
        directory=args.directory,
        pattern=args.pattern,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
