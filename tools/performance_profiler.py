#!/usr/bin/env python3
"""
HydroClaude 性能分析和基准测试工具

功能:
- 测试不同网格尺寸的性能
- 对比 Numba 加速效果
- 分析各模块计算时间占比
- 生成性能报告和优化建议

用法:
    python tools/performance_profiler.py --grid-sizes 50,100,200 --days 10
    python tools/performance_profiler.py --profile-modules --days 5
    python tools/performance_profiler.py --compare-numba --grid-size 100

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
import time
import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        """初始化分析器"""
        self.results = {}

    def benchmark_grid_scaling(self, grid_sizes, n_days=10, use_numba=False):
        """
        测试网格规模对性能的影响

        Parameters:
        -----------
        grid_sizes : list
            网格数量列表
        n_days : int
            模拟天数
        use_numba : bool
            是否使用Numba加速
        """
        print("\n" + "=" * 70)
        print(f"网格规模性能测试 (Numba={'ON' if use_numba else 'OFF'})")
        print("=" * 70)
        print(f"模拟时长: {n_days} 天")
        print(f"测试网格: {grid_sizes}")

        results = {
            'grid_sizes': [],
            'total_time': [],
            'time_per_step': [],
            'memory_usage': []
        }

        for n_cells in grid_sizes:
            print(f"\n测试网格: {n_cells} cells")
            print("-" * 70)

            dx = 10000.0 / n_cells  # 固定总长度10km

            # 初始化求解器
            temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=use_numba)
            do_solver = DissolvedOxygenSolver(n_cells, dx, use_numba=use_numba)
            ice_solver = IceCoverSolver(n_cells=n_cells)
            nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=use_numba)
            algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=use_numba)

            # 初始条件
            temp_solver.T = np.full(n_cells, 2.0)
            do_solver.DO = np.full(n_cells, 12.0)
            do_solver.BOD = np.full(n_cells, 3.0)
            ice_solver.h_ice = np.zeros(n_cells)
            nutrients_solver.NH4 = np.full(n_cells, 0.3)
            nutrients_solver.NO3 = np.full(n_cells, 1.2)
            nutrients_solver.PO4 = np.full(n_cells, 0.08)
            nutrients_solver.OrgN = np.full(n_cells, 0.5)
            nutrients_solver.OrgP = np.full(n_cells, 0.05)
            algae_solver.Chla = np.full(n_cells, 12.0)

            # 环境条件
            u = np.full(n_cells, 0.3)
            h = np.full(n_cells, 2.5)
            manning_n = np.full(n_cells, 0.03)

            # 运行基准测试
            dt = 3600.0
            n_steps = n_days * 24

            start_time = time.time()

            for step in range(n_steps):
                T_air = -5.0
                I_0 = np.full(n_cells, 100.0)

                # 推进所有模块
                T = temp_solver.step(dt, u, h, T_air, I_0.mean(), 5.0, 0.7)
                ice_state = ice_solver.step(dt, T_air, T)
                nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
                algae_state = algae_solver.step(dt, u, h, T, I_0,
                                               nutrients_solver.NH4,
                                               nutrients_solver.NO3,
                                               nutrients_solver.PO4)
                do_state = do_solver.step(dt, u, h, T, manning_n)

            elapsed_time = time.time() - start_time

            # 统计
            time_per_step = elapsed_time / n_steps * 1000  # ms
            results['grid_sizes'].append(n_cells)
            results['total_time'].append(elapsed_time)
            results['time_per_step'].append(time_per_step)
            results['memory_usage'].append(n_cells * 8 * 15 / 1024)  # KB (估算)

            print(f"  总耗时: {elapsed_time:.2f} 秒")
            print(f"  每步耗时: {time_per_step:.2f} ms")
            print(f"  内存占用: {results['memory_usage'][-1]:.1f} KB (估算)")

        # 转换为numpy数组
        for key in results:
            results[key] = np.array(results[key])

        self.results['grid_scaling'] = results
        return results

    def compare_numba_acceleration(self, grid_size=100, n_days=10):
        """
        对比Numba加速效果

        Parameters:
        -----------
        grid_size : int
            网格数量
        n_days : int
            模拟天数
        """
        print("\n" + "=" * 70)
        print("Numba 加速效果对比")
        print("=" * 70)
        print(f"网格尺寸: {grid_size} cells")
        print(f"模拟时长: {n_days} 天")

        results = {}

        for use_numba in [False, True]:
            print(f"\n运行测试: Numba = {use_numba}")
            print("-" * 70)

            # 运行基准测试
            benchmark_result = self.benchmark_single_run(grid_size, n_days, use_numba)

            key = 'with_numba' if use_numba else 'without_numba'
            results[key] = benchmark_result

        # 计算加速比
        speedup = results['without_numba']['total_time'] / results['with_numba']['total_time']

        print("\n" + "=" * 70)
        print("加速效果汇总")
        print("=" * 70)
        print(f"无Numba: {results['without_numba']['total_time']:.2f} 秒")
        print(f"有Numba: {results['with_numba']['total_time']:.2f} 秒")
        print(f"加速比: {speedup:.2f}x")

        if speedup > 2.0:
            print(f"✓ Numba 加速显著 ({speedup:.1f}x)，强烈推荐启用!")
        elif speedup > 1.2:
            print(f"✓ Numba 加速有效 ({speedup:.1f}x)，建议启用")
        else:
            print(f"⚠ Numba 加速不明显 ({speedup:.1f}x)")

        self.results['numba_comparison'] = {
            'without_numba': results['without_numba'],
            'with_numba': results['with_numba'],
            'speedup': speedup
        }

        return results

    def profile_modules(self, grid_size=100, n_days=5):
        """
        分析各模块计算时间占比

        Parameters:
        -----------
        grid_size : int
            网格数量
        n_days : int
            模拟天数
        """
        print("\n" + "=" * 70)
        print("模块性能分析")
        print("=" * 70)
        print(f"网格尺寸: {grid_size} cells")
        print(f"模拟时长: {n_days} 天")

        n_cells = grid_size
        dx = 10000.0 / n_cells

        # 初始化求解器
        temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
        do_solver = DissolvedOxygenSolver(n_cells, dx, use_numba=False)
        ice_solver = IceCoverSolver(n_cells=n_cells)
        nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
        algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)

        # 初始条件
        temp_solver.T = np.full(n_cells, 2.0)
        do_solver.DO = np.full(n_cells, 12.0)
        do_solver.BOD = np.full(n_cells, 3.0)
        ice_solver.h_ice = np.zeros(n_cells)
        nutrients_solver.NH4 = np.full(n_cells, 0.3)
        nutrients_solver.NO3 = np.full(n_cells, 1.2)
        nutrients_solver.PO4 = np.full(n_cells, 0.08)
        nutrients_solver.OrgN = np.full(n_cells, 0.5)
        nutrients_solver.OrgP = np.full(n_cells, 0.05)
        algae_solver.Chla = np.full(n_cells, 12.0)

        # 环境条件
        u = np.full(n_cells, 0.3)
        h = np.full(n_cells, 2.5)
        manning_n = np.full(n_cells, 0.03)

        # 分析各模块性能
        dt = 3600.0
        n_steps = n_days * 24

        module_times = {
            'water_temperature': 0.0,
            'ice_cover': 0.0,
            'nutrients': 0.0,
            'phytoplankton': 0.0,
            'dissolved_oxygen': 0.0,
            'coupling': 0.0
        }

        print("\n运行性能分析...")

        for step in range(n_steps):
            T_air = -5.0
            I_0 = np.full(n_cells, 100.0)

            # 水温
            t0 = time.time()
            T = temp_solver.step(dt, u, h, T_air, I_0.mean(), 5.0, 0.7)
            module_times['water_temperature'] += time.time() - t0

            # 冰盖
            t0 = time.time()
            ice_state = ice_solver.step(dt, T_air, T)
            module_times['ice_cover'] += time.time() - t0

            # 营养盐
            t0 = time.time()
            nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
            module_times['nutrients'] += time.time() - t0

            # 藻类
            t0 = time.time()
            algae_state = algae_solver.step(dt, u, h, T, I_0,
                                           nutrients_solver.NH4,
                                           nutrients_solver.NO3,
                                           nutrients_solver.PO4)
            module_times['phytoplankton'] += time.time() - t0

            # 溶解氧
            t0 = time.time()
            do_state = do_solver.step(dt, u, h, T, manning_n)
            module_times['dissolved_oxygen'] += time.time() - t0

            # 耦合
            t0 = time.time()
            dt_day = dt / 86400.0
            do_solver.DO += algae_state['DO_production'] * dt_day
            nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
            nutrients_solver.NO3 -= algae_state['NO3_uptake'] * dt_day
            nutrients_solver.PO4 -= algae_state['PO4_uptake'] * dt_day
            module_times['coupling'] += time.time() - t0

        total_time = sum(module_times.values())

        print("\n" + "=" * 70)
        print("模块计算时间分布")
        print("=" * 70)
        print(f"{'模块':<20} {'时间 (s)':<12} {'占比 (%)':<10} {'每步 (ms)':<12}")
        print("-" * 70)

        for module, t in sorted(module_times.items(), key=lambda x: x[1], reverse=True):
            percentage = t / total_time * 100
            time_per_step = t / n_steps * 1000
            print(f"{module:<20} {t:10.3f}   {percentage:8.1f}   {time_per_step:10.2f}")

        print("-" * 70)
        print(f"{'总计':<20} {total_time:10.3f}   {100.0:8.1f}   {total_time/n_steps*1000:10.2f}")

        self.results['module_profiling'] = module_times
        return module_times

    def benchmark_single_run(self, grid_size, n_days, use_numba):
        """单次基准测试"""
        n_cells = grid_size
        dx = 10000.0 / n_cells

        # 初始化
        temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=use_numba)
        do_solver = DissolvedOxygenSolver(n_cells, dx, use_numba=use_numba)
        ice_solver = IceCoverSolver(n_cells=n_cells)
        nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=use_numba)
        algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=use_numba)

        temp_solver.T = np.full(n_cells, 2.0)
        do_solver.DO = np.full(n_cells, 12.0)
        do_solver.BOD = np.full(n_cells, 3.0)
        ice_solver.h_ice = np.zeros(n_cells)
        nutrients_solver.NH4 = np.full(n_cells, 0.3)
        nutrients_solver.NO3 = np.full(n_cells, 1.2)
        nutrients_solver.PO4 = np.full(n_cells, 0.08)
        nutrients_solver.OrgN = np.full(n_cells, 0.5)
        nutrients_solver.OrgP = np.full(n_cells, 0.05)
        algae_solver.Chla = np.full(n_cells, 12.0)

        u = np.full(n_cells, 0.3)
        h = np.full(n_cells, 2.5)
        manning_n = np.full(n_cells, 0.03)

        dt = 3600.0
        n_steps = n_days * 24

        start_time = time.time()

        for step in range(n_steps):
            T_air = -5.0
            I_0 = np.full(n_cells, 100.0)

            T = temp_solver.step(dt, u, h, T_air, I_0.mean(), 5.0, 0.7)
            ice_state = ice_solver.step(dt, T_air, T)
            nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
            algae_state = algae_solver.step(dt, u, h, T, I_0,
                                           nutrients_solver.NH4,
                                           nutrients_solver.NO3,
                                           nutrients_solver.PO4)
            do_state = do_solver.step(dt, u, h, T, manning_n)

        elapsed_time = time.time() - start_time

        return {
            'total_time': elapsed_time,
            'time_per_step': elapsed_time / n_steps * 1000,
            'grid_size': grid_size,
            'n_steps': n_steps
        }

    def plot_results(self, output_file='performance_analysis.png'):
        """绘制性能分析图表"""
        print(f"\n生成性能分析图表: {output_file}")

        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. 网格规模性能
        if 'grid_scaling' in self.results:
            ax1 = fig.add_subplot(gs[0, 0])
            data = self.results['grid_scaling']
            ax1.plot(data['grid_sizes'], data['time_per_step'], 'o-', linewidth=2, markersize=8)
            ax1.set_xlabel('Grid Size (cells)')
            ax1.set_ylabel('Time per Step (ms)')
            ax1.set_title('Performance vs Grid Size')
            ax1.grid(True, alpha=0.3)
            ax1.set_xscale('log')
            ax1.set_yscale('log')

        # 2. 模块时间分布饼图
        if 'module_profiling' in self.results:
            ax2 = fig.add_subplot(gs[0, 1])
            data = self.results['module_profiling']
            labels = [k.replace('_', ' ').title() for k in data.keys()]
            sizes = list(data.values())
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc', '#c2c2f0']
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
            ax2.set_title('Module Time Distribution')

        # 3. Numba加速对比
        if 'numba_comparison' in self.results:
            ax3 = fig.add_subplot(gs[1, 0])
            data = self.results['numba_comparison']
            categories = ['Without Numba', 'With Numba']
            times = [data['without_numba']['total_time'], data['with_numba']['total_time']]
            bars = ax3.bar(categories, times, color=['#ff6b6b', '#4ecdc4'])
            ax3.set_ylabel('Total Time (s)')
            ax3.set_title(f"Numba Acceleration ({data['speedup']:.2f}x)")
            ax3.grid(True, alpha=0.3, axis='y')

            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}s', ha='center', va='bottom')

        # 4. 性能建议
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')

        recommendations = "Performance Optimization Recommendations\n" + "="*40 + "\n\n"

        if 'numba_comparison' in self.results:
            speedup = self.results['numba_comparison']['speedup']
            if speedup > 2.0:
                recommendations += f"✓ Enable Numba: {speedup:.1f}x speedup!\n\n"
            else:
                recommendations += f"• Numba speedup: {speedup:.1f}x (moderate)\n\n"

        if 'module_profiling' in self.results:
            data = self.results['module_profiling']
            total = sum(data.values())
            sorted_modules = sorted(data.items(), key=lambda x: x[1], reverse=True)
            recommendations += "Top 3 slowest modules:\n"
            for i, (module, time_val) in enumerate(sorted_modules[:3], 1):
                pct = time_val / total * 100
                recommendations += f"  {i}. {module}: {pct:.1f}%\n"

        recommendations += "\nGeneral tips:\n"
        recommendations += "  • Use coarser grids for long simulations\n"
        recommendations += "  • Enable Numba for production runs\n"
        recommendations += "  • Consider parallel processing for\n"
        recommendations += "    multiple scenarios\n"

        ax4.text(0.05, 0.95, recommendations, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.suptitle('HydroClaude Performance Analysis', fontsize=16, fontweight='bold')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ 图表已保存: {output_file}")
        plt.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='HydroClaude Performance Profiler')
    parser.add_argument('--grid-sizes', type=str, default='50,100,200',
                       help='Comma-separated grid sizes (default: 50,100,200)')
    parser.add_argument('--days', type=int, default=10,
                       help='Simulation days (default: 10)')
    parser.add_argument('--profile-modules', action='store_true',
                       help='Profile individual modules')
    parser.add_argument('--compare-numba', action='store_true',
                       help='Compare Numba acceleration')
    parser.add_argument('--grid-size', type=int, default=100,
                       help='Grid size for single tests (default: 100)')
    parser.add_argument('--output', type=str, default='outputs/performance_analysis.png',
                       help='Output figure path')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("HydroClaude 性能分析工具")
    print("=" * 70)

    profiler = PerformanceProfiler()

    # 网格规模测试
    if not args.profile_modules and not args.compare_numba:
        grid_sizes = [int(x) for x in args.grid_sizes.split(',')]
        profiler.benchmark_grid_scaling(grid_sizes, args.days, use_numba=False)

    # 模块分析
    if args.profile_modules:
        profiler.profile_modules(args.grid_size, args.days)

    # Numba对比
    if args.compare_numba:
        profiler.compare_numba_acceleration(args.grid_size, args.days)

    # 生成图表
    if profiler.results:
        profiler.plot_results(args.output)

    print("\n" + "=" * 70)
    print("性能分析完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
