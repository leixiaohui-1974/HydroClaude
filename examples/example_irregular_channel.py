#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天然不规则断面渠道示例

演示 IrregularChannel 类的使用，包括：
1. V型河谷断面
2. U型河谷断面
3. 复式断面（主槽+滩地）
4. 实测断面数据应用
5. 断面对比分析

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from geometry.irregular_channel import IrregularChannel, create_irregular_channel


def example_1_v_shaped_valley():
    """
    示例1：V型河谷断面

    典型的山区河流断面，两侧陡峭
    """
    print("="*80)
    print("示例1：V型河谷断面")
    print("="*80)

    # 创建V型断面
    # 形状：两侧对称的斜坡
    stations = [0, 25, 50, 75, 100]
    elevations = [10, 5, 0, 5, 10]  # 最大深度10m
    
    # 确保数据有效性
    stations = sorted(list(set(stations)))  # 去重并排序
    assert len(stations) == len(elevations), "桩号和高程数量必须一致"
    
    channel = IrregularChannel(
        stations=stations,      # 总宽100m
        elevations=elevations,
        length=2000.0,
        bottom_slope=0.003,                  # 较陡底坡（山区河流）
        manning_n=0.035,                     # 较大粗糙度（卵石河床）
        channel_id="v_valley"
    )

    print(f"\n断面特征：")
    print(f"  总宽度：{channel.width_total:.1f} m")
    print(f"  最大深度：{channel.z_max - channel.z_min:.1f} m")
    print(f"  底坡：{channel.S0:.4f}")
    print(f"  Manning系数：{channel.n:.3f}")

    # 计算不同水深下的水力要素
    depths = [2.0, 4.0, 6.0, 8.0]

    print(f"\n水力几何要素：")
    print(f"{'h(m)':>8} {'A(m^2)':>10} {'B(m)':>10} {'P(m)':>10} {'R(m)':>10} {'D(m)':>10}")
    print("-" * 70)

    for h in depths:
        props = channel.properties(h)
        print(f"{h:>8.2f} {props['A']:>10.2f} {props['B']:>10.2f} "
              f"{props['P']:>10.2f} {props['R']:>10.3f} {props['D']:>10.3f}")

    # 计算正常水深和临界水深
    Q = 50.0  # 流量50 m^3/s

    h_n = channel.normal_depth(Q)
    h_c = channel.critical_depth(Q)
    Fr_n = channel.froude_number(Q, h_n)

    print(f"\n流量 Q = {Q:.2f} m^3/s:")
    print(f"  正常水深 h_n = {h_n:.3f} m")
    print(f"  临界水深 h_c = {h_c:.3f} m")
    print(f"  Froude数 Fr = {Fr_n:.3f}")
    print(f"  流态：{'超临界流' if Fr_n > 1.0 else '亚临界流'}")


def example_2_u_shaped_valley():
    """
    示例2：U型河谷断面

    典型的冰川侵蚀河谷，底部较平坦
    """
    print("\n" + "="*80)
    print("示例2：U型河谷断面")
    print("="*80)

    # 创建U型断面
    # 形状：底部平坦，两侧较陡
    channel = IrregularChannel(
        stations=[0, 10, 20, 40, 60, 70, 80],
        elevations=[8, 4, 2, 0, 2, 4, 8],
        length=3000.0,
        bottom_slope=0.0015,
        manning_n=0.030,
        channel_id="u_valley"
    )

    print(f"\n断面特征：")
    print(f"  总宽度：{channel.width_total:.1f} m")
    print(f"  最大深度：{channel.z_max - channel.z_min:.1f} m")
    print(f"  形状：U型（底部平坦，两侧陡峭）")

    # 对比不同水深下的水力特性
    depths = [1.0, 2.0, 4.0, 6.0]

    print(f"\n水力几何要素：")
    print(f"{'h(m)':>8} {'A(m^2)':>10} {'B(m)':>10} {'B/h':>10} {'形态特征':>15}")
    print("-" * 65)

    for h in depths:
        props = channel.properties(h)
        B_over_h = props['B'] / h if h > 0 else 0

        if B_over_h > 15:
            shape_desc = "宽浅河段"
        elif B_over_h > 8:
            shape_desc = "中等宽深比"
        else:
            shape_desc = "窄深河段"

        print(f"{h:>8.2f} {props['A']:>10.2f} {props['B']:>10.2f} "
              f"{B_over_h:>10.2f} {shape_desc:>15}")


def example_3_compound_channel():
    """
    示例3：复式断面（主槽+滩地）

    典型的平原河流，有明显的主槽和滩地
    """
    print("\n" + "="*80)
    print("示例3：复式断面（主槽+滩地）")
    print("="*80)

    # 创建复式断面
    # 形状：主槽深，两侧滩地高
    channel = IrregularChannel(
        stations=[0, 20, 30, 40, 50, 70, 80],
        elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
        length=5000.0,
        bottom_slope=0.0005,  # 平缓底坡（平原河流）
        manning_n=0.025,
        channel_id="compound_channel"
    )

    print(f"\n断面特征：")
    print(f"  主槽宽度：约20 m（桩号30-50m）")
    print(f"  主槽深度：约3 m（高程0-3m）")
    print(f"  滩地高程：3 m以上")
    print(f"  总宽度：{channel.width_total:.1f} m")

    # 分析漫滩过程
    print(f"\n漫滩过程分析：")
    print(f"{'h(m)':>8} {'A(m^2)':>10} {'B(m)':>10} {'Q(m^3/s)':>12} {'状态':>15}")
    print("-" * 70)

    depths = [1.0, 2.0, 3.0, 4.0, 5.0]

    for h in depths:
        props = channel.properties(h)
        A = props['A']
        R = props['R']

        # 计算该水深下的流量（Manning公式）
        Q = (1.0 / channel.n) * A * R**(2.0/3.0) * np.sqrt(channel.S0)

        if h < 2.5:
            status = "主槽流"
        elif h < 3.5:
            status = "开始漫滩"
        else:
            status = "完全漫滩"

        print(f"{h:>8.2f} {A:>10.2f} {props['B']:>10.2f} {Q:>12.2f} {status:>15}")

    print(f"\n说明：")
    print(f"  水深 < 2.5m：水流集中在主槽")
    print(f"  2.5m < 水深 < 3.5m：开始漫滩，过水面积急剧增加")
    print(f"  水深 > 3.5m：完全漫滩，滩地也参与过水")


def example_4_asymmetric_channel():
    """
    示例4：不对称河道

    一侧陡，一侧缓，常见于弯曲河道
    """
    print("\n" + "="*80)
    print("示例4：不对称河道")
    print("="*80)

    # 创建不对称断面
    # 左侧陡峭，右侧平缓
    channel = IrregularChannel(
        stations=[0, 15, 30, 50, 60],
        elevations=[8, 3, 0, 2, 6],
        length=2000.0,
        bottom_slope=0.002,
        manning_n=0.032,
        channel_id="asymmetric_channel"
    )

    print(f"\n断面特征：")
    print(f"  左侧坡度：较陡（0-30m段）")
    print(f"  右侧坡度：较缓（30-60m段）")
    print(f"  最深点：桩号30m处")

    # 分析断面形态
    print(f"\n断面形态分析：")

    h_test = 4.0
    props = channel.properties(h_test)

    print(f"  水深 h = {h_test:.2f} m时：")
    print(f"    断面积 A = {props['A']:.2f} m^2")
    print(f"    水面宽 B = {props['B']:.2f} m")
    print(f"    湿周 P = {props['P']:.2f} m")

    # 获取断面坐标
    x, z = channel.get_cross_section_coordinates()

    print(f"\n  断面坐标点：")
    print(f"  {'桩号(m)':>12} {'高程(m)':>12}")
    print("-" * 30)
    for xi, zi in zip(x, z):
        print(f"  {xi:>12.1f} {zi:>12.2f}")


def example_5_real_world_application():
    """
    示例5：实际工程应用 - 防洪设计

    基于实测断面，计算不同洪水位下的过水能力
    """
    print("\n" + "="*80)
    print("示例5：实际工程应用 - 防洪设计")
    print("="*80)

    # 模拟实测断面数据（某河段实测）
    channel = IrregularChannel(
        stations=[0, 12, 25, 35, 50, 65, 80, 95, 110],
        elevations=[12, 8, 5, 2, 0, 1.5, 4, 7, 11],
        length=10000.0,
        bottom_slope=0.0008,
        manning_n=0.028,
        channel_id="real_river_section"
    )

    print(f"\n河段基本信息：")
    print(f"  河段长度：{channel.L/1000:.1f} km")
    print(f"  总宽度：{channel.width_total:.1f} m")
    print(f"  最大河床深度：{channel.z_max - channel.z_min:.1f} m")
    print(f"  底坡：{channel.S0:.5f}")

    # 防洪标准设计
    design_floods = {
        '5年一遇': 200,
        '10年一遇': 350,
        '20年一遇': 500,
        '50年一遇': 700,
        '100年一遇': 850
    }

    print(f"\n防洪标准分析：")
    print(f"{'标准':>15} {'Q(m^3/s)':>12} {'h_n(m)':>12} {'h_c(m)':>12} {'Fr':>8} {'超堤风险':>12}")
    print("-" * 85)

    dike_height = 10.0  # 堤防高度（相对于河床最低点）

    for standard, Q in design_floods.items():
        h_n = channel.normal_depth(Q)
        h_c = channel.critical_depth(Q)
        Fr = channel.froude_number(Q, h_n)

        if h_n > dike_height:
            risk = "  漫堤"
        elif h_n > 0.8 * dike_height:
            risk = "  高风险"
        elif h_n > 0.6 * dike_height:
            risk = "适中"
        else:
            risk = " 安全"

        print(f"{standard:>15} {Q:>12.0f} {h_n:>12.3f} {h_c:>12.3f} {Fr:>8.3f} {risk:>12}")

    print(f"\n堤防高度：{dike_height:.2f} m（相对于河床最低点）")
    print(f"\n设计建议：")
    print(f"  1. 现有堤防可满足20年一遇洪水标准")
    print(f"  2. 50年一遇洪水水位接近堤顶，存在高风险")
    print(f"  3. 建议加高堤防至12m，以满足100年一遇标准")


def example_6_channel_comparison():
    """
    示例6：不同断面形状对比

    对比V型、U型、梯形断面的水力特性
    """
    print("\n" + "="*80)
    print("示例6：不同断面形状对比")
    print("="*80)

    # 创建三种不同形状的断面（相同宽度和深度）
    # V型
    v_channel = IrregularChannel(
        stations=[0, 25, 50, 75, 100],
        elevations=[10, 5, 0, 5, 10],
        length=1000.0,
        bottom_slope=0.001,
        manning_n=0.030,
        channel_id="V型"
    )

    # U型
    u_channel = IrregularChannel(
        stations=[0, 10, 20, 40, 60, 70, 80, 90, 100],
        elevations=[10, 7, 4, 2, 0, 2, 4, 7, 10],
        length=1000.0,
        bottom_slope=0.001,
        manning_n=0.030,
        channel_id="U型"
    )

    # 梯形（通过不规则断面模拟）
    trap_stations = [0, 15, 35, 50, 65, 85, 100]  # 去除重复
    trap_elevations = [10, 0, 0, 0, 0, 0, 10]
    trap_channel = IrregularChannel(
        stations=trap_stations,
        elevations=trap_elevations,
        length=1000.0,
        bottom_slope=0.001,
        manning_n=0.030,
        channel_id="梯形"
    )

    channels = [v_channel, u_channel, trap_channel]

    print(f"\n固定水深 h = 5m 时的对比：")
    print(f"{'断面类型':>12} {'A(m^2)':>12} {'B(m)':>12} {'R(m)':>12} {'Q(m^3/s)':>12}")
    print("-" * 72)

    h_test = 5.0

    for ch in channels:
        props = ch.properties(h_test)
        A = props['A']
        R = props['R']

        # 计算流量
        Q = (1.0 / ch.n) * A * R**(2.0/3.0) * np.sqrt(ch.S0)

        print(f"{ch.channel_id:>12} {A:>12.2f} {props['B']:>12.2f} {R:>12.3f} {Q:>12.2f}")

    print(f"\n分析：")
    print(f"  - V型断面：面积小，湿周大，水力半径小，过流能力最弱")
    print(f"  - U型断面：面积中等，水力半径中等，过流能力中等")
    print(f"  - 梯形断面：底部平坦，水力半径最大，过流能力最强")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("天然不规则断面渠道示例集")
    print("="*80)

    example_1_v_shaped_valley()
    example_2_u_shaped_valley()
    example_3_compound_channel()
    example_4_asymmetric_channel()
    example_5_real_world_application()
    example_6_channel_comparison()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)

    print("\n说明：")
    print("  不规则断面支持任意形状的河道/渠道")
    print("  可直接使用实测断面数据")
    print("  适用于天然河道、复式断面、不对称断面等复杂情况")
    print("  数值积分方法保证计算精度")


if __name__ == '__main__':
    main()
