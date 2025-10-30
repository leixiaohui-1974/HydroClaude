#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
侧堰水工建筑物模块

实现侧堰分流计算，包括 De Marchi 公式和分流比计算。

理论基础：
1. De Marchi 侧堰公式（1934）：
   - 考虑沿程水位变化的侧堰溢流公式
   - dQ/dx = -Cd * L_weir * √(2g) * (h - z_crest)^(3/2)
   - 负号表示主渠流量沿程减小

2. 侧堰类型：
   - 薄壁侧堰：Cd ≈ 0.4-0.5
   - 宽顶侧堰：Cd ≈ 0.3-0.4
   - 淹没侧堰：需修正系数

3. 分流特性：
   - 分流比 = Q_diverted / Q_inflow
   - 主渠水位沿程降低
   - 需要迭代计算沿程水位

4. 应用场景：
   - 灌溉渠道分水
   - 防洪溢流
   - 城市排水溢流堰

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Literal, Tuple, List


class SideWeir:
    """
    侧堰水工建筑物类

    支持 De Marchi 公式计算侧堰分流，适用于灌溉分水、防洪溢流等场景。

    Attributes:
        weir_id: 侧堰标识
        length: 侧堰长度 (m)
        crest_elevation: 堰顶高程 (m)
        discharge_coefficient: 流量系数 Cd，典型值 0.35-0.50
        weir_type: 堰型 'sharp' (薄壁) 或 'broad' (宽顶)
        channel_width: 主渠宽度 (m)
        channel_slope: 主渠底坡 S0
        manning_n: 主渠 Manning 系数
    """

    def __init__(
        self,
        weir_id: str,
        length: float,
        crest_elevation: float,
        channel_width: float,
        channel_slope: float,
        manning_n: float = 0.020,
        discharge_coefficient: Optional[float] = None,
        weir_type: Literal["sharp", "broad"] = "sharp"
    ):
        """
        初始化侧堰结构

        Args:
            weir_id: 侧堰标识
            length: 侧堰长度 (m)
            crest_elevation: 堰顶高程 (m)
            channel_width: 主渠宽度 (m)
            channel_slope: 主渠底坡 S0
            manning_n: 主渠 Manning 系数，默认 0.020
            discharge_coefficient: 流量系数 Cd，若不指定则根据 weir_type 自动设置
            weir_type: 堰型，'sharp' (薄壁) 或 'broad' (宽顶)

        Raises:
            ValueError: 参数不合理时抛出异常
        """
        # 验证输入参数
        if length <= 0:
            raise ValueError(f"length must be > 0, got {length}")
        if channel_width <= 0:
            raise ValueError(f"channel_width must be > 0, got {channel_width}")
        if channel_slope < 0:
            raise ValueError(f"channel_slope must be >= 0, got {channel_slope}")
        if manning_n <= 0:
            raise ValueError(f"manning_n must be > 0, got {manning_n}")

        # 基本属性
        self.weir_id = weir_id
        self.L = length
        self.z_crest = crest_elevation
        self.B = channel_width
        self.S0 = channel_slope
        self.n = manning_n
        self.weir_type = weir_type

        # 流量系数
        if discharge_coefficient is not None:
            if not (0 < discharge_coefficient < 1):
                raise ValueError(
                    f"discharge_coefficient must be in (0, 1), got {discharge_coefficient}"
                )
            self.Cd = discharge_coefficient
        else:
            # 根据堰型设置默认流量系数
            if weir_type == "sharp":
                self.Cd = 0.45  # 薄壁侧堰
            else:  # broad
                self.Cd = 0.35  # 宽顶侧堰

        # 重力加速度
        self.g = 9.81  # m/s²

    def compute_diversion(
        self,
        Q_inflow: float,
        h_upstream: float,
        n_segments: int = 20
    ) -> Dict[str, any]:
        """
        计算侧堰分流

        使用数值积分方法沿侧堰长度计算分流流量和水位变化。

        Args:
            Q_inflow: 主渠进口流量 (m³/s)
            h_upstream: 上游水位高程 (m)
            n_segments: 计算分段数，默认 20

        Returns:
            字典，包含：
            - 'Q_diverted': 分流流量 (m³/s)
            - 'Q_downstream': 下游剩余流量 (m³/s)
            - 'diversion_ratio': 分流比 (0-1)
            - 'h_downstream': 下游水位高程 (m)
            - 'water_depth_drop': 水深降落 (m)
            - 'profile': 沿程剖面数据列表，每个元素包含 {'x', 'h', 'Q', 'q'}

        Raises:
            ValueError: 上游水位低于堰顶时抛出异常
        """
        if h_upstream < self.z_crest:
            raise ValueError(
                f"Upstream water level ({h_upstream:.2f} m) is below "
                f"weir crest ({self.z_crest:.2f} m). No overflow occurs."
            )

        # 沿程计算
        dx = self.L / n_segments
        x_values = np.linspace(0, self.L, n_segments + 1)

        # 初始化
        Q = Q_inflow
        h = h_upstream
        Q_diverted_total = 0.0

        # 存储沿程剖面
        profile = []
        profile.append({
            'x': 0.0,
            'h': h,
            'Q': Q,
            'q': 0.0  # 单宽溢流流量
        })

        # 沿侧堰长度积分
        for i in range(n_segments):
            x = x_values[i]

            # 当前段的堰顶水头
            if h > self.z_crest:
                H = h - self.z_crest
            else:
                H = 0.0

            # De Marchi 公式：单位长度分流流量
            # dQ/dx = -Cd * √(2g) * H^(3/2)
            if H > 0:
                dQ_dx = -self.Cd * np.sqrt(2 * self.g) * (H ** 1.5)
            else:
                dQ_dx = 0.0

            # 当前段分流流量
            dQ = dQ_dx * dx
            Q_diverted_segment = -dQ  # 负号表示从主渠流出

            # 更新主渠流量
            Q_new = Q + dQ  # dQ 是负值
            Q_new = max(Q_new, 0.0)  # 确保非负

            # 累计分流流量
            Q_diverted_total += Q_diverted_segment

            # 计算新水位（基于 Manning 方程）
            if Q_new > 0 and self.S0 > 0:
                # 均匀流公式：Q = (1/n) * A * R^(2/3) * √S0
                # 矩形渠道：A = B*h, R = B*h/(B+2*h)
                # 简化迭代求解水深
                h_new = self._compute_normal_depth(Q_new)
            else:
                h_new = self.z_crest  # 流量为0时，水位降至堰顶

            # 记录当前段数据
            q = Q_diverted_segment / dx if dx > 0 else 0.0
            profile.append({
                'x': x + dx,
                'h': h_new,
                'Q': Q_new,
                'q': q
            })

            # 更新到下一段
            Q = Q_new
            h = h_new

        # 下游流量和水位
        Q_downstream = Q
        h_downstream = h

        # 分流比
        diversion_ratio = Q_diverted_total / Q_inflow if Q_inflow > 0 else 0.0

        # 水深降落
        water_depth_drop = h_upstream - h_downstream

        return {
            'Q_diverted': Q_diverted_total,
            'Q_downstream': Q_downstream,
            'diversion_ratio': diversion_ratio,
            'h_downstream': h_downstream,
            'water_depth_drop': water_depth_drop,
            'profile': profile
        }

    def _compute_normal_depth(
        self,
        Q: float,
        tol: float = 1e-4,
        max_iter: int = 50
    ) -> float:
        """
        计算矩形渠道均匀流水深（Manning 公式）

        Args:
            Q: 流量 (m³/s)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数

        Returns:
            均匀流水深 (m)
        """
        if Q <= 0:
            return 0.0

        # 初始猜测：基于宽矩形渠道 h ≈ (Qn / (B√S0))^(3/5)
        if self.S0 > 0:
            h_guess = (Q * self.n / (self.B * np.sqrt(self.S0))) ** (3/5)
        else:
            h_guess = 1.0

        for iteration in range(max_iter):
            # Manning 公式
            A = self.B * h_guess
            P = self.B + 2 * h_guess
            R = A / P

            Q_computed = (1.0 / self.n) * A * (R ** (2/3)) * np.sqrt(self.S0)

            residual = Q_computed - Q

            if abs(residual) < tol:
                return h_guess

            # 数值导数
            dh = max(1e-4, h_guess * 1e-6)
            A_perturbed = self.B * (h_guess + dh)
            P_perturbed = self.B + 2 * (h_guess + dh)
            R_perturbed = A_perturbed / P_perturbed
            Q_perturbed = (1.0 / self.n) * A_perturbed * (R_perturbed ** (2/3)) * np.sqrt(self.S0)

            dQ_dh = (Q_perturbed - Q_computed) / dh

            if abs(dQ_dh) > 1e-10:
                # 牛顿迭代
                delta_h = -residual / dQ_dh
                delta_h = np.clip(delta_h, -0.5, 0.5)
                h_guess += delta_h
            else:
                # 比例调整
                h_guess *= 1.1

            # 确保非负
            h_guess = max(h_guess, 0.01)

        # 返回最后估计值
        return h_guess

    def compute_required_length(
        self,
        Q_inflow: float,
        h_upstream: float,
        target_diversion_ratio: float,
        tol: float = 0.01,
        max_iter: int = 50
    ) -> float:
        """
        计算达到目标分流比所需的侧堰长度

        Args:
            Q_inflow: 主渠进口流量 (m³/s)
            h_upstream: 上游水位高程 (m)
            target_diversion_ratio: 目标分流比 (0-1)
            tol: 收敛容差
            max_iter: 最大迭代次数

        Returns:
            所需侧堰长度 (m)

        Raises:
            ValueError: 目标分流比不合理或迭代不收敛时抛出异常
        """
        if not (0 < target_diversion_ratio <= 1):
            raise ValueError(
                f"target_diversion_ratio must be in (0, 1], got {target_diversion_ratio}"
            )

        # 保存原始长度
        original_length = self.L

        # 初始猜测：线性估计
        L_guess = original_length * target_diversion_ratio

        for iteration in range(max_iter):
            # 临时设置长度
            self.L = L_guess

            # 计算分流比
            result = self.compute_diversion(Q_inflow, h_upstream)
            ratio_computed = result['diversion_ratio']

            residual = ratio_computed - target_diversion_ratio

            if abs(residual) < tol:
                # 恢复原始长度
                self.L = original_length
                return L_guess

            # 数值导数
            dL = max(1.0, L_guess * 0.05)
            self.L = L_guess + dL
            result_perturbed = self.compute_diversion(Q_inflow, h_upstream)
            ratio_perturbed = result_perturbed['diversion_ratio']

            dratio_dL = (ratio_perturbed - ratio_computed) / dL

            if abs(dratio_dL) > 1e-10:
                # 牛顿迭代
                delta_L = -residual / dratio_dL
                delta_L = np.clip(delta_L, -L_guess * 0.5, L_guess * 2.0)
                L_guess += delta_L
            else:
                # 比例调整
                if ratio_computed < target_diversion_ratio:
                    L_guess *= 1.2
                else:
                    L_guess *= 0.8

            # 确保长度合理
            L_guess = max(L_guess, 1.0)

        # 恢复原始长度
        self.L = original_length

        raise ValueError(
            f"Required length calculation did not converge after {max_iter} iterations. "
            f"Target ratio = {target_diversion_ratio:.2%}, "
            f"last computed ratio = {ratio_computed:.2%}"
        )

    def compute_submergence_effect(
        self,
        Q_inflow: float,
        h_upstream: float,
        h_downstream_channel: float
    ) -> Dict[str, float]:
        """
        计算下游淹没对侧堰分流的影响

        当侧渠水位较高时，会影响侧堰溢流能力。

        Args:
            Q_inflow: 主渠进口流量 (m³/s)
            h_upstream: 上游水位高程 (m)
            h_downstream_channel: 侧渠水位高程 (m)

        Returns:
            字典，包含：
            - 'Q_diverted_free': 自由溢流时的分流流量 (m³/s)
            - 'Q_diverted_submerged': 淹没条件下的分流流量 (m³/s)
            - 'submergence_ratio': 淹没比 h_downstream / h_upstream
            - 'reduction_factor': 流量折减系数 (0-1)
        """
        # 计算自由溢流流量
        result_free = self.compute_diversion(Q_inflow, h_upstream)
        Q_diverted_free = result_free['Q_diverted']

        # 计算淹没比
        if h_upstream > self.z_crest:
            submergence_ratio = (h_downstream_channel - self.z_crest) / (h_upstream - self.z_crest)
            submergence_ratio = max(0.0, min(submergence_ratio, 1.0))
        else:
            submergence_ratio = 0.0

        # 淹没修正系数（经验公式）
        # 当 submergence_ratio < 0.7 时，影响较小
        # 当 submergence_ratio > 0.7 时，流量显著减小
        if submergence_ratio < 0.7:
            reduction_factor = 1.0 - 0.1 * submergence_ratio
        else:
            reduction_factor = 1.0 - 0.07 - 0.75 * (submergence_ratio - 0.7)

        reduction_factor = max(0.0, min(reduction_factor, 1.0))

        # 淹没条件下的分流流量
        Q_diverted_submerged = Q_diverted_free * reduction_factor

        return {
            'Q_diverted_free': Q_diverted_free,
            'Q_diverted_submerged': Q_diverted_submerged,
            'submergence_ratio': submergence_ratio,
            'reduction_factor': reduction_factor
        }

    def properties(self) -> Dict[str, float]:
        """
        返回侧堰几何属性

        Returns:
            字典，包含侧堰几何参数
        """
        return {
            'length': self.L,
            'crest_elevation': self.z_crest,
            'channel_width': self.B,
            'channel_slope': self.S0,
            'manning_n': self.n,
            'discharge_coefficient': self.Cd,
            'weir_type': self.weir_type
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"SideWeir(id='{self.weir_id}', "
            f"L={self.L:.1f}m, "
            f"z_crest={self.z_crest:.2f}m, "
            f"Cd={self.Cd:.3f}, "
            f"type='{self.weir_type}')"
        )


def create_side_weir(
    weir_id: str,
    length: float,
    crest_elevation: float,
    channel_width: float,
    channel_slope: float,
    **kwargs
) -> SideWeir:
    """
    便捷函数：创建侧堰对象

    Args:
        weir_id: 侧堰标识
        length: 侧堰长度 (m)
        crest_elevation: 堰顶高程 (m)
        channel_width: 主渠宽度 (m)
        channel_slope: 主渠底坡
        **kwargs: 其他可选参数

    Returns:
        SideWeir 对象

    Example:
        >>> side_weir = create_side_weir(
        ...     weir_id="SW001",
        ...     length=50.0,
        ...     crest_elevation=102.0,
        ...     channel_width=5.0,
        ...     channel_slope=0.001,
        ...     weir_type="sharp"
        ... )
    """
    return SideWeir(
        weir_id=weir_id,
        length=length,
        crest_elevation=crest_elevation,
        channel_width=channel_width,
        channel_slope=channel_slope,
        **kwargs
    )
