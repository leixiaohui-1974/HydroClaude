#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应网格生成工具

提供在水工建筑物附近加密网格的功能，以提高数值精度

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import List, Tuple, Optional, Dict


def generate_adaptive_grid(
    total_length: float,
    refinement_zones: List[Tuple[float, float]],
    dx_fine: float = 5.0,
    dx_coarse: float = 33.0,
    transition_width: float = 50.0
) -> np.ndarray:
    """
    生成自适应加密网格

    在指定区域使用精细网格，其他区域使用粗网格，过渡区平滑过渡

    Args:
        total_length: 渠道总长度 (m)
        refinement_zones: 加密区列表 [(x_start, x_end), ...]
        dx_fine: 加密区网格间距 (m)
        dx_coarse: 粗网格区间距 (m)
        transition_width: 过渡区宽度 (m)

    Returns:
        x: 网格点坐标数组

    网格分布示例：
        |<-coarse->|<-trans->|<-fine->|<-trans->|<-coarse->|
        [  50m    ][ 25m   ][  5m  ][ 25m   ][  50m    ]
    """

    # 合并重叠的加密区
    refined_zones = _merge_overlapping_zones(refinement_zones)

    # 扩展加密区包含过渡区
    extended_zones = []
    for x_start, x_end in refined_zones:
        extended_zones.append((
            max(0, x_start - transition_width),
            min(total_length, x_end + transition_width)
        ))

    # 生成网格点
    x_points = []
    current_x = 0.0

    while current_x < total_length:
        x_points.append(current_x)

        # 确定当前位置的网格间距
        dx = _get_local_grid_spacing(
            current_x, refined_zones, extended_zones,
            dx_fine, dx_coarse, transition_width
        )

        current_x += dx

    # 确保包含终点
    if x_points[-1] < total_length:
        x_points.append(total_length)

    return np.array(x_points)


def generate_structure_refined_grid(
    total_length: float,
    structure_positions: List[float],
    refinement_radius: float = 200.0,
    dx_fine: float = 5.0,
    dx_coarse: float = 33.0,
    transition_width: float = 50.0
) -> np.ndarray:
    """
    基于水工建筑物位置生成自适应网格

    在每个建筑物周围±radius范围内加密网格

    Args:
        total_length: 渠道总长度 (m)
        structure_positions: 建筑物位置列表 (m)
        refinement_radius: 加密半径 (m)
        dx_fine: 加密区网格间距 (m)
        dx_coarse: 粗网格区间距 (m)
        transition_width: 过渡区宽度 (m)

    Returns:
        x: 网格点坐标数组
    """

    # 为每个建筑物创建加密区
    refinement_zones = []
    for pos in structure_positions:
        x_start = max(0, pos - refinement_radius)
        x_end = min(total_length, pos + refinement_radius)
        refinement_zones.append((x_start, x_end))

    return generate_adaptive_grid(
        total_length, refinement_zones,
        dx_fine, dx_coarse, transition_width
    )


def _merge_overlapping_zones(zones: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    合并重叠或相邻的区间

    Args:
        zones: 区间列表 [(x_start, x_end), ...]

    Returns:
        merged_zones: 合并后的区间列表
    """
    if not zones:
        return []

    # 按起点排序
    sorted_zones = sorted(zones, key=lambda z: z[0])

    merged = [sorted_zones[0]]

    for current in sorted_zones[1:]:
        last = merged[-1]

        # 如果当前区间与上一个重叠或相邻
        if current[0] <= last[1]:
            # 合并区间
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            # 添加新区间
            merged.append(current)

    return merged


def _get_local_grid_spacing(
    x: float,
    refined_zones: List[Tuple[float, float]],
    extended_zones: List[Tuple[float, float]],
    dx_fine: float,
    dx_coarse: float,
    transition_width: float
) -> float:
    """
    计算指定位置的网格间距

    根据位置所在区域（精细/过渡/粗糙）返回相应的间距
    使用余弦函数实现平滑过渡

    Args:
        x: 当前位置
        refined_zones: 精细网格区列表
        extended_zones: 扩展区列表（包含过渡区）
        dx_fine: 精细网格间距
        dx_coarse: 粗网格间距
        transition_width: 过渡区宽度

    Returns:
        dx: 当前位置的网格间距
    """

    # 检查是否在精细区内
    for x_start, x_end in refined_zones:
        if x_start <= x <= x_end:
            return dx_fine

    # 检查是否在过渡区内
    for i, (ext_start, ext_end) in enumerate(extended_zones):
        ref_start, ref_end = refined_zones[i]

        if ext_start <= x <= ext_end:
            # 在扩展区内但不在精细区内，说明在过渡区

            # 左过渡区
            if x < ref_start:
                # 从粗到细
                dist_from_start = x - ext_start
                if dist_from_start < transition_width:
                    # 余弦平滑过渡: coarse -> fine
                    alpha = (1 - np.cos(np.pi * dist_from_start / transition_width)) / 2
                    return dx_coarse + alpha * (dx_fine - dx_coarse)

            # 右过渡区
            elif x > ref_end:
                # 从细到粗
                dist_from_end = x - ref_end
                if dist_from_end < transition_width:
                    # 余弦平滑过渡: fine -> coarse
                    alpha = (1 - np.cos(np.pi * dist_from_end / transition_width)) / 2
                    return dx_fine + alpha * (dx_coarse - dx_fine)

    # 不在任何特殊区域，使用粗网格
    return dx_coarse


def analyze_grid_quality(x: np.ndarray) -> Dict:
    """
    分析网格质量

    计算网格间距、均匀性、加密比等指标

    Args:
        x: 网格点坐标数组

    Returns:
        stats: 网格统计信息字典
    """

    dx = np.diff(x)

    stats = {
        'n_points': len(x),
        'total_length': x[-1] - x[0],
        'dx_min': np.min(dx),
        'dx_max': np.max(dx),
        'dx_mean': np.mean(dx),
        'dx_std': np.std(dx),
        'refinement_ratio': np.max(dx) / np.min(dx),
        'dx_range': (np.min(dx), np.max(dx))
    }

    # 计算网格平滑性（相邻间距比的最大值）
    dx_ratio = dx[1:] / dx[:-1]
    stats['max_stretch_ratio'] = max(np.max(dx_ratio), np.max(1.0 / dx_ratio))

    return stats


def visualize_grid_distribution(x: np.ndarray, structure_positions: Optional[List[float]] = None):
    """
    可视化网格分布（生成ASCII艺术图）

    Args:
        x: 网格点坐标数组
        structure_positions: 建筑物位置（可选）
    """

    dx = np.diff(x)

    print("\n" + "=" * 80)
    print("网格分布分析")
    print("=" * 80)

    stats = analyze_grid_quality(x)

    print(f"\n网格统计:")
    print(f"  总点数: {stats['n_points']}")
    print(f"  渠道长度: {stats['total_length']:.1f} m")
    print(f"  平均间距: {stats['dx_mean']:.2f} m")
    print(f"  间距范围: {stats['dx_min']:.2f} - {stats['dx_max']:.2f} m")
    print(f"  加密比: {stats['refinement_ratio']:.2f}x")
    print(f"  最大拉伸比: {stats['max_stretch_ratio']:.3f}")

    # 绘制间距分布图
    print(f"\n网格间距分布:")
    print(f"  位置 (m) | 间距 (m) | 可视化")
    print(f"  " + "-" * 60)

    n_samples = min(20, len(dx))  # 最多显示20个样本
    indices = np.linspace(0, len(dx)-1, n_samples, dtype=int)

    max_bar_width = 40

    for i in indices:
        pos = x[i]
        spacing = dx[i]

        # 标记是否靠近建筑物
        near_structure = ""
        if structure_positions:
            for s_pos in structure_positions:
                if abs(pos - s_pos) < 250:
                    near_structure = " [结构附近]"
                    break

        # 绘制条形图
        bar_length = int(spacing / stats['dx_max'] * max_bar_width)
        bar = "█" * bar_length

        print(f"  {pos:8.1f} | {spacing:7.2f} | {bar}{near_structure}")

    print("\n" + "=" * 80)


# 测试函数
if __name__ == "__main__":
    # 测试: 三闸门场景
    total_length = 10000.0
    gate_positions = [2500.0, 5000.0, 7500.0]

    # 生成自适应网格
    x_adaptive = generate_structure_refined_grid(
        total_length=total_length,
        structure_positions=gate_positions,
        refinement_radius=200.0,
        dx_fine=5.0,
        dx_coarse=33.0,
        transition_width=50.0
    )

    print(f"\n生成自适应网格: {len(x_adaptive)} 个点")

    # 可视化网格分布
    visualize_grid_distribution(x_adaptive, gate_positions)

    # 对比均匀网格
    print("\n" + "=" * 80)
    print("对比: 均匀网格 (301点)")
    print("=" * 80)
    x_uniform = np.linspace(0, total_length, 301)
    stats_uniform = analyze_grid_quality(x_uniform)
    print(f"  平均间距: {stats_uniform['dx_mean']:.2f} m")
    print(f"  间距范围: {stats_uniform['dx_min']:.2f} - {stats_uniform['dx_max']:.2f} m")

    print(f"\n网格点数对比:")
    print(f"  均匀网格: 301 点")
    print(f"  自适应网格: {len(x_adaptive)} 点")
    print(f"  增加比例: {len(x_adaptive)/301:.2f}x")
