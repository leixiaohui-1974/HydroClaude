#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
梯形断面渠道示例

演示 TrapezoidalChannel 类的使用，包括：
1. 水力几何计算
2. 正常水深计算
3. 临界水深计算
4. 流态判断

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry.trapezoidal_channel import TrapezoidalChannel, create_trapezoidal_channel


def example_1_basic_geometry():
    """
    示例1：基本水力几何计算

    计算给定水深下的所有水力要素
    """
    print("="*80)
    print("示例1：梯形断面基本水力几何计算")
    print("="*80)

    # 创建梯形渠道
    channel = TrapezoidalChannel(
        bottom_width=5.0,      # 底宽 5m
        side_slope=1.5,        # 边坡 1.5:1
        length=1000.0,         # 长度 1000m
        bottom_slope=0.001,    # 底坡 0.001
        manning_n=0.020,       # Manning系数 0.020
        channel_id="main_canal"
    )

    print(f"\n渠道参数：")
    print(f"  底宽 B = {channel.B_bottom:.2f} m")
    print(f"  边坡 m = {channel.m:.2f}:1")
    print(f"  长度 L = {channel.L:.0f} m")
    print(f"  底坡 S0 = {channel.S0:.5f}")
    print(f"  Manning系数 n = {channel.n:.4f}")

    # 计算不同水深下的水力要素
    depths = [0.5, 1.0, 1.5, 2.0, 2.5]

    print(f"\n水力几何要素：")
    print(f"{'h(m)':>8} {'A(m^2)':>10} {'B(m)':>10} {'P(m)':>10} {'R(m)':>10} {'D(m)':>10}")
    print("-" * 70)

    for h in depths:
        props = channel.properties(h)
        print(f"{h:>8.2f} {props['A']:>10.3f} {props['B']:>10.3f} "
              f"{props['P']:>10.3f} {props['R']:>10.3f} {props['D']:>10.3f}")

    print("\n说明：")
    print("  A: 过水断面积 (m^2)")
    print("  B: 水面宽度 (m)")
    print("  P: 湿周 (m)")
    print("  R: 水力半径 R=A/P (m)")
    print("  D: 水力深度 D=A/B (m)")


def example_2_normal_and_critical_depth():
    """
    示例2：正常水深和临界水深计算

    对比不同流量下的正常水深和临界水深
    """
    print("\n" + "="*80)
    print("示例2：正常水深和临界水深计算")
    print("="*80)

    # 缓坡渠道（亚临界流）
    mild_channel = TrapezoidalChannel(
        bottom_width=5.0,
        side_slope=1.5,
        length=1000.0,
        bottom_slope=0.001,    # 缓坡
        manning_n=0.020
    )

    print(f"\n渠道类型：缓坡渠道（S0 = {mild_channel.S0}）")
    print(f"\n流量-水深关系：")
    print(f"{'Q(m^3/s)':>12} {'h_n(m)':>12} {'h_c(m)':>12} {'h_n/h_c':>12} {'流态':>12}")
    print("-" * 72)

    flow_rates = [5.0, 10.0, 15.0, 20.0, 25.0]

    for Q in flow_rates:
        h_n = mild_channel.normal_depth(Q)
        h_c = mild_channel.critical_depth(Q)
        ratio = h_n / h_c

        # 判断流态
        Fr_n = mild_channel.froude_number(Q, h_n)
        flow_regime = "亚临界" if Fr_n < 1.0 else "超临界"

        print(f"{Q:>12.2f} {h_n:>12.3f} {h_c:>12.3f} {ratio:>12.3f} {flow_regime:>12}")

    print("\n分析：")
    print("  缓坡渠道：h_n > h_c，正常流为亚临界流")
    print("  h_n/h_c > 1，比值随流量变化")


def example_3_steep_vs_mild_slope():
    """
    示例3：缓坡 vs 陡坡渠道对比

    比较缓坡和陡坡渠道的流态特性
    """
    print("\n" + "="*80)
    print("示例3：缓坡 vs 陡坡渠道对比")
    print("="*80)

    Q = 10.0  # 固定流量 10 m^3/s

    # 缓坡渠道
    mild_channel = TrapezoidalChannel(
        bottom_width=5.0,
        side_slope=1.5,
        length=1000.0,
        bottom_slope=0.0005,   # 缓坡
        manning_n=0.020
    )

    # 陡坡渠道
    steep_channel = TrapezoidalChannel(
        bottom_width=5.0,
        side_slope=1.5,
        length=1000.0,
        bottom_slope=0.01,     # 陡坡
        manning_n=0.020
    )

    print(f"\n固定流量 Q = {Q:.2f} m^3/s")
    print(f"\n{'渠道类型':>12} {'S0':>12} {'h_n(m)':>12} {'h_c(m)':>12} {'Fr_n':>12} {'流态':>12}")
    print("-" * 84)

    # 缓坡
    h_n_mild = mild_channel.normal_depth(Q)
    h_c_mild = mild_channel.critical_depth(Q)
    Fr_mild = mild_channel.froude_number(Q, h_n_mild)
    regime_mild = "亚临界" if Fr_mild < 1.0 else "超临界"

    print(f"{'缓坡':>12} {mild_channel.S0:>12.5f} {h_n_mild:>12.3f} "
          f"{h_c_mild:>12.3f} {Fr_mild:>12.3f} {regime_mild:>12}")

    # 陡坡
    h_n_steep = steep_channel.normal_depth(Q)
    h_c_steep = steep_channel.critical_depth(Q)
    Fr_steep = steep_channel.froude_number(Q, h_n_steep)
    regime_steep = "亚临界" if Fr_steep < 1.0 else "超临界"

    print(f"{'陡坡':>12} {steep_channel.S0:>12.5f} {h_n_steep:>12.3f} "
          f"{h_c_steep:>12.3f} {Fr_steep:>12.3f} {regime_steep:>12}")

    print("\n结论：")
    print("  缓坡（S < S_critical）：h_n > h_c，Fr < 1，亚临界流")
    print("  陡坡（S > S_critical）：h_n < h_c，Fr > 1，超临界流")


def example_4_design_application():
    """
    示例4：渠道设计应用

    设计灌溉渠道：给定流量和流速约束，确定断面尺寸
    """
    print("\n" + "="*80)
    print("示例4：灌溉渠道设计应用")
    print("="*80)

    # 设计要求
    Q_design = 15.0  # 设计流量 15 m^3/s
    v_max = 1.5      # 最大允许流速 1.5 m/s（防冲刷）
    v_min = 0.6      # 最小流速 0.6 m/s（防淤积）

    print(f"\n设计要求：")
    print(f"  设计流量 Q = {Q_design:.2f} m^3/s")
    print(f"  最大流速 v_max = {v_max:.2f} m/s（防冲刷）")
    print(f"  最小流速 v_min = {v_min:.2f} m/s（防淤积）")

    # 尝试不同的底宽
    bottom_widths = [3.0, 4.0, 5.0, 6.0, 7.0]
    side_slope = 1.5
    S0 = 0.0008  # 底坡
    n = 0.022    # 土质衬砌

    print(f"\n断面参数：m = {side_slope}:1, S0 = {S0}, n = {n}")
    print(f"\n{'B(m)':>8} {'h_n(m)':>12} {'A(m^2)':>12} {'v(m/s)':>12} {'Fr':>12} {'评价':>12}")
    print("-" * 80)

    suitable_designs = []

    for B in bottom_widths:
        channel = TrapezoidalChannel(B, side_slope, 1000.0, S0, n)

        h_n = channel.normal_depth(Q_design)
        props = channel.properties(h_n)
        A = props['A']
        v = Q_design / A
        Fr = channel.froude_number(Q_design, h_n)

        # 评价
        if v_min <= v <= v_max:
            evaluation = " 合格"
            suitable_designs.append((B, h_n, v))
        elif v > v_max:
            evaluation = " 流速过大"
        else:
            evaluation = " 流速过小"

        print(f"{B:>8.2f} {h_n:>12.3f} {A:>12.3f} {v:>12.3f} {Fr:>12.3f} {evaluation:>12}")

    print(f"\n推荐设计方案：")
    if suitable_designs:
        for B, h_n, v in suitable_designs:
            print(f"  底宽 B = {B:.2f} m, 正常水深 h_n = {h_n:.3f} m, 流速 v = {v:.3f} m/s")
    else:
        print(f"  没有满足约束的设计方案，需要调整参数")


def example_5_hydraulic_jump():
    """
    示例5：水跃现象

    分析超临界流向亚临界流转换的水跃
    """
    print("\n" + "="*80)
    print("示例5：水跃现象分析")
    print("="*80)

    channel = TrapezoidalChannel(
        bottom_width=5.0,
        side_slope=1.5,
        length=1000.0,
        bottom_slope=0.001,
        manning_n=0.020
    )

    Q = 10.0  # 流量

    print(f"\n渠道参数：B = {channel.B_bottom} m, m = {channel.m}:1")
    print(f"流量 Q = {Q:.2f} m^3/s")

    # 临界水深
    h_c = channel.critical_depth(Q)

    print(f"\n临界水深 h_c = {h_c:.3f} m")

    # 水跃前（超临界）
    h1 = 0.8 * h_c  # 跃前水深 < h_c
    Fr1 = channel.froude_number(Q, h1)
    v1 = Q / channel.area(h1)

    # 水跃后（亚临界）估算
    # 使用共轭水深近似公式（矩形渠道）
    # h2/h1 ~= 0.5 * (-1 + sqrt(1 + 8*Fr1^2))
    h2_approx = h1 * 0.5 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr1**2))
    Fr2 = channel.froude_number(Q, h2_approx)
    v2 = Q / channel.area(h2_approx)

    print(f"\n水跃分析（近似）：")
    print(f"{'位置':>12} {'h(m)':>12} {'v(m/s)':>12} {'Fr':>12} {'流态':>12}")
    print("-" * 72)
    print(f"{'跃前':>12} {h1:>12.3f} {v1:>12.3f} {Fr1:>12.3f} {'超临界':>12}")
    print(f"{'跃后':>12} {h2_approx:>12.3f} {v2:>12.3f} {Fr2:>12.3f} {'亚临界':>12}")

    # 能量损失
    g = 9.81
    E1 = h1 + v1**2 / (2*g)
    E2 = h2_approx + v2**2 / (2*g)
    delta_E = E1 - E2
    efficiency = (E2 / E1) * 100

    print(f"\n能量分析：")
    print(f"  跃前比能 E1 = {E1:.3f} m")
    print(f"  跃后比能 E2 = {E2:.3f} m")
    print(f"  能量损失 DeltaE = {delta_E:.3f} m ({100-efficiency:.1f}%)")

    print(f"\n说明：")
    print(f"  水跃导致水深增加 {(h2_approx-h1):.3f} m")
    print(f"  流速降低 {(v1-v2):.3f} m/s")
    print(f"  能量损失主要转化为湍流和热能")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("梯形断面渠道示例集")
    print("="*80)

    example_1_basic_geometry()
    example_2_normal_and_critical_depth()
    example_3_steep_vs_mild_slope()
    example_4_design_application()
    example_5_hydraulic_jump()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == '__main__':
    main()
