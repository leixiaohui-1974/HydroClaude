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
    """下游正常水深边界条件（Manning 公式反推）。"""

    def __init__(self, section, manning_n: float, bed_slope: float):
        """
        Args:
            section: CrossSection 实例
            manning_n: Manning 糙率系数
            bed_slope: 底坡
        """
        self.section = section
        self.manning_n = manning_n
        self.bed_slope = bed_slope

    def compute_normal_wse(self, Q: float) -> float:
        """给定流量 Q，反解正常水深对应的水位 Z。

        使用二分法求解 K(Z) * sqrt(S0) = Q。
        """
        from scipy.optimize import brentq

        invert = self.section.get_invert_elevation()
        target_K = abs(Q) / max(self.bed_slope ** 0.5, 1e-10)

        def residual(z: float) -> float:
            return self.section.compute_conveyance(z, self.manning_n) - target_K

        # 搜索上界
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
    """下游水位-流量关系曲线边界条件。"""

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
