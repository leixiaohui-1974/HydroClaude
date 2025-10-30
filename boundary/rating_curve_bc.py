#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rating Curve 边界条件模块

实现水位-流量关系曲线（Rating Curve），支持双向插值和幂律拟合。

理论基础：
1. Rating Curve（水位-流量关系）：
   - 描述河道断面处水位与流量的关系
   - 幂律形式：Q = a * (h - h0)^b
   - a: 流量系数
   - b: 指数（通常 1.5-2.5）
   - h0: 零流量水位

2. 应用场景：
   - 河道边界条件（已知水位推算流量）
   - 水文监测站（水位-流量转换）
   - 反向计算（已知流量推算水位）

3. 插值方法：
   - 线性插值：简单快速
   - 样条插值：平滑连续
   - 幂律拟合：物理意义明确

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Literal, Union, List, Tuple
from pathlib import Path
from scipy.interpolate import interp1d, CubicSpline
from scipy.optimize import curve_fit


class RatingCurveBoundary:
    """
    Rating Curve 边界条件类

    支持水位-流量双向转换，可使用插值或幂律拟合。

    Attributes:
        bc_id: 边界条件标识
        h_data: 水位数组 (m)
        Q_data: 流量数组 (m³/s)
        interpolation_method: 插值方法
        use_power_law: 是否使用幂律拟合
    """

    def __init__(
        self,
        bc_id: str,
        h_data: Union[np.ndarray, List[float]],
        Q_data: Union[np.ndarray, List[float]],
        interpolation_method: Literal["linear", "cubic"] = "linear",
        extrapolation_method: Literal["constant", "linear", "power_law"] = "constant",
        use_power_law: bool = False,
        power_law_params: Optional[Dict[str, float]] = None
    ):
        """
        初始化 Rating Curve 边界条件

        Args:
            bc_id: 边界条件标识
            h_data: 水位数据 [h1, h2, ..., hn] (m)
            Q_data: 流量数据 [Q1, Q2, ..., Qn] (m³/s)
            interpolation_method: 插值方法
                - 'linear': 线性插值（默认）
                - 'cubic': 三次样条插值
            extrapolation_method: 外推方法
                - 'constant': 边界值保持不变（默认）
                - 'linear': 线性外推
                - 'power_law': 幂律外推（需要拟合参数）
            use_power_law: 是否使用幂律拟合 Q = a*(h-h0)^b
            power_law_params: 幂律参数 {'a', 'b', 'h0'}，若不提供则自动拟合

        Raises:
            ValueError: 输入数据不合理时抛出异常
        """
        # 转换为 numpy 数组
        self.h = np.array(h_data, dtype=float)
        self.Q = np.array(Q_data, dtype=float)

        if len(self.h) != len(self.Q):
            raise ValueError(
                f"Length mismatch: h_data has {len(self.h)} points, "
                f"Q_data has {len(self.Q)} points"
            )

        if len(self.h) < 2:
            raise ValueError(f"Need at least 2 data points, got {len(self.h)}")

        # 验证水位单调性（Rating Curve 要求水位单调递增）
        if not np.all(np.diff(self.h) > 0):
            raise ValueError("Water level (h) must be monotonically increasing")

        # 验证流量非负且单调递增
        if np.any(self.Q < 0):
            raise ValueError("Discharge (Q) must be non-negative")

        if not np.all(np.diff(self.Q) >= 0):
            raise ValueError("Discharge (Q) must be monotonically increasing")

        # 基本属性
        self.bc_id = bc_id
        self.interpolation_method = interpolation_method
        self.extrapolation_method = extrapolation_method
        self.use_power_law = use_power_law

        # 幂律拟合
        if use_power_law:
            if power_law_params is not None:
                self.power_law_params = power_law_params
            else:
                self.power_law_params = self._fit_power_law()
        else:
            self.power_law_params = None

        # 创建插值器
        self._create_interpolators()

    def _fit_power_law(self) -> Dict[str, float]:
        """
        拟合幂律关系：Q = a * (h - h0)^b

        Returns:
            字典，包含拟合参数 {'a', 'b', 'h0'}
        """
        # 估计 h0（零流量水位）：取最低水位向下偏移
        h0_guess = self.h[0] - 0.1 * (self.h[-1] - self.h[0])

        # 定义幂律函数
        def power_law(h, a, b, h0):
            # 避免负数
            h_effective = np.maximum(h - h0, 1e-6)
            return a * (h_effective ** b)

        try:
            # 拟合
            popt, _ = curve_fit(
                power_law,
                self.h,
                self.Q,
                p0=[1.0, 2.0, h0_guess],  # 初始猜测
                bounds=([0.01, 0.5, -np.inf], [np.inf, 5.0, self.h[0]])  # 参数范围
            )

            a, b, h0 = popt

            return {'a': float(a), 'b': float(b), 'h0': float(h0)}

        except Exception as e:
            # 拟合失败，使用默认值
            return {'a': 1.0, 'b': 2.0, 'h0': float(self.h[0] - 1.0)}

    def _create_interpolators(self):
        """创建插值器（h->Q 和 Q->h）"""
        # h -> Q 插值器
        if self.interpolation_method == "linear":
            self._h_to_Q_interpolator = interp1d(
                self.h, self.Q,
                kind='linear',
                bounds_error=False,
                fill_value=(self.Q[0], self.Q[-1])
            )
        elif self.interpolation_method == "cubic":
            if len(self.h) >= 4:
                self._h_to_Q_interpolator = CubicSpline(
                    self.h, self.Q,
                    bc_type='natural',
                    extrapolate=False
                )
            else:
                # 退化为线性
                self._h_to_Q_interpolator = interp1d(
                    self.h, self.Q,
                    kind='linear',
                    bounds_error=False,
                    fill_value=(self.Q[0], self.Q[-1])
                )

        # Q -> h 反向插值器（交换 x 和 y）
        if self.interpolation_method == "linear":
            self._Q_to_h_interpolator = interp1d(
                self.Q, self.h,
                kind='linear',
                bounds_error=False,
                fill_value=(self.h[0], self.h[-1])
            )
        elif self.interpolation_method == "cubic":
            if len(self.Q) >= 4:
                self._Q_to_h_interpolator = CubicSpline(
                    self.Q, self.h,
                    bc_type='natural',
                    extrapolate=False
                )
            else:
                self._Q_to_h_interpolator = interp1d(
                    self.Q, self.h,
                    kind='linear',
                    bounds_error=False,
                    fill_value=(self.h[0], self.h[-1])
                )

    def h_to_Q(self, h: float) -> float:
        """
        根据水位计算流量

        Args:
            h: 水位 (m)

        Returns:
            流量 (m³/s)
        """
        # 处理外推
        if h < self.h[0]:
            return self._extrapolate_h_to_Q(h, direction='low')
        if h > self.h[-1]:
            return self._extrapolate_h_to_Q(h, direction='high')

        # 插值
        Q = self._h_to_Q_interpolator(h)

        if isinstance(Q, np.ndarray):
            return float(Q.item())
        else:
            return float(Q)

    def Q_to_h(self, Q: float) -> float:
        """
        根据流量计算水位

        Args:
            Q: 流量 (m³/s)

        Returns:
            水位 (m)
        """
        # 确保非负
        Q = max(Q, 0.0)

        # 处理外推
        if Q < self.Q[0]:
            return self._extrapolate_Q_to_h(Q, direction='low')
        if Q > self.Q[-1]:
            return self._extrapolate_Q_to_h(Q, direction='high')

        # 插值
        h = self._Q_to_h_interpolator(Q)

        if isinstance(h, np.ndarray):
            return float(h.item())
        else:
            return float(h)

    def _extrapolate_h_to_Q(self, h: float, direction: str) -> float:
        """
        外推 h -> Q

        Args:
            h: 水位 (m)
            direction: 'low' 或 'high'

        Returns:
            流量 (m³/s)
        """
        if self.extrapolation_method == "constant":
            # 常数外推
            if direction == 'low':
                return float(self.Q[0])
            else:
                return float(self.Q[-1])

        elif self.extrapolation_method == "linear":
            # 线性外推
            if direction == 'low':
                # 使用前两个点
                slope = (self.Q[1] - self.Q[0]) / (self.h[1] - self.h[0])
                return float(self.Q[0] + slope * (h - self.h[0]))
            else:
                # 使用后两个点
                slope = (self.Q[-1] - self.Q[-2]) / (self.h[-1] - self.h[-2])
                return float(self.Q[-1] + slope * (h - self.h[-1]))

        elif self.extrapolation_method == "power_law":
            # 幂律外推
            if self.power_law_params is not None:
                a = self.power_law_params['a']
                b = self.power_law_params['b']
                h0 = self.power_law_params['h0']
                h_effective = max(h - h0, 1e-6)
                return float(a * (h_effective ** b))
            else:
                # 无幂律参数，退化为常数
                return float(self.Q[0] if direction == 'low' else self.Q[-1])

    def _extrapolate_Q_to_h(self, Q: float, direction: str) -> float:
        """
        外推 Q -> h

        Args:
            Q: 流量 (m³/s)
            direction: 'low' 或 'high'

        Returns:
            水位 (m)
        """
        if self.extrapolation_method == "constant":
            # 常数外推
            if direction == 'low':
                return float(self.h[0])
            else:
                return float(self.h[-1])

        elif self.extrapolation_method == "linear":
            # 线性外推
            if direction == 'low':
                slope = (self.h[1] - self.h[0]) / (self.Q[1] - self.Q[0]) if self.Q[1] != self.Q[0] else 0
                return float(self.h[0] + slope * (Q - self.Q[0]))
            else:
                slope = (self.h[-1] - self.h[-2]) / (self.Q[-1] - self.Q[-2]) if self.Q[-1] != self.Q[-2] else 0
                return float(self.h[-1] + slope * (Q - self.Q[-1]))

        elif self.extrapolation_method == "power_law":
            # 幂律反推：h = h0 + (Q/a)^(1/b)
            if self.power_law_params is not None:
                a = self.power_law_params['a']
                b = self.power_law_params['b']
                h0 = self.power_law_params['h0']
                if Q > 0 and a > 0 and b > 0:
                    return float(h0 + (Q / a) ** (1 / b))
                else:
                    return float(h0)
            else:
                return float(self.h[0] if direction == 'low' else self.h[-1])

    def get_range(self) -> Dict[str, Tuple[float, float]]:
        """
        获取数据范围

        Returns:
            字典，包含 'h_range' 和 'Q_range'
        """
        return {
            'h_range': (float(self.h[0]), float(self.h[-1])),
            'Q_range': (float(self.Q[0]), float(self.Q[-1]))
        }

    def evaluate_fit(self) -> Dict[str, float]:
        """
        评估幂律拟合质量（如果使用了幂律）

        Returns:
            字典，包含拟合统计信息
        """
        if not self.use_power_law or self.power_law_params is None:
            return {}

        a = self.power_law_params['a']
        b = self.power_law_params['b']
        h0 = self.power_law_params['h0']

        # 计算拟合值
        h_effective = np.maximum(self.h - h0, 1e-6)
        Q_fitted = a * (h_effective ** b)

        # 残差
        residuals = self.Q - Q_fitted

        # 统计指标
        rmse = np.sqrt(np.mean(residuals ** 2))
        mae = np.mean(np.abs(residuals))
        r_squared = 1 - np.sum(residuals ** 2) / np.sum((self.Q - np.mean(self.Q)) ** 2)

        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r_squared': float(r_squared),
            'max_error': float(np.max(np.abs(residuals)))
        }

    @classmethod
    def from_file(
        cls,
        bc_id: str,
        filepath: Union[str, Path],
        h_column: int = 0,
        Q_column: int = 1,
        skiprows: int = 1,
        delimiter: str = ',',
        **kwargs
    ) -> 'RatingCurveBoundary':
        """
        从CSV文件加载 Rating Curve

        Args:
            bc_id: 边界条件标识
            filepath: CSV文件路径
            h_column: 水位列索引，默认0
            Q_column: 流量列索引，默认1
            skiprows: 跳过的行数，默认1
            delimiter: 分隔符，默认逗号
            **kwargs: 传递给 __init__ 的其他参数

        Returns:
            RatingCurveBoundary 对象
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            data = np.loadtxt(filepath, delimiter=delimiter, skiprows=skiprows)

            if data.ndim == 1:
                raise ValueError("Need at least 2 columns (h and Q)")

            h_data = data[:, h_column]
            Q_data = data[:, Q_column]

            return cls(
                bc_id=bc_id,
                h_data=h_data,
                Q_data=Q_data,
                **kwargs
            )

        except Exception as e:
            raise ValueError(f"Failed to load rating curve from {filepath}: {str(e)}")

    def to_file(
        self,
        filepath: Union[str, Path],
        delimiter: str = ',',
        header: Optional[str] = None
    ):
        """
        保存 Rating Curve 到CSV文件

        Args:
            filepath: 输出文件路径
            delimiter: 分隔符，默认逗号
            header: 标题行，如 "h,Q"
        """
        filepath = Path(filepath)

        data = np.column_stack([self.h, self.Q])

        if header is None:
            header = "h,Q"

        np.savetxt(filepath, data, delimiter=delimiter, header=header, comments='')

    def properties(self) -> Dict[str, any]:
        """
        返回边界条件属性

        Returns:
            字典，包含边界条件参数
        """
        props = {
            'bc_id': self.bc_id,
            'interpolation_method': self.interpolation_method,
            'extrapolation_method': self.extrapolation_method,
            'n_points': len(self.h),
            'h_range': self.get_range()['h_range'],
            'Q_range': self.get_range()['Q_range'],
            'use_power_law': self.use_power_law
        }

        if self.use_power_law and self.power_law_params is not None:
            props['power_law_params'] = self.power_law_params
            props['fit_quality'] = self.evaluate_fit()

        return props

    def __repr__(self) -> str:
        """字符串表示"""
        h_range = self.get_range()['h_range']
        Q_range = self.get_range()['Q_range']

        return (
            f"RatingCurveBoundary(id='{self.bc_id}', "
            f"n_points={len(self.h)}, "
            f"h=[{h_range[0]:.2f}, {h_range[1]:.2f}]m, "
            f"Q=[{Q_range[0]:.1f}, {Q_range[1]:.1f}]m³/s)"
        )


def create_rating_curve(
    bc_id: str,
    h_data: Union[np.ndarray, List[float]],
    Q_data: Union[np.ndarray, List[float]],
    **kwargs
) -> RatingCurveBoundary:
    """
    便捷函数：创建 Rating Curve 边界条件对象

    Args:
        bc_id: 边界条件标识
        h_data: 水位数据
        Q_data: 流量数据
        **kwargs: 其他可选参数

    Returns:
        RatingCurveBoundary 对象

    Example:
        >>> rc = create_rating_curve(
        ...     bc_id="RC_OUTLET",
        ...     h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
        ...     Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        ... )
    """
    return RatingCurveBoundary(
        bc_id=bc_id,
        h_data=h_data,
        Q_data=Q_data,
        **kwargs
    )
