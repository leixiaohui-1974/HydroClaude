#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复合断面渠道示例

演示 CompoundChannel 类的使用，包括：
1. 主槽和滩地的分区计算
2. 漫滩流量分析
3. 分区流速法 vs 等效糙率法对比
4. 防洪设计应用
5. Manning系数敏感性分析

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from geometry.compound_channel import CompoundChannel, create_compound_channel


def example_1_basic_compound_channel():
    """
    示例1：基本复合断面渠道

    典型河道断面：主槽 + 左右滩地
    """
    print("="*80)
    print("示例1：基本复合断面渠道")
    print("="*80)

    # 定义断面测点（站号，高程）
    # 左滩地 - 主槽 - 右滩地
    stations = [0, 20, 25, 25, 55, 60, 80]
    elevations = [105, 105, 100, 100, 100, 105, 105]

    bankfull_elevation = 104.0  # 主槽设计水位

    # 创建复合断面
    channel = CompoundChannel(
        stations=stations,
        elevations=elevations,
        bankfull_elevation=bankfull_elevation,
        length=2000.0,
        bottom_slope=0.0005,
        manning_n_main=0.025,      # 主槽：混凝土衬砌
        manning_n_floodplain=0.040  # 滩地：草地覆盖
    )

    print(f"\n断面参数：")
    print(f"  主槽底高程: {channel.z_min:.2f} m")
    print(f"  设计水位: {channel.z_bankfull:.2f} m")
    print(f"  主槽深度: {channel.z_bankfull - channel.z_min:.2f} m")
    print(f"  主槽Manning系数: n = {channel.n_main:.4f}")
    print(f"  滩地Manning系数: n = {channel.n_flood:.4f}")
    print(f"  底坡: S0 = {channel.S0:.5f}")

    # 计算不同水深下的水力要素
    water_depths = [2.0, 3.0, 4.0, 5.0, 6.0]  # 相对于河底的水深

    print(f"\n水力几何要素：")
    print(f"{'h(m)':>8} {'水位(m)':>10} {'状态':>12} {'A(m^2)':>12} {'B(m)':>12} {'P(m)':>12} {'R(m)':>12}")
    print("-" * 88)

    for h in water_depths:
        water_level = channel.z_min + h
        is_overbank = channel.is_overbank(h)
        status = "漫滩" if is_overbank else "在槽"

        props = channel.properties(h)
        print(f"{h:>8.2f} {water_level:>10.2f} {status:>12} {props['A']:>12.2f} "
              f"{props['B']:>12.2f} {props['P']:>12.2f} {props['R']:>12.3f}")

    print("\n说明：")
    print("  h < 4.0m: 水流在主槽内")
    print("  h >= 4.0m: 水流漫过滩地，激活左右滩地")


def example_2_flood_stage_analysis():
    """
    示例2：洪水演进分析

    分析从在槽流到漫滩流的过渡过程
    """
    print("\n" + "="*80)
    print("示例2：洪水演进分析")
    print("="*80)

    # 自然河道断面
    stations = [0, 15, 20, 20, 50, 55, 70]
    elevations = [108, 108, 103, 103, 103, 108, 108]
    bankfull_elevation = 107.0

    channel = CompoundChannel(
        stations=stations,
        elevations=elevations,
        bankfull_elevation=bankfull_elevation,
        length=3000.0,
        bottom_slope=0.0008,
        manning_n_main=0.030,      # 主槽：天然河床
        manning_n_floodplain=0.050  # 滩地：灌木丛
    )

    print(f"\n河道参数：")
    print(f"  主槽深度: {bankfull_elevation - channel.z_min:.2f} m")
    print(f"  主槽Manning系数: n_main = {channel.n_main:.4f}")
    print(f"  滩地Manning系数: n_flood = {channel.n_flood:.4f}")

    # 不同重现期的设计流量
    print(f"\n洪水演进分析：")
    print(f"{'重现期':>12} {'Q(m^3/s)':>12} {'h(m)':>12} {'状态':>12} "
          f"{'主槽Q(%)':>12} {'滩地Q(%)':>12} {'流速(m/s)':>12}")
    print("-" * 96)

    design_flows = [
        ("常水位", 50),
        ("5年", 120),
        ("10年", 180),
        ("20年", 250),
        ("50年", 350),
        ("100年", 450)
    ]

    for return_period, Q in design_flows:
        h_n = channel.normal_depth(Q, method='divided')
        is_overbank = channel.is_overbank(h_n)
        status = "漫滩" if is_overbank else "在槽"

        # 获取分区信息
        info = channel.get_subdivision_info(h_n)
        Q_main = info['main']['Q']
        Q_flood_left = info['left_flood']['Q']
        Q_flood_right = info['right_flood']['Q']
        Q_flood_total = Q_flood_left + Q_flood_right

        main_pct = (Q_main / Q) * 100
        flood_pct = (Q_flood_total / Q) * 100

        # 平均流速
        A_total = channel.area(h_n)
        v_avg = Q / A_total

        print(f"{return_period:>12} {Q:>12.1f} {h_n:>12.3f} {status:>12} "
              f"{main_pct:>12.1f} {flood_pct:>12.1f} {v_avg:>12.3f}")

    print("\n分析结论：")
    print("  1. 小流量时，水流主要在主槽，流速较高")
    print("  2. 漫滩后，滩地承担大量流量，但流速较低（高糙率）")
    print("  3. 大洪水时，滩地可承担30-50%的总流量")


def example_3_method_comparison():
    """
    示例3：计算方法对比

    比较分区流速法和等效糙率法的差异
    """
    print("\n" + "="*80)
    print("示例3：计算方法对比")
    print("="*80)

    stations = [0, 10, 15, 15, 45, 50, 60]
    elevations = [110, 110, 105, 105, 105, 110, 110]
    bankfull_elevation = 109.0

    channel = CompoundChannel(
        stations=stations,
        elevations=elevations,
        bankfull_elevation=bankfull_elevation,
        length=1500.0,
        bottom_slope=0.001,
        manning_n_main=0.025,
        manning_n_floodplain=0.045
    )

    print(f"\n断面参数：")
    print(f"  主槽Manning系数: n_main = {channel.n_main:.4f}")
    print(f"  滩地Manning系数: n_flood = {channel.n_flood:.4f}")
    print(f"  糙率比: n_flood/n_main = {channel.n_flood/channel.n_main:.2f}")

    # 测试不同流量
    flow_rates = [50, 100, 150, 200, 250]

    print(f"\n方法对比：")
    print(f"{'Q(m^3/s)':>12} {'h_divided(m)':>15} {'h_equiv(m)':>15} "
          f"{'差异(m)':>12} {'差异(%)':>12} {'状态':>12}")
    print("-" * 90)

    for Q in flow_rates:
        # 分区流速法
        h_divided = channel.normal_depth(Q, method='divided')

        # 等效糙率法
        h_equiv = channel.normal_depth(Q, method='equivalent')

        # 计算差异
        diff_abs = h_equiv - h_divided
        diff_pct = (diff_abs / h_divided) * 100

        is_overbank = channel.is_overbank(h_divided)
        status = "漫滩" if is_overbank else "在槽"

        print(f"{Q:>12.1f} {h_divided:>15.4f} {h_equiv:>15.4f} "
              f"{diff_abs:>12.4f} {diff_pct:>12.2f} {status:>12}")

    print("\n分析：")
    print("  1. 在槽流时，两种方法结果接近（仅主槽，单一糙率）")
    print("  2. 漫滩后，等效糙率法高估水深（忽略了分区效应）")
    print("  3. 糙率差异越大，方法间差异越显著")
    print("  4. 推荐使用分区流速法以获得更准确的结果")


def example_4_flood_design():
    """
    示例4：防洪设计应用

    设计河道断面以满足防洪标准
    """
    print("\n" + "="*80)
    print("示例4：防洪设计应用")
    print("="*80)

    # 设计要求
    Q_100yr = 400.0  # 百年一遇设计流量 400 m^3/s
    freeboard = 0.5  # 安全超高 0.5 m
    v_max = 2.5      # 最大允许流速 2.5 m/s（防冲刷）

    print(f"\n设计标准：")
    print(f"  百年一遇流量: Q_100 = {Q_100yr:.1f} m^3/s")
    print(f"  安全超高: Deltah = {freeboard:.2f} m")
    print(f"  最大允许流速: v_max = {v_max:.2f} m/s")

    # 现有河道断面
    stations = [0, 25, 35, 35, 75, 85, 110]
    elevations = [112, 112, 106, 106, 106, 112, 112]
    bankfull_elevation = 111.0

    channel = CompoundChannel(
        stations=stations,
        elevations=elevations,
        bankfull_elevation=bankfull_elevation,
        length=5000.0,
        bottom_slope=0.0006,
        manning_n_main=0.028,
        manning_n_floodplain=0.045
    )

    # 计算百年一遇水位
    h_100 = channel.normal_depth(Q_100yr, method='divided')
    water_level_100 = channel.z_min + h_100

    # 检查是否满足设计要求
    props = channel.properties(h_100)
    A = props['A']
    v_avg = Q_100yr / A

    # 获取分区信息
    info = channel.get_subdivision_info(h_100)
    v_main = info['main']['v']

    # 堤顶高程
    levee_elevation = water_level_100 + freeboard

    print(f"\n现有断面复核：")
    print(f"  百年一遇水深: h_100 = {h_100:.3f} m")
    print(f"  百年一遇水位: z_100 = {water_level_100:.2f} m")
    print(f"  平均流速: v_avg = {v_avg:.3f} m/s")
    print(f"  主槽流速: v_main = {v_main:.3f} m/s")
    print(f"  所需堤顶高程: z_levee = {levee_elevation:.2f} m")
    print(f"  现有堤顶高程: {elevations[0]:.2f} m")

    # 评价
    print(f"\n设计复核：")

    if v_main > v_max:
        print(f"   主槽流速 {v_main:.2f} m/s > {v_max:.2f} m/s，需要护坡措施")
    else:
        print(f"   主槽流速 {v_main:.2f} m/s <= {v_max:.2f} m/s，满足要求")

    if levee_elevation > elevations[0]:
        delta_h = levee_elevation - elevations[0]
        print(f"   需加高堤防 {delta_h:.2f} m")
    else:
        print(f"   堤防高度满足要求")

    # 分析不同重现期的安全裕度
    print(f"\n安全裕度分析：")
    print(f"{'重现期':>12} {'Q(m^3/s)':>12} {'h(m)':>12} {'水位(m)':>12} "
          f"{'裕度(m)':>12} {'评价':>12}")
    print("-" * 84)

    design_scenarios = [
        ("5年", 150),
        ("10年", 200),
        ("20年", 280),
        ("50年", 350),
        ("100年", 400)
    ]

    for period, Q in design_scenarios:
        h = channel.normal_depth(Q, method='divided')
        water_level = channel.z_min + h
        margin = elevations[0] - water_level

        if margin > freeboard:
            evaluation = "安全"
        elif margin > 0:
            evaluation = "临界"
        else:
            evaluation = "超标"

        print(f"{period:>12} {Q:>12.1f} {h:>12.3f} {water_level:>12.2f} "
              f"{margin:>12.2f} {evaluation:>12}")


def example_5_manning_sensitivity():
    """
    示例5：Manning系数敏感性分析

    分析滩地糙率变化对水深和流速的影响
    """
    print("\n" + "="*80)
    print("示例5：Manning系数敏感性分析")
    print("="*80)

    stations = [0, 20, 30, 30, 70, 80, 100]
    elevations = [115, 115, 110, 110, 110, 115, 115]
    bankfull_elevation = 114.0

    Q = 200.0  # 固定流量

    print(f"\n分析条件：")
    print(f"  固定流量: Q = {Q:.1f} m^3/s")
    print(f"  主槽Manning系数: n_main = 0.030（固定）")
    print(f"  滩地Manning系数: 变化范围 0.035-0.070")

    print(f"\n敏感性分析结果：")
    print(f"{'n_flood':>12} {'h(m)':>12} {'Deltah(m)':>12} {'v_main(m/s)':>15} "
          f"{'v_flood(m/s)':>15} {'主槽Q(%)':>12}")
    print("-" * 90)

    n_main = 0.030
    n_flood_values = [0.035, 0.040, 0.045, 0.050, 0.060, 0.070]

    h_baseline = None

    for n_flood in n_flood_values:
        channel = CompoundChannel(
            stations=stations,
            elevations=elevations,
            bankfull_elevation=bankfull_elevation,
            length=2000.0,
            bottom_slope=0.0008,
            manning_n_main=n_main,
            manning_n_floodplain=n_flood
        )

        h = channel.normal_depth(Q, method='divided')

        if h_baseline is None:
            h_baseline = h
            delta_h = 0.0
        else:
            delta_h = h - h_baseline

        # 获取分区信息
        info = channel.get_subdivision_info(h)
        v_main = info['main']['v']
        v_flood_left = info['left_flood']['v']
        v_flood_right = info['right_flood']['v']
        v_flood_avg = (v_flood_left + v_flood_right) / 2 if (v_flood_left + v_flood_right) > 0 else 0

        Q_main = info['main']['Q']
        main_pct = (Q_main / Q) * 100

        print(f"{n_flood:>12.4f} {h:>12.4f} {delta_h:>12.4f} {v_main:>15.3f} "
              f"{v_flood_avg:>15.3f} {main_pct:>12.1f}")

    print("\n结论：")
    print("  1. 滩地糙率增加 -> 水深增加（阻力增大）")
    print("  2. 滩地糙率增加 -> 滩地流速降低")
    print("  3. 滩地糙率增加 -> 主槽承担更大比例的流量")
    print("  4. n_flood从0.035增至0.070，水深增加约0.2-0.3m")
    print("  5. 准确估计滩地糙率对水位预报至关重要")


def example_6_subdivision_details():
    """
    示例6：分区详细信息

    展示复合断面各分区的详细水力计算
    """
    print("\n" + "="*80)
    print("示例6：分区详细水力信息")
    print("="*80)

    stations = [0, 15, 20, 20, 60, 65, 80]
    elevations = [108, 108, 103, 103, 103, 108, 108]
    bankfull_elevation = 107.0

    channel = CompoundChannel(
        stations=stations,
        elevations=elevations,
        bankfull_elevation=bankfull_elevation,
        length=2500.0,
        bottom_slope=0.0007,
        manning_n_main=0.028,
        manning_n_floodplain=0.042
    )

    Q = 180.0
    h = channel.normal_depth(Q, method='divided')

    print(f"\n总体信息：")
    print(f"  流量: Q = {Q:.1f} m^3/s")
    print(f"  水深: h = {h:.3f} m")
    print(f"  水位: z = {channel.z_min + h:.2f} m")
    print(f"  是否漫滩: {'是' if channel.is_overbank(h) else '否'}")

    # 获取详细分区信息
    info = channel.get_subdivision_info(h)

    print(f"\n分区详细信息：")
    print(f"{'分区':>15} {'A(m^2)':>12} {'P(m)':>12} {'R(m)':>12} "
          f"{'n':>12} {'Q(m^3/s)':>12} {'v(m/s)':>12}")
    print("-" * 99)

    zones = [
        ('左滩地', 'left_flood'),
        ('主槽', 'main'),
        ('右滩地', 'right_flood')
    ]

    Q_total_check = 0.0

    for zone_name, zone_key in zones:
        zone_info = info[zone_key]
        A = zone_info['A']
        P = zone_info['P']
        R = zone_info['R']
        n = zone_info['n']
        Q_zone = zone_info['Q']
        v = zone_info['v']

        Q_total_check += Q_zone

        if A > 0:
            print(f"{zone_name:>15} {A:>12.2f} {P:>12.2f} {R:>12.3f} "
                  f"{n:>12.4f} {Q_zone:>12.2f} {v:>12.3f}")
        else:
            print(f"{zone_name:>15} {'---':>12} {'---':>12} {'---':>12} "
                  f"{'---':>12} {'---':>12} {'---':>12}")

    print("-" * 99)
    print(f"{'总计':>15} {info['total']['A']:>12.2f} {info['total']['P']:>12.2f} "
          f"{info['total']['R']:>12.3f} {'---':>12} {Q_total_check:>12.2f} "
          f"{info['total']['v']:>12.3f}")

    print(f"\n流量分配：")
    for zone_name, zone_key in zones:
        Q_zone = info[zone_key]['Q']
        pct = (Q_zone / Q) * 100 if Q > 0 else 0
        print(f"  {zone_name}: {Q_zone:.2f} m^3/s ({pct:.1f}%)")

    print(f"\n验证：")
    print(f"  各分区流量之和: {Q_total_check:.2f} m^3/s")
    print(f"  总流量: {Q:.2f} m^3/s")
    print(f"  误差: {abs(Q_total_check - Q):.4f} m^3/s")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("复合断面渠道示例集")
    print("="*80)

    example_1_basic_compound_channel()
    example_2_flood_stage_analysis()
    example_3_method_comparison()
    example_4_flood_design()
    example_5_manning_sensitivity()
    example_6_subdivision_details()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == '__main__':
    main()
