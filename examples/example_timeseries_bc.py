#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列边界条件示例

演示 TimeSeriesBoundary 类的使用，包括：
1. 基本时间序列边界条件
2. 洪水过程模拟
3. 潮汐边界条件
4. 水库调度过程
5. 不同插值方法对比
6. 外推方法比较
7. 文件读写和数据处理

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
from pathlib import Path
import tempfile

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from boundary.timeseries_bc import TimeSeriesBoundary, create_timeseries_boundary


def example_1_basic_timeseries():
    """
    示例1：基本时间序列边界条件

    创建简单的流量边界条件并查询值
    """
    print("="*80)
    print("示例1：基本时间序列边界条件")
    print("="*80)

    # 创建流量边界条件（小时尺度）
    time_hours = [0, 1, 2, 3, 4, 5, 6]  # 小时
    time_seconds = [t * 3600 for t in time_hours]  # 转换为秒
    flow_values = [10.0, 12.0, 15.0, 18.0, 16.0, 13.0, 10.0]  # m^3/s

    bc = TimeSeriesBoundary(
        bc_id="BC_INFLOW",
        bc_type="Q",
        time_data=time_seconds,
        value_data=flow_values,
        interpolation_method="linear"
    )

    print(f"\n边界条件信息：")
    print(f"  标识: {bc.bc_id}")
    print(f"  类型: {bc.bc_type} (流量)")
    print(f"  数据点数: {len(bc.t)}")
    print(f"  时间范围: {bc.t[0]/3600:.1f} - {bc.t[-1]/3600:.1f} 小时")
    print(f"  流量范围: {min(bc.values):.1f} - {max(bc.values):.1f} m^3/s")

    # 查询不同时刻的值
    print(f"\n流量查询：")
    print(f"{'时间(h)':>12} {'流量(m^3/s)':>15} {'说明':>20}")
    print("-" * 60)

    query_times_hours = [0, 0.5, 1.5, 3.0, 4.5, 6.0]
    for t_h in query_times_hours:
        t_s = t_h * 3600
        Q = bc.get_value(t_s)

        if t_h in time_hours:
            note = "数据点"
        else:
            note = "线性插值"

        print(f"{t_h:>12.1f} {Q:>15.2f} {note:>20}")

    print("\n说明：")
    print("  - 在数据点上返回精确值")
    print("  - 数据点之间线性插值")


def example_2_flood_hydrograph():
    """
    示例2：洪水过程模拟

    典型的洪水过程线：涨水-洪峰-退水
    """
    print("\n" + "="*80)
    print("示例2：洪水过程模拟")
    print("="*80)

    # 构造洪水过程线（天尺度）
    time_days = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])  # 天
    time_seconds = time_days * 86400  # 转换为秒

    # 洪水流量（m^3/s）：基流 -> 涨水 -> 洪峰 -> 退水 -> 基流
    Q_base = 50.0  # 基流
    Q_peak = 500.0  # 洪峰流量
    flow_values = np.array([
        50, 80, 150, 300, 500, 450, 350, 250, 150, 100, 50
    ], dtype=float)

    bc_flood = TimeSeriesBoundary(
        bc_id="BC_FLOOD",
        bc_type="Q",
        time_data=time_seconds,
        value_data=flow_values,
        interpolation_method="cubic"  # 使用三次样条使过程线更平滑
    )

    print(f"\n洪水特征：")
    stats = bc_flood.get_statistics()
    print(f"  基流: {Q_base:.1f} m^3/s")
    print(f"  洪峰: {Q_peak:.1f} m^3/s")
    print(f"  平均流量: {stats['mean']:.1f} m^3/s")
    print(f"  历时: {stats['duration']/86400:.1f} 天")

    # 分析洪水过程
    print(f"\n洪水过程分析：")
    print(f"{'时间(天)':>12} {'流量(m^3/s)':>15} {'阶段':>15}")
    print("-" * 50)

    for t_day in [0, 2, 4, 6, 8, 10]:
        t_s = t_day * 86400
        Q = bc_flood.get_value(t_s)

        if Q < 100:
            stage = "基流期"
        elif Q < 250:
            stage = "涨水期" if t_day < 4 else "退水期"
        else:
            stage = "洪峰期"

        print(f"{t_day:>12.1f} {Q:>15.1f} {stage:>15}")

    # 计算洪水总量（数值积分）
    t_fine = np.linspace(time_seconds[0], time_seconds[-1], 1000)
    Q_fine = bc_flood.get_values(t_fine)
    dt = t_fine[1] - t_fine[0]
    total_volume = np.sum(Q_fine * dt)  # m^3

    print(f"\n洪水总量: {total_volume/1e6:.2f} 百万立方米")


def example_3_tidal_boundary():
    """
    示例3：潮汐边界条件

    正弦潮汐变化（周期约12.4小时）
    """
    print("\n" + "="*80)
    print("示例3：潮汐边界条件")
    print("="*80)

    # 生成潮汐水位数据
    t_hours = np.linspace(0, 24, 49)  # 24小时，每0.5小时一个点
    t_seconds = t_hours * 3600

    # 潮汐参数
    mean_level = 2.0  # 平均水位 (m)
    tidal_range = 1.5  # 潮差 (m)
    period = 12.4  # 潮汐周期 (小时)

    # 正弦潮汐
    h_tidal = mean_level + (tidal_range / 2) * np.sin(2 * np.pi * t_hours / period)

    bc_tide = TimeSeriesBoundary(
        bc_id="BC_TIDE",
        bc_type="h",
        time_data=t_seconds,
        value_data=h_tidal,
        interpolation_method="cubic"
    )

    print(f"\n潮汐特征：")
    print(f"  平均水位: {mean_level:.2f} m")
    print(f"  潮差: {tidal_range:.2f} m")
    print(f"  最高水位: {np.max(h_tidal):.2f} m")
    print(f"  最低水位: {np.min(h_tidal):.2f} m")
    print(f"  潮汐周期: {period:.1f} 小时")

    # 查询潮位
    print(f"\n潮位变化：")
    print(f"{'时间(h)':>12} {'潮位(m)':>12} {'潮汐状态':>15}")
    print("-" * 50)

    for t_h in [0, 3, 6, 9, 12, 15, 18, 21, 24]:
        t_s = t_h * 3600
        h = bc_tide.get_value(t_s)

        if h > mean_level + 0.5:
            state = "高潮"
        elif h < mean_level - 0.5:
            state = "低潮"
        else:
            state = "涨潮" if np.sin(2*np.pi*t_h/period) > 0 else "落潮"

        print(f"{t_h:>12.1f} {h:>12.3f} {state:>15}")


def example_4_reservoir_operation():
    """
    示例4：水库调度过程

    模拟水库闸门操作的流量过程
    """
    print("\n" + "="*80)
    print("示例4：水库调度过程")
    print("="*80)

    # 水库调度计划（阶梯式变化）
    time_hours = [0, 2, 4, 8, 10, 12]  # 去除重复时间点
    time_seconds = [t * 3600 for t in time_hours]
    discharge = [20.0, 50.0, 80.0, 30.0, 20.0, 20.0]  # 对应的流量

    # 使用前向保持插值（阶跃变化）
    bc_reservoir = TimeSeriesBoundary(
        bc_id="BC_RESERVOIR",
        bc_type="Q",
        time_data=time_seconds,
        value_data=discharge,
        interpolation_method="previous"  # 阶跃变化
    )

    print(f"\n调度计划：")
    print(f"{'时段':>15} {'放水流量(m^3/s)':>18} {'说明':>20}")
    print("-" * 65)

    schedules = [
        ("0-2小时", 20.0, "正常流量"),
        ("2-4小时", 50.0, "增加发电"),
        ("4-8小时", 80.0, "高峰发电"),
        ("8-10小时", 30.0, "减少出库"),
        ("10-12小时", 20.0, "恢复正常")
    ]

    for period, Q, note in schedules:
        print(f"{period:>15} {Q:>18.1f} {note:>20}")

    # 详细查询
    print(f"\n逐时流量：")
    print(f"{'时间(h)':>12} {'流量(m^3/s)':>15}")
    print("-" * 35)

    for t_h in range(13):
        t_s = t_h * 3600
        Q = bc_reservoir.get_value(t_s)
        print(f"{t_h:>12.1f} {Q:>15.1f}")

    print("\n说明：")
    print("  使用前向保持插值模拟闸门阶跃操作")


def example_5_interpolation_comparison():
    """
    示例5：不同插值方法对比

    对比线性、三次样条和阶跃插值
    """
    print("\n" + "="*80)
    print("示例5：不同插值方法对比")
    print("="*80)

    # 原始数据（稀疏）
    time_data = [0, 10, 20, 30, 40, 50]
    value_data = [10.0, 20.0, 15.0, 25.0, 18.0, 12.0]

    print(f"\n原始数据：")
    print(f"  时间: {time_data}")
    print(f"  值: {value_data}")

    # 创建不同插值方法的边界条件
    methods = {
        "线性": "linear",
        "三次样条": "cubic",
        "前向保持": "previous",
        "后向保持": "next"
    }

    bcs = {}
    for name, method in methods.items():
        bcs[name] = TimeSeriesBoundary(
            bc_id=f"BC_{method}",
            bc_type="Q",
            time_data=time_data,
            value_data=value_data,
            interpolation_method=method
        )

    # 比较插值结果
    print(f"\n插值对比（t=15秒）：")
    print(f"{'插值方法':>12} {'插值结果':>15} {'特点':>30}")
    print("-" * 70)

    t_test = 15.0
    comparisons = [
        ("线性", "连续，折线"),
        ("三次样条", "平滑，曲线"),
        ("前向保持", "阶跃，保持前值"),
        ("后向保持", "阶跃，保持后值")
    ]

    for name, feature in comparisons:
        value = bcs[name].get_value(t_test)
        print(f"{name:>12} {value:>15.2f} {feature:>30}")

    print("\n应用建议：")
    print("  线性插值：默认选择，适用于大多数情况")
    print("  三次样条：需要平滑曲线时（如洪水过程）")
    print("  前向保持：阶跃变化（如闸门操作）")
    print("  后向保持：预测型边界条件")


def example_6_extrapolation_comparison():
    """
    示例6：外推方法比较

    对比常数外推和线性外推
    """
    print("\n" + "="*80)
    print("示例6：外推方法比较")
    print("="*80)

    # 时间序列（10-30秒）
    time_data = [10, 15, 20, 25, 30]
    value_data = [10.0, 15.0, 20.0, 25.0, 30.0]  # 线性增长

    print(f"\n数据范围：")
    print(f"  时间: {min(time_data)} - {max(time_data)} 秒")
    print(f"  值: {min(value_data)} - {max(value_data)}")

    # 常数外推
    bc_const = TimeSeriesBoundary(
        bc_id="BC_CONST_EXTRAP",
        bc_type="Q",
        time_data=time_data,
        value_data=value_data,
        extrapolation_method="constant"
    )

    # 线性外推
    bc_linear = TimeSeriesBoundary(
        bc_id="BC_LINEAR_EXTRAP",
        bc_type="Q",
        time_data=time_data,
        value_data=value_data,
        extrapolation_method="linear"
    )

    # 比较外推结果
    print(f"\n外推对比：")
    print(f"{'查询时间':>12} {'常数外推':>15} {'线性外推':>15} {'备注':>20}")
    print("-" * 75)

    test_times = [0, 5, 10, 20, 30, 35, 40]
    for t in test_times:
        v_const = bc_const.get_value(t)
        v_linear = bc_linear.get_value(t)

        if t < 10:
            note = "序列之前"
        elif t > 30:
            note = "序列之后"
        else:
            note = "序列内"

        print(f"{t:>12.1f} {v_const:>15.2f} {v_linear:>15.2f} {note:>20}")

    print("\n应用建议：")
    print("  常数外推：保守，边界值保持不变（默认）")
    print("  线性外推：假设趋势延续，需谨慎使用")


def example_7_file_operations():
    """
    示例7：文件读写和数据处理

    演示从文件加载、处理和保存时间序列
    """
    print("\n" + "="*80)
    print("示例7：文件读写和数据处理")
    print("="*80)

    # 创建原始时间序列
    time_data = np.arange(0, 100, 10)  # 0-90秒，步长10秒
    value_data = 50 + 20 * np.sin(2 * np.pi * time_data / 60)  # 正弦波动

    bc_original = TimeSeriesBoundary(
        bc_id="BC_ORIGINAL",
        bc_type="Q",
        time_data=time_data,
        value_data=value_data
    )

    print(f"\n原始时间序列：")
    stats = bc_original.get_statistics()
    print(f"  数据点数: {stats['n_points']}")
    print(f"  时间跨度: {stats['duration']:.1f} 秒")
    print(f"  平均值: {stats['mean']:.2f}")
    print(f"  标准差: {stats['std']:.2f}")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_file = f.name

    try:
        bc_original.to_file(temp_file)
        print(f"\n已保存到: {temp_file}")

        # 从文件加载
        bc_loaded = TimeSeriesBoundary.from_file(
            bc_id="BC_LOADED",
            bc_type="Q",
            filepath=temp_file
        )

        print(f"\n已从文件加载")
        print(f"  加载点数: {len(bc_loaded.t)}")

        # 数据变换：重采样
        bc_resampled = bc_loaded.resample(dt=5.0)  # 重采样到5秒间隔
        print(f"\n重采样（dt=5秒）：")
        print(f"  新点数: {len(bc_resampled.t)}")

        # 数据变换：缩放
        bc_scaled = bc_loaded.scale_values(scale_factor=1.5)
        print(f"\n流量缩放（x1.5）：")
        print(f"  原始平均值: {bc_loaded.get_statistics()['mean']:.2f}")
        print(f"  缩放后平均值: {bc_scaled.get_statistics()['mean']:.2f}")

        # 数据变换：时间平移
        bc_shifted = bc_loaded.shift_time(time_shift=3600)  # 平移1小时
        t_range_orig = bc_loaded.get_time_range()
        t_range_shift = bc_shifted.get_time_range()
        print(f"\n时间平移（+1小时）：")
        print(f"  原始时间范围: {t_range_orig[0]:.1f} - {t_range_orig[1]:.1f} 秒")
        print(f"  平移后范围: {t_range_shift[0]:.1f} - {t_range_shift[1]:.1f} 秒")

    finally:
        # 清理临时文件
        Path(temp_file).unlink()
        print(f"\n已清理临时文件")


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("时间序列边界条件示例集")
    print("="*80)

    example_1_basic_timeseries()
    example_2_flood_hydrograph()
    example_3_tidal_boundary()
    example_4_reservoir_operation()
    example_5_interpolation_comparison()
    example_6_extrapolation_comparison()
    example_7_file_operations()

    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == '__main__':
    main()
