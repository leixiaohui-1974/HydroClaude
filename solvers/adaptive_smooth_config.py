#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应平滑权重配置

根据局部流动状态动态调整平滑权重，在守恒性和稳定性之间智能平衡

作者: Claude
日期: 2025-10-23
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AdaptiveSmoothConfig:
    """
    自适应平滑权重配置

    支持四种模式：
    - 'fixed': 固定权重（向后兼容）
    - 'residual': 基于残差的自适应
    - 'distance': 基于距离的自适应
    - 'hybrid': 混合模式（推荐）
    """

    # 模式选择
    mode: Literal['fixed', 'residual', 'distance', 'hybrid'] = 'hybrid'

    # 权重范围
    smooth_weight_min: float = 0.25  # 远场/低残差区最小权重
    smooth_weight_max: float = 0.75  # 近场/高残差区最大权重

    # 固定模式参数
    fixed_weight: float = 0.55  # mode='fixed'时使用

    # 距离模式参数
    characteristic_length: float = 150.0  # 闸门影响特征长度 (m)

    # 残差模式参数
    residual_scale: float = 0.03  # 残差归一化尺度
    residual_high_threshold: float = 0.05  # 高残差阈值
    residual_medium_threshold: float = 0.02  # 中等残差阈值

    # 混合模式参数
    alpha: float = 0.6  # 距离因子的权重
    beta: float = 0.4   # 残差因子的权重

    def __post_init__(self):
        """参数验证"""
        # 验证模式
        if self.mode not in ['fixed', 'residual', 'distance', 'hybrid']:
            raise ValueError(f"Invalid mode: {self.mode}")

        # 验证权重范围
        if not (0.0 <= self.smooth_weight_min <= 1.0):
            raise ValueError(f"smooth_weight_min must be in [0, 1], got {self.smooth_weight_min}")
        if not (0.0 <= self.smooth_weight_max <= 1.0):
            raise ValueError(f"smooth_weight_max must be in [0, 1], got {self.smooth_weight_max}")
        if self.smooth_weight_min > self.smooth_weight_max:
            raise ValueError("smooth_weight_min must be <= smooth_weight_max")

        # 验证混合参数
        if self.mode == 'hybrid':
            if abs(self.alpha + self.beta - 1.0) > 1e-6:
                # 自动归一化
                total = self.alpha + self.beta
                if total > 0:
                    self.alpha /= total
                    self.beta /= total
                else:
                    raise ValueError("alpha and beta must sum to 1.0 (or be positive)")

    def __repr__(self):
        """字符串表示"""
        if self.mode == 'fixed':
            return f"AdaptiveSmoothConfig(mode='fixed', weight={self.fixed_weight})"
        elif self.mode == 'residual':
            return (f"AdaptiveSmoothConfig(mode='residual', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}])")
        elif self.mode == 'distance':
            return (f"AdaptiveSmoothConfig(mode='distance', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}], "
                   f"L_char={self.characteristic_length}m)")
        else:  # hybrid
            return (f"AdaptiveSmoothConfig(mode='hybrid', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}], "
                   f"α={self.alpha:.2f}, β={self.beta:.2f})")


# 预定义配置
DEFAULT_CONFIG = AdaptiveSmoothConfig(mode='fixed', fixed_weight=0.55)

AGGRESSIVE_CONFIG = AdaptiveSmoothConfig(
    mode='hybrid',
    smooth_weight_min=0.20,
    smooth_weight_max=0.80,
    alpha=0.5,
    beta=0.5
)

CONSERVATIVE_CONFIG = AdaptiveSmoothConfig(
    mode='hybrid',
    smooth_weight_min=0.30,
    smooth_weight_max=0.70,
    alpha=0.7,
    beta=0.3
)

DISTANCE_ONLY_CONFIG = AdaptiveSmoothConfig(
    mode='distance',
    smooth_weight_min=0.25,
    smooth_weight_max=0.75,
    characteristic_length=150.0
)

RESIDUAL_ONLY_CONFIG = AdaptiveSmoothConfig(
    mode='residual',
    smooth_weight_min=0.25,
    smooth_weight_max=0.75,
    residual_scale=0.03
)
