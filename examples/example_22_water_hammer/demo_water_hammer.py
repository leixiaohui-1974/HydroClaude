import os
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例22: 水锤效应分析

演示管道系统中的瞬态压力波动现象

场景:
- 管道系统：长管道 + 阀门
- 初始状态：稳定流动
- 扰动：阀门快速关闭
- 分析：压力波传播、最大压力、水锤强度

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.constants import PhysicsConstants
from physics.pipe import Pipe
from physics.valve import Valve


def calculate_water_hammer_theory(V0: float, a: float, closure_time: float) -> Dict:
    """
    水锤理论计算

    Args:
        V0: 初始流速 (m/s)
        a: 压力波速 (m/s)
        closure_time: 阀门关闭时间 (s)

    Returns:
        理论计算结果字典
    """
    # Joukowsky公式: DeltaP = rho * a * DeltaV
    rho = PhysicsConstants.WATER_DENSITY
    delta_v = V0  # 流速从V0降到0

    # 理论最大压力升高
    delta_p_max_joukowsky = rho * a * delta_v  # Pa
    delta_h_max = delta_p_max_joukowsky / (rho * PhysicsConstants.GRAVITY)  # m

    # 临界关闭时间
    critical_time = 2 * 1000 / a  # 假设管道长1000m

    # 关闭类型判断
    if closure_time < critical_time:
        closure_type = "直接水锤"
        reduction_factor = 1.0
    else:
        closure_type = "间接水锤"
        reduction_factor = critical_time / closure_time

    actual_delta_h = delta_h_max * reduction_factor

    return {
        'delta_p_joukowsky': delta_p_max_joukowsky,
        'delta_h_joukowsky': delta_h_max,
        'critical_time': critical_time,
        'closure_type': closure_type,
        'reduction_factor': reduction_factor,
        'actual_delta_h': actual_delta_h,
        'wave_speed': a
    }


def demo_water_hammer_basic():
    """基础水锤效应演示"""

    print("="*80)
    print("示例22: 水锤效应分析")
    print("="*80)
    print()

    # ========================================
    # 1. 系统参数设置
    # ========================================

    pipe_length = 1000.0      # 管道长度 (m)
    pipe_diameter = 0.5       # 管道直径 (m)
    pipe_thickness = 0.01     # 管壁厚度 (m)
    initial_velocity = 2.0    # 初始流速 (m/s)

    # 压力波速计算 (Korteweg公式)
    E_water = 2.1e9          # 水的弹性模量 (Pa)
    E_steel = 2.1e11         # 钢管弹性模量 (Pa)
    rho = PhysicsConstants.WATER_DENSITY

    # 考虑管壁弹性的波速
    c1 = 1.0 / rho
    c2 = 1.0 / E_water
    c3 = pipe_diameter / (E_steel * pipe_thickness)
    wave_speed = np.sqrt(1.0 / (c1 * (c2 + c3)))

    print("【系统参数】")
    print(f"  管道长度: {pipe_length} m")
    print(f"  管道直径: {pipe_diameter} m")
    print(f"  管壁厚度: {pipe_thickness} m")
    print(f"  初始流速: {initial_velocity} m/s")
    print(f"  压力波速: {wave_speed:.1f} m/s")
    print()

    # ========================================
    # 2. 理论计算
    # ========================================

    closure_scenarios = [
        ("极快关闭", 0.5),
        ("快速关闭", 1.0),
        ("正常关闭", 2.0),
        ("缓慢关闭", 5.0),
    ]

    print("【理论水锤计算】")
    print("-" * 80)

    results = []
    for scenario_name, closure_time in closure_scenarios:
        result = calculate_water_hammer_theory(initial_velocity, wave_speed, closure_time)
        results.append((scenario_name, closure_time, result))

        print(f"\n{scenario_name} (关闭时间 {closure_time}s):")
        print(f"  Joukowsky压升: {result['delta_h_joukowsky']:.2f} m")
        print(f"  关闭类型: {result['closure_type']}")
        print(f"  临界时间: {result['critical_time']:.3f} s")
        print(f"  折减系数: {result['reduction_factor']:.3f}")
        print(f"  实际压升: {result['actual_delta_h']:.2f} m")

    print()

    # ========================================
    # 3. 可视化结果
    # ========================================

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('水锤效应分析', fontsize=16, fontweight='bold')

    # 子图1: 压力升高对比
    ax1 = axes[0, 0]
    scenario_names = [r[0] for r in results]
    delta_h_values = [r[2]['actual_delta_h'] for r in results]
    delta_h_joukowsky = [r[2]['delta_h_joukowsky'] for r in results]

    x = np.arange(len(scenario_names))
    width = 0.35
    ax1.bar(x - width/2, delta_h_joukowsky, width, label='Joukowsky formula',
            alpha=0.7, color='red')
    ax1.bar(x + width/2, delta_h_values, width, label='Actual (with reduction)',
            alpha=0.7, color='blue')

    ax1.set_xlabel('Closure Scenario')
    ax1.set_ylabel('Pressure Rise (m)')
    ax1.set_title('Maximum Pressure Rise Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenario_names, rotation=15, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2: 关闭时间 vs 压力升高
    ax2 = axes[0, 1]
    closure_times = np.linspace(0.1, 10, 100)
    pressure_rises = []

    for t in closure_times:
        result = calculate_water_hammer_theory(initial_velocity, wave_speed, t)
        pressure_rises.append(result['actual_delta_h'])

    ax2.plot(closure_times, pressure_rises, 'b-', linewidth=2, label='Pressure rise')
    critical_t = results[0][2]['critical_time']
    ax2.axvline(critical_t, color='r', linestyle='--', linewidth=2,
                label=f'Critical time ({critical_t:.2f}s)')

    # 标记测试点
    for scenario_name, t, result in results:
        ax2.plot(t, result['actual_delta_h'], 'ro', markersize=8)
        ax2.annotate(scenario_name, (t, result['actual_delta_h']),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)

    ax2.set_xlabel('Closure Time (s)')
    ax2.set_ylabel('Pressure Rise (m)')
    ax2.set_title('Pressure Rise vs Closure Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3: 压力波传播示意
    ax3 = axes[1, 0]

    # 绘制管道
    ax3.plot([0, pipe_length], [0, 0], 'k-', linewidth=3, label='Pipe')
    ax3.plot([pipe_length], [0], 'rs', markersize=15, label='Valve')

    # 绘制压力波在不同时刻的位置
    times_to_plot = [0, 0.25, 0.5, 0.75, 1.0]
    colors = plt.cm.Reds(np.linspace(0.3, 1.0, len(times_to_plot)))

    for i, t_frac in enumerate(times_to_plot):
        t = t_frac * (2 * pipe_length / wave_speed)
        wave_pos = wave_speed * t

        if wave_pos <= pipe_length:
            # 压力波向上游传播
            ax3.plot([pipe_length - wave_pos, pipe_length], [0, 0],
                    color=colors[i], linewidth=5, alpha=0.7,
                    label=f't = {t:.3f}s')
        else:
            # 压力波反射
            reflected_pos = wave_pos - pipe_length
            ax3.plot([0, reflected_pos], [0, 0],
                    color=colors[i], linewidth=5, alpha=0.7,
                    label=f't = {t:.3f}s (reflected)')

    ax3.set_xlabel('Position along pipe (m)')
    ax3.set_ylabel('Pressure wave')
    ax3.set_title('Pressure Wave Propagation')
    ax3.set_xlim(-50, pipe_length + 50)
    ax3.set_ylim(-0.5, 0.5)
    ax3.legend(loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)

    # 子图4: 水锤强度分类
    ax4 = axes[1, 1]

    # 绘制水锤强度分类图
    closure_range = np.linspace(0.1, 10, 100)
    intensity_categories = []

    for t in closure_range:
        result = calculate_water_hammer_theory(initial_velocity, wave_speed, t)
        delta_h = result['actual_delta_h']

        # 水锤强度分类 (基于压升大小)
        if delta_h > 200:
            intensity_categories.append(4)  # 极强
        elif delta_h > 150:
            intensity_categories.append(3)  # 强
        elif delta_h > 100:
            intensity_categories.append(2)  # 中等
        else:
            intensity_categories.append(1)  # 弱

    colors_map = {1: 'green', 2: 'yellow', 3: 'orange', 4: 'red'}
    intensity_colors = [colors_map[cat] for cat in intensity_categories]

    ax4.scatter(closure_range, [calculate_water_hammer_theory(initial_velocity, wave_speed, t)['actual_delta_h']
                                for t in closure_range],
               c=intensity_colors, s=20, alpha=0.6)

    ax4.axhline(100, color='green', linestyle='--', alpha=0.5, label='Weak (<100m)')
    ax4.axhline(150, color='yellow', linestyle='--', alpha=0.5, label='Medium (<150m)')
    ax4.axhline(200, color='orange', linestyle='--', alpha=0.5, label='Strong (<200m)')

    ax4.set_xlabel('Closure Time (s)')
    ax4.set_ylabel('Pressure Rise (m)')
    ax4.set_title('Water Hammer Intensity Classification')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    output_path = 'examples/example_22_water_hammer/water_hammer_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图像已保存到: {output_path}")
    print()

    # ========================================
    # 4. 工程建议
    # ========================================

    print("【工程设计建议】")
    print("-" * 80)
    print()

    print("1. 水锤防护措施:")
    print("   - 延长阀门关闭时间 (>5s)")
    print("   - 安装调压塔或空气罐")
    print("   - 使用缓闭止回阀")
    print("   - 设置泄压阀")
    print()

    print("2. 管道设计考虑:")
    print(f"   - 设计压力应考虑水锤压升 (+{delta_h_values[0]:.1f}m)")
    print(f"   - 临界关闭时间: {critical_t:.2f}s")
    print("   - 管材选择应考虑压力波速")
    print()

    print("3. 操作规程:")
    print("   - 避免突然关闭阀门")
    print("   - 按规定速度启停泵")
    print("   - 定期检查安全装置")
    print()

    return results


def demo_water_hammer_with_protection():
    """带保护措施的水锤分析"""

    print("="*80)
    print("水锤保护措施对比")
    print("="*80)
    print()

    # 系统参数
    V0 = 2.0
    a = 1000.0
    L = 1000.0

    scenarios = {
        "无保护": {
            "closure_time": 1.0,
            "has_surge_tank": False,
            "has_relief_valve": False,
        },
        "延长关闭时间": {
            "closure_time": 5.0,
            "has_surge_tank": False,
            "has_relief_valve": False,
        },
        "调压塔": {
            "closure_time": 1.0,
            "has_surge_tank": True,
            "has_relief_valve": False,
        },
        "泄压阀": {
            "closure_time": 1.0,
            "has_surge_tank": False,
            "has_relief_valve": True,
        },
    }

    print("【保护措施效果对比】")
    print("-" * 80)

    for scenario_name, config in scenarios.items():
        result = calculate_water_hammer_theory(V0, a, config['closure_time'])
        delta_h = result['actual_delta_h']

        # 考虑保护措施的修正
        if config['has_surge_tank']:
            delta_h *= 0.3  # 调压塔可减少70%压升
        if config['has_relief_valve']:
            delta_h *= 0.5  # 泄压阀可减少50%压升

        print(f"\n{scenario_name}:")
        print(f"  关闭时间: {config['closure_time']}s")
        print(f"  压力升高: {delta_h:.1f}m")
        print(f"  相对无保护: {delta_h / scenarios['无保护']['closure_time'] * 100:.1f}%")

    print()


if __name__ == '__main__':
    # 运行基础演示
    results = demo_water_hammer_basic()

    print()
    print("="*80)

    # 运行保护措施对比
    demo_water_hammer_with_protection()

    print()
    print("="*80)
    print("示例22完成!")
    print("="*80)
    print()
    print("关键成果:")
    print("   Joukowsky公式应用")
    print("   水锤强度计算")
    print("   压力波传播分析")
    print("   保护措施设计")
    print("   工程设计建议")
