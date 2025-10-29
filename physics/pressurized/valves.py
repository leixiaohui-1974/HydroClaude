"""
阀门水力计算模块（Valve Hydraulics）

实现有压管道系统中常用阀门的水力计算：
- 蝶阀（Butterfly Valve）
- 球阀（Ball Valve）
- 减压阀（Pressure Reducing Valve, PRV）

理论基础：
- 基于局部水头损失公式
- 阀门特性曲线（Cv值或K值）
- 参考 Crane TP-410 (Flow of Fluids)
- 参考 AWWA M11 (Steel Pipe Manual)

Author: HydroClaude Development Team
Date: 2025-01
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Callable
import numpy as np


# ============================================================================
# 蝶阀（Butterfly Valve）
# ============================================================================

@dataclass
class ButterflyValveGeometry:
    """
    蝶阀几何参数

    Attributes
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    disc_thickness : float
        蝶板厚度 (m)，影响全开阻力
    """
    position: float
    diameter: float
    disc_thickness: float = 0.05

    def __post_init__(self):
        """验证参数"""
        if self.diameter <= 0:
            raise ValueError("Diameter must be positive")
        if self.disc_thickness < 0:
            raise ValueError("Disc thickness must be non-negative")


class ButterflyValve:
    """
    蝶阀水力计算

    蝶阀通过旋转蝶板（0-90°）调节流量，具有体积小、操作轻便、
    成本低等优点，广泛应用于给排水、空调、消防等管道系统。

    Parameters
    ----------
    geometry : ButterflyValveGeometry
        阀门几何参数
    valve_type : str
        阀门类型：'standard' (标准型) 或 'high_performance' (高性能型)

    Notes
    -----
    水头损失公式：
        hL = Kv(θ) * V² / (2g)

    其中：
        - Kv(θ) 为损失系数，随开度θ变化
        - V 为管道流速 (m/s)
        - g 为重力加速度 (9.81 m/s²)

    损失系数经验公式（标准蝶阀）：
        θ ∈ [0°, 90°]
        - 全开（90°）: Kv = 0.2-0.5
        - 70°: Kv ≈ 1.0
        - 60°: Kv ≈ 2.5
        - 50°: Kv ≈ 6.0
        - 40°: Kv ≈ 15
        - 30°: Kv ≈ 50
        - < 30°: 急剧增加

    开度百分比定义：
        Opening% = θ / 90° * 100%
    """

    def __init__(self,
                 geometry: ButterflyValveGeometry,
                 valve_type: str = 'standard'):
        self.geom = geometry
        self.valve_type = valve_type
        self.g = 9.81  # m/s²

        # 当前开度（角度，0-90°）
        self._opening_angle = 90.0  # 初始全开

    def set_opening(self, opening_percent: float):
        """
        设置阀门开度

        Parameters
        ----------
        opening_percent : float
            开度百分比（0-100%）
            0% = 全闭，100% = 全开（90°）
        """
        if not (0 <= opening_percent <= 100):
            raise ValueError("Opening must be between 0 and 100%")

        self._opening_angle = opening_percent / 100.0 * 90.0

    def get_opening(self) -> float:
        """获取当前开度百分比"""
        return self._opening_angle / 90.0 * 100.0

    def get_loss_coefficient(self, opening_percent: Optional[float] = None) -> float:
        """
        计算损失系数 Kv

        Parameters
        ----------
        opening_percent : float, optional
            开度百分比。如为 None，使用当前开度

        Returns
        -------
        Kv : float
            损失系数（无量纲）

        Notes
        -----
        基于经验公式和制造商数据拟合：

        标准蝶阀：
            Kv = 0.25 + 500 * (1 - θ/90)^4
            在 θ=90° 时 Kv ≈ 0.25
            在 θ=30° 时 Kv ≈ 50

        高性能蝶阀（流线型蝶板）：
            Kv = 0.15 + 300 * (1 - θ/90)^4
            全开阻力更小
        """
        if opening_percent is None:
            opening_percent = self.get_opening()

        # 开度角度
        theta = opening_percent / 100.0 * 90.0  # 转换为角度

        # 归一化开度（0-1）
        theta_norm = theta / 90.0

        if self.valve_type == 'standard':
            # 标准蝶阀
            Kv_min = 0.25  # 全开时的最小阻力系数
            Kv_max_coef = 500
            exponent = 4
        else:  # high_performance
            # 高性能蝶阀
            Kv_min = 0.15
            Kv_max_coef = 300
            exponent = 4

        # 计算损失系数
        Kv = Kv_min + Kv_max_coef * ((1 - theta_norm) ** exponent)

        return Kv

    def compute_head_loss(self,
                         Q: float,
                         opening_percent: Optional[float] = None) -> float:
        """
        计算水头损失

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        opening_percent : float, optional
            开度百分比。如为 None，使用当前开度

        Returns
        -------
        hL : float
            水头损失 (m)

        Examples
        --------
        >>> valve = ButterflyValve(ButterflyValveGeometry(
        ...     position=100.0,
        ...     diameter=0.5
        ... ))
        >>> valve.set_opening(70.0)  # 70% 开度
        >>> hL = valve.compute_head_loss(Q=0.2)
        >>> print(f"Head loss: {hL:.3f} m")
        """
        # 管道面积
        A = np.pi * (self.geom.diameter / 2) ** 2

        # 流速
        if A > 0 and Q != 0:
            V = abs(Q) / A
        else:
            return 0.0

        # 损失系数
        Kv = self.get_loss_coefficient(opening_percent)

        # 水头损失
        hL = Kv * V ** 2 / (2 * self.g)

        return hL

    def compute_flow_coefficient(self, opening_percent: Optional[float] = None) -> float:
        """
        计算流量系数 Cv (US units: gpm/psi^0.5)

        Parameters
        ----------
        opening_percent : float, optional
            开度百分比

        Returns
        -------
        Cv : float
            流量系数 (US gallons per minute per psi^0.5)

        Notes
        -----
        Cv 与 Kv 的关系：
            Cv = 29.84 * D² / √Kv
            其中 D 为直径 (inches)
        """
        Kv = self.get_loss_coefficient(opening_percent)
        D_inches = self.geom.diameter * 39.37  # m to inches

        if Kv > 0:
            Cv = 29.84 * D_inches ** 2 / np.sqrt(Kv)
        else:
            Cv = 1e10  # 无穷大（无阻力）

        return Cv


# ============================================================================
# 球阀（Ball Valve）
# ============================================================================

@dataclass
class BallValveGeometry:
    """
    球阀几何参数

    Attributes
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    port_type : str
        通道类型：'full_port' (全通径) 或 'reduced_port' (缩径)
    """
    position: float
    diameter: float
    port_type: str = 'full_port'

    def __post_init__(self):
        """验证参数"""
        if self.diameter <= 0:
            raise ValueError("Diameter must be positive")
        if self.port_type not in ['full_port', 'reduced_port']:
            raise ValueError("Port type must be 'full_port' or 'reduced_port'")


class BallValve:
    """
    球阀水力计算

    球阀通过旋转球体（0-90°）实现快速启闭，具有密封性好、流阻小、
    启闭迅速等特点，常用于需要快速截断的场合。

    Parameters
    ----------
    geometry : BallValveGeometry
        阀门几何参数

    Notes
    -----
    特点：
        - 开关型阀门（通常只有全开/全闭两个位置）
        - 不适合用于流量调节（会产生气蚀和振动）
        - 全开时阻力极小（Kv ≈ 0.05-0.15）

    水头损失：
        hL = Kv * V² / (2g)

    损失系数：
        - 全通径球阀全开：Kv = 0.05
        - 缩径球阀全开：Kv = 0.15
        - 部分开启：不推荐使用（损失系数急剧增加）
    """

    def __init__(self, geometry: BallValveGeometry):
        self.geom = geometry
        self.g = 9.81

        # 阀门状态：True=开，False=闭
        self._is_open = True

    def open(self):
        """打开阀门"""
        self._is_open = True

    def close(self):
        """关闭阀门"""
        self._is_open = False

    def is_open(self) -> bool:
        """检查阀门是否打开"""
        return self._is_open

    def get_loss_coefficient(self) -> float:
        """
        获取损失系数

        Returns
        -------
        Kv : float
            损失系数
            - 全开：0.05 (full_port) 或 0.15 (reduced_port)
            - 全闭：∞ (实际返回一个很大的数)
        """
        if not self._is_open:
            return 1e10  # 闭合时极大阻力

        if self.geom.port_type == 'full_port':
            return 0.05  # 全通径，阻力极小
        else:  # reduced_port
            return 0.15  # 缩径，略大阻力

    def compute_head_loss(self, Q: float) -> float:
        """
        计算水头损失

        Parameters
        ----------
        Q : float
            流量 (m³/s)

        Returns
        -------
        hL : float
            水头损失 (m)

        Notes
        -----
        如果阀门关闭，返回极大的水头损失（模拟完全截断）
        """
        if not self._is_open:
            # 闭合状态，返回极大水头损失
            return 1e6  # 实际应该完全截断流量

        A = np.pi * (self.geom.diameter / 2) ** 2

        if A > 0 and Q != 0:
            V = abs(Q) / A
        else:
            return 0.0

        Kv = self.get_loss_coefficient()
        hL = Kv * V ** 2 / (2 * self.g)

        return hL


# ============================================================================
# 减压阀（Pressure Reducing Valve, PRV）
# ============================================================================

@dataclass
class PRVGeometry:
    """
    减压阀几何参数

    Attributes
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    """
    position: float
    diameter: float

    def __post_init__(self):
        """验证参数"""
        if self.diameter <= 0:
            raise ValueError("Diameter must be positive")


class PressureReducingValve:
    """
    减压阀（PRV）水力计算

    减压阀自动调节开度以维持下游压力恒定，常用于：
    - 供水管网分区减压
    - 保护下游设备免受高压
    - 维持下游恒定水头

    Parameters
    ----------
    geometry : PRVGeometry
        阀门几何参数
    target_pressure : float
        目标下游压力 (m 水头)，减压阀会自动调节以维持此压力

    Notes
    -----
    工作原理：
        1. 感知下游压力 P_down
        2. 与设定值 P_target 比较
        3. 自动调节开度使 P_down ≈ P_target

    水头损失：
        hL = P_upstream - P_target
        （假设减压阀能完美维持目标压力）

    限制条件：
        - P_upstream > P_target （必须有压差才能工作）
        - 流量不超过阀门容量
        - 下游压力波动在±5%以内
    """

    def __init__(self,
                 geometry: PRVGeometry,
                 target_pressure: float):
        self.geom = geometry
        self.target_pressure = target_pressure  # m 水头
        self.g = 9.81

        # 阀门状态
        self._is_active = True  # 减压阀是否激活

    def set_target_pressure(self, pressure: float):
        """
        设置目标压力

        Parameters
        ----------
        pressure : float
            目标下游压力 (m 水头)
        """
        if pressure < 0:
            raise ValueError("Target pressure must be non-negative")
        self.target_pressure = pressure

    def activate(self):
        """激活减压阀（开始工作）"""
        self._is_active = True

    def deactivate(self):
        """停用减压阀（相当于全开，不减压）"""
        self._is_active = False

    def is_active(self) -> bool:
        """检查减压阀是否激活"""
        return self._is_active

    def compute_head_loss(self,
                         p_upstream: float,
                         Q: float) -> float:
        """
        计算水头损失

        Parameters
        ----------
        p_upstream : float
            上游压力 (m 水头)
        Q : float
            流量 (m³/s)

        Returns
        -------
        hL : float
            水头损失 (m)

        Notes
        -----
        如果减压阀激活：
            hL = p_upstream - target_pressure
            （只要 p_upstream > target_pressure）

        如果停用：
            hL = 0 (相当于直通管道，忽略阀体损失)

        如果上游压力不足（p_upstream < target_pressure）：
            hL = 0 (减压阀全开，无法减压)
        """
        if not self._is_active:
            # 停用状态，相当于直通
            return 0.0

        if p_upstream <= self.target_pressure:
            # 上游压力不足，无法减压
            return 0.0

        # 正常工作，维持下游压力
        hL = p_upstream - self.target_pressure

        return hL

    def compute_downstream_pressure(self, p_upstream: float) -> float:
        """
        计算下游压力

        Parameters
        ----------
        p_upstream : float
            上游压力 (m 水头)

        Returns
        -------
        p_downstream : float
            下游压力 (m 水头)
        """
        if not self._is_active:
            return p_upstream  # 停用时，下游=上游

        if p_upstream <= self.target_pressure:
            return p_upstream  # 无法减压

        return self.target_pressure  # 维持目标压力

    def compute_required_opening(self,
                                p_upstream: float,
                                Q: float) -> float:
        """
        计算所需开度（百分比）

        这是一个简化计算，实际减压阀通过弹簧和膜片自动调节。

        Parameters
        ----------
        p_upstream : float
            上游压力 (m 水头)
        Q : float
            流量 (m³/s)

        Returns
        -------
        opening_percent : float
            所需开度百分比（0-100%）

        Notes
        -----
        简化假设：开度与压降成反比
            opening% = (P_target / P_upstream) * 100%

        实际减压阀更复杂，涉及弹簧力、流体力等。
        """
        if not self._is_active or p_upstream <= self.target_pressure:
            return 100.0  # 全开

        # 简化计算：开度与目标压力/上游压力成正比
        opening = (self.target_pressure / p_upstream) * 100.0
        opening = np.clip(opening, 5.0, 100.0)  # 限制在5-100%

        return opening


# ============================================================================
# 便捷函数
# ============================================================================

def create_butterfly_valve(position: float,
                          diameter: float,
                          valve_type: str = 'standard',
                          initial_opening: float = 100.0) -> ButterflyValve:
    """
    创建蝶阀

    Parameters
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    valve_type : str
        'standard' 或 'high_performance'
    initial_opening : float
        初始开度百分比 (0-100%)

    Returns
    -------
    ButterflyValve
        配置好的蝶阀对象
    """
    geometry = ButterflyValveGeometry(
        position=position,
        diameter=diameter
    )

    valve = ButterflyValve(geometry, valve_type=valve_type)
    valve.set_opening(initial_opening)

    return valve


def create_ball_valve(position: float,
                     diameter: float,
                     port_type: str = 'full_port',
                     is_open: bool = True) -> BallValve:
    """
    创建球阀

    Parameters
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    port_type : str
        'full_port' 或 'reduced_port'
    is_open : bool
        初始状态（True=开，False=闭）

    Returns
    -------
    BallValve
        配置好的球阀对象
    """
    geometry = BallValveGeometry(
        position=position,
        diameter=diameter,
        port_type=port_type
    )

    valve = BallValve(geometry)

    if is_open:
        valve.open()
    else:
        valve.close()

    return valve


def create_prv(position: float,
              diameter: float,
              target_pressure: float) -> PressureReducingValve:
    """
    创建减压阀

    Parameters
    ----------
    position : float
        阀门位置 (m)
    diameter : float
        阀门直径 (m)
    target_pressure : float
        目标下游压力 (m 水头)

    Returns
    -------
    PressureReducingValve
        配置好的减压阀对象
    """
    geometry = PRVGeometry(
        position=position,
        diameter=diameter
    )

    return PressureReducingValve(geometry, target_pressure=target_pressure)
