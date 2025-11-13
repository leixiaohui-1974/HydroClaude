#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
旧代码清理工具 - 删除过时的求解器和功能

不考虑向后兼容性，彻底清理旧版本代码

Author: Claude
Date: 2025-10-23
"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Dict, Tuple


class LegacyCodeCleaner:
    """旧代码清理器"""

    # 明确要删除的旧求解器
    LEGACY_SOLVERS = [
        'solvers/single_canal_solver.py',
        'solvers/canal_solver.py',
        'solvers/canal_solver_anderson.py',
        'solvers/canal_solver_improved.py',
    ]

    # 可能的旧版本文件（需要分析）
    POTENTIAL_LEGACY = [
        ('solvers/hydrostatic_reconstruction.py', 'solvers/hydrostatic_reconstruction_v2.py', 'solvers/hydrostatic_reconstruction_v3.py'),
        ('solvers/hybrid_solver.py', 'solvers/hybrid_solver_enhanced.py'),
        ('solvers/digital_twin.py', 'solvers/digital_twin_advanced.py'),
        ('solvers/fvm_steady_solver.py', 'solvers/fvm_steady_full.py'),
        ('solvers/mpc_scheduler.py', 'solvers/mpc_scheduler_fast.py', 'solvers/mpc_scheduler_parallel.py'),
    ]

    def __init__(self, backup_dir: str = 'legacy_backup'):
        """初始化清理器"""
        self.backup_dir = backup_dir
        self.analysis_report = {}
        self.deleted_files = []
        self.affected_files = {}

    def analyze_file_usage(self, filepath: str) -> List[str]:
        """
        分析哪些文件使用了指定文件

        Args:
            filepath: 要分析的文件路径

        Returns:
            使用该文件的文件列表
        """
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        using_files = []

        # 搜索所有Python文件
        for py_file in Path('.').rglob('*.py'):
            if py_file.name.endswith('.bak') or 'backup' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查导入
                patterns = [
                    f'from {filepath.replace("/", ".").replace(".py", "")} import',
                    f'import {module_name}',
                    f'from solvers.{module_name} import',
                ]

                for pattern in patterns:
                    if pattern in content:
                        using_files.append(str(py_file))
                        break

            except:
                pass

        return using_files

    def analyze_version_group(self, files: Tuple[str, ...]) -> Dict:
        """
        分析一组版本文件，确定哪个是最新的

        Args:
            files: 文件路径元组

        Returns:
            分析结果
        """
        existing = [f for f in files if os.path.exists(f)]
        if not existing:
            return {'action': 'skip', 'reason': '文件不存在'}

        # 简单策略：保留最后一个（通常是最新版本）
        if len(existing) == 1:
            return {
                'action': 'keep',
                'keep': existing[0],
                'delete': [],
                'reason': '仅有一个文件'
            }

        # 检查文件大小和修改时间
        file_stats = []
        for f in existing:
            stat = os.stat(f)
            file_stats.append({
                'path': f,
                'size': stat.st_size,
                'mtime': stat.st_mtime
            })

        # 按修改时间排序，保留最新的
        file_stats.sort(key=lambda x: x['mtime'], reverse=True)
        latest = file_stats[0]['path']
        to_delete = [f['path'] for f in file_stats[1:]]

        return {
            'action': 'consolidate',
            'keep': latest,
            'delete': to_delete,
            'reason': f'保留最新版本 (修改时间: {file_stats[0]["mtime"]})'
        }

    def analyze_all(self) -> Dict:
        """
        分析所有旧代码

        Returns:
            完整分析报告
        """
        print("=" * 80)
        print("旧代码分析")
        print("=" * 80)

        report = {
            'legacy_solvers': {},
            'version_groups': {},
            'total_to_delete': 0,
            'total_to_keep': 0,
            'affected_examples': set()
        }

        # 分析明确的旧求解器
        print("\n明确的旧求解器:")
        print("-" * 80)
        for solver_path in self.LEGACY_SOLVERS:
            if not os.path.exists(solver_path):
                print(f"  ⊘ {solver_path} (不存在)")
                continue

            using_files = self.analyze_file_usage(solver_path)
            report['legacy_solvers'][solver_path] = {
                'exists': True,
                'using_files': using_files,
                'count': len(using_files)
            }

            print(f"   {solver_path}")
            print(f"    使用数: {len(using_files)}")
            if using_files:
                for f in using_files[:5]:  # 只显示前5个
                    print(f"      - {f}")
                if len(using_files) > 5:
                    print(f"      ... 还有 {len(using_files) - 5} 个文件")

            report['total_to_delete'] += 1
            report['affected_examples'].update(using_files)

        # 分析版本组
        print("\n版本文件组分析:")
        print("-" * 80)
        for file_group in self.POTENTIAL_LEGACY:
            group_name = os.path.basename(file_group[0]).replace('.py', '')
            analysis = self.analyze_version_group(file_group)
            report['version_groups'][group_name] = analysis

            if analysis['action'] == 'skip':
                continue
            elif analysis['action'] == 'keep':
                print(f"   {group_name}: {analysis['reason']}")
                report['total_to_keep'] += 1
            elif analysis['action'] == 'consolidate':
                print(f"  ⟳ {group_name}:")
                print(f"    保留: {analysis['keep']}")
                print(f"    删除: {', '.join(analysis['delete'])}")
                report['total_to_delete'] += len(analysis['delete'])
                report['total_to_keep'] += 1

        # 总结
        print("\n" + "=" * 80)
        print("分析总结")
        print("=" * 80)
        print(f"  待删除文件数: {report['total_to_delete']}")
        print(f"  保留文件数: {report['total_to_keep']}")
        print(f"  受影响的示例脚本数: {len(report['affected_examples'])}")

        self.analysis_report = report
        return report

    def backup_file(self, filepath: str):
        """备份文件"""
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_path = os.path.join(self.backup_dir, filepath.replace('/', '_'))
        shutil.copy2(filepath, backup_path)
        print(f"     备份到: {backup_path}")

    def delete_legacy_solvers(self, dry_run: bool = False):
        """
        删除旧求解器

        Args:
            dry_run: 是否试运行
        """
        print("\n" + "=" * 80)
        print("删除旧求解器")
        print("=" * 80)

        for solver_path in self.LEGACY_SOLVERS:
            if not os.path.exists(solver_path):
                continue

            print(f"\n处理: {solver_path}")

            if not dry_run:
                self.backup_file(solver_path)
                os.remove(solver_path)
                self.deleted_files.append(solver_path)
                print(f"     已删除")
            else:
                print(f"     试运行 - 将删除")

    def consolidate_versions(self, dry_run: bool = False):
        """
        合并版本文件

        Args:
            dry_run: 是否试运行
        """
        print("\n" + "=" * 80)
        print("合并版本文件")
        print("=" * 80)

        for file_group in self.POTENTIAL_LEGACY:
            analysis = self.analyze_version_group(file_group)

            if analysis['action'] != 'consolidate':
                continue

            group_name = os.path.basename(file_group[0]).replace('.py', '')
            print(f"\n处理组: {group_name}")
            print(f"  保留: {analysis['keep']}")

            for old_file in analysis['delete']:
                print(f"  删除: {old_file}")
                if not dry_run:
                    self.backup_file(old_file)
                    os.remove(old_file)
                    self.deleted_files.append(old_file)
                    print(f"     已删除")
                else:
                    print(f"     试运行 - 将删除")

    def generate_migration_guide(self) -> str:
        """
        生成迁移指南

        Returns:
            迁移指南文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append("旧代码迁移指南")
        lines.append("=" * 80)
        lines.append("")

        if 'legacy_solvers' in self.analysis_report:
            lines.append("## 已删除的旧求解器")
            lines.append("")
            for solver_path, info in self.analysis_report['legacy_solvers'].items():
                if not info.get('exists'):
                    continue

                solver_name = os.path.basename(solver_path).replace('.py', '')
                lines.append(f"### {solver_name}")
                lines.append(f"- 文件: `{solver_path}`")
                lines.append(f"- 迁移到: `HydrostaticCanalSolver`")
                lines.append("")

                if info['using_files']:
                    lines.append("需要更新的文件:")
                    for f in info['using_files']:
                        lines.append(f"  - {f}")
                    lines.append("")

                # 迁移说明
                if 'SingleCanalSolver' in solver_name:
                    lines.append("迁移步骤:")
                    lines.append("```python")
                    lines.append("# 旧代码:")
                    lines.append("from solvers.single_canal_solver import SingleCanalSolver")
                    lines.append("solver = SingleCanalSolver(total_length=L, structures=[...], nx_total=N, ...)")
                    lines.append("")
                    lines.append("# 新代码:")
                    lines.append("from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver")
                    lines.append("solver = HydrostaticCanalSolver(length=L, internal_structures=[(pos, obj), ...], nx=N, ...)")
                    lines.append("```")
                    lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def save_report(self, filename: str = 'legacy_cleanup_report.txt'):
        """保存清理报告"""
        report = []
        report.append("=" * 80)
        report.append("旧代码清理报告")
        report.append("=" * 80)
        report.append("")
        report.append(f"删除文件数: {len(self.deleted_files)}")
        report.append("")
        report.append("已删除文件列表:")
        for f in self.deleted_files:
            report.append(f"  - {f}")
        report.append("")

        report_text = "\n".join(report)
        report_text += "\n\n" + self.generate_migration_guide()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"\n 清理报告已保存: {filename}")
        return report_text


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="清理旧代码")
    parser.add_argument('--dry-run', action='store_true', help="试运行（不实际删除）")
    parser.add_argument('--backup-dir', default='legacy_backup', help="备份目录")

    args = parser.parse_args()

    cleaner = LegacyCodeCleaner(backup_dir=args.backup_dir)

    # 分析
    cleaner.analyze_all()

    # 确认
    if not args.dry_run:
        print("\n" + "!" * 80)
        print("警告: 即将删除旧代码！所有文件将先备份。")
        print("!" * 80)
        response = input("\n确认继续吗？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return

    # 执行清理
    cleaner.delete_legacy_solvers(dry_run=args.dry_run)
    cleaner.consolidate_versions(dry_run=args.dry_run)

    # 生成报告
    if not args.dry_run:
        cleaner.save_report()


if __name__ == "__main__":
    main()
