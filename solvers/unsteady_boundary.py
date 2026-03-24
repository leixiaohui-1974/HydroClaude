"""非恒定流时序边界条件模块。"""

import numpy as np
from typing import Sequence


class FlowHydrographBC:
    """上游流量过程线边界条件 Q(t)。"""

    def __init__(self, times: Sequence[float], flows: Sequence[float]):
        """
        Args:
            times: 时间序列 (s)
            flows: 对应流量 (m³/s)
        """
        self.times = np.asarray(times, dtype=float)
        self.flows = np.asarray(flows, dtype=float)

    def __call__(self, t: float) -> float:
        """线性插值获取 t 时刻流量"""
        return float(np.interp(t, self.times, self.flows))


class StageHydrographBC:
    """下游水位过程线边界条件 Z(t)。"""

    def __init__(self, times: Sequence[float], stages: Sequence[float]):
        self.times = np.asarray(times, dtype=float)
        self.stages = np.asarray(stages, dtype=float)

    def __call__(self, t: float) -> float:
        return float(np.interp(t, self.times, self.stages))


class NormalDepthBC:
    """下游正常水深边界条件（Manning 公式反推）。

    K 计算方式（按优先级）：
    1. 分区 K (LOB/Ch/ROB)：提供 bank stations + Manning n 分区值
    2. 单一 Manning n：后备
    """

    def __init__(self, section, manning_n: float, bed_slope: float,
                 manning_n_lob: float | None = None,
                 manning_n_rob: float | None = None,
                 left_bank: float | None = None,
                 right_bank: float | None = None,
                 K_elevations: np.ndarray | None = None,
                 K_values: np.ndarray | None = None):
        """
        Args:
            section: CrossSection 实例（需有 distances/elevations 属性）
            manning_n: 主槽 Manning 糙率系数
            bed_slope: 底坡
            manning_n_lob: 左滩 Manning n（分区计算用）
            manning_n_rob: 右滩 Manning n（分区计算用）
            left_bank: 左岸站号 (m)（分区计算用）
            right_bank: 右岸站号 (m)（分区计算用）
            K_elevations: 预计算 K 高程数组 (m)，可选（已弃用）
            K_values: 预计算 K 数组 (m³/s)，可选（已弃用）
        """
        self.section = section
        self.manning_n = manning_n
        self.bed_slope = bed_slope
        self._manning_n_lob = manning_n_lob
        self._manning_n_rob = manning_n_rob
        self._left_bank = left_bank
        self._right_bank = right_bank
        # Legacy support: pre-computed K table
        self._K_elevations = K_elevations
        self._K_values = K_values

    def _compute_K(self, z: float) -> float:
        """计算给定水位的 K，优先用分区计算。"""
        # 分区 K
        if (self._left_bank is not None and self._right_bank is not None
                and hasattr(self.section, 'distances') and hasattr(self.section, 'elevations')):
            from physics.property_table import subdivided_conveyance
            n_lob = self._manning_n_lob if self._manning_n_lob else self.manning_n
            n_rob = self._manning_n_rob if self._manning_n_rob else self.manning_n
            K, _A = subdivided_conveyance(
                np.asarray(self.section.distances),
                np.asarray(self.section.elevations),
                z, self._left_bank, self._right_bank,
                n_lob, self.manning_n, n_rob,
            )
            return K
        # Legacy: pre-computed K table
        if self._K_elevations is not None and self._K_values is not None:
            return float(np.interp(z, self._K_elevations, self._K_values))
        # Fallback: single Manning n
        return self.section.compute_conveyance(z, self.manning_n)

    def compute_normal_wse(self, Q: float) -> float:
        """给定流量 Q，反解正常水深对应的水位 Z。

        使用二分法求解 K(Z) * sqrt(S0) = Q。
        """
        from scipy.optimize import brentq

        invert = self.section.get_invert_elevation()
        target_K = abs(Q) / max(self.bed_slope ** 0.5, 1e-10)

        def residual(z: float) -> float:
            return self._compute_K(z) - target_K

        z_hi = invert + 0.1
        for _ in range(50):
            if residual(z_hi) > 0:
                break
            z_hi += z_hi - invert
        else:
            return z_hi

        try:
            return brentq(residual, invert + 1e-6, z_hi, xtol=1e-6)
        except ValueError:
            return invert + 1.0


class RatingCurveBC:
    """下游水位-流量关系曲线边界条件。

    从 HEC-RAS 的 Rating Curve BC 提取：(Q, Z) 对应关系。
    支持 PreissmannSolver 的 compute_normal_wse 接口。
    """

    def __init__(self, flows: Sequence[float], stages: Sequence[float]):
        """
        Args:
            flows: 流量数组 (m³/s)，递增
            stages: 对应水位数组 (m)
        """
        self.flows = np.asarray(flows, dtype=float)
        self.stages = np.asarray(stages, dtype=float)

    def compute_wse(self, Q: float) -> float:
        """给定流量反查水位"""
        return float(np.interp(abs(Q), self.flows, self.stages))

    def compute_normal_wse(self, Q: float) -> float:
        """与 NormalDepthBC 兼容的接口：Q → Z。"""
        return self.compute_wse(Q)


class ConstantFlowBC:
    """恒定流量边界（用于稳态验证）。"""

    def __init__(self, Q: float):
        self.Q = Q

    def __call__(self, t: float) -> float:
        return self.Q


class ConstantStageBC:
    """恒定水位边界（用于稳态验证）。"""

    def __init__(self, Z: float):
        self.Z = Z

    def __call__(self, t: float) -> float:
        return self.Z
