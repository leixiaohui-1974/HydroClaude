#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量验证所有脚本工具

运行所有示例脚本并生成验证报告

Author: Claude
Date: 2025-10-23
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import json


class ScriptValidator:
    """脚本验证器 - 批量运行和验证所有脚本"""

    def __init__(self, output_dir: str = "validation_reports"):
        """
        初始化验证器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = {}

    def analyze_script(self, filepath: str) -> Dict:
        """
        分析脚本使用的求解器

        Args:
            filepath: 脚本路径

        Returns:
            分析结果
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            analysis = {
                'path': filepath,
                'name': os.path.basename(filepath),
                'uses_hydrostatic': 'HydrostaticCanalSolver' in content,
                'uses_single': 'SingleCanalSolver' in content,
                'uses_canal': 'from solvers.canal_solver import CanalSolver' in content,
                'has_validation': 'result_validator' in content or 'ResultValidator' in content,
                'has_gate': 'SluiceGate' in content or 'Gate' in content,
                'analyzable': True
            }

            # 确定使用的求解器类型
            if analysis['uses_hydrostatic']:
                analysis['solver_type'] = 'HydrostaticCanalSolver ( 最新)'
            elif analysis['uses_single']:
                analysis['solver_type'] = 'SingleCanalSolver (需迁移)'
            elif analysis['uses_canal']:
                analysis['solver_type'] = 'CanalSolver (需迁移)'
            else:
                analysis['solver_type'] = '未知或无求解器'

            return analysis

        except Exception as e:
            return {
                'path': filepath,
                'name': os.path.basename(filepath),
                'analyzable': False,
                'error': str(e)
            }

    def run_script(self, filepath: str, timeout: int = 300) -> Dict:
        """
        运行单个脚本

        Args:
            filepath: 脚本路径
            timeout: 超时时间（秒）

        Returns:
            运行结果
        """
        print(f"\n{'='*80}")
        print(f"运行脚本: {os.path.basename(filepath)}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            # 运行脚本
            result = subprocess.run(
                [sys.executable, filepath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(filepath) or '.'
            )

            elapsed_time = time.time() - start_time

            # 分析输出
            success = result.returncode == 0
            has_error = result.returncode != 0 or 'Error' in result.stderr or 'Traceback' in result.stderr

            # 检查流量守恒
            flow_error = None
            if '流量守恒误差' in result.stdout or '流量误差' in result.stdout:
                import re
                error_match = re.search(r'流量.*?误差.*?(\d+\.?\d*)%', result.stdout)
                if error_match:
                    flow_error = float(error_match.group(1))

            output = {
                'success': success,
                'returncode': result.returncode,
                'elapsed_time': elapsed_time,
                'has_error': has_error,
                'flow_error': flow_error,
                'stdout_lines': len(result.stdout.split('\n')),
                'stderr_lines': len(result.stderr.split('\n')),
                'stdout': result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,  # 保留最后2000字符
                'stderr': result.stderr
            }

            status = " 成功" if success else " 失败"
            print(f"状态: {status}")
            print(f"耗时: {elapsed_time:.2f}秒")
            if flow_error is not None:
                print(f"流量误差: {flow_error:.6f}%")
            if has_error:
                print(f"错误输出: {result.stderr[:500]}")

            return output

        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            print(f" 超时 ({timeout}秒)")
            return {
                'success': False,
                'timeout': True,
                'elapsed_time': elapsed_time,
                'error': f'Timeout after {timeout}s'
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f" 运行失败: {e}")
            return {
                'success': False,
                'exception': True,
                'elapsed_time': elapsed_time,
                'error': str(e)
            }

    def validate_directory(
        self,
        directory: str,
        pattern: str = "*.py",
        run_scripts: bool = False,
        timeout: int = 300
    ):
        """
        验证目录下的所有脚本

        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            run_scripts: 是否实际运行脚本
            timeout: 每个脚本的超时时间
        """
        print(f"\n{'#'*80}")
        print(f"验证目录: {directory}")
        print(f"匹配模式: {pattern}")
        print(f"运行脚本: {'是' if run_scripts else '否（仅分析）'}")
        print(f"{'#'*80}")

        # 查找所有脚本
        script_files = sorted(Path(directory).glob(pattern))

        # 过滤掉工具脚本
        excluded = ['output_helper.py', '__init__.py', 'batch_modify_scripts.py', 'run_all.py']
        script_files = [f for f in script_files if f.name not in excluded]

        print(f"\n找到 {len(script_files)} 个脚本")

        # 分析所有脚本
        for script_file in script_files:
            script_path = str(script_file)
            analysis = self.analyze_script(script_path)

            if run_scripts and analysis.get('analyzable', False):
                run_result = self.run_script(script_path, timeout=timeout)
                analysis.update(run_result)

            self.results[script_path] = analysis

    def generate_report(self) -> str:
        """
        生成验证报告

        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 100)
        lines.append("脚本验证报告")
        lines.append("=" * 100)
        lines.append("")

        # 统计
        total = len(self.results)
        hydrostatic_count = sum(1 for r in self.results.values() if r.get('uses_hydrostatic', False))
        needs_migration = sum(1 for r in self.results.values()
                            if r.get('uses_single', False) or r.get('uses_canal', False))
        has_validation = sum(1 for r in self.results.values() if r.get('has_validation', False))

        lines.append(f"总计脚本数: {total}")
        lines.append(f"  已使用HydrostaticCanalSolver: {hydrostatic_count} ({hydrostatic_count/total*100:.1f}%)")
        lines.append(f"  需要迁移: {needs_migration} ({needs_migration/total*100:.1f}%)")
        lines.append(f"  已添加验证: {has_validation} ({has_validation/total*100:.1f}%)")
        lines.append("")

        # 成功运行的脚本
        run_scripts = [k for k, v in self.results.items() if 'success' in v]
        if run_scripts:
            success_count = sum(1 for k in run_scripts if self.results[k]['success'])
            lines.append(f"已运行脚本数: {len(run_scripts)}")
            lines.append(f"  成功: {success_count}")
            lines.append(f"  失败: {len(run_scripts) - success_count}")
            lines.append("")

        # 详细列表
        lines.append("=" * 100)
        lines.append("详细分析")
        lines.append("=" * 100)
        lines.append("")

        # 按求解器类型分组
        for category, title in [
            ('uses_hydrostatic', ' 已使用HydrostaticCanalSolver'),
            ('uses_single', ' 使用SingleCanalSolver（需迁移）'),
            ('uses_canal', ' 使用CanalSolver（需迁移）')
        ]:
            scripts = [k for k, v in self.results.items() if v.get(category, False)]
            if scripts:
                lines.append(f"\n{title} ({len(scripts)}个):")
                lines.append("-" * 100)
                for script in sorted(scripts):
                    result = self.results[script]
                    name = os.path.basename(script)

                    status_parts = [f"  • {name}"]

                    if 'success' in result:
                        status = "" if result['success'] else ""
                        time_str = f"{result['elapsed_time']:.1f}s"
                        status_parts.append(f"[{status} {time_str}]")

                        if result.get('flow_error') is not None:
                            error = result['flow_error']
                            if error < 0.01:
                                status_parts.append(f"误差:{error:.6f}% (优秀)")
                            elif error < 0.1:
                                status_parts.append(f"误差:{error:.4f}% (良好)")
                            elif error < 1.0:
                                status_parts.append(f"误差:{error:.2f}% (可接受)")
                            else:
                                status_parts.append(f"误差:{error:.2f}% (需改进)")

                    if result.get('has_validation'):
                        status_parts.append("[已验证]")

                    lines.append(" ".join(status_parts))

        # 未知类型
        unknown = [k for k, v in self.results.items()
                  if not any(v.get(cat, False) for cat in ['uses_hydrostatic', 'uses_single', 'uses_canal'])]
        if unknown:
            lines.append(f"\nℹ 其他脚本 ({len(unknown)}个):")
            lines.append("-" * 100)
            for script in sorted(unknown):
                lines.append(f"  • {os.path.basename(script)}")

        lines.append("")
        lines.append("=" * 100)

        return "\n".join(lines)

    def save_report(self, filename: str = "validation_report.txt"):
        """
        保存报告

        Args:
            filename: 文件名
        """
        report = self.generate_report()
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n 报告已保存: {filepath}")

        # 同时保存JSON格式
        json_path = os.path.join(self.output_dir, filename.replace('.txt', '.json'))
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f" JSON数据已保存: {json_path}")

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="批量验证所有脚本")
    parser.add_argument('directory', help="脚本目录")
    parser.add_argument('--pattern', default='*.py', help="文件匹配模式")
    parser.add_argument('--run', action='store_true', help="实际运行脚本（否则仅分析）")
    parser.add_argument('--timeout', type=int, default=300, help="每个脚本超时时间（秒）")
    parser.add_argument('--output-dir', default='validation_reports', help="输出目录")

    args = parser.parse_args()

    validator = ScriptValidator(output_dir=args.output_dir)
    validator.validate_directory(
        directory=args.directory,
        pattern=args.pattern,
        run_scripts=args.run,
        timeout=args.timeout
    )

    report = validator.save_report()
    print("\n")
    print(report)


if __name__ == "__main__":
    main()
