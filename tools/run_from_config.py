#!/usr/bin/env python3
"""
HydroClaude 配置文件驱动模拟工具

功能: 从JSON配置文件读取参数并运行模拟
- 支持完整的参数配置
- 自动创建求解器
- 自动保存结果
- 自动生成可视化

用法:
    python tools/run_from_config.py config/example_winter_simulation.json

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

def load_config(config_file):
    """加载配置文件"""
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def create_solvers(config):
    """根据配置创建求解器"""
    domain = config['domain']
    n_cells = domain['n_cells']
    dx = domain['dx']

    solvers = {}
    params = config['solver_parameters']

    # 水温求解器
    if 'water_temperature' in params:
        solvers['temperature'] = WaterTemperatureSolver(
            n_cells, dx,
            use_numba=params['water_temperature'].get('use_numba', False)
        )

    # DO求解器
    if 'dissolved_oxygen' in params:
        do_params = params['dissolved_oxygen']
        solvers['do'] = DissolvedOxygenSolver(
            n_cells, dx,
            kd_20=do_params.get('kd_20', 0.15),
            SOD_20=do_params.get('SOD_20', 1.0),
            use_numba=do_params.get('use_numba', False)
        )

    # 冰盖求解器
    if 'ice_cover' in params and params['ice_cover'].get('enabled', False):
        solvers['ice'] = IceCoverSolver(n_cells=n_cells)

    # 营养盐求解器
    if 'nutrients' in params:
        solvers['nutrients'] = NutrientsSolver(
            n_cells, dx,
            use_numba=params['nutrients'].get('use_numba', False)
        )

    # 藻类求解器
    if 'phytoplankton' in params:
        algae_params = params['phytoplankton']
        solvers['algae'] = PhytoplanktonSolver(
            n_cells, dx,
            use_numba=algae_params.get('use_numba', False)
        )
        # 设置参数
        solvers['algae'].mu_max_20 = algae_params.get('mu_max_20', 2.0)
        solvers['algae'].I_s = algae_params.get('I_s', 100.0)
        solvers['algae'].K_N_NH4 = algae_params.get('K_N_NH4', 0.025)
        solvers['algae'].K_N_NO3 = algae_params.get('K_N_NO3', 0.05)
        solvers['algae'].K_P = algae_params.get('K_P', 0.001)
        solvers['algae'].k_d = algae_params.get('k_d', 0.05)
        solvers['algae'].k_r = algae_params.get('k_r', 0.05)
        solvers['algae'].vs_algae = algae_params.get('vs_algae', 0.1)

    return solvers

def initialize_solvers(solvers, config):
    """初始化求解器"""
    ic = config['initial_conditions']
    n_cells = config['domain']['n_cells']

    if 'temperature' in solvers:
        solvers['temperature'].T = np.full(n_cells, ic.get('water_temperature', 20.0))

    if 'do' in solvers:
        solvers['do'].DO = np.full(n_cells, ic.get('dissolved_oxygen', 8.0))
        solvers['do'].BOD = np.full(n_cells, ic.get('BOD', 3.0))

    if 'ice' in solvers:
        solvers['ice'].ice_thickness = np.full(n_cells, ic.get('ice_thickness', 0.0))
        if ic.get('ice_thickness', 0.0) > 0:
            solvers['ice'].ice_cover_fraction = np.ones(n_cells)
        else:
            solvers['ice'].ice_cover_fraction = np.zeros(n_cells)

    if 'nutrients' in solvers:
        solvers['nutrients'].NH4 = np.full(n_cells, ic.get('NH4', 0.3))
        solvers['nutrients'].NO3 = np.full(n_cells, ic.get('NO3', 1.2))
        solvers['nutrients'].PO4 = np.full(n_cells, ic.get('PO4', 0.08))
        solvers['nutrients'].OrgN = np.full(n_cells, ic.get('OrgN', 0.5))
        solvers['nutrients'].OrgP = np.full(n_cells, ic.get('OrgP', 0.05))

    if 'algae' in solvers:
        solvers['algae'].Chla = np.full(n_cells, ic.get('chlorophyll_a', 10.0))

def get_meteorology(day, config):
    """获取气象强迫"""
    met = config['meteorology']
    n_days = config['simulation_time']['duration_days']

    # 气温线性变化
    T_start = met.get('air_temperature_initial', 0.0)
    T_end = met.get('air_temperature_final', -15.0)
    T_air = T_start + (T_end - T_start) * day / n_days

    # 日变化
    hour = (day - int(day)) * 24
    T_amplitude = 3.0
    T_air += T_amplitude * np.sin(2 * np.pi * (hour - 6) / 24)

    # 太阳辐射
    daylight_hours = met.get('daylight_hours', 10)
    sunrise = 12 - daylight_hours / 2
    sunset = 12 + daylight_hours / 2

    if sunrise <= hour <= sunset:
        max_rad = met.get('solar_radiation_max', 300.0)
        I_0 = max_rad * np.sin(np.pi * (hour - sunrise) / daylight_hours)
    else:
        I_0 = 0.0

    return T_air, I_0

def run_simulation(config):
    """运行模拟"""
    print("=" * 70)
    print(f"HydroClaude 配置文件驱动模拟")
    print("=" * 70)
    print(f"模拟名称: {config.get('simulation_name', 'Unnamed')}")
    print(f"描述: {config.get('description', 'No description')}")
    print()

    # 创建求解器
    print("[1] 创建求解器...")
    solvers = create_solvers(config)
    print(f"✓ 创建了 {len(solvers)} 个求解器: {list(solvers.keys())}")

    # 初始化
    print("[2] 初始化...")
    initialize_solvers(solvers, config)
    print("✓ 初始化完成")
    print()

    # 准备模拟
    domain = config['domain']
    hydraulics = config['hydraulics']
    sim_time = config['simulation_time']

    n_cells = domain['n_cells']
    u = np.full(n_cells, hydraulics['velocity'])
    h = np.full(n_cells, hydraulics['depth'])
    manning_n = np.full(n_cells, hydraulics['manning_n'])

    dt = sim_time['time_step_seconds']
    n_days = sim_time['duration_days']
    n_steps = int(n_days * 24 * 3600 / dt)
    output_interval = int(sim_time.get('output_interval_hours', 24) * 3600 / dt)

    print(f"[3] 开始模拟 {n_days} 天...")
    print(f"时间步长: {dt/3600:.1f} 小时")
    print(f"总步数: {n_steps}")
    print()

    # 存储
    output_times = []
    output = {key: [] for key in config['output']['variables']}

    # 保存初始状态
    output_times.append(0)
    if 'water_temperature' in output and 'temperature' in solvers:
        output['water_temperature'].append(solvers['temperature'].T.mean())
    if 'dissolved_oxygen' in output and 'do' in solvers:
        output['dissolved_oxygen'].append(solvers['do'].DO.mean())
    if 'ice_thickness' in output and 'ice' in solvers:
        output['ice_thickness'].append(solvers['ice'].ice_thickness.mean())
    if 'chlorophyll_a' in output and 'algae' in solvers:
        output['chlorophyll_a'].append(solvers['algae'].Chla.mean())

    # 时间循环
    for step in range(n_steps):
        t = step * dt
        day = t / 86400.0

        # 气象
        T_air, I_0_surface = get_meteorology(day, config)
        I_0 = np.full(n_cells, I_0_surface)
        wind_speed = config['meteorology']['wind_speed']
        rel_hum = config['meteorology']['relative_humidity']

        # 获取冰盖覆盖率
        ice_fraction = solvers['ice'].ice_cover_fraction if 'ice' in solvers else np.zeros(n_cells)

        # 各模块求解
        if 'temperature' in solvers:
            T = solvers['temperature'].step(dt, u, h, T_air, I_0_surface, wind_speed, rel_hum, ice_fraction)
        else:
            T = np.full(n_cells, 20.0)

        if 'ice' in solvers:
            ice_state = solvers['ice'].step(dt, T_air, T)

        if 'do' in solvers:
            do_state = solvers['do'].step(dt, u, h, T, manning_n, ice_fraction)

        if 'nutrients' in solvers:
            DO = solvers['do'].DO if 'do' in solvers else np.full(n_cells, 8.0)
            nutrients_state = solvers['nutrients'].step(dt, u, h, T, DO)

        if 'algae' in solvers and 'nutrients' in solvers:
            algae_state = solvers['algae'].step(
                dt, u, h, T, I_0,
                solvers['nutrients'].NH4,
                solvers['nutrients'].NO3,
                solvers['nutrients'].PO4,
                ice_fraction
            )

            # 耦合
            dt_day = dt / 86400.0
            if 'do' in solvers:
                solvers['do'].DO += algae_state['DO_production'] * dt_day
                solvers['do'].DO = np.maximum(solvers['do'].DO, 0.0)

            solvers['nutrients'].NH4 -= algae_state['NH4_uptake'] * dt_day
            solvers['nutrients'].NH4 = np.maximum(solvers['nutrients'].NH4, 0.0)
            solvers['nutrients'].NO3 -= algae_state['NO3_uptake'] * dt_day
            solvers['nutrients'].NO3 = np.maximum(solvers['nutrients'].NO3, 0.0)

        # 输出
        if (step + 1) % output_interval == 0:
            output_times.append(day)
            if 'water_temperature' in output and 'temperature' in solvers:
                output['water_temperature'].append(solvers['temperature'].T.mean())
            if 'dissolved_oxygen' in output and 'do' in solvers:
                output['dissolved_oxygen'].append(solvers['do'].DO.mean())
            if 'ice_thickness' in output and 'ice' in solvers:
                output['ice_thickness'].append(solvers['ice'].ice_thickness.mean())
            if 'ice_cover_fraction' in output and 'ice' in solvers:
                output['ice_cover_fraction'].append(solvers['ice'].ice_cover_fraction.mean())
            if 'NH4' in output and 'nutrients' in solvers:
                output['NH4'].append(solvers['nutrients'].NH4.mean())
            if 'NO3' in output and 'nutrients' in solvers:
                output['NO3'].append(solvers['nutrients'].NO3.mean())
            if 'chlorophyll_a' in output and 'algae' in solvers:
                output['chlorophyll_a'].append(solvers['algae'].Chla.mean())

            print(f"Day {day:5.0f}: ", end='')
            if 'temperature' in solvers:
                print(f"T={T.mean():5.2f}°C, ", end='')
            if 'do' in solvers:
                print(f"DO={solvers['do'].DO.mean():6.2f}mg/L, ", end='')
            if 'ice' in solvers:
                print(f"Ice={solvers['ice'].ice_thickness.mean()*100:5.1f}cm, ", end='')
            if 'algae' in solvers:
                print(f"Chla={solvers['algae'].Chla.mean():5.1f}μg/L", end='')
            print()

    print()
    print("✓ 模拟完成!")
    print()

    # 保存结果
    output_config = config.get('output', {})
    save_path = Path(output_config.get('save_path', './outputs'))
    save_path.mkdir(exist_ok=True)

    save_format = output_config.get('save_format', 'npz')
    if save_format == 'npz':
        output_file = save_path / 'simulation_results.npz'
        np.savez(output_file, times=np.array(output_times), **{k: np.array(v) for k, v in output.items()})
        print(f"✓ 结果已保存: {output_file}")

    # 可视化
    if output_config.get('create_plots', True):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        times = np.array(output_times)

        if 'water_temperature' in output and len(output['water_temperature']) > 0:
            axes[0, 0].plot(times, output['water_temperature'], 'b-', linewidth=2)
            axes[0, 0].set_xlabel('Time (days)')
            axes[0, 0].set_ylabel('Temperature (°C)')
            axes[0, 0].set_title('Water Temperature')
            axes[0, 0].grid(True, alpha=0.3)

        if 'dissolved_oxygen' in output and len(output['dissolved_oxygen']) > 0:
            axes[0, 1].plot(times, output['dissolved_oxygen'], 'r-', linewidth=2)
            axes[0, 1].set_xlabel('Time (days)')
            axes[0, 1].set_ylabel('DO (mg/L)')
            axes[0, 1].set_title('Dissolved Oxygen')
            axes[0, 1].grid(True, alpha=0.3)

        if 'ice_thickness' in output and len(output['ice_thickness']) > 0:
            ice_cm = np.array(output['ice_thickness']) * 100
            axes[1, 0].plot(times, ice_cm, 'c-', linewidth=2)
            axes[1, 0].set_xlabel('Time (days)')
            axes[1, 0].set_ylabel('Ice Thickness (cm)')
            axes[1, 0].set_title('Ice Cover')
            axes[1, 0].grid(True, alpha=0.3)

        if 'chlorophyll_a' in output and len(output['chlorophyll_a']) > 0:
            axes[1, 1].plot(times, output['chlorophyll_a'], 'g-', linewidth=2)
            axes[1, 1].set_xlabel('Time (days)')
            axes[1, 1].set_ylabel('Chlorophyll-a (μg/L)')
            axes[1, 1].set_title('Phytoplankton')
            axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plot_format = output_config.get('plot_format', 'png')
        plot_dpi = output_config.get('plot_dpi', 150)
        plot_file = save_path / f'simulation_results.{plot_format}'
        plt.savefig(plot_file, dpi=plot_dpi)
        print(f"✓ 图表已保存: {plot_file}")

    print()
    print("=" * 70)
    print("配置驱动模拟完成!")
    print("=" * 70)

    return solvers, output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run HydroClaude simulation from configuration file')
    parser.add_argument('config', type=str, help='Path to configuration JSON file')
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 运行模拟
    solvers, output = run_simulation(config)
