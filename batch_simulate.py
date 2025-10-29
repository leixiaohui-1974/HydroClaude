#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量运行仿真工具

支持：
1. 批量运行多个配置文件
2. 并行运行（可选）
3. 生成汇总报告
4. 失败重试

用法:
    python batch_simulate.py config1.json config2.json config3.json
    python batch_simulate.py examples/config_driven/*.json
    python batch_simulate.py --parallel 4 examples/config_driven/*.json

作者: HydroClaude Team
日期: 2025-10-28
"""

import sys
import os
from pathlib import Path
import argparse
import subprocess
import time
import json
from datetime import datetime
from typing import List, Dict
import concurrent.futures

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


class BatchSimulator:
    """批量仿真运行器"""

    def __init__(self, config_files: List[str], parallel: int = 1, retry: int = 0):
        """
        初始化

        Args:
            config_files: 配置文件列表
            parallel: 并行运行数量（默认1=串行）
            retry: 失败重试次数（默认0=不重试）
        """
        self.config_files = [Path(f) for f in config_files]
        self.parallel = parallel
        self.retry = retry
        self.results = []

    def run_single(self, config_file: Path) -> Dict:
        """
        运行单个仿真

        Args:
            config_file: 配置文件路径

        Returns:
            结果字典
        """
        print(f"\n{'='*80}")
        print(f"运行: {config_file.name}")
        print(f"{'='*80}")

        start_time = time.time()

        # 尝试运行
        attempts = 0
        max_attempts = self.retry + 1
        success = False
        stderr = ""
        stdout = ""

        while attempts < max_attempts and not success:
            attempts += 1

            if attempts > 1:
                print(f"  重试 {attempts}/{max_attempts}...")

            try:
                result = subprocess.run(
                    [sys.executable, 'simulate.py', str(config_file)],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10分钟超时
                )

                success = (result.returncode == 0)
                stdout = result.stdout
                stderr = result.stderr

                if success:
                    print(f"  ✓ 成功")
                else:
                    print(f"  ✗ 失败 (返回码: {result.returncode})")
                    if attempts < max_attempts:
                        time.sleep(2)  # 等待2秒后重试

            except subprocess.TimeoutExpired:
                print(f"  ⏱️  超时（>10分钟）")
                stderr = "Timeout after 10 minutes"
                if attempts < max_attempts:
                    time.sleep(2)

            except Exception as e:
                print(f"  ❌ 异常: {e}")
                stderr = str(e)
                if attempts < max_attempts:
                    time.sleep(2)

        wall_time = time.time() - start_time

        # 尝试读取统计信息
        stats = None
        try:
            # 从配置文件读取输出目录
            with open(config_file, 'r') as f:
                config = json.load(f)
                output_dir = Path(config['output']['directory'])
                stats_file = output_dir / 'statistics.json'

                if stats_file.exists():
                    with open(stats_file, 'r') as sf:
                        stats = json.load(sf)
        except:
            pass

        return {
            'config_file': str(config_file),
            'name': config_file.stem,
            'success': success,
            'attempts': attempts,
            'wall_time': wall_time,
            'statistics': stats,
            'stderr': stderr if not success else None
        }

    def run_all(self):
        """运行所有仿真"""
        print("="*80)
        print("HydroClaude 批量仿真运行器")
        print("="*80)
        print(f"配置文件数: {len(self.config_files)}")
        print(f"并行度: {self.parallel}")
        print(f"重试次数: {self.retry}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        start_time = time.time()

        if self.parallel == 1:
            # 串行运行
            for config_file in self.config_files:
                result = self.run_single(config_file)
                self.results.append(result)
        else:
            # 并行运行
            print(f"使用 {self.parallel} 个并行进程\n")

            with concurrent.futures.ProcessPoolExecutor(max_workers=self.parallel) as executor:
                futures = {executor.submit(self.run_single, cf): cf for cf in self.config_files}

                for future in concurrent.futures.as_completed(futures):
                    config_file = futures[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                    except Exception as e:
                        print(f"✗ {config_file.name} 异常: {e}")
                        self.results.append({
                            'config_file': str(config_file),
                            'name': config_file.stem,
                            'success': False,
                            'wall_time': 0,
                            'stderr': str(e)
                        })

        total_time = time.time() - start_time

        # 生成报告
        self.generate_report(total_time)

    def generate_report(self, total_time: float):
        """生成汇总报告"""
        print("\n" + "="*80)
        print("批量运行汇总")
        print("="*80)

        success_count = sum(1 for r in self.results if r['success'])
        total_count = len(self.results)

        print(f"\n总计: {total_count} 个配置")
        print(f"成功: {success_count} ({success_count/total_count*100:.1f}%)")
        print(f"失败: {total_count - success_count}")
        print(f"总耗时: {total_time:.2f} s")
        print()

        # 详细结果表格
        print(f"{'配置文件':<30} {'状态':<10} {'模拟时间':<12} {'墙钟时间':<12} {'步数':<10}")
        print("-" * 80)

        for r in self.results:
            status = "✓ 成功" if r['success'] else "✗ 失败"

            sim_time = "N/A"
            wall_time = f"{r['wall_time']:.2f}s"
            n_steps = "N/A"

            if r['statistics']:
                sim_stats = r['statistics'].get('simulation', {})
                if 'sim_time' in sim_stats:
                    sim_time = f"{sim_stats['sim_time']:.2f}s"
                if 'n_steps' in sim_stats:
                    n_steps = str(sim_stats['n_steps'])

            print(f"{r['name']:<30} {status:<10} {sim_time:<12} {wall_time:<12} {n_steps:<10}")

        print()

        # 失败详情
        failures = [r for r in self.results if not r['success']]
        if failures:
            print("失败详情:")
            for r in failures:
                print(f"  - {r['name']}")
                if r.get('stderr'):
                    # 只显示前200个字符
                    error_msg = r['stderr'][:200]
                    print(f"    错误: {error_msg}...")
            print()

        # 保存JSON报告
        report_file = Path('batch_simulation_report.json')
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_count': total_count,
            'success_count': success_count,
            'failure_count': total_count - success_count,
            'total_time': total_time,
            'parallel': self.parallel,
            'results': self.results
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"详细报告已保存: {report_file}")
        print()

        # 总结
        print("="*80)
        if success_count == total_count:
            print("✅ 所有仿真成功完成！")
        elif success_count > 0:
            print(f"⚠️  部分仿真成功 ({success_count}/{total_count})")
        else:
            print("❌ 所有仿真失败")
        print("="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='HydroClaude 批量仿真运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 串行运行多个配置
  python batch_simulate.py config1.json config2.json config3.json

  # 使用通配符
  python batch_simulate.py examples/config_driven/*.json

  # 并行运行（4个进程）
  python batch_simulate.py --parallel 4 examples/config_driven/*.json

  # 失败重试1次
  python batch_simulate.py --retry 1 examples/config_driven/*.json
        """
    )

    parser.add_argument('configs', nargs='+', help='配置文件路径（支持通配符）')
    parser.add_argument('--parallel', '-p', type=int, default=1,
                        help='并行运行数量（默认1=串行）')
    parser.add_argument('--retry', '-r', type=int, default=0,
                        help='失败重试次数（默认0=不重试）')

    args = parser.parse_args()

    # 检查配置文件
    config_files = []
    for pattern in args.configs:
        path = Path(pattern)
        if path.exists() and path.is_file():
            config_files.append(str(path))
        else:
            # 尝试通配符
            from glob import glob
            matches = glob(pattern)
            config_files.extend(matches)

    if not config_files:
        print("❌ 错误: 未找到任何配置文件")
        sys.exit(1)

    # 去重
    config_files = list(set(config_files))

    try:
        runner = BatchSimulator(config_files, parallel=args.parallel, retry=args.retry)
        runner.run_all()

    except KeyboardInterrupt:
        print("\n\n⚠️  批量运行被用户中断")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 批量运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
