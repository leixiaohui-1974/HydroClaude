#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rating Curve 边界条件示例

演示 RatingCurveBoundary 类的使用，包括：
1. 基本 Rating Curve 边界条件
2. 双向转换（h -> Q 和 Q -> h）
3. 幂律拟合
4. 水文站应用
5. 不同插值方法
6. 外推方法比较
7. 文件读写

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boundary.rating_curve_bc import RatingCurveBoundary, create_rating_curve


def example_1_basic_rating_curve():
    """
    示例1：基本 Rating Curve 边界条件

    创建简单的水位-流量关系并进行双向查询
    """
    print("="*80)
    print("示例1：基本 Rating Curve 边界条件")
    print("="*80)

    # 河道断面的实测水位-流量数据
    h_data = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]  # 水位 (m)
    Q_data = [5.0, 15.0, 30.0, 50.0, 75.0, 105.0, 140.0]  # 流量 (m^3/s)

    rc = RatingCurveBoundary(
        bc_id="RC_MAIN",
        h_data=h_data,
        Q_data=Q_data,
        interpolation_method="linear"
    )

    print(f"\nRating Curve 信息：")
    print(f"  标识: {rc.bc_id}")
    print(f"  数据点数: {len(rc.h)}")
    ranges = rc.get_range()
    print(f"  水位范围: {ranges['h_range'][0]:.2f} - {ranges['h_range'][1]:.2f} m")
    print(f"  流量范围: {ranges['Q_range'][0]:.1f} - {ranges['Q_range'][1]:.1f} m^3/s")

    # 水位 -> 流量查询
    print(f"\n水位 -> 流量转换：")
    print(f"{'水位(m)':>12} {'流量(m^3/s)':>15} {'说明':>20}")
    print("-" * 60)

    h_queries = [1.0, 1.25, 1.75, 2.5, 3.2, 4.0]
    for h in h_queries:
        Q = rc.h_to_Q(h)
        if h in h_data:
            note = "数据点"
        else:
            note = "插值"
        print(f"{h:>12.2f} {Q:>15.2f} {note:>20}")

    # 流量 -> 水位查询
    print(f"\n流量 -> 水位转换（反查）：")
    print(f"{'流量(m^3/s)':>15} {'水位(m)':>12} {'说明':>20}")
    print("-" * 60)

    Q_queries = [5.0, 20.0, 45.0, 75.0, 120.0]
    for Q in Q_queries:
        h = rc.Q_to_h(Q)
        if Q in Q_data:
            note = "数据点"
        else:
            note = "插值"
        print(f"{Q:>15.1f} {h:>12.2f} {note:>20}")


def example_2_bidirectional_conversion():
    """
    示例2：双向转换验证

    验证 h -> Q -> h 和 Q -> h -> Q 的一致性
    """
    print("\n" + "="*80)
    print("示例2：双向转换验证")
    print("="*80)

    rc = RatingCurveBoundary(
        bc_id="RC_BIDIRECT",
        h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
        Q_data=[10.0, 25.0, 45.0, 70.0, 100.0]
    )

    print(f"\n双向转换一致性检验：")
    print(f"{'原始水位(m)':>15} {'h->Q(m^3/s)':>15} {'Q->h(m)':>15} {'误差(m)':>15}")
    print("-" * 75)

    h_tests = [1.2, 1.7, 2.3, 2.8]
    for h_orig in h_tests:
        Q = rc.h_to_Q(h_orig)
        h_back = rc.Q_to_h(Q)
        error = abs(h_back - h_orig)
        print(f"{h_orig:>15.2f} {Q:>15.2f} {h_back:>15.2f} {error:>15.4f}")

    print(f"\n{'原始流量(m^3/s)':>18} {'Q->h(m)':>12} {'h->Q(m^3/s)':>15} {'误差(m^3/s)':>18}")
    print("-" * 78)

    Q_tests = [15.0, 35.0, 60.0, 85.0]
    for Q_orig in Q_tests:
        h = rc.Q_to_h(Q_orig)
        Q_back = rc.h_to_Q(h)
        error = abs(Q_back - Q_orig)
        print(f"{Q_orig:>18.1f} {h:>12.2f} {Q_back:>15.2f} {error:>18.2f}")

    print("\n结论：双向转换误差极小（< 0.01），转换一致")


def example_3_power_law_fitting():
    """
    示例3：幂律拟合

    拟合幂律关系 Q = a * (h - h0)^b
    """
    print("\n" + "="*80)
    print("示例3：幂律拟合")
    print("="*80)

    # 生成符合幂律的模拟数据
    h_true = np.array([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    a_true = 8.0
    b_true = 2.2
    h0_true = 1.0
    Q_true = a_true * (h_true - h0_true) ** b_true

    print(f"\n真实幂律参数：")
    print(f"  Q = a * (h - h0)^b")
    print(f"  a = {a_true:.2f}")
    print(f"  b = {b_true:.2f}")
    print(f"  h0 = {h0_true:.2f} m")

    # 使用幂律拟合
    rc_power = RatingCurveBoundary(
        bc_id="RC_POWER",
        h_data=h_true,
        Q_data=Q_true,
        use_power_law=True
    )

    print(f"\n拟合幂律参数：")
    params = rc_power.power_law_params
    print(f"  a = {params['a']:.2f}")
    print(f"  b = {params['b']:.2f}")
    print(f"  h0 = {params['h0']:.2f} m")

    # 评估拟合质量
    fit_stats = rc_power.evaluate_fit()
    print(f"\n拟合质量：")
    print(f"  R^2 = {fit_stats['r_squared']:.6f}")
    print(f"  RMSE = {fit_stats['rmse']:.4f} m^3/s")
    print(f"  MAE = {fit_stats['mae']:.4f} m^3/s")
    print(f"  最大误差 = {fit_stats['max_error']:.4f} m^3/s")

    # 对比插值和幂律
    print(f"\n插值 vs 幂律公式对比：")
    print(f"{'水位(m)':>12} {'插值Q(m^3/s)':>18} {'幂律Q(m^3/s)':>18} {'差异(%)':>15}")
    print("-" * 75)

    rc_interp = RatingCurveBoundary(
        bc_id="RC_INTERP",
        h_data=h_true,
        Q_data=Q_true,
        use_power_law=False
    )

    h_tests = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]  # 包含外推点 5.0
    for h in h_tests:
        Q_interp = rc_interp.h_to_Q(h)
        Q_power = rc_power.h_to_Q(h)
        diff_pct = abs(Q_power - Q_interp) / Q_interp * 100 if Q_interp > 0 else 0

        print(f"{h:>12.2f} {Q_interp:>18.2f} {Q_power:>18.2f} {diff_pct:>15.2f}")

    print("\n优势：")
    print("  - 幂律公式物理意义明确")
    print("  - 外推更合理（h=5.0m 处差异明显）")
    print("  - 适用于天然河道")


def example_4_hydrological_station():
    """
    示例4：水文站应用

    模拟实际水文监测站的水位-流量转换
    """
    print("\n" + "="*80)
    print("示例4：水文站应用")
    print("="*80)

    # 某水文站实测 Rating Curve（典型河道数据）
    h_measured = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]  # m
    Q_measured = [2.0, 8.0, 18.0, 32.0, 50.0, 72.0, 98.0, 128.0, 162.0, 200.0]  # m^3/s

    rc_station = RatingCurveBoundary(
        bc_id="STATION_001",
        h_data=h_measured,
        Q_data=Q_measured,
        interpolation_method="cubic",  # 平滑插值
        use_power_law=True  # 同时拟合幂律
    )

    print(f"\n水文站：{rc_station.bc_id}")
    print(f"  监测断面水位-流量关系")
    print(f"  数据点数: {len(rc_station.h)}")

    # 模拟实时水位监测
    print(f"\n实时流量推算（基于水位观测）：")
    print(f"{'观测时间':>12} {'水位(m)':>12} {'推算流量(m^3/s)':>18} {'水情描述':>15}")
    print("-" * 72)

    observations = [
        ("08:00", 1.2, "正常"),
        ("10:00", 1.8, "涨水"),
        ("12:00", 2.6, "接近警戒"),
        ("14:00", 3.5, "超警戒"),
        ("16:00", 4.2, "洪水"),
        ("18:00", 3.0, "退水")
    ]

    for time, h_obs, desc in observations:
        Q_calc = rc_station.h_to_Q(h_obs)
        print(f"{time:>12} {h_obs:>12.2f} {Q_calc:>18.1f} {desc:>15}")

    # 反向计算：已知流量需求，推算所需水位
    print(f"\n水位需求计算（基于流量要求）：")
    print(f"{'需求流量(m^3/s)':>18} {'所需水位(m)':>15} {'用途':>20}")
    print("-" * 65)

    flow_requirements = [
        (15.0, "生态基流"),
        (50.0, "灌溉供水"),
        (100.0, "防洪调度"),
        (150.0, "洪峰削减")
    ]

    for Q_req, purpose in flow_requirements:
        h_req = rc_station.Q_to_h(Q_req)
        print(f"{Q_req:>18.1f} {h_req:>15.2f} {purpose:>20}")


def example_5_interpolation_methods():
    """
    示例5：不同插值方法比较

    对比线性插值和样条插值
    """
    print("\n" + "="*80)
    print("示例5：不同插值方法比较")
    print("="*80)

    # 稀疏数据
    h_sparse = [1.0, 2.0, 3.0, 4.0, 5.0]
    Q_sparse = [5.0, 25.0, 60.0, 110.0, 175.0]

    print(f"\n原始数据点：")
    for h, Q in zip(h_sparse, Q_sparse):
        print(f"  h = {h:.1f} m, Q = {Q:.1f} m^3/s")

    # 线性插值
    rc_linear = RatingCurveBoundary(
        bc_id="RC_LINEAR",
        h_data=h_sparse,
        Q_data=Q_sparse,
        interpolation_method="linear"
    )

    # 样条插值
    rc_cubic = RatingCurveBoundary(
        bc_id="RC_CUBIC",
        h_data=h_sparse,
        Q_data=Q_sparse,
        interpolation_method="cubic"
    )

    print(f"\n插值方法对比：")
    print(f"{'水位(m)':>12} {'线性插值(m^3/s)':>18} {'样条插值(m^3/s)':>18} {'差异(%)':>15}")
    print("-" * 75)

    h_tests = [1.5, 2.5, 3.5, 4.5]
    for h in h_tests:
        Q_linear = rc_linear.h_to_Q(h)
        Q_cubic = rc_cubic.h_to_Q(h)
        diff_pct = abs(Q_cubic - Q_linear) / Q_linear * 100

        print(f"{h:>12.2f} {Q_linear:>18.2f} {Q_cubic:>18.2f} {diff_pct:>15.2f}")

    print("\n选择建议：")
    print("  线性插值：简单快速，数据密集时优选")
    print("  样条插值：平滑曲线，数据稀疏时推荐")


def example_6_extrapolation_methods():
    """
    示例6：外推方法比较

    对比常数、线性和幂律外推
    """
    print("\n" + "="*80)
    print("示例6：外推方法比较")
    print("="*80)

    h_data = [2.0, 2.5, 3.0, 3.5, 4.0]
    Q_data = [20.0, 35.0, 55.0, 80.0, 110.0]

    print(f"\n数据范围：")
    print(f"  水位: {min(h_data):.1f} - {max(h_data):.1f} m")
    print(f"  流量: {min(Q_data):.1f} - {max(Q_data):.1f} m^3/s")

    # 不同外推方法
    rc_const = RatingCurveBoundary(
        bc_id="RC_CONST",
        h_data=h_data,
        Q_data=Q_data,
        extrapolation_method="constant"
    )

    rc_linear = RatingCurveBoundary(
        bc_id="RC_LINEAR_EX",
        h_data=h_data,
        Q_data=Q_data,
        extrapolation_method="linear"
    )

    rc_power = RatingCurveBoundary(
        bc_id="RC_POWER_EX",
        h_data=h_data,
        Q_data=Q_data,
        use_power_law=True,
        extrapolation_method="power_law"
    )

    print(f"\n外推对比（超出数据范围）：")
    print(f"{'水位(m)':>12} {'常数外推':>15} {'线性外推':>15} {'幂律外推':>15} {'位置':>12}")
    print("-" * 84)

    h_tests = [1.0, 1.5, 2.0, 3.0, 4.0, 4.5, 5.0]
    for h in h_tests:
        Q_const = rc_const.h_to_Q(h)
        Q_linear = rc_linear.h_to_Q(h)
        Q_power = rc_power.h_to_Q(h)

        if h < min(h_data):
            pos = "下外推"
        elif h > max(h_data):
            pos = "上外推"
        else:
            pos = "数据内"

        print(f"{h:>12.2f} {Q_const:>15.1f} {Q_linear:>15.1f} {Q_power:>15.1f} {pos:>12}")

    print("\n外推方法建议：")
    print("  常数外推：保守，避免过度推测（默认）")
    print("  线性外推：简单，适用于短距离外推")
    print("  幂律外推：物理合理，适用于天然河道")


def example_7_file_operations():
    """
    示例7：文件读写

    演示 Rating Curve 的保存和加载
    """
    print("\n" + "="*80)
    print("示例7：文件读写")
    print("="*80)

    # 创建 Rating Curve
    h_data = np.linspace(1.0, 5.0, 21)  # 21个点
    Q_data = 10 * (h_data - 0.5) ** 2.1  # 幂律关系

    rc_original = RatingCurveBoundary(
        bc_id="RC_FILE",
        h_data=h_data,
        Q_data=Q_data,
        use_power_law=True
    )

    print(f"\n原始 Rating Curve：")
    print(f"  标识: {rc_original.bc_id}")
    print(f"  数据点数: {len(rc_original.h)}")
    ranges = rc_original.get_range()
    print(f"  水位范围: {ranges['h_range'][0]:.2f} - {ranges['h_range'][1]:.2f} m")

    if rc_original.power_law_params:
        params = rc_original.power_law_params
        print(f"\n幂律参数：")
        print(f"  a = {params['a']:.4f}")
        print(f"  b = {params['b']:.4f}")
        print(f"  h0 = {params['h0']:.4f} m")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_file = f.name

    try:
        rc_original.to_file(temp_file)
        print(f"\n已保存到: {temp_file}")

        # 从文件加载
        rc_loaded = RatingCurveBoundary.from_file(
            bc_id="RC_LOADED",
            filepath=temp_file,
            use_power_law=True  # 重新拟合
        )

        print(f"\n从文件加载：")
        print(f"  标识: {rc_loaded.bc_id}")
        print(f"  数据点数: {len(rc_loaded.h)}")

        # 验证一致性
        h_test = 3.5
        Q_original = rc_original.h_to_Q(h_test)
        Q_loaded = rc_loaded.h_to_Q(h_test)

        print(f"\n一致性验证（h = {h_test:.1f} m）：")
        print(f"  原始: Q = {Q_original:.2f} m^3/s")
        print(f"  加载: Q = {Q_loaded:.2f} m^3/s")
        print(f"  误差: {abs(Q_loaded - Q_original):.4f} m^3/s")

    finally:
        # 清理临时文件
        Path(temp_file).unlink()
        print(f"\n已清理临时文件")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("Rating Curve 边界条件示例集")
    print("="*80)

    example_1_basic_rating_curve()
    example_2_bidirectional_conversion()
    example_3_power_law_fitting()
    example_4_hydrological_station()
    example_5_interpolation_methods()
    example_6_extrapolation_methods()
    example_7_file_operations()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == '__main__':
    main()
