"""
HydroClaude Boundary Conditions Module

边界条件模块 - Stage 4

提供时变边界条件功能，包括时间序列边界和 Rating Curve。

主要组件:
- TimeSeriesBoundary: 时间序列边界条件
- RatingCurveBoundary: 水位-流量关系曲线

作者: HydroClaude Team
日期: 2025-10-29
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "HydroClaude Team"

from .timeseries_bc import TimeSeriesBoundary, create_timeseries_boundary
from .rating_curve_bc import RatingCurveBoundary, create_rating_curve

__all__ = [
    'TimeSeriesBoundary',
    'create_timeseries_boundary',
    'RatingCurveBoundary',
    'create_rating_curve',
]
