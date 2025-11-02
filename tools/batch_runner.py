#!/usr/bin/env python3
"""
HydroClaude 批量场景运行器

功能:
- 自动运行多个参数组合的模拟
- 支持参数空间采样 (网格采样、拉丁超立方、蒙特卡洛)
- 并行执行多个场景
- 自动结果对比和统计分析
- 生成综合报告

用法:
    # 网格采样
    python tools/batch_runner.py config/base_config.json --param-grid kd_20:0.1,0.2,0.3 SOD_20:1.0,2.0

    # 拉丁超立方采样
    python tools/batch_runner.py config/base_config.json --lhs kd_20:0.1-0.3 SOD_20:1.0-3.0 --n-samples 20

    # 蒙特卡洛采样
    python tools/batch_runner.py config/base_config.json --monte-carlo --n-samples 100

    # 并行运行
    python tools/batch_runner.py config/base_config.json --param-grid kd_20:0.1,0.2,0.3 --parallel --n-jobs 4

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import json
import argparse
import sys
from pathlib import Path
import time
from itertools import product
import multiprocessing as mp
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver


class BatchScenarioRunner:
    """批量场景运行器"""

    def __init__(self, base_config_file):
        """
        初始化批量运行器

        Parameters:
        -----------
        base_config_file : str
            基础配置文件路径
        """
        self.base_config_file = Path(base_config_file)
        self.base_config = self.load_config(base_config_file)
        self.results = []
        self.scenarios = []

    def load_config(self, config_file):
        """加载配置文件"""
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_param_grid(self, param_ranges: Dict[str, List[float]]) -> List[Dict]:
        """
        生成参数网格

        Parameters:
        -----------
        param_ranges : dict
            参数范围字典，例如 {'kd_20': [0.1, 0.2, 0.3], 'SOD_20': [1.0, 2.0]}

        Returns:
        --------
        scenarios : list of dict
            参数组合列表
        """
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())

        scenarios = []
        for values in product(*param_values):
            scenario = dict(zip(param_names, values))
            scenarios.append(scenario)

        print(f"生成网格采样: {len(scenarios)} 个场景")
        for i, scenario in enumerate(scenarios[:5]):  # 显示前5个
            print(f"  场景 {i+1}: {scenario}")
        if len(scenarios) > 5:
            print(f"  ... 以及其他 {len(scenarios)-5} 个场景")

        return scenarios

    def generate_lhs_samples(self, param_ranges: Dict[str, Tuple[float, float]],
                            n_samples: int) -> List[Dict]:
        """
        拉丁超立方采样 (LHS)

        Parameters:
        -----------
        param_ranges : dict
            参数范围字典，例如 {'kd_20': (0.1, 0.3), 'SOD_20': (1.0, 3.0)}
        n_samples : int
            样本数量

        Returns:
        --------
        scenarios : list of dict
            参数组合列表
        """
        try:
            from scipy.stats import qmc

            param_names = list(param_ranges.keys())
            n_params = len(param_names)

            # 创建LHS采样器
            sampler = qmc.LatinHypercube(d=n_params)
            samples = sampler.random(n=n_samples)

            # 缩放到实际参数范围
            scenarios = []
            for sample in samples:
                scenario = {}
                for i, param_name in enumerate(param_names):
                    low, high = param_ranges[param_name]
                    scenario[param_name] = low + sample[i] * (high - low)
                scenarios.append(scenario)

            print(f"生成拉丁超立方采样: {n_samples} 个场景")
            for i, scenario in enumerate(scenarios[:5]):
                print(f"  场景 {i+1}: {scenario}")
            if len(scenarios) > 5:
                print(f"  ... 以及其他 {len(scenarios)-5} 个场景")

            return scenarios

        except ImportError:
            print("警告: scipy未安装，回退到随机采样")
            return self.generate_random_samples(param_ranges, n_samples)

    def generate_random_samples(self, param_ranges: Dict[str, Tuple[float, float]],
                               n_samples: int) -> List[Dict]:
        """
        蒙特卡洛随机采样

        Parameters:
        -----------
        param_ranges : dict
            参数范围字典
        n_samples : int
            样本数量

        Returns:
        --------
        scenarios : list of dict
            参数组合列表
        """
        param_names = list(param_ranges.keys())

        scenarios = []
        for _ in range(n_samples):
            scenario = {}
            for param_name in param_names:
                low, high = param_ranges[param_name]
                scenario[param_name] = np.random.uniform(low, high)
            scenarios.append(scenario)

        print(f"生成蒙特卡洛采样: {n_samples} 个场景")
        return scenarios

    def run_single_scenario(self, scenario_id: int, params: Dict) -> Dict:
        """
        运行单个场景

        Parameters:
        -----------
        scenario_id : int
            场景ID
        params : dict
            参数字典

        Returns:
        --------
        result : dict
            场景结果
        """
        print(f"  运行场景 {scenario_id}: {params}")

        # 合并参数到配置
        config = self.base_config.copy()

        # 更新求解器参数
        if 'solver_parameters' not in config:
            config['solver_parameters'] = {}

        for key, value in params.items():
            # 识别参数属于哪个模块
            if key in ['kd_20', 'SOD_20']:
                if 'dissolved_oxygen' not in config['solver_parameters']:
                    config['solver_parameters']['dissolved_oxygen'] = {}
                config['solver_parameters']['dissolved_oxygen'][key] = value
            elif key in ['mu_max_20', 'I_s', 'K_N', 'K_P']:
                if 'phytoplankton' not in config['solver_parameters']:
                    config['solver_parameters']['phytoplankton'] = {}
                config['solver_parameters']['phytoplankton'][key] = value
            elif key in ['kn_20', 'kdn_20']:
                if 'nutrients' not in config['solver_parameters']:
                    config['solver_parameters']['nutrients'] = {}
                config['solver_parameters']['nutrients'][key] = value

        # 运行模拟
        result = self._execute_simulation(config)
        result['scenario_id'] = scenario_id
        result['parameters'] = params

        return result

    def _execute_simulation(self, config: Dict) -> Dict:
        """
        执行模拟

        Parameters:
        -----------
        config : dict
            配置字典

        Returns:
        --------
        result : dict
            模拟结果
        """
        # 提取配置
        n_cells = config['domain']['n_cells']
        dx = config['domain']['dx']
        duration_days = config['simulation_time']['duration_days']
        dt = config['simulation_time']['time_step_seconds']

        # 初始化求解器
        do_params = config['solver_parameters'].get('dissolved_oxygen', {})
        temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
        do_solver = DissolvedOxygenSolver(
            n_cells, dx,
            kd_20=do_params.get('kd_20', 0.15),
            SOD_20=do_params.get('SOD_20', 1.0),
            use_numba=False
        )
        ice_solver = IceCoverSolver(n_cells=n_cells)
        nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
        algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)

        # 初始条件
        ic = config['initial_conditions']
        temp_solver.T = np.full(n_cells, ic.get('water_temperature', 2.0))
        do_solver.DO = np.full(n_cells, ic.get('dissolved_oxygen', 12.0))
        do_solver.BOD = np.full(n_cells, ic.get('BOD', 3.0))
        ice_solver.h_ice = np.full(n_cells, ic.get('ice_thickness', 0.0))
        nutrients_solver.NH4 = np.full(n_cells, ic.get('NH4', 0.3))
        nutrients_solver.NO3 = np.full(n_cells, ic.get('NO3', 1.2))
        nutrients_solver.PO4 = np.full(n_cells, ic.get('PO4', 0.08))
        nutrients_solver.OrgN = np.full(n_cells, ic.get('OrgN', 0.5))
        nutrients_solver.OrgP = np.full(n_cells, ic.get('OrgP', 0.05))
        algae_solver.Chla = np.full(n_cells, ic.get('chlorophyll_a', 12.0))

        # 水力条件
        hydraulics = config['hydraulics']
        u = np.full(n_cells, hydraulics['velocity'])
        h = np.full(n_cells, hydraulics['depth'])
        manning_n = np.full(n_cells, hydraulics['manning_n'])

        # 气象条件
        meteo = config['meteorology']
        T_air_initial = meteo['air_temperature_initial']
        T_air_final = meteo['air_temperature_final']

        # 运行模拟
        n_steps = int(duration_days * 24 * 3600 / dt)

        # 存储关键指标
        metrics = {
            'DO_mean': [],
            'DO_min': [],
            'ice_thickness_max': [],
            'TN_mean': [],
            'Chla_mean': []
        }

        for step in range(n_steps):
            time_days = step * dt / 86400.0

            # 线性温度变化
            T_air = T_air_initial + (T_air_final - T_air_initial) * (time_days / duration_days)

            # 简化气象参数
            I_0 = np.full(n_cells, meteo.get('solar_radiation', 100.0))
            wind_speed = meteo.get('wind_speed', 5.0)
            relative_humidity = meteo.get('relative_humidity', 0.7)

            # 推进各模块
            T = temp_solver.step(dt, u, h, T_air, I_0.mean(), wind_speed, relative_humidity)
            ice_state = ice_solver.step(dt, T_air, T)
            nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
            algae_state = algae_solver.step(dt, u, h, T, I_0,
                                           nutrients_solver.NH4,
                                           nutrients_solver.NO3,
                                           nutrients_solver.PO4)
            do_state = do_solver.step(dt, u, h, T, manning_n)

            # 耦合
            dt_day = dt / 86400.0
            do_solver.DO += algae_state['DO_production'] * dt_day
            do_solver.DO = np.maximum(do_solver.DO, 0.0)

            nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
            nutrients_solver.NO3 -= algae_state['NO3_uptake'] * dt_day
            nutrients_solver.PO4 -= algae_state['PO4_uptake'] * dt_day

            nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)
            nutrients_solver.NO3 = np.maximum(nutrients_solver.NO3, 0.0)
            nutrients_solver.PO4 = np.maximum(nutrients_solver.PO4, 0.0)

            # 记录每日指标
            if step % int(24 * 3600 / dt) == 0:
                metrics['DO_mean'].append(do_solver.DO.mean())
                metrics['DO_min'].append(do_solver.DO.min())
                metrics['ice_thickness_max'].append(ice_state['h_ice'].max())
                metrics['TN_mean'].append(nutrients_state['TN'].mean())
                metrics['Chla_mean'].append(algae_solver.Chla.mean())

        # 计算汇总统计
        result = {
            'DO_mean_avg': np.mean(metrics['DO_mean']),
            'DO_min_overall': np.min(metrics['DO_min']),
            'ice_thickness_max': np.max(metrics['ice_thickness_max']),
            'TN_mean_avg': np.mean(metrics['TN_mean']),
            'Chla_mean_avg': np.mean(metrics['Chla_mean']),
            'timeseries': metrics
        }

        return result

    def run_batch(self, scenarios: List[Dict], parallel: bool = False,
                 n_jobs: int = None) -> List[Dict]:
        """
        批量运行场景

        Parameters:
        -----------
        scenarios : list of dict
            场景列表
        parallel : bool
            是否并行运行
        n_jobs : int
            并行任务数

        Returns:
        --------
        results : list of dict
            结果列表
        """
        print(f"\n开始批量运行 {len(scenarios)} 个场景")
        print(f"并行模式: {'是' if parallel else '否'}")
        if parallel and n_jobs:
            print(f"并行任务数: {n_jobs}")
        print("=" * 70)

        self.scenarios = scenarios
        start_time = time.time()

        if parallel and len(scenarios) > 1:
            # 并行运行
            if n_jobs is None:
                n_jobs = min(mp.cpu_count(), len(scenarios))

            print(f"使用 {n_jobs} 个进程并行运行...")

            with mp.Pool(processes=n_jobs) as pool:
                args = [(i, scenario) for i, scenario in enumerate(scenarios)]
                results = pool.starmap(self.run_single_scenario, args)

        else:
            # 串行运行
            results = []
            for i, scenario in enumerate(scenarios):
                result = self.run_single_scenario(i, scenario)
                results.append(result)

        elapsed_time = time.time() - start_time

        print("\n" + "=" * 70)
        print(f"批量运行完成!")
        print(f"总耗时: {elapsed_time:.2f} 秒")
        print(f"平均每个场景: {elapsed_time/len(scenarios):.2f} 秒")
        print("=" * 70)

        self.results = results
        return results

    def analyze_results(self):
        """分析批量结果"""
        if not self.results:
            print("没有可分析的结果")
            return

        print("\n" + "=" * 70)
        print("批量结果统计分析")
        print("=" * 70)

        # 提取所有结果
        DO_means = [r['DO_mean_avg'] for r in self.results]
        DO_mins = [r['DO_min_overall'] for r in self.results]
        ice_maxs = [r['ice_thickness_max'] for r in self.results]
        TN_means = [r['TN_mean_avg'] for r in self.results]
        Chla_means = [r['Chla_mean_avg'] for r in self.results]

        # 统计汇总
        print(f"\n{'指标':<25} {'最小值':<12} {'最大值':<12} {'平均值':<12} {'标准差':<12}")
        print("-" * 70)
        print(f"{'DO平均值 (mg/L)':<25} {np.min(DO_means):10.2f}   {np.max(DO_means):10.2f}   {np.mean(DO_means):10.2f}   {np.std(DO_means):10.2f}")
        print(f"{'DO最低值 (mg/L)':<25} {np.min(DO_mins):10.2f}   {np.max(DO_mins):10.2f}   {np.mean(DO_mins):10.2f}   {np.std(DO_mins):10.2f}")
        print(f"{'最大冰厚 (cm)':<25} {np.min(ice_maxs)*100:10.2f}   {np.max(ice_maxs)*100:10.2f}   {np.mean(ice_maxs)*100:10.2f}   {np.std(ice_maxs)*100:10.2f}")
        print(f"{'TN平均值 (mg/L)':<25} {np.min(TN_means):10.2f}   {np.max(TN_means):10.2f}   {np.mean(TN_means):10.2f}   {np.std(TN_means):10.2f}")
        print(f"{'Chla平均值 (μg/L)':<25} {np.min(Chla_means):10.2f}   {np.max(Chla_means):10.2f}   {np.mean(Chla_means):10.2f}   {np.std(Chla_means):10.2f}")

        # 参数敏感性分析（如果参数数量合适）
        if len(self.scenarios) > 1:
            param_names = list(self.scenarios[0].keys())
            if len(param_names) <= 3:
                print("\n参数敏感性分析:")
                print("-" * 70)
                for param_name in param_names:
                    param_values = [s[param_name] for s in self.scenarios]

                    # 计算与DO的相关性
                    corr_DO = np.corrcoef(param_values, DO_means)[0, 1]
                    corr_Chla = np.corrcoef(param_values, Chla_means)[0, 1]

                    print(f"{param_name}:")
                    print(f"  范围: {np.min(param_values):.3f} - {np.max(param_values):.3f}")
                    print(f"  与DO相关性: {corr_DO:+.3f}")
                    print(f"  与Chla相关性: {corr_Chla:+.3f}")

    def plot_results(self, output_file='outputs/batch_results.png'):
        """绘制批量结果"""
        if not self.results:
            print("没有可绘制的结果")
            return

        print(f"\n生成批量结果图表: {output_file}")

        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. DO平均值分布
        ax1 = fig.add_subplot(gs[0, 0])
        DO_means = [r['DO_mean_avg'] for r in self.results]
        ax1.hist(DO_means, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(DO_means), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(DO_means):.2f}')
        ax1.set_xlabel('DO Average (mg/L)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('DO Average Distribution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 冰厚分布
        ax2 = fig.add_subplot(gs[0, 1])
        ice_maxs = [r['ice_thickness_max'] * 100 for r in self.results]
        ax2.hist(ice_maxs, bins=20, color='lightblue', edgecolor='black', alpha=0.7)
        ax2.axvline(np.mean(ice_maxs), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(ice_maxs):.2f}')
        ax2.set_xlabel('Max Ice Thickness (cm)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Ice Thickness Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. 叶绿素分布
        ax3 = fig.add_subplot(gs[1, 0])
        Chla_means = [r['Chla_mean_avg'] for r in self.results]
        ax3.hist(Chla_means, bins=20, color='lightgreen', edgecolor='black', alpha=0.7)
        ax3.axvline(np.mean(Chla_means), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(Chla_means):.2f}')
        ax3.set_xlabel('Chlorophyll-a Average (μg/L)')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Chlorophyll-a Distribution')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 参数散点图（如果有参数变化）
        ax4 = fig.add_subplot(gs[1, 1])
        if len(self.scenarios) > 1:
            param_names = list(self.scenarios[0].keys())
            if len(param_names) >= 1:
                param_name = param_names[0]
                param_values = [s[param_name] for s in self.scenarios]
                ax4.scatter(param_values, DO_means, alpha=0.6, s=50)
                ax4.set_xlabel(f'{param_name}')
                ax4.set_ylabel('DO Average (mg/L)')
                ax4.set_title(f'DO vs {param_name}')
                ax4.grid(True, alpha=0.3)

                # 添加趋势线
                z = np.polyfit(param_values, DO_means, 1)
                p = np.poly1d(z)
                ax4.plot(param_values, p(param_values), "r--", alpha=0.8, linewidth=2)

        # 5. 指标对比箱线图
        ax5 = fig.add_subplot(gs[2, :])
        TN_means = [r['TN_mean_avg'] for r in self.results]

        # 归一化到0-1范围用于对比
        def normalize(data):
            return (np.array(data) - np.min(data)) / (np.max(data) - np.min(data) + 1e-10)

        data_to_plot = [
            normalize(DO_means),
            normalize(ice_maxs),
            normalize(TN_means),
            normalize(Chla_means)
        ]

        labels = ['DO', 'Ice Thickness', 'TN', 'Chla']
        bp = ax5.boxplot(data_to_plot, labels=labels, patch_artist=True)

        colors = ['skyblue', 'lightblue', 'lightcoral', 'lightgreen']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)

        ax5.set_ylabel('Normalized Value (0-1)')
        ax5.set_title('Normalized Metrics Comparison (Box Plot)')
        ax5.grid(True, alpha=0.3, axis='y')

        plt.suptitle(f'Batch Simulation Results ({len(self.results)} scenarios)',
                    fontsize=16, fontweight='bold')

        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ 图表已保存: {output_file}")
        plt.close()

    def save_results(self, output_file='outputs/batch_results.json'):
        """保存结果到JSON"""
        if not self.results:
            print("没有可保存的结果")
            return

        output_data = {
            'n_scenarios': len(self.results),
            'scenarios': self.scenarios,
            'results': self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✓ 结果已保存: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='HydroClaude Batch Scenario Runner')
    parser.add_argument('config', type=str, help='Base configuration file')
    parser.add_argument('--param-grid', type=str, nargs='+',
                       help='Parameter grid: param1:val1,val2,val3 param2:val1,val2')
    parser.add_argument('--lhs', type=str, nargs='+',
                       help='Latin Hypercube Sampling: param1:min-max param2:min-max')
    parser.add_argument('--monte-carlo', action='store_true',
                       help='Monte Carlo sampling')
    parser.add_argument('--n-samples', type=int, default=10,
                       help='Number of samples for LHS/MC (default: 10)')
    parser.add_argument('--parallel', action='store_true',
                       help='Run scenarios in parallel')
    parser.add_argument('--n-jobs', type=int, default=None,
                       help='Number of parallel jobs')
    parser.add_argument('--output', type=str, default='outputs/batch_results.json',
                       help='Output file for results')
    parser.add_argument('--plot', type=str, default='outputs/batch_results.png',
                       help='Output file for plots')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("HydroClaude 批量场景运行器")
    print("=" * 70)

    # 创建运行器
    runner = BatchScenarioRunner(args.config)

    # 生成场景
    scenarios = []

    if args.param_grid:
        # 网格采样
        param_ranges = {}
        for param_spec in args.param_grid:
            param_name, values_str = param_spec.split(':')
            values = [float(v) for v in values_str.split(',')]
            param_ranges[param_name] = values
        scenarios = runner.generate_param_grid(param_ranges)

    elif args.lhs:
        # 拉丁超立方采样
        param_ranges = {}
        for param_spec in args.lhs:
            param_name, range_str = param_spec.split(':')
            min_val, max_val = map(float, range_str.split('-'))
            param_ranges[param_name] = (min_val, max_val)
        scenarios = runner.generate_lhs_samples(param_ranges, args.n_samples)

    elif args.monte_carlo:
        # 蒙特卡洛采样（需要在配置文件中定义范围）
        print("蒙特卡洛采样需要在配置文件中定义参数范围")
        return

    else:
        print("错误: 必须指定采样方法 (--param-grid, --lhs, 或 --monte-carlo)")
        return

    # 运行批量模拟
    runner.run_batch(scenarios, parallel=args.parallel, n_jobs=args.n_jobs)

    # 分析结果
    runner.analyze_results()

    # 绘制结果
    runner.plot_results(args.plot)

    # 保存结果
    runner.save_results(args.output)

    print("\n" + "=" * 70)
    print("批量运行完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
