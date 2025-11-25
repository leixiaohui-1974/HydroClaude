# -*- coding: utf-8 -*-
"""
示例17: 水库基础示例

演示水库组件的基本功能:
1. 水库物理仿真
2. 库容演算
3. 水位变化
4. 发电计算
5. 约束检查

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

from physics.reservoir import Reservoir

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def demo_basic_reservoir():
    """
    演示1: 基础水库仿真
    """
    print("=" * 80)
    print("示例17: 水库基础仿真")
    print("=" * 80)

    # 创建水库
    # 参数基于典型中型水库
    reservoir = Reservoir(
        reservoir_id="demo_reservoir",
        total_capacity=5000e4,  # 5000万m^3 = 5000 * 10^4 m^3
        dead_storage=500e4,     # 500万m^3
        min_level=100.0,        # 死水位 100m
        normal_level=150.0,     # 正常蓄水位 150m
        flood_limit_level=145.0,  # 防洪限制水位 145m
        design_level=155.0,     # 设计洪水位 155m
        catchment_area=1000.0,  # 集水面积 1000 km^2
        ecological_flow=10.0,   # 生态流量 10 m^3/s
        max_discharge=2000.0,   # 最大泄流 2000 m^3/s
        has_spillway=True,
        has_turbine=True,
        turbine_capacity=100.0,  # 装机容量 100 MW
        hydraulic_head=50.0,     # 水头 50m
        turbine_efficiency=0.85
    )

    print(f"\n水库参数:")
    print(f"  总库容: {reservoir.total_capacity/1e4:.0f} 万m^3")
    print(f"  死库容: {reservoir.dead_storage/1e4:.0f} 万m^3")
    print(f"  兴利库容: {reservoir.active_storage/1e4:.0f} 万m^3")
    print(f"  水位范围: {reservoir.min_level:.1f} - {reservoir.design_level:.1f} m")
    print(f"  装机容量: {reservoir.turbine_capacity:.0f} MW")

    # 初始状态
    print(f"\n初始状态:")
    status = reservoir.get_operation_status()
    print(f"  库容: {status['storage']/1e4:.0f} 万m^3 ({status['storage_percent']:.1f}%)")
    print(f"  水位: {status['water_level']:.2f} m")

    # 仿真参数
    dt = 3600.0  # 时间步长 1小时 = 3600秒
    n_hours = 72  # 仿真72小时（3天）

    # 生成入流过程线（模拟洪水过程）
    time_hours = np.arange(n_hours)
    inflow_base = 500.0  # 基流 500 m^3/s

    # 模拟洪峰过程
    flood_peak_time = 24  # 洪峰出现在第24小时
    inflow = inflow_base + 1500 * np.exp(-0.5 * ((time_hours - flood_peak_time) / 10) ** 2)

    print(f"\n仿真设置:")
    print(f"  时间步长: {dt/3600:.1f} 小时")
    print(f"  仿真时长: {n_hours} 小时")
    print(f"  基流: {inflow_base:.0f} m^3/s")
    print(f"  洪峰流量: {np.max(inflow):.0f} m^3/s")

    # 仿真循环
    results = {
        'time': [],
        'inflow': [],
        'outflow': [],
        'storage': [],
        'level': [],
        'turbine_discharge': [],
        'spillway_discharge': [],
        'power': []
    }

    print(f"\n开始仿真...")

    for i in range(n_hours):
        # 控制策略：根据水位调整出流
        current_level = reservoir.state.water_level

        if current_level < reservoir.flood_limit_level:
            # 低于防洪限制水位，正常发电
            turbine_discharge = min(inflow[i] * 0.8, reservoir._get_max_turbine_flow())
            spillway_opening = 0.0
        elif current_level < reservoir.normal_level:
            # 接近正常蓄水位，增加发电出流
            turbine_discharge = reservoir._get_max_turbine_flow()
            spillway_opening = 0.0
        else:
            # 超过正常蓄水位，开启溢洪道
            turbine_discharge = reservoir._get_max_turbine_flow()
            spillway_opening = min((current_level - reservoir.normal_level) / 5.0, 1.0)

        # 更新水库状态
        inputs = {
            'inflow': inflow[i],
            'turbine_discharge': turbine_discharge,
            'spillway_opening': spillway_opening
        }

        state = reservoir.update_high_fidelity(dt, inputs)

        # 记录结果
        results['time'].append(i)
        results['inflow'].append(state.inflow)
        results['outflow'].append(state.outflow)
        results['storage'].append(state.storage / 1e4)  # 转换为万m^3
        results['level'].append(state.water_level)
        results['turbine_discharge'].append(state.turbine_discharge)
        results['spillway_discharge'].append(state.spillway_discharge)
        results['power'].append(state.power_generation)

    print(f"仿真完成!")

    # 统计结果
    print(f"\n仿真结果统计:")
    print(f"  最大入流: {np.max(results['inflow']):.0f} m^3/s")
    print(f"  最大出流: {np.max(results['outflow']):.0f} m^3/s")
    print(f"  最高水位: {np.max(results['level']):.2f} m")
    print(f"  最低水位: {np.min(results['level']):.2f} m")
    print(f"  最大发电: {np.max(results['power']):.2f} MW")
    print(f"  总发电量: {np.sum(results['power']):.2f} MWh")
    print(f"  防洪约束: {'满足' if np.max(results['level']) <= reservoir.design_level else '不满足'}")
    print(f"  生态流量: {'满足' if np.min(results['outflow']) >= reservoir.ecological_flow else '不满足'}")

    # 可视化
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))

    # 子图1: 流量过程
    axes[0].plot(results['time'], results['inflow'], 'b-', label='入流', linewidth=2)
    axes[0].plot(results['time'], results['outflow'], 'r-', label='出流', linewidth=2)
    axes[0].axhline(reservoir.ecological_flow, color='g', linestyle='--', label='生态流量')
    axes[0].set_ylabel('流量 (m^3/s)', fontsize=12)
    axes[0].set_title('水库流量过程', fontsize=14, fontweight='bold')
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)

    # 子图2: 水位过程
    axes[1].plot(results['time'], results['level'], 'b-', linewidth=2)
    axes[1].axhline(reservoir.normal_level, color='g', linestyle='--', label='正常蓄水位')
    axes[1].axhline(reservoir.flood_limit_level, color='orange', linestyle='--', label='防洪限制水位')
    axes[1].axhline(reservoir.design_level, color='r', linestyle='--', label='设计洪水位')
    axes[1].fill_between(results['time'], reservoir.min_level, reservoir.flood_limit_level,
                         alpha=0.2, color='green', label='安全区')
    axes[1].set_ylabel('水位 (m)', fontsize=12)
    axes[1].set_title('水库水位过程', fontsize=14, fontweight='bold')
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)

    # 子图3: 库容过程
    axes[2].plot(results['time'], results['storage'], 'b-', linewidth=2)
    axes[2].axhline(reservoir.dead_storage/1e4, color='r', linestyle='--', label='死库容')
    axes[2].axhline(reservoir.total_capacity/1e4, color='g', linestyle='--', label='总库容')
    axes[2].set_ylabel('库容 (万m^3)', fontsize=12)
    axes[2].set_title('水库库容过程', fontsize=14, fontweight='bold')
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)

    # 子图4: 发电过程
    axes[3].plot(results['time'], results['power'], 'b-', linewidth=2)
    axes[3].axhline(reservoir.turbine_capacity, color='r', linestyle='--', label='装机容量')
    axes[3].set_xlabel('时间 (小时)', fontsize=12)
    axes[3].set_ylabel('发电功率 (MW)', fontsize=12)
    axes[3].set_title('水库发电过程', fontsize=14, fontweight='bold')
    axes[3].legend(loc='upper right')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), r'reservoir_simulation.png'), dpi=150)
    print(f"\n图像已保存到: reservoir_simulation.png")

    return reservoir, results


def demo_constraint_check():
    """
    演示2: 约束检查
    """
    print("\n" + "=" * 80)
    print("约束检查演示")
    print("=" * 80)

    reservoir = Reservoir(
        reservoir_id="test_reservoir",
        total_capacity=1000e4,
        dead_storage=100e4,
        min_level=100.0,
        normal_level=120.0,
        flood_limit_level=118.0,
        design_level=125.0,
        ecological_flow=5.0,
        max_discharge=500.0,
        has_turbine=True,
        turbine_capacity=50.0,
        hydraulic_head=30.0
    )

    print("\n约束条件:")
    constraints = reservoir.get_constraints()
    for key, (lower, upper) in constraints.items():
        print(f"  {key}: [{lower:.2f}, {upper:.2f}]")

    # 测试不同场景
    scenarios = [
        ("正常运行", 300.0, 200.0, 0.0),
        ("大洪水", 800.0, 500.0, 0.5),
        ("干旱期", 50.0, 30.0, 0.0),
    ]

    dt = 3600.0

    for scenario_name, inflow, turbine, spillway_opening in scenarios:
        print(f"\n场景: {scenario_name}")
        print(f"  入流: {inflow:.0f} m^3/s")

        reservoir.reset()
        inputs = {
            'inflow': inflow,
            'turbine_discharge': turbine,
            'spillway_opening': spillway_opening
        }

        state = reservoir.update_high_fidelity(dt, inputs)

        print(f"  水位: {state.water_level:.2f} m")
        print(f"  出流: {state.outflow:.2f} m^3/s")
        print(f"  防洪约束: {'' if reservoir.check_flood_control() else ''}")
        print(f"  抗旱约束: {'' if reservoir.check_drought_control() else ''}")
        print(f"  生态流量: {'' if reservoir.check_ecological_flow() else ''}")


if __name__ == "__main__":
    # 运行演示
    reservoir, results = demo_basic_reservoir()
    demo_constraint_check()

    print("\n" + "=" * 80)
    print("示例17完成!")
    print("=" * 80)
