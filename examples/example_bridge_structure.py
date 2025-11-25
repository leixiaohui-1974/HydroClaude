#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
桥梁水工建筑物示例

演示 Bridge 类的使用，包括：
1. 基本桥梁过流计算
2. 流态转换分析（自由流 vs 压力流）
3. 桥梁壅水效应
4. 洪水位计算
5. 桥梁过流能力评估
6. 桥墩影响分析

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.bridge_structure import Bridge, create_bridge


def example_1_basic_bridge_flow():
    """
    示例1：基本桥梁过流计算

    计算不同上下游水位组合下的流量和流态
    """
    print("="*80)
    print("示例1：基本桥梁过流计算")
    print("="*80)

    # 创建桥梁
    bridge = Bridge(
        bridge_id="BR001",
        total_width=30.0,       # 桥孔总宽 30m
        opening_height=5.0,     # 桥孔净高 5m
        bottom_elevation=100.0, # 桥底高程 100m
        n_piers=2,              # 2个桥墩
        pier_width=1.5          # 每个桥墩宽1.5m
    )

    print(f"\n桥梁参数：")
    props = bridge.properties()
    print(f"  桥孔总宽: {props['total_width']:.1f} m")
    print(f"  桥墩数量: {props['n_piers']}")
    print(f"  桥墩总宽: {props['total_pier_width']:.1f} m")
    print(f"  有效净宽: {props['effective_width']:.1f} m")
    print(f"  桥孔净高: {props['opening_height']:.1f} m")
    print(f"  桥底高程: {props['bottom_elevation']:.1f} m")
    print(f"  桥面高程: {props['deck_elevation']:.1f} m")

    # 不同水位组合
    print(f"\n过流计算：")
    print(f"{'上游(m)':>10} {'下游(m)':>10} {'流态':>20} {'流量(m^3/s)':>15} {'流速(m/s)':>12} {'水头损失(m)':>15}")
    print("-" * 95)

    test_cases = [
        (101.0, 100.5),  # 堰流
        (103.0, 102.0),  # 堰流
        (104.5, 103.0),  # 自由孔流
        (106.0, 104.0),  # 自由孔流
        (107.0, 106.0),  # 压力流
        (108.0, 107.5),  # 压力流
    ]

    for h_up, h_down in test_cases:
        result = bridge.compute_discharge(h_up, h_down)

        regime_cn = {
            "free_flow_weir": "自由堰流",
            "free_flow_orifice": "自由孔流",
            "pressure_flow": "压力流"
        }
        regime_str = regime_cn[result['regime']]

        print(f"{h_up:>10.1f} {h_down:>10.1f} {regime_str:>20} "
              f"{result['Q']:>15.2f} {result['velocity']:>12.3f} {result['head_loss']:>15.3f}")

    print("\n说明：")
    print("  - 堰流：上游水位较低，水流跃过桥底")
    print("  - 自由孔流：上游水位较高，但下游未淹没桥面")
    print("  - 压力流：下游水位淹没桥面，形成满管流")


def example_2_flow_regime_transition():
    """
    示例2：流态转换分析

    分析从自由流到压力流的转换过程
    """
    print("\n" + "="*80)
    print("示例2：流态转换分析")
    print("="*80)

    bridge = Bridge(
        bridge_id="BR002",
        total_width=25.0,
        opening_height=4.0,
        bottom_elevation=100.0
    )
    # z_bottom = 100.0 m, z_deck = 104.0 m

    # 固定上游水位，变化下游水位
    h_upstream = 107.0
    h_downstream_values = np.linspace(101.0, 106.5, 20)

    print(f"\n固定上游水位: {h_upstream:.1f} m")
    print(f"变化下游水位: {h_downstream_values[0]:.1f} - {h_downstream_values[-1]:.1f} m")
    print(f"\n{'下游(m)':>10} {'流态':>20} {'流量(m^3/s)':>15} {'水头损失(m)':>15}")
    print("-" * 72)

    Q_values = []
    regimes = []

    for h_down in h_downstream_values:
        result = bridge.compute_discharge(h_upstream, h_down)
        Q_values.append(result['Q'])
        regimes.append(result['regime'])

        # 仅打印几个关键点
        if h_down in [101.0, 103.0, 103.9, 104.1, 105.0, 106.5]:
            regime_cn = {
                "free_flow_weir": "自由堰流",
                "free_flow_orifice": "自由孔流",
                "pressure_flow": "压力流"
            }
            regime_str = regime_cn[result['regime']]
            print(f"{h_down:>10.1f} {regime_str:>20} {result['Q']:>15.2f} {result['head_loss']:>15.3f}")

    print("\n分析：")
    print(f"  1. 下游水位 < {bridge.z_deck:.1f}m (桥面)：自由流")
    print(f"  2. 下游水位 >= {bridge.z_deck:.1f}m (桥面)：压力流")
    print(f"  3. 自由流 -> 压力流转换点：下游水位 = 桥面高程")
    print(f"  4. 下游水位升高 -> 水头差减小 -> 流量减小")


def example_3_backwater_effect():
    """
    示例3：桥梁壅水效应

    给定流量和下游水位，计算桥梁引起的上游壅水
    """
    print("\n" + "="*80)
    print("示例3：桥梁壅水效应")
    print("="*80)

    bridge = Bridge(
        bridge_id="BR003",
        total_width=28.0,
        opening_height=5.5,
        bottom_elevation=100.0,
        n_piers=1,
        pier_width=2.0,
        Cd_pressure=0.8
    )

    print(f"\n桥梁参数：")
    print(f"  有效净宽: {bridge.W_effective:.1f} m")
    print(f"  桥孔净高: {bridge.H_opening:.1f} m")
    print(f"  桥底高程: {bridge.z_bottom:.1f} m")
    print(f"  桥面高程: {bridge.z_deck:.1f} m")

    # 不同设计流量
    h_downstream = 106.0  # 下游水位固定

    print(f"\n下游水位固定: {h_downstream:.1f} m")
    print(f"\n{'设计流量':>12} {'上游水位(m)':>15} {'壅水高度(m)':>15} {'水头损失(m)':>15} {'流速(m/s)':>12}")
    print("-" * 84)

    flow_rates = [50, 100, 150, 200, 250, 300]

    for Q in flow_rates:
        # 计算壅水后的上游水位
        h_upstream = bridge.compute_backwater_effect(Q, h_downstream, method='iterative')

        # 壅水高度 = 上游水位 - 下游水位
        backwater_height = h_upstream - h_downstream

        # 验证流量
        result = bridge.compute_discharge(h_upstream, h_downstream)

        print(f"Q={Q:>3d} m^3/s {h_upstream:>15.3f} {backwater_height:>15.3f} "
              f"{result['head_loss']:>15.3f} {result['velocity']:>12.3f}")

    print("\n结论：")
    print("  1. 流量增大 -> 上游壅水增高")
    print("  2. 壅水高度与流量平方成正比（压力流）")
    print("  3. 桥梁过流能力不足会显著抬高上游水位")
    print("  4. 设计时需考虑桥梁壅水对上游防洪的影响")


def example_4_flood_level_calculation():
    """
    示例4：洪水位计算

    计算不同重现期洪水下的桥梁过流水位
    """
    print("\n" + "="*80)
    print("示例4：洪水位计算")
    print("="*80)

    # 现有桥梁
    bridge = Bridge(
        bridge_id="BR_EXISTING",
        total_width=35.0,
        opening_height=6.0,
        bottom_elevation=98.0,
        n_piers=3,
        pier_width=1.5,
        Cd_pressure=0.75
    )

    print(f"\n现有桥梁参数：")
    print(f"  有效净宽: {bridge.W_effective:.1f} m")
    print(f"  桥孔净高: {bridge.H_opening:.1f} m")
    print(f"  桥面高程: {bridge.z_deck:.1f} m")

    # 天然河道下游水位（无桥梁时）
    h_downstream_natural = 105.0

    # 不同重现期的设计流量
    design_floods = [
        ("5年", 150),
        ("10年", 200),
        ("20年", 280),
        ("50年", 380),
        ("100年", 500)
    ]

    print(f"\n下游天然水位: {h_downstream_natural:.1f} m")
    print(f"\n{'重现期':>12} {'流量(m^3/s)':>15} {'上游水位(m)':>15} "
          f"{'壅水(m)':>12} {'流态':>15} {'评价':>12}")
    print("-" * 96)

    freeboard = 0.5  # 安全超高 0.5m
    max_safe_level = bridge.z_deck + freeboard  # 最高安全水位

    for period, Q in design_floods:
        # 计算桥梁上游水位
        h_upstream = bridge.compute_backwater_effect(Q, h_downstream_natural, method='iterative')

        # 壅水高度
        backwater = h_upstream - h_downstream_natural

        # 流态
        result = bridge.compute_discharge(h_upstream, h_downstream_natural)
        regime_cn = {
            "free_flow_weir": "自由堰流",
            "free_flow_orifice": "自由孔流",
            "pressure_flow": "压力流"
        }
        regime = regime_cn[result['regime']]

        # 安全评价
        if h_upstream < max_safe_level:
            evaluation = "安全"
        elif h_upstream < bridge.z_deck + 1.0:
            evaluation = "临界"
        else:
            evaluation = "超标"

        print(f"{period:>12} {Q:>15.1f} {h_upstream:>15.2f} {backwater:>12.2f} {regime:>15} {evaluation:>12}")

    print(f"\n设计建议：")
    print(f"  桥面高程: {bridge.z_deck:.1f} m")
    print(f"  安全水位（含超高）: {max_safe_level:.1f} m")
    print(f"   5-20年一遇：安全")
    print(f"   50年一遇：需核查")
    print(f"   100年一遇：可能超标，建议加大桥孔或加高桥面")


def example_5_bridge_capacity_assessment():
    """
    示例5：桥梁过流能力评估

    评估现有桥梁的最大过流能力
    """
    print("\n" + "="*80)
    print("示例5：桥梁过流能力评估")
    print("="*80)

    bridge = Bridge(
        bridge_id="BR_ASSESS",
        total_width=32.0,
        opening_height=5.5,
        bottom_elevation=100.0,
        n_piers=2,
        pier_width=1.8
    )

    print(f"\n桥梁参数：")
    print(f"  有效净宽: {bridge.W_effective:.1f} m")
    print(f"  桥孔净高: {bridge.H_opening:.1f} m")
    print(f"  桥底高程: {bridge.z_bottom:.1f} m")
    print(f"  桥面高程: {bridge.z_deck:.1f} m")

    # 评估不同上下游水位差下的过流能力
    h_downstream = 105.0
    h_upstream_values = np.linspace(105.5, 110.0, 10)

    print(f"\n下游水位固定: {h_downstream:.1f} m")
    print(f"\n{'上游水位(m)':>15} {'水位差(m)':>12} {'流量(m^3/s)':>15} "
          f"{'流速(m/s)':>12} {'流态':>15}")
    print("-" * 84)

    Q_values = []

    for h_up in h_upstream_values:
        result = bridge.compute_discharge(h_up, h_downstream)
        Q_values.append(result['Q'])

        regime_cn = {
            "free_flow_weir": "自由堰流",
            "free_flow_orifice": "自由孔流",
            "pressure_flow": "压力流"
        }
        regime = regime_cn[result['regime']]

        dh = h_up - h_downstream

        print(f"{h_up:>15.2f} {dh:>12.2f} {result['Q']:>15.1f} "
              f"{result['velocity']:>12.2f} {regime:>15}")

    print(f"\n过流能力分析：")
    Q_max = max(Q_values)
    h_max = h_upstream_values[Q_values.index(Q_max)]
    print(f"  最大过流量: {Q_max:.1f} m^3/s")
    print(f"  对应上游水位: {h_max:.2f} m")
    print(f"  最大流速: {max([bridge.compute_discharge(h, h_downstream)['velocity'] for h in h_upstream_values]):.2f} m/s")

    # 推荐设计流量
    Q_design_recommended = Q_max * 0.85  # 85% 的最大过流量
    print(f"\n推荐设计流量: {Q_design_recommended:.1f} m^3/s (最大过流量的85%)")


def example_6_pier_effect_analysis():
    """
    示例6：桥墩影响分析

    分析桥墩数量和宽度对过流能力的影响
    """
    print("\n" + "="*80)
    print("示例6：桥墩影响分析")
    print("="*80)

    total_width = 30.0
    opening_height = 5.0
    bottom_elevation = 100.0

    # 固定水位
    h_upstream = 107.0
    h_downstream = 106.0

    print(f"\n固定条件：")
    print(f"  桥孔总宽: {total_width:.1f} m")
    print(f"  桥孔净高: {opening_height:.1f} m")
    print(f"  上游水位: {h_upstream:.1f} m")
    print(f"  下游水位: {h_downstream:.1f} m")

    print(f"\n桥墩配置对比：")
    print(f"{'桥墩数':>10} {'墩宽(m)':>10} {'有效宽(m)':>12} "
          f"{'流量(m^3/s)':>15} {'流量损失(%)':>15}")
    print("-" * 75)

    pier_configs = [
        (0, 0.0),     # 无桥墩
        (1, 1.5),
        (2, 1.5),
        (3, 1.5),
        (2, 2.0),     # 增大墩宽
        (2, 2.5),
    ]

    Q_baseline = None

    for n_piers, pier_width in pier_configs:
        bridge = Bridge(
            bridge_id=f"BR_PIER_{n_piers}_{pier_width}",
            total_width=total_width,
            opening_height=opening_height,
            bottom_elevation=bottom_elevation,
            n_piers=n_piers,
            pier_width=pier_width
        )

        result = bridge.compute_discharge(h_upstream, h_downstream)
        Q = result['Q']

        if Q_baseline is None:
            Q_baseline = Q
            loss_pct = 0.0
        else:
            loss_pct = (Q_baseline - Q) / Q_baseline * 100

        W_eff = bridge.W_effective

        print(f"{n_piers:>10} {pier_width:>10.1f} {W_eff:>12.1f} "
              f"{Q:>15.1f} {loss_pct:>15.1f}")

    print("\n结论：")
    print("  1. 桥墩数量增加 -> 有效宽度减小 -> 流量减小")
    print("  2. 桥墩宽度增加 -> 有效宽度减小 -> 流量减小")
    print("  3. 流量与有效宽度成正比（压力流）")
    print("  4. 设计时应权衡结构安全与过流能力")


def example_7_discharge_curve():
    """
    示例7：流量曲线绘制

    绘制桥梁过流流量与水位的关系曲线
    """
    print("\n" + "="*80)
    print("示例7：桥梁流量曲线")
    print("="*80)

    bridge = Bridge(
        bridge_id="BR_CURVE",
        total_width=28.0,
        opening_height=5.0,
        bottom_elevation=100.0,
        n_piers=2,
        pier_width=1.2
    )

    # 固定下游水位，变化上游水位
    h_downstream = 104.0
    h_upstream_range = np.linspace(100.5, 110.0, 100)

    Q_values = []
    regimes = []

    print(f"\n计算流量曲线...")
    print(f"  下游水位: {h_downstream:.1f} m")
    print(f"  上游水位范围: {h_upstream_range[0]:.1f} - {h_upstream_range[-1]:.1f} m")

    for h_up in h_upstream_range:
        result = bridge.compute_discharge(h_up, h_downstream)
        Q_values.append(result['Q'])
        regimes.append(result['regime'])

    # 找出流态转换点
    regime_changes = []
    for i in range(1, len(regimes)):
        if regimes[i] != regimes[i-1]:
            regime_changes.append((h_upstream_range[i], Q_values[i]))

    print(f"\n流态转换点：")
    for i, (h, Q) in enumerate(regime_changes):
        regime_from = regimes[i]
        regime_to = regimes[i+1] if i+1 < len(regimes) else regimes[-1]
        regime_cn = {
            "free_flow_weir": "自由堰流",
            "free_flow_orifice": "自由孔流",
            "pressure_flow": "压力流"
        }
        print(f"  上游水位 {h:.2f} m: {regime_cn.get(regime_from, regime_from)} -> "
              f"{regime_cn.get(regime_to, regime_to)}, Q = {Q:.1f} m^3/s")

    print(f"\n流量范围: {min(Q_values):.1f} - {max(Q_values):.1f} m^3/s")
    print(f"桥面高程: {bridge.z_deck:.1f} m")

    print("\n说明：")
    print("  流量曲线可用于：")
    print("  1. 洪水演算的边界条件")
    print("  2. 水位-流量关系查询")
    print("  3. 桥梁过流能力评估")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("桥梁水工建筑物示例集")
    print("="*80)

    example_1_basic_bridge_flow()
    example_2_flow_regime_transition()
    example_3_backwater_effect()
    example_4_flood_level_calculation()
    example_5_bridge_capacity_assessment()
    example_6_pier_effect_analysis()
    example_7_discharge_curve()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == '__main__':
    main()
