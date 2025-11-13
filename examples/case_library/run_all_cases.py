#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude Case Library Runner - 案例库运行器
============================================

Convenient tool to run all engineering cases or selected cases.
方便的工具来运行所有工程案例或选定的案例。

Usage / 使用方法:
    python run_all_cases.py                    # Run all cases / 运行所有案例
    python run_all_cases.py --case 1           # Run case 01 only / 只运行案例01
    python run_all_cases.py --case 1 2 3       # Run cases 01, 02, 03 / 运行案例01,02,03
    python run_all_cases.py --quick            # Quick mode (shorter simulations) / 快速模式
    python run_all_cases.py --benchmark        # Benchmark mode (measure performance) / 性能测试模式

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class CaseRunner:
    """
    Case runner for HydroClaude engineering cases
    HydroClaude工程案例运行器
    """

    def __init__(self, quick_mode: bool = False, benchmark_mode: bool = False):
        """
        Initialize case runner
        初始化案例运行器

        Args:
            quick_mode: Run cases in quick mode (shorter simulations)
            benchmark_mode: Measure and report performance metrics
        """
        self.quick_mode = quick_mode
        self.benchmark_mode = benchmark_mode
        self.case_dir = Path(__file__).parent

        # Case configurations / 案例配置
        self.cases = {
            1: {
                'name': 'Hydropower Plant',
                'name_cn': '水电站系统',
                'file': 'case_01_hydropower_plant.py',
                'description': '100MW Francis turbine with surge tank',
                'description_cn': '100MW法兰西斯水轮机含调压井',
                'est_time': '2-3 min' if not quick_mode else '30 sec'
            },
            2: {
                'name': 'Water Supply Network',
                'name_cn': '城市供水管网',
                'file': 'case_02_water_supply_network.py',
                'description': '50 nodes, 70 pipes, pump optimization',
                'description_cn': '50节点, 70管道, 水泵优化',
                'est_time': '1-2 min' if not quick_mode else '20 sec'
            },
            3: {
                'name': 'Irrigation Canal',
                'name_cn': '灌溉渠系统',
                'file': 'case_03_irrigation_canal.py',
                'description': '50km main canal, rotation irrigation',
                'description_cn': '50km主渠, 轮灌调度',
                'est_time': '1-2 min' if not quick_mode else '20 sec'
            },
            4: {
                'name': 'Urban Drainage',
                'name_cn': '城市排涝系统',
                'file': 'case_04_urban_drainage.py',
                'description': 'Preissmann Slot, rainfall-runoff',
                'description_cn': 'Preissmann Slot, 降雨径流',
                'est_time': '30-60 sec' if not quick_mode else '15 sec'
            },
            5: {
                'name': 'River Network',
                'name_cn': '河网系统',
                'file': 'case_05_river_network.py',
                'description': 'Compound channel, flood routing',
                'description_cn': '复式断面, 洪水演进',
                'est_time': '1-2 min' if not quick_mode else '20 sec'
            }
        }

        # Results tracking / 结果追踪
        self.results = {
            'passed': [],
            'failed': [],
            'times': {}
        }

    def print_header(self):
        """Print header / 打印标题"""
        print("\n" + "="*80)
        print("HydroClaude Engineering Cases Runner")
        print("HydroClaude 工程案例运行器")
        print("="*80)
        print()

        mode_str = []
        if self.quick_mode:
            mode_str.append("QUICK MODE / 快速模式")
        if self.benchmark_mode:
            mode_str.append("BENCHMARK MODE / 性能测试模式")

        if mode_str:
            print(f"Mode / 模式: {' + '.join(mode_str)}")
            print()

    def list_cases(self):
        """List all available cases / 列出所有可用案例"""
        print("Available Cases / 可用案例:")
        print()

        for case_id, case_info in sorted(self.cases.items()):
            print(f"Case {case_id}: {case_info['name']} / {case_info['name_cn']}")
            print(f"  Description: {case_info['description']}")
            print(f"  描述: {case_info['description_cn']}")
            print(f"  Estimated Time: {case_info['est_time']}")
            print(f"  File: {case_info['file']}")
            print()

    def run_case(self, case_id: int) -> bool:
        """
        Run a single case
        运行单个案例

        Args:
            case_id: Case ID (1-5)

        Returns:
            True if successful, False otherwise
        """
        if case_id not in self.cases:
            print(f" Error: Case {case_id} not found")
            return False

        case_info = self.cases[case_id]
        case_file = self.case_dir / case_info['file']

        if not case_file.exists():
            print(f" Error: Case file not found: {case_file}")
            return False

        print(f"\n{'='*80}")
        print(f"Running Case {case_id}: {case_info['name']} / {case_info['name_cn']}")
        print(f"{'='*80}\n")
        print(f"Description: {case_info['description']}")
        print(f"描述: {case_info['description_cn']}")
        print(f"Estimated Time: {case_info['est_time']}")
        print()

        # Prepare environment variables for quick mode
        env = os.environ.copy()
        if self.quick_mode:
            env['HYDROC_QUICK_MODE'] = '1'

        try:
            start_time = time.time()

            # Run the case
            result = subprocess.run(
                [sys.executable, str(case_file)],
                cwd=str(self.case_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            elapsed_time = time.time() - start_time

            # Check result
            if result.returncode == 0:
                print(f"\n Case {case_id} completed successfully in {elapsed_time:.2f}s")
                self.results['passed'].append(case_id)
                self.results['times'][case_id] = elapsed_time

                # Print relevant output
                if self.benchmark_mode or "Error" in result.stdout or "error" in result.stdout.lower():
                    print("\nOutput:")
                    print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)

                return True
            else:
                print(f"\n Case {case_id} FAILED with return code {result.returncode}")
                print(f"\nStdout:")
                print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
                print(f"\nStderr:")
                print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
                self.results['failed'].append(case_id)
                return False

        except subprocess.TimeoutExpired:
            print(f"\n Case {case_id} TIMEOUT (exceeded 10 minutes)")
            self.results['failed'].append(case_id)
            return False

        except Exception as e:
            print(f"\n Case {case_id} ERROR: {e}")
            self.results['failed'].append(case_id)
            return False

    def run_all_cases(self, case_ids: Optional[List[int]] = None):
        """
        Run all cases or selected cases
        运行所有案例或选定的案例

        Args:
            case_ids: List of case IDs to run, or None for all cases
        """
        if case_ids is None:
            case_ids = sorted(self.cases.keys())

        total_start = time.time()

        for case_id in case_ids:
            self.run_case(case_id)

        total_elapsed = time.time() - total_start

        # Print summary
        self.print_summary(total_elapsed)

    def print_summary(self, total_time: float):
        """
        Print execution summary
        打印执行总结

        Args:
            total_time: Total execution time in seconds
        """
        print(f"\n{'='*80}")
        print("EXECUTION SUMMARY / 执行总结")
        print(f"{'='*80}\n")

        total_cases = len(self.results['passed']) + len(self.results['failed'])
        passed_count = len(self.results['passed'])
        failed_count = len(self.results['failed'])

        print(f"Total Cases Run / 运行案例总数:    {total_cases}")
        print(f"Passed / 通过:                     {passed_count}")
        print(f"Failed / 失败:                     {failed_count}")
        print(f"Total Time / 总时间:               {total_time:.2f}s ({total_time/60:.1f} min)")
        print()

        if self.results['passed']:
            print("Passed Cases / 通过的案例:")
            for case_id in self.results['passed']:
                elapsed = self.results['times'].get(case_id, 0)
                case_name = self.cases[case_id]['name']
                print(f"   Case {case_id}: {case_name} ({elapsed:.2f}s)")
            print()

        if self.results['failed']:
            print("Failed Cases / 失败的案例:")
            for case_id in self.results['failed']:
                case_name = self.cases[case_id]['name']
                print(f"   Case {case_id}: {case_name}")
            print()

        # Performance summary (if benchmark mode)
        if self.benchmark_mode and self.results['times']:
            print("Performance Summary / 性能总结:")
            times = list(self.results['times'].values())
            print(f"  Average time / 平均时间:      {sum(times)/len(times):.2f}s")
            print(f"  Fastest case / 最快案例:     {min(times):.2f}s")
            print(f"  Slowest case / 最慢案例:     {max(times):.2f}s")
            print()

        # Success rate
        success_rate = (passed_count / total_cases * 100) if total_cases > 0 else 0
        status_emoji = "" if success_rate == 100 else "" if success_rate >= 80 else ""

        print(f"Success Rate / 成功率: {success_rate:.1f}% {status_emoji}")
        print()

        if success_rate == 100:
            print(" All cases completed successfully!")
            print(" 所有案例成功完成!")
        elif success_rate >= 80:
            print("  Most cases completed, but some failures occurred.")
            print("  大部分案例完成，但有一些失败。")
        else:
            print(" Many cases failed. Please check the errors above.")
            print(" 许多案例失败。请检查上面的错误。")

        print()


def main():
    """Main function / 主函数"""
    parser = argparse.ArgumentParser(
        description='HydroClaude Engineering Cases Runner / HydroClaude工程案例运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / 示例:
  %(prog)s                    Run all cases / 运行所有案例
  %(prog)s --case 1           Run case 01 only / 只运行案例01
  %(prog)s --case 1 2 3       Run cases 01, 02, 03 / 运行案例01,02,03
  %(prog)s --quick            Quick mode / 快速模式
  %(prog)s --benchmark        Benchmark mode / 性能测试模式
  %(prog)s --list             List all cases / 列出所有案例
        """
    )

    parser.add_argument(
        '--case', '-c',
        type=int,
        nargs='+',
        metavar='N',
        help='Case number(s) to run (1-5) / 要运行的案例编号 (1-5)'
    )

    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick mode (shorter simulations) / 快速模式 (较短的模拟)'
    )

    parser.add_argument(
        '--benchmark', '-b',
        action='store_true',
        help='Benchmark mode (measure performance) / 性能测试模式 (测量性能)'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available cases / 列出所有可用案例'
    )

    args = parser.parse_args()

    # Create runner
    runner = CaseRunner(quick_mode=args.quick, benchmark_mode=args.benchmark)

    # Print header
    runner.print_header()

    # List cases if requested
    if args.list:
        runner.list_cases()
        return 0

    # Run cases
    case_ids = args.case if args.case else None
    runner.run_all_cases(case_ids)

    # Exit code based on results
    if runner.results['failed']:
        return 1
    else:
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
