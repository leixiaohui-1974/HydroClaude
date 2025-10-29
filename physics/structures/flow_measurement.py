"""
流量测量设施（Flow Measurement Structures）

实现标准流量测量设备的水力计算：
- 矩形堰（Rectangular Weir）
- 三角堰（Triangular/V-notch Weir）
- 巴歇尔槽（Parshall Flume）

理论基础：
- 基于标准堰流公式和经验关系
- 参考 ISO 1438 (Thin-plate weirs)
- 参考 USBR (1997) Water Measurement Manual
- 参考 ASTM D5390 (Parshall Flume)

Author: HydroClaude Development Team
Date: 2025-01
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np


# ============================================================================
# 矩形堰（Rectangular Weir）
# ============================================================================

@dataclass
class RectangularWeirGeometry:
    """
    矩形堰几何参数

    Attributes
    ----------
    position : float
        堰位置 (m)
    crest_width : float
        堰口宽度 (m)
    crest_elevation : float
        堰顶高程 (m)
    channel_width : float
        渠道宽度 (m)，用于判断是否为全宽堰
    weir_height : float
        堰高 (m)，堰顶距离渠底的高度
    """
    position: float
    crest_width: float
    crest_elevation: float = 0.0
    channel_width: Optional[float] = None
    weir_height: float = 1.0

    def __post_init__(self):
        """验证参数"""
        if self.crest_width <= 0:
            raise ValueError("Crest width must be positive")
        if self.weir_height < 0:
            raise ValueError("Weir height must be non-negative")
        if self.channel_width is not None and self.crest_width > self.channel_width:
            raise ValueError("Crest width cannot exceed channel width")


class RectangularWeir:
    """
    矩形堰流量计算

    实现标准矩形锐缘堰流量公式（Rehbock公式）

    Parameters
    ----------
    geometry : RectangularWeirGeometry
        堰几何参数
    discharge_coef : float, optional
        流量系数（默认 0.42，标准锐缘堰）

    Notes
    -----
    标准Rehbock公式（全宽堰）：
        Q = (2/3) * Cd * b * √(2g) * h^(3/2)

    简化形式：
        Q = Cd * b * √(2g) * h^(3/2)
        其中 Cd ≈ 0.40-0.42

    收缩矩形堰（Francis公式）：
        Q = Cd * (b - 0.1*n*h) * √(2g) * h^(3/2)
        其中 n 为端收缩数（1或2）
    """

    def __init__(self,
                 geometry: RectangularWeirGeometry,
                 discharge_coef: float = 0.42):
        self.geom = geometry
        self.Cd = discharge_coef
        self.g = 9.81  # 重力加速度 (m/s²)

    def compute_discharge(self, h: float) -> float:
        """
        计算通过矩形堰的流量

        Parameters
        ----------
        h : float
            堰顶水头 (m)，相对于堰顶

        Returns
        -------
        Q : float
            流量 (m³/s)

        Examples
        --------
        >>> weir = RectangularWeir(RectangularWeirGeometry(
        ...     position=100.0,
        ...     crest_width=2.0,
        ...     crest_elevation=1.0
        ... ))
        >>> Q = weir.compute_discharge(h=0.5)
        >>> print(f"Discharge: {Q:.3f} m³/s")
        """
        if h <= 0:
            return 0.0

        # 判断是否为全宽堰或收缩堰
        if self.geom.channel_width is None:
            # 假设为全宽堰
            b_effective = self.geom.crest_width
        else:
            # 收缩堰 - 使用Francis公式修正
            # 端收缩数：如果两侧都收缩则n=2，否则n=1
            if self.geom.crest_width < self.geom.channel_width * 0.95:
                # 有收缩
                n_contractions = 2
                # Francis修正：有效宽度减小
                b_effective = self.geom.crest_width - 0.1 * n_contractions * h
            else:
                # 全宽堰
                b_effective = self.geom.crest_width

        b_effective = max(b_effective, 0.1)  # 确保有效宽度为正

        # 标准堰流公式
        Q = self.Cd * b_effective * np.sqrt(2 * self.g) * (h ** 1.5)

        return Q

    def compute_head(self, Q: float, tolerance: float = 0.001) -> float:
        """
        反算水头（给定流量）

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        tolerance : float
            收敛容差 (m)

        Returns
        -------
        h : float
            堰顶水头 (m)

        Notes
        -----
        使用迭代法求解非线性方程
        """
        if Q <= 0:
            return 0.0

        # 初始猜测：基于简化公式 Q = C * b * h^1.5
        h_guess = (Q / (self.Cd * self.geom.crest_width * np.sqrt(2 * self.g))) ** (2.0 / 3.0)

        # Newton迭代
        for _ in range(50):
            Q_calc = self.compute_discharge(h_guess)
            error = Q_calc - Q

            if abs(error) < tolerance * Q:
                return h_guess

            # 数值导数
            dh = 0.001
            Q_perturb = self.compute_discharge(h_guess + dh)
            dQ_dh = (Q_perturb - Q_calc) / dh

            if abs(dQ_dh) > 1e-10:
                h_guess -= error / dQ_dh
                h_guess = max(h_guess, 0.001)  # 确保为正
            else:
                break

        return h_guess


# ============================================================================
# 三角堰（Triangular/V-notch Weir）
# ============================================================================

@dataclass
class TriangularWeirGeometry:
    """
    三角堰几何参数

    Attributes
    ----------
    position : float
        堰位置 (m)
    notch_angle : float
        V形缺口角度 (度)，常用 90°
    crest_elevation : float
        堰顶高程 (m)，即V形顶点高程
    """
    position: float
    notch_angle: float = 90.0
    crest_elevation: float = 0.0

    def __post_init__(self):
        """验证参数"""
        if not (10 <= self.notch_angle <= 120):
            raise ValueError("Notch angle must be between 10° and 120°")


class TriangularWeir:
    """
    三角堰（V型堰）流量计算

    实现标准三角堰流量公式（Thomson公式）

    Parameters
    ----------
    geometry : TriangularWeirGeometry
        堰几何参数
    discharge_coef : float, optional
        流量系数（默认 0.58，标准90°锐缘三角堰）

    Notes
    -----
    Thomson公式（90°三角堰）：
        Q = (8/15) * Cd * tan(θ/2) * √(2g) * h^(5/2)

    对于90°堰（θ=90°），tan(45°) = 1：
        Q = (8/15) * Cd * √(2g) * h^(5/2)
        Q ≈ 1.4 * Cd * h^(5/2)  [当Cd=0.58时]
        Q ≈ 1.38 * h^(2.5)

    特点：
        - 适用于小流量测量（Q < 300 L/s）
        - 精度高，对低水头敏感
        - h^(5/2) 关系使小流量测量更准确
    """

    def __init__(self,
                 geometry: TriangularWeirGeometry,
                 discharge_coef: float = 0.58):
        self.geom = geometry
        self.Cd = discharge_coef
        self.g = 9.81  # 重力加速度 (m/s²)

    def compute_discharge(self, h: float) -> float:
        """
        计算通过三角堰的流量

        Parameters
        ----------
        h : float
            堰顶水头 (m)，相对于V形顶点

        Returns
        -------
        Q : float
            流量 (m³/s)

        Examples
        --------
        >>> weir = TriangularWeir(TriangularWeirGeometry(
        ...     position=100.0,
        ...     notch_angle=90.0
        ... ))
        >>> Q = weir.compute_discharge(h=0.2)
        >>> print(f"Discharge: {Q:.4f} m³/s")
        """
        if h <= 0:
            return 0.0

        # Thomson公式
        theta_rad = np.deg2rad(self.geom.notch_angle)
        Q = (8.0 / 15.0) * self.Cd * np.tan(theta_rad / 2.0) * \
            np.sqrt(2 * self.g) * (h ** 2.5)

        return Q

    def compute_head(self, Q: float, tolerance: float = 0.0001) -> float:
        """
        反算水头（给定流量）

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        tolerance : float
            收敛容差 (m)

        Returns
        -------
        h : float
            堰顶水头 (m)
        """
        if Q <= 0:
            return 0.0

        # 从Thomson公式直接反算
        # Q = K * h^2.5, 其中 K = (8/15) * Cd * tan(θ/2) * √(2g)
        theta_rad = np.deg2rad(self.geom.notch_angle)
        K = (8.0 / 15.0) * self.Cd * np.tan(theta_rad / 2.0) * np.sqrt(2 * self.g)

        h = (Q / K) ** (1.0 / 2.5)

        return h


# ============================================================================
# 巴歇尔槽（Parshall Flume）
# ============================================================================

@dataclass
class ParshallFlumeGeometry:
    """
    巴歇尔槽几何参数

    Attributes
    ----------
    position : float
        量水槽位置 (m)
    throat_width : float
        喉道宽度 (ft 或 m)，标准尺寸：1", 3", 6", 9", 1'-8'
    crest_elevation : float
        槽底高程 (m)
    units : str
        单位系统：'SI' (m, m³/s) 或 'Imperial' (ft, ft³/s)
    """
    position: float
    throat_width: float
    crest_elevation: float = 0.0
    units: str = 'SI'  # 'SI' or 'Imperial'

    def __post_init__(self):
        """验证参数"""
        if self.throat_width <= 0:
            raise ValueError("Throat width must be positive")
        if self.units not in ['SI', 'Imperial']:
            raise ValueError("Units must be 'SI' or 'Imperial'")


class ParshallFlume:
    """
    巴歇尔槽流量计算

    实现标准巴歇尔槽流量公式（USBR标准）

    Parameters
    ----------
    geometry : ParshallFlumeGeometry
        巴歇尔槽几何参数

    Notes
    -----
    自由流条件下的流量公式：
        Q = C * W^x * H^n

    其中：
        - Q: 流量 (ft³/s 或 m³/s)
        - W: 喉道宽度 (ft 或 m)
        - H: 上游水头 (ft 或 m)，在喉道上游2/3收缩段长度处测量
        - C, x, n: 经验系数，取决于喉道宽度

    标准系数（Imperial单位，ft-ft³/s）：
        - W = 1-8 ft: C = 4.0, x = 0, n = 1.522 (对小型槽)
        - W = 1 ft:   Q = 4.0 * W * H^1.522 = 4.0 * H^1.522
        - W = 2 ft:   Q = 4.0 * W * H^1.538 = 8.0 * H^1.538

    淹没条件：
        - 当下游水位过高时，需要修正
        - 淹没度 S = Hb/Ha (下游水头/上游水头)
        - 自由流: S < 0.6-0.7
        - 淹没流: S >= 0.7，需要使用修正公式
    """

    # 标准巴歇尔槽系数表（Imperial单位）
    # 格式：{throat_width_ft: (C, x, n)}
    _standard_coefficients_imperial = {
        0.25: (2.06, 0, 1.55),   # 3" throat
        0.5: (2.4, 0, 1.55),     # 6" throat
        0.75: (3.07, 0, 1.55),   # 9" throat
        1.0: (4.0, 0, 1.522),    # 1 ft throat
        1.5: (6.0, 0, 1.538),    # 1.5 ft
        2.0: (8.0, 0, 1.550),    # 2 ft
        3.0: (12.0, 0, 1.566),   # 3 ft
        4.0: (16.0, 0, 1.578),   # 4 ft
        5.0: (20.0, 0, 1.587),   # 5 ft
        6.0: (24.0, 0, 1.595),   # 6 ft
        7.0: (28.0, 0, 1.601),   # 7 ft
        8.0: (32.0, 0, 1.607),   # 8 ft
    }

    def __init__(self, geometry: ParshallFlumeGeometry):
        self.geom = geometry
        self.g = 9.81  # 重力加速度 (m/s²)

        # 获取流量系数
        self._set_coefficients()

    def _set_coefficients(self):
        """设置流量系数"""
        W = self.geom.throat_width

        if self.geom.units == 'Imperial':
            # 使用Imperial单位系数
            # 查找最接近的标准尺寸
            standard_widths = list(self._standard_coefficients_imperial.keys())
            closest_width = min(standard_widths, key=lambda x: abs(x - W))

            if abs(W - closest_width) > 0.1:
                # 警告：非标准尺寸
                pass

            self.C, self.x, self.n = self._standard_coefficients_imperial[closest_width]

        else:  # SI units
            # SI单位（m, m³/s）：使用通用公式 Q = C * W^x * H^n
            # 基于Imperial公式转换，考虑单位换算
            # 对于小型槽（W < 3 m），典型系数：
            if W < 0.3:
                self.C = 2.2
                self.x = 1.0  # 线性关系
                self.n = 1.55
            elif W < 1.0:
                self.C = 2.25
                self.x = 1.0
                self.n = 1.56
            else:
                self.C = 2.3
                self.x = 1.0
                self.n = 1.60

    def compute_discharge(self, H_upstream: float) -> Tuple[float, str]:
        """
        计算通过巴歇尔槽的流量

        Parameters
        ----------
        H_upstream : float
            上游水头 (m 或 ft)，在标准测量位置

        Returns
        -------
        Q : float
            流量 (m³/s 或 ft³/s)
        flow_condition : str
            'free' (自由流) 或 'submerged' (淹没流)

        Notes
        -----
        此方法仅计算自由流条件下的流量。
        淹没流条件需要额外的下游水头测量。

        Examples
        --------
        >>> flume = ParshallFlume(ParshallFlumeGeometry(
        ...     position=100.0,
        ...     throat_width=1.0,  # 1 ft
        ...     units='Imperial'
        ... ))
        >>> Q, condition = flume.compute_discharge(H_upstream=0.5)
        >>> print(f"Discharge: {Q:.3f} ft³/s, Condition: {condition}")
        """
        if H_upstream <= 0:
            return 0.0, 'free'

        # 自由流流量公式
        W = self.geom.throat_width
        Q = self.C * (W ** self.x) * (H_upstream ** self.n)

        return Q, 'free'

    def compute_head(self, Q: float, tolerance: float = 0.001) -> float:
        """
        反算上游水头（给定流量）

        Parameters
        ----------
        Q : float
            流量 (m³/s 或 ft³/s)
        tolerance : float
            收敛容差

        Returns
        -------
        H : float
            上游水头 (m 或 ft)
        """
        if Q <= 0:
            return 0.0

        # 从流量公式直接反算
        # Q = C * W^x * H^n
        # H = (Q / (C * W^x))^(1/n)
        W = self.geom.throat_width
        K = self.C * (W ** self.x)
        H = (Q / K) ** (1.0 / self.n)

        return H

    def check_submergence(self, H_upstream: float, H_downstream: float) -> Tuple[float, bool]:
        """
        检查淹没条件

        Parameters
        ----------
        H_upstream : float
            上游水头 (m 或 ft)
        H_downstream : float
            下游水头 (m 或 ft)，在喉道末端测量

        Returns
        -------
        submergence : float
            淹没度 S = Hb/Ha
        is_submerged : bool
            是否淹没

        Notes
        -----
        自由流临界淹没度：
            - 1-3" 喉道: S_c = 0.50
            - 6-9" 喉道: S_c = 0.60
            - 1-8 ft 喉道: S_c = 0.70
        """
        if H_upstream <= 0:
            return 0.0, False

        S = H_downstream / H_upstream

        # 临界淹没度（根据喉道宽度）
        W = self.geom.throat_width
        if self.geom.units == 'Imperial':
            if W <= 0.75:  # <= 9"
                S_critical = 0.60
            else:
                S_critical = 0.70
        else:  # SI
            if W <= 0.23:  # ≈ 9"
                S_critical = 0.60
            else:
                S_critical = 0.70

        is_submerged = (S >= S_critical)

        return S, is_submerged


# ============================================================================
# 便捷函数
# ============================================================================

def create_rectangular_weir(position: float,
                           crest_width: float,
                           crest_elevation: float = 0.0,
                           channel_width: Optional[float] = None) -> RectangularWeir:
    """创建矩形堰"""
    geometry = RectangularWeirGeometry(
        position=position,
        crest_width=crest_width,
        crest_elevation=crest_elevation,
        channel_width=channel_width
    )
    return RectangularWeir(geometry)


def create_triangular_weir(position: float,
                          notch_angle: float = 90.0,
                          crest_elevation: float = 0.0) -> TriangularWeir:
    """创建三角堰（默认90°）"""
    geometry = TriangularWeirGeometry(
        position=position,
        notch_angle=notch_angle,
        crest_elevation=crest_elevation
    )
    return TriangularWeir(geometry)


def create_parshall_flume(position: float,
                         throat_width: float,
                         crest_elevation: float = 0.0,
                         units: str = 'SI') -> ParshallFlume:
    """创建巴歇尔槽"""
    geometry = ParshallFlumeGeometry(
        position=position,
        throat_width=throat_width,
        crest_elevation=crest_elevation,
        units=units
    )
    return ParshallFlume(geometry)
