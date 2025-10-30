#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列边界条件模块

实现时变边界条件，支持从时间序列数据获取边界值。

理论基础：
1. 时间序列插值：
   - 线性插值：适用于密集采样数据
   - 三次样条插值：适用于平滑曲线
   - 前向/后向保持：适用于阶跃变化

2. 边界条件类型：
   - 流量边界 (Q): 指定流量时间序列
   - 水位边界 (h): 指定水位时间序列

3. 应用场景：
   - 洪水过程模拟
   - 潮汐边界条件
   - 水库调度过程
   - 闸门操作过程

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Literal, Union, List
from pathlib import Path
from scipy.interpolate import interp1d, CubicSpline


class TimeSeriesBoundary:
    """
    时间序列边界条件类

    支持从时间序列数据中获取任意时刻的边界值，使用线性或样条插值。

    Attributes:
        bc_id: 边界条件标识
        bc_type: 边界类型 'Q' (流量) 或 'h' (水位)
        time: 时间数组 (s)
        values: 对应的边界值数组 (m³/s 或 m)
        interpolation_method: 插值方法
    """

    def __init__(
        self,
        bc_id: str,
        bc_type: Literal["Q", "h"],
        time_data: Union[np.ndarray, List[float]],
        value_data: Union[np.ndarray, List[float]],
        interpolation_method: Literal["linear", "cubic", "previous", "next"] = "linear",
        extrapolation_method: Literal["constant", "linear"] = "constant"
    ):
        """
        初始化时间序列边界条件

        Args:
            bc_id: 边界条件标识
            bc_type: 边界类型，'Q' (流量) 或 'h' (水位)
            time_data: 时间序列 [t1, t2, ..., tn] (s)
            value_data: 对应值 [v1, v2, ..., vn] (m³/s 或 m)
            interpolation_method: 插值方法
                - 'linear': 线性插值（默认）
                - 'cubic': 三次样条插值（更平滑）
                - 'previous': 前向保持（阶跃）
                - 'next': 后向保持（阶跃）
            extrapolation_method: 外推方法
                - 'constant': 边界值保持不变（默认）
                - 'linear': 线性外推

        Raises:
            ValueError: 输入数据不合理时抛出异常
        """
        # 验证输入
        if bc_type not in ["Q", "h"]:
            raise ValueError(f"bc_type must be 'Q' or 'h', got '{bc_type}'")

        # 转换为 numpy 数组
        self.t = np.array(time_data, dtype=float)
        self.values = np.array(value_data, dtype=float)

        if len(self.t) != len(self.values):
            raise ValueError(
                f"Length mismatch: time_data has {len(self.t)} points, "
                f"value_data has {len(self.values)} points"
            )

        if len(self.t) < 2:
            raise ValueError(f"Need at least 2 data points, got {len(self.t)}")

        # 验证时间单调性
        dt = np.diff(self.t)
        if np.any(dt < 0):
            raise ValueError("Time series must be monotonically increasing")

        if np.any(dt == 0):
            raise ValueError("Time series cannot have duplicate time points")

        # 基本属性
        self.bc_id = bc_id
        self.bc_type = bc_type
        self.interpolation_method = interpolation_method
        self.extrapolation_method = extrapolation_method

        # 创建插值器
        self._create_interpolator()

    def _create_interpolator(self):
        """创建插值器"""
        if self.interpolation_method == "linear":
            # 线性插值
            self._interpolator = interp1d(
                self.t, self.values,
                kind='linear',
                bounds_error=False,
                fill_value=(self.values[0], self.values[-1])
            )
        elif self.interpolation_method == "cubic":
            # 三次样条插值
            if len(self.t) < 4:
                # 数据点太少，退化为线性插值
                self._interpolator = interp1d(
                    self.t, self.values,
                    kind='linear',
                    bounds_error=False,
                    fill_value=(self.values[0], self.values[-1])
                )
            else:
                self._interpolator = CubicSpline(
                    self.t, self.values,
                    bc_type='natural',
                    extrapolate=False
                )
        elif self.interpolation_method == "previous":
            # 前向保持
            self._interpolator = interp1d(
                self.t, self.values,
                kind='previous',
                bounds_error=False,
                fill_value=(self.values[0], self.values[-1])
            )
        elif self.interpolation_method == "next":
            # 后向保持
            self._interpolator = interp1d(
                self.t, self.values,
                kind='next',
                bounds_error=False,
                fill_value=(self.values[0], self.values[-1])
            )
        else:
            raise ValueError(f"Unknown interpolation method: {self.interpolation_method}")

    def get_value(self, t: float) -> float:
        """
        获取给定时刻的边界值

        Args:
            t: 时刻 (s)

        Returns:
            边界值 (m³/s 或 m)
        """
        # 处理边界外推
        if t < self.t[0]:
            if self.extrapolation_method == "constant":
                return float(self.values[0])
            else:  # linear
                # 使用前两个点线性外推
                if len(self.t) >= 2:
                    slope = (self.values[1] - self.values[0]) / (self.t[1] - self.t[0])
                    return float(self.values[0] + slope * (t - self.t[0]))
                else:
                    return float(self.values[0])

        if t > self.t[-1]:
            if self.extrapolation_method == "constant":
                return float(self.values[-1])
            else:  # linear
                # 使用最后两个点线性外推
                if len(self.t) >= 2:
                    slope = (self.values[-1] - self.values[-2]) / (self.t[-1] - self.t[-2])
                    return float(self.values[-1] + slope * (t - self.t[-1]))
                else:
                    return float(self.values[-1])

        # 插值
        value = self._interpolator(t)

        # 确保返回标量
        if isinstance(value, np.ndarray):
            return float(value.item())
        else:
            return float(value)

    def get_values(self, t_array: Union[np.ndarray, List[float]]) -> np.ndarray:
        """
        获取一组时刻的边界值（批量查询）

        Args:
            t_array: 时刻数组 (s)

        Returns:
            边界值数组 (m³/s 或 m)
        """
        t_array = np.array(t_array, dtype=float)
        return np.array([self.get_value(t) for t in t_array])

    def get_time_range(self) -> tuple:
        """
        获取时间序列的时间范围

        Returns:
            (t_min, t_max) 时间范围 (s)
        """
        return (float(self.t[0]), float(self.t[-1]))

    def get_value_range(self) -> tuple:
        """
        获取边界值的范围

        Returns:
            (v_min, v_max) 值范围
        """
        return (float(np.min(self.values)), float(np.max(self.values)))

    def get_statistics(self) -> Dict[str, float]:
        """
        获取时间序列统计信息

        Returns:
            字典，包含统计信息
        """
        return {
            'n_points': len(self.t),
            'duration': float(self.t[-1] - self.t[0]),
            'mean': float(np.mean(self.values)),
            'std': float(np.std(self.values)),
            'min': float(np.min(self.values)),
            'max': float(np.max(self.values)),
            'median': float(np.median(self.values))
        }

    def resample(self, dt: float) -> 'TimeSeriesBoundary':
        """
        重采样时间序列到固定时间步长

        Args:
            dt: 采样时间步长 (s)

        Returns:
            新的 TimeSeriesBoundary 对象
        """
        t_new = np.arange(self.t[0], self.t[-1] + dt, dt)
        values_new = self.get_values(t_new)

        return TimeSeriesBoundary(
            bc_id=f"{self.bc_id}_resampled",
            bc_type=self.bc_type,
            time_data=t_new,
            value_data=values_new,
            interpolation_method=self.interpolation_method,
            extrapolation_method=self.extrapolation_method
        )

    def shift_time(self, time_shift: float) -> 'TimeSeriesBoundary':
        """
        平移时间序列

        Args:
            time_shift: 时间平移量 (s)，正值向后平移

        Returns:
            新的 TimeSeriesBoundary 对象
        """
        t_new = self.t + time_shift

        return TimeSeriesBoundary(
            bc_id=f"{self.bc_id}_shifted",
            bc_type=self.bc_type,
            time_data=t_new,
            value_data=self.values.copy(),
            interpolation_method=self.interpolation_method,
            extrapolation_method=self.extrapolation_method
        )

    def scale_values(self, scale_factor: float) -> 'TimeSeriesBoundary':
        """
        缩放边界值

        Args:
            scale_factor: 缩放系数

        Returns:
            新的 TimeSeriesBoundary 对象
        """
        values_new = self.values * scale_factor

        return TimeSeriesBoundary(
            bc_id=f"{self.bc_id}_scaled",
            bc_type=self.bc_type,
            time_data=self.t.copy(),
            value_data=values_new,
            interpolation_method=self.interpolation_method,
            extrapolation_method=self.extrapolation_method
        )

    @classmethod
    def from_file(
        cls,
        bc_id: str,
        bc_type: Literal["Q", "h"],
        filepath: Union[str, Path],
        time_column: int = 0,
        value_column: int = 1,
        skiprows: int = 1,
        delimiter: str = ',',
        **kwargs
    ) -> 'TimeSeriesBoundary':
        """
        从CSV文件加载时间序列

        Args:
            bc_id: 边界条件标识
            bc_type: 边界类型 'Q' 或 'h'
            filepath: CSV文件路径
            time_column: 时间列索引，默认0
            value_column: 值列索引，默认1
            skiprows: 跳过的行数（通常跳过标题行），默认1
            delimiter: 分隔符，默认逗号
            **kwargs: 传递给 __init__ 的其他参数

        Returns:
            TimeSeriesBoundary 对象

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            # 读取数据
            data = np.loadtxt(filepath, delimiter=delimiter, skiprows=skiprows)

            # 提取时间和值列
            if data.ndim == 1:
                # 只有一列，假设是值，时间从0开始
                time_data = np.arange(len(data), dtype=float)
                value_data = data
            else:
                time_data = data[:, time_column]
                value_data = data[:, value_column]

            return cls(
                bc_id=bc_id,
                bc_type=bc_type,
                time_data=time_data,
                value_data=value_data,
                **kwargs
            )

        except Exception as e:
            raise ValueError(f"Failed to load time series from {filepath}: {str(e)}")

    def to_file(
        self,
        filepath: Union[str, Path],
        delimiter: str = ',',
        header: Optional[str] = None
    ):
        """
        保存时间序列到CSV文件

        Args:
            filepath: 输出文件路径
            delimiter: 分隔符，默认逗号
            header: 标题行，如 "time,Q" 或 "time,h"
        """
        filepath = Path(filepath)

        # 准备数据
        data = np.column_stack([self.t, self.values])

        # 默认标题
        if header is None:
            header = f"time,{self.bc_type}"

        # 保存
        np.savetxt(filepath, data, delimiter=delimiter, header=header, comments='')

    def properties(self) -> Dict[str, any]:
        """
        返回边界条件属性

        Returns:
            字典，包含边界条件参数
        """
        stats = self.get_statistics()
        t_range = self.get_time_range()
        v_range = self.get_value_range()

        return {
            'bc_id': self.bc_id,
            'bc_type': self.bc_type,
            'interpolation_method': self.interpolation_method,
            'extrapolation_method': self.extrapolation_method,
            'n_points': stats['n_points'],
            'time_range': t_range,
            'duration': stats['duration'],
            'value_range': v_range,
            'mean_value': stats['mean'],
            'std_value': stats['std'],
            'min_value': stats['min'],
            'max_value': stats['max']
        }

    def __repr__(self) -> str:
        """字符串表示"""
        t_range = self.get_time_range()
        v_range = self.get_value_range()

        return (
            f"TimeSeriesBoundary(id='{self.bc_id}', "
            f"type='{self.bc_type}', "
            f"n_points={len(self.t)}, "
            f"t=[{t_range[0]:.1f}, {t_range[1]:.1f}]s, "
            f"v=[{v_range[0]:.2f}, {v_range[1]:.2f}])"
        )


def create_timeseries_boundary(
    bc_id: str,
    bc_type: Literal["Q", "h"],
    time_data: Union[np.ndarray, List[float]],
    value_data: Union[np.ndarray, List[float]],
    **kwargs
) -> TimeSeriesBoundary:
    """
    便捷函数：创建时间序列边界条件对象

    Args:
        bc_id: 边界条件标识
        bc_type: 边界类型 'Q' 或 'h'
        time_data: 时间序列
        value_data: 对应值
        **kwargs: 其他可选参数

    Returns:
        TimeSeriesBoundary 对象

    Example:
        >>> bc = create_timeseries_boundary(
        ...     bc_id="BC_INFLOW",
        ...     bc_type="Q",
        ...     time_data=[0, 3600, 7200, 10800],
        ...     value_data=[10.0, 15.0, 12.0, 8.0]
        ... )
    """
    return TimeSeriesBoundary(
        bc_id=bc_id,
        bc_type=bc_type,
        time_data=time_data,
        value_data=value_data,
        **kwargs
    )
