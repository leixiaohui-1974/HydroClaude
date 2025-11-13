#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应网格细化模块

根据解的梯度自动细化/粗化网格

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Tuple, Dict, Optional


class AdaptiveRefiner:
    """
    自适应网格细化器

    功能：
    - 基于梯度的网格细化判据
    - 自动插值生成新网格点
    - 网格粗化（移除不必要的点）
    - 网格质量控制
    """

    def __init__(self, refine_threshold: float = 0.1,
                 coarsen_threshold: float = 0.01,
                 max_refinement_level: int = 3):
        """
        初始化自适应细化器

        Args:
            refine_threshold: 细化阈值（相对梯度）
            coarsen_threshold: 粗化阈值（相对梯度）
            max_refinement_level: 最大细化层级
        """
        self.refine_threshold = refine_threshold
        self.coarsen_threshold = coarsen_threshold
        self.max_refinement_level = max_refinement_level
        self.current_level = 0

    def compute_refinement_indicator(self, x: np.ndarray, h: np.ndarray) -> np.ndarray:
        """
        计算细化指示器（基于水深梯度）

        Args:
            x: 网格坐标
            h: 水深

        Returns:
            indicator: 每个单元的细化指示器
        """
        # 计算水深梯度
        dh_dx = np.gradient(h, x)

        # 归一化梯度
        h_mean = np.mean(h)
        indicator = np.abs(dh_dx) / h_mean

        return indicator

    def identify_refine_cells(self, indicator: np.ndarray) -> np.ndarray:
        """
        识别需要细化的单元

        Args:
            indicator: 细化指示器数组

        Returns:
            refine_mask: 布尔数组，True表示需要细化
        """
        return indicator > self.refine_threshold

    def identify_coarsen_cells(self, indicator: np.ndarray) -> np.ndarray:
        """
        识别可以粗化的单元

        Args:
            indicator: 细化指示器数组

        Returns:
            coarsen_mask: 布尔数组，True表示可以粗化
        """
        return indicator < self.coarsen_threshold

    def refine_grid(self, x: np.ndarray, h: np.ndarray, hu: np.ndarray) \
            -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        细化网格

        Args:
            x: 原网格坐标
            h: 原网格上的水深
            hu: 原网格上的流量

        Returns:
            x_new, h_new, hu_new: 细化后的网格和解
        """
        if self.current_level >= self.max_refinement_level:
            print(f" 已达到最大细化层级 {self.max_refinement_level}，跳过细化")
            return x, h, hu

        # 计算细化指示器
        indicator = self.compute_refinement_indicator(x, h)
        refine_mask = self.identify_refine_cells(indicator)

        if not np.any(refine_mask):
            print(" 无需细化")
            return x, h, hu

        # 在需要细化的单元中间插入新点
        x_new = []
        h_new = []
        hu_new = []

        for i in range(len(x) - 1):
            x_new.append(x[i])
            h_new.append(h[i])
            hu_new.append(hu[i])

            if refine_mask[i]:
                # 在两点中间插入新点
                x_mid = (x[i] + x[i+1]) / 2.0
                h_mid = (h[i] + h[i+1]) / 2.0
                hu_mid = (hu[i] + hu[i+1]) / 2.0

                x_new.append(x_mid)
                h_new.append(h_mid)
                hu_new.append(hu_mid)

        # 添加最后一个点
        x_new.append(x[-1])
        h_new.append(h[-1])
        hu_new.append(hu[-1])

        self.current_level += 1
        n_refined = np.sum(refine_mask)
        print(f" 细化完成: 在{n_refined}个单元插入新点，网格点数: {len(x)} → {len(x_new)}")

        return np.array(x_new), np.array(h_new), np.array(hu_new)

    def coarsen_grid(self, x: np.ndarray, h: np.ndarray, hu: np.ndarray) \
            -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        粗化网格

        Args:
            x: 原网格坐标
            h: 原网格上的水深
            hu: 原网格上的流量

        Returns:
            x_new, h_new, hu_new: 粗化后的网格和解
        """
        if self.current_level <= 0:
            print(" 已是基础网格，无需粗化")
            return x, h, hu

        # 计算细化指示器
        indicator = self.compute_refinement_indicator(x, h)
        coarsen_mask = self.identify_coarsen_cells(indicator)

        if not np.any(coarsen_mask):
            print(" 无可粗化单元")
            return x, h, hu

        # 移除可粗化的点（每隔一个点移除）
        keep_mask = np.ones(len(x), dtype=bool)

        for i in range(1, len(x) - 1):  # 不移除边界点
            if coarsen_mask[i] and i % 2 == 1:
                keep_mask[i] = False

        x_new = x[keep_mask]
        h_new = h[keep_mask]
        hu_new = hu[keep_mask]

        self.current_level = max(0, self.current_level - 1)
        n_removed = len(x) - len(x_new)
        print(f" 粗化完成: 移除{n_removed}个点，网格点数: {len(x)} → {len(x_new)}")

        return x_new, h_new, hu_new

    def adaptive_refine(self, x: np.ndarray, h: np.ndarray, hu: np.ndarray,
                       max_iterations: int = 3) \
            -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
        """
        自适应网格细化（主接口）

        Args:
            x: 原网格坐标
            h: 原网格上的水深
            hu: 原网格上的流量
            max_iterations: 最大细化迭代次数

        Returns:
            x_final, h_final, hu_final: 细化后的网格和解
            stats: 细化统计信息
        """
        stats = {
            'iterations': 0,
            'initial_points': len(x),
            'final_points': len(x),
            'refinement_ratio': 1.0
        }

        x_current = x.copy()
        h_current = h.copy()
        hu_current = hu.copy()

        for iteration in range(max_iterations):
            print(f"\n--- 自适应细化迭代 {iteration + 1}/{max_iterations} ---")

            # 计算指示器
            indicator = self.compute_refinement_indicator(x_current, h_current)
            refine_mask = self.identify_refine_cells(indicator)

            if not np.any(refine_mask):
                print(" 达到收敛，无需进一步细化")
                break

            # 细化
            x_current, h_current, hu_current = self.refine_grid(
                x_current, h_current, hu_current
            )

            stats['iterations'] = iteration + 1

        stats['final_points'] = len(x_current)
        stats['refinement_ratio'] = stats['final_points'] / stats['initial_points']

        print(f"\n 自适应细化完成:")
        print(f"  迭代次数: {stats['iterations']}")
        print(f"  网格点数: {stats['initial_points']} → {stats['final_points']}")
        print(f"  细化倍率: {stats['refinement_ratio']:.2f}x")

        return x_current, h_current, hu_current, stats

    def __repr__(self) -> str:
        return (f"AdaptiveRefiner(refine_threshold={self.refine_threshold}, "
                f"coarsen_threshold={self.coarsen_threshold}, "
                f"level={self.current_level}/{self.max_refinement_level})")


if __name__ == "__main__":
    # 测试自适应细化器
    print("=" * 80)
    print("自适应网格细化器测试")
    print("=" * 80)

    # 创建测试网格和解
    nx = 101
    x = np.linspace(0, 10000, nx)
    h = 3.0 + 0.5 * np.sin(2 * np.pi * x / 10000)  # 模拟水深变化
    # 在中点创建一个陡变
    h[40:60] += 2.0 * np.exp(-((x[40:60] - 5000)**2) / (500**2))
    hu = 10.0 / 10.0 * np.ones_like(h)  # 单宽流量

    # 创建细化器
    refiner = AdaptiveRefiner(refine_threshold=0.05, coarsen_threshold=0.01)

    print(f"\n初始网格: {len(x)}个点")

    # 执行自适应细化
    x_refined, h_refined, hu_refined, stats = refiner.adaptive_refine(
        x, h, hu, max_iterations=3
    )

    print("\n" + "=" * 80)
