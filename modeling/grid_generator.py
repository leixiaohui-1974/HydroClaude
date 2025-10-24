#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网格自动剖分模块

根据渠道长度、结构物位置自动生成网格

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import List, Tuple, Optional, Dict

from modeling.constants import GridConstants


class GridGenerator:
    """
    网格自动剖分器

    功能：
    - 根据目标网格间距自动计算网格点数
    - 在结构物附近自动加密网格
    - 生成非均匀网格（如需要）
    - 验证网格质量
    """

    def __init__(self, length: float, structures: Optional[List[Tuple[float, any]]] = None):
        """
        初始化网格生成器

        Args:
            length: 渠道总长度 (m)
            structures: 结构物列表 [(位置, 结构对象), ...]
        """
        self.length = length
        self.structures = structures or []

    def generate_uniform_grid(self, nx: Optional[int] = None,
                             dx_target: Optional[float] = None) -> np.ndarray:
        """
        生成均匀网格

        Args:
            nx: 网格点数（与dx_target二选一）
            dx_target: 目标网格间距 (m)

        Returns:
            x: 网格坐标数组
        """
        if nx is None and dx_target is None:
            raise ValueError("必须指定nx或dx_target之一")

        if nx is not None:
            # 根据点数生成
            x = np.linspace(0, self.length, nx)
        else:
            # 根据目标间距生成
            nx = int(np.ceil(self.length / dx_target)) + 1
            x = np.linspace(0, self.length, nx)

        return x

    def generate_refined_grid(self, dx_base: float = 200.0,
                             dx_refined: float = 50.0,
                             refine_width: float = 1000.0) -> np.ndarray:
        """
        生成结构物附近加密的网格

        Args:
            dx_base: 基础网格间距 (m)
            dx_refined: 结构物附近的细化间距 (m)
            refine_width: 细化区域半宽度 (m)

        Returns:
            x: 非均匀网格坐标数组
        """
        if not self.structures:
            # 没有结构物，返回均匀网格
            return self.generate_uniform_grid(dx_target=dx_base)

        x_points = []

        # 提取结构物位置
        structure_positions = [pos for pos, _ in self.structures]

        # 在渠道上生成网格
        x_current = 0.0

        while x_current <= self.length:
            x_points.append(x_current)

            # 检查是否靠近结构物
            near_structure = False
            for pos in structure_positions:
                if abs(x_current - pos) < refine_width:
                    near_structure = True
                    break

            # 根据位置选择间距
            if near_structure:
                dx = dx_refined
            else:
                dx = dx_base

            x_current += dx

        # 确保最后一个点正好是渠道末端
        if x_points[-1] < self.length:
            x_points.append(self.length)

        return np.array(x_points)

    def generate_adaptive_grid(self,
                              dx_min: float = None,
                              dx_max: float = None,
                              transition_length: float = None) -> np.ndarray:
        """
        生成自适应网格（结构物附近平滑过渡）

        Args:
            dx_min: 最小网格间距 (m)，默认使用GridConstants.DEFAULT_DX_MIN
            dx_max: 最大网格间距 (m)，默认使用GridConstants.DEFAULT_DX_MAX
            transition_length: 过渡区长度 (m)，默认使用GridConstants.DEFAULT_TRANSITION_LENGTH

        Returns:
            x: 自适应网格坐标数组
        """
        # 使用常量作为默认值
        if dx_min is None:
            dx_min = GridConstants.DEFAULT_DX_MIN
        if dx_max is None:
            dx_max = GridConstants.DEFAULT_DX_MAX
        if transition_length is None:
            transition_length = GridConstants.DEFAULT_TRANSITION_LENGTH

        if not self.structures:
            return self.generate_uniform_grid(dx_target=dx_max)

        x_points = []
        structure_positions = [pos for pos, _ in self.structures]

        x_current = 0.0

        while x_current <= self.length:
            x_points.append(x_current)

            # 计算到最近结构物的距离
            min_dist = min([abs(x_current - pos) for pos in structure_positions])

            # 根据距离计算网格间距（S型过渡）
            if min_dist <= transition_length:
                # 在过渡区内，使用S型函数插值
                alpha = min_dist / transition_length
                alpha_smooth = 3 * alpha**2 - 2 * alpha**3  # S曲线
                dx = dx_min + (dx_max - dx_min) * alpha_smooth
            else:
                dx = dx_max

            x_current += dx

        if x_points[-1] < self.length:
            x_points.append(self.length)

        return np.array(x_points)

    def validate_grid(self, x: np.ndarray) -> Dict[str, any]:
        """
        验证网格质量

        Args:
            x: 网格坐标数组

        Returns:
            validation_result: 验证结果字典
        """
        dx = np.diff(x)

        result = {
            'n_points': len(x),
            'dx_min': np.min(dx),
            'dx_max': np.max(dx),
            'dx_mean': np.mean(dx),
            'dx_std': np.std(dx),
            'uniformity': np.std(dx) / np.mean(dx),  # 0表示完全均匀
            'quality_rating': None
        }

        # 质量评级
        if result['uniformity'] < 0.1:
            result['quality_rating'] = 'Excellent (均匀网格)'
        elif result['uniformity'] < 0.3:
            result['quality_rating'] = 'Good (轻微非均匀)'
        elif result['uniformity'] < 0.5:
            result['quality_rating'] = 'Acceptable (非均匀)'
        else:
            result['quality_rating'] = 'Poor (严重非均匀)'

        return result

    def recommend_grid_size(self, dx_target: float = 100.0) -> int:
        """
        推荐网格点数

        Args:
            dx_target: 目标网格间距 (m)

        Returns:
            nx: 推荐的网格点数
        """
        nx = int(np.ceil(self.length / dx_target)) + 1

        # 考虑结构物密度调整
        if self.structures:
            n_structures = len(self.structures)
            # 每个结构物周围增加20个点
            nx_adjustment = n_structures * 20
            nx += nx_adjustment

        return nx

    def __repr__(self) -> str:
        return f"GridGenerator(length={self.length}m, structures={len(self.structures)})"


if __name__ == "__main__":
    # 测试网格生成器
    print("=" * 80)
    print("网格生成器测试")
    print("=" * 80)

    # 测试1：均匀网格
    gen = GridGenerator(length=10000.0)
    x_uniform = gen.generate_uniform_grid(dx_target=200.0)
    validation = gen.validate_grid(x_uniform)

    print("\n1. 均匀网格:")
    print(f"   点数: {validation['n_points']}")
    print(f"   间距范围: {validation['dx_min']:.1f} - {validation['dx_max']:.1f} m")
    print(f"   平均间距: {validation['dx_mean']:.1f} m")
    print(f"   质量评级: {validation['quality_rating']}")

    # 测试2：加密网格
    structures = [(5000.0, None)]
    gen2 = GridGenerator(length=10000.0, structures=structures)
    x_refined = gen2.generate_refined_grid(dx_base=200.0, dx_refined=50.0)
    validation2 = gen2.validate_grid(x_refined)

    print("\n2. 结构物加密网格:")
    print(f"   点数: {validation2['n_points']}")
    print(f"   间距范围: {validation2['dx_min']:.1f} - {validation2['dx_max']:.1f} m")
    print(f"   平均间距: {validation2['dx_mean']:.1f} m")
    print(f"   质量评级: {validation2['quality_rating']}")

    # 测试3：自适应网格
    x_adaptive = gen2.generate_adaptive_grid(dx_min=30.0, dx_max=200.0)
    validation3 = gen2.validate_grid(x_adaptive)

    print("\n3. 自适应网格:")
    print(f"   点数: {validation3['n_points']}")
    print(f"   间距范围: {validation3['dx_min']:.1f} - {validation3['dx_max']:.1f} m")
    print(f"   平均间距: {validation3['dx_mean']:.1f} m")
    print(f"   质量评级: {validation3['quality_rating']}")

    # 推荐网格大小
    nx_recommend = gen2.recommend_grid_size(dx_target=100.0)
    print(f"\n推荐网格点数: {nx_recommend}")

    print("\n" + "=" * 80)
