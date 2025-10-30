"""
HydroClaude Geometry Module

断面几何模块 - Stage 4

提供各种断面形状的水力计算功能。

主要组件:
- trapezoidal_channel: 梯形断面
- irregular_channel: 天然不规则断面
- compound_channel: 复合断面（主槽+滩地）

作者: HydroClaude Team
日期: 2025-10-29
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "HydroClaude Team"

from .trapezoidal_channel import TrapezoidalChannel, create_trapezoidal_channel
from .irregular_channel import IrregularChannel, create_irregular_channel
from .compound_channel import CompoundChannel, create_compound_channel

__all__ = [
    'TrapezoidalChannel',
    'create_trapezoidal_channel',
    'IrregularChannel',
    'create_irregular_channel',
    'CompoundChannel',
    'create_compound_channel',
]
