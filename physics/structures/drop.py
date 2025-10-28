"""
跌水结构（Drop Structure）水力计算模块

实现渠道跌水的水力计算，包括：
- 自由跌水流量计算
- 淹没跌水流量计算
- 跌水后水深计算
- 能量消散计算

理论基础：
- 基于临界流和能量方程
- 参考 Chow (1959) Open Channel Hydraulics
- USBR (1997) Water Measurement Manual

Author: HydroClaude Development Team
Date: 2025-01
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np


@dataclass
class DropGeometry:
    """
    跌水几何参数

    Attributes
    ----------
    position : float
        跌水位置 (m)
    width : float
        跌水堰宽 (m)
    drop_height : float
        跌水高度 (m)
    crest_elevation : float
        堰顶高程 (m)
    shape : str
        跌水形式：'sharp' (锐缘), 'broad' (宽顶), 'ogee' (曲线)
    """
    position: float
    width: float
    drop_height: float
    crest_elevation: float = 0.0
    shape: str = 'sharp'  # 'sharp', 'broad', 'ogee'

    def __post_init__(self):
        """验证参数"""
        if self.width <= 0:
            raise ValueError("Drop width must be positive")
        if self.drop_height < 0:
            raise ValueError("Drop height must be non-negative")
        if self.shape not in ['sharp', 'broad', 'ogee']:
            raise ValueError("Shape must be 'sharp', 'broad', or 'ogee'")


class Drop:
    """
    跌水结构水力计算

    支持自由跌水和淹没跌水两种流态的计算。

    Parameters
    ----------
    geometry : DropGeometry
        跌水几何参数
    discharge_coef : float, optional
        流量系数 (默认根据跌水类型自动选择)
        - 锐缘跌水: 0.40
        - 宽顶跌水: 0.55
        - 曲线跌水: 0.48

    Notes
    -----
    自由跌水流量公式：
        Q = Cd * b * h^(3/2) * √(2g)

    其中：
        - Cd: 流量系数
        - b: 堰宽
        - h: 堰顶水头
        - g: 重力加速度

    淹没判别：
        - 淹没度 S = (h_下游 - 堰底) / (h_上游 - 堰底)
        - S < 0.67: 自由流
        - S >= 0.67: 淹没流
    """

    def __init__(self,
                 geometry: DropGeometry,
                 discharge_coef: Optional[float] = None):
        self.geom = geometry
        self.g = 9.81  # 重力加速度 (m/s²)

        # 流量系数（根据跌水类型）
        if discharge_coef is not None:
            self.Cd = discharge_coef
        else:
            self._discharge_coefficients = {
                'sharp': 0.40,   # 锐缘跌水
                'broad': 0.55,   # 宽顶堰
                'ogee': 0.48     # 曲线堰（溢流堰）
            }
            self.Cd = self._discharge_coefficients.get(geometry.shape, 0.45)

    def compute_discharge(self,
                         h_upstream: float,
                         h_downstream: float) -> Tuple[float, str]:
        """
        计算通过跌水的流量

        Parameters
        ----------
        h_upstream : float
            上游水深 (m，相对于堰顶高程)
        h_downstream : float
            下游水深 (m，相对于跌水后河底高程)

        Returns
        -------
        Q : float
            流量 (m³/s)
        flow_type : str
            'free' (自由流) 或 'submerged' (淹没流)

        Examples
        --------
        >>> drop = Drop(DropGeometry(
        ...     position=100.0,
        ...     width=5.0,
        ...     drop_height=2.0,
        ...     crest_elevation=10.0
        ... ))
        >>> Q, flow_type = drop.compute_discharge(h_upstream=1.5, h_downstream=0.8)
        >>> print(f"Flow: {Q:.2f} m³/s, Type: {flow_type}")
        """
        # 计算堰顶水头
        H = h_upstream  # 相对于堰顶

        if H <= 0:
            return 0.0, 'free'

        # 判断是否淹没
        # 淹没度定义：下游水位相对于上游水头的比例
        # 考虑跌水高度
        downstream_elevation = h_downstream  # 下游水深
        upstream_head = H

        # 淹没判别：如果下游水位超过跌水后临界水深的某个倍数
        # 简化判别：S = h_d / (H + Z) 其中Z为跌水高度
        submergence = downstream_elevation / (upstream_head + self.geom.drop_height)

        if submergence < 0.67:
            # 自由流
            Q = self._compute_free_flow(H)
            return Q, 'free'
        else:
            # 淹没流
            Q = self._compute_submerged_flow(H, h_downstream)
            return Q, 'submerged'

    def _compute_free_flow(self, H: float) -> float:
        """
        自由流流量计算

        使用标准堰流公式：
        Q = Cd * b * H^(3/2) * √(2g)

        Parameters
        ----------
        H : float
            堰顶水头 (m)

        Returns
        -------
        Q : float
            流量 (m³/s)
        """
        # 标准堰流公式
        Q = self.Cd * self.geom.width * (H ** 1.5) * np.sqrt(2 * self.g)
        return Q

    def _compute_submerged_flow(self,
                                H_upstream: float,
                                h_downstream: float) -> float:
        """
        淹没流流量计算

        使用修正的淹没堰流公式：
        Q = Cd' * b * H^(3/2) * √(2g)

        其中 Cd' = Cd * (1 - S)^0.385
        S 为淹没度

        Parameters
        ----------
        H_upstream : float
            上游堰顶水头 (m)
        h_downstream : float
            下游水深 (m)

        Returns
        -------
        Q : float
            流量 (m³/s)
        """
        # 计算淹没度
        total_head_upstream = H_upstream + self.geom.drop_height
        S = h_downstream / total_head_upstream
        S = min(S, 0.95)  # 限制最大淹没度

        # 淹没修正系数（Villemonte公式）
        Cd_submerged = self.Cd * ((1 - S) ** 0.385)

        # 计算流量
        Q = Cd_submerged * self.geom.width * (H_upstream ** 1.5) * np.sqrt(2 * self.g)

        return Q

    def compute_tailwater_depth(self,
                               Q: float,
                               h_upstream: float) -> float:
        """
        计算跌水后的尾水深度

        使用能量方程和经验公式估算跌水后的水深。

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        h_upstream : float
            上游堰顶水头 (m)

        Returns
        -------
        h_tailwater : float
            跌水后水深 (m)

        Notes
        -----
        基于能量守恒和水跃理论：
        1. 跌水后形成急流
        2. 可能发生水跃
        3. 水深由共轭水深关系确定
        """
        # 跌水后的单宽流量
        q = Q / self.geom.width

        # 跌水底部的临界水深
        # hc = (q²/g)^(1/3)
        h_critical = (q ** 2 / self.g) ** (1.0 / 3.0)

        # 跌水后的急流水深（经验公式）
        # 假设跌水后水深约为临界水深的0.7倍
        h_supercritical = 0.7 * h_critical

        # 如果发生水跃，计算共轭水深
        Fr_super = q / (h_supercritical * np.sqrt(self.g * h_supercritical))

        if Fr_super > 1.7:
            # 发生水跃，计算共轭水深（Belanger方程）
            h_tailwater = (h_supercritical / 2) * (
                np.sqrt(1 + 8 * Fr_super ** 2) - 1
            )
        else:
            # 未发生水跃或弱水跃
            h_tailwater = h_supercritical

        return h_tailwater

    def compute_energy_dissipation(self,
                                   Q: float,
                                   h_upstream: float,
                                   h_downstream: float) -> float:
        """
        计算能量消散

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        h_upstream : float
            上游堰顶水头 (m)
        h_downstream : float
            下游水深 (m)

        Returns
        -------
        E_loss : float
            能量损失 (m，水头形式)

        Notes
        -----
        能量损失 = E_上游 - E_下游
        其中 E = h + V²/(2g) + Z
        """
        # 上游能量
        A_upstream = self.geom.width * h_upstream
        V_upstream = Q / A_upstream if A_upstream > 0 else 0.0
        E_upstream = h_upstream + V_upstream ** 2 / (2 * self.g) + self.geom.crest_elevation

        # 下游能量（相对于跌水后河底）
        A_downstream = self.geom.width * h_downstream
        V_downstream = Q / A_downstream if A_downstream > 0 else 0.0
        # 下游河底高程 = 堰顶高程 - 跌水高度
        downstream_bed_elevation = self.geom.crest_elevation - self.geom.drop_height
        E_downstream = h_downstream + V_downstream ** 2 / (2 * self.g) + downstream_bed_elevation

        # 能量损失
        E_loss = E_upstream - E_downstream

        return max(E_loss, 0.0)

    def compute_critical_depth(self, Q: float) -> float:
        """
        计算临界水深

        Parameters
        ----------
        Q : float
            流量 (m³/s)

        Returns
        -------
        h_critical : float
            临界水深 (m)

        Notes
        -----
        对于矩形渠道：hc = (q²/g)^(1/3)
        """
        q = Q / self.geom.width
        h_critical = (q ** 2 / self.g) ** (1.0 / 3.0)
        return h_critical

    def compute_head_loss(self,
                         Q: float,
                         h_upstream: float,
                         h_downstream: float) -> float:
        """
        计算水头损失（便捷方法，与compute_energy_dissipation相同）

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        h_upstream : float
            上游堰顶水头 (m)
        h_downstream : float
            下游水深 (m)

        Returns
        -------
        head_loss : float
            水头损失 (m)
        """
        return self.compute_energy_dissipation(Q, h_upstream, h_downstream)


# ============================================================================
# 便捷函数
# ============================================================================

def create_drop_structure(position: float,
                         width: float,
                         drop_height: float,
                         crest_elevation: float = 0.0,
                         shape: str = 'sharp') -> Drop:
    """
    创建标准跌水结构

    Parameters
    ----------
    position : float
        跌水位置 (m)
    width : float
        堰宽 (m)
    drop_height : float
        跌水高度 (m)
    crest_elevation : float
        堰顶高程 (m)
    shape : str
        跌水形式 ('sharp', 'broad', 'ogee')

    Returns
    -------
    Drop
        跌水对象

    Examples
    --------
    >>> drop = create_drop_structure(
    ...     position=100.0,
    ...     width=5.0,
    ...     drop_height=2.0,
    ...     shape='broad'
    ... )
    """
    geometry = DropGeometry(
        position=position,
        width=width,
        drop_height=drop_height,
        crest_elevation=crest_elevation,
        shape=shape
    )

    return Drop(geometry)
