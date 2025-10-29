"""
泵站水力计算模块（Pump Station Hydraulics）

实现离心泵及泵站系统的水力计算：
- 离心泵特性曲线（H-Q关系）
- 效率曲线和功率计算
- 泵的串联和并联运行
- 变速运行（相似定律）

理论基础：
- 离心泵特性曲线理论
- 泵的相似定律
- 参考 AWWA M11 (Steel Pipe Manual)
- 参考 Karassik (Pump Handbook)

Author: HydroClaude Development Team
Date: 2025-01
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List, Callable
import numpy as np


# ============================================================================
# 离心泵（Centrifugal Pump）
# ============================================================================

@dataclass
class PumpCharacteristics:
    """
    泵的特性曲线参数

    Attributes
    ----------
    H0 : float
        关死扬程 (m)，Q=0时的扬程
    Q_design : float
        设计流量 (m³/s)
    H_design : float
        设计扬程 (m)
    eta_design : float
        设计效率（0-1）
    n_rated : float
        额定转速 (rpm)
    curve_type : str
        曲线类型：'parabolic' (抛物线) 或 'polynomial' (三次多项式)
    """
    H0: float
    Q_design: float
    H_design: float
    eta_design: float = 0.85
    n_rated: float = 1450.0
    curve_type: str = 'parabolic'

    def __post_init__(self):
        """验证参数"""
        if self.H0 <= 0:
            raise ValueError("Shutoff head H0 must be positive")
        if self.Q_design <= 0:
            raise ValueError("Design flow must be positive")
        if self.H_design <= 0:
            raise ValueError("Design head must be positive")
        if not (0 < self.eta_design <= 1.0):
            raise ValueError("Efficiency must be between 0 and 1")
        if self.n_rated <= 0:
            raise ValueError("Rated speed must be positive")
        if self.curve_type not in ['parabolic', 'polynomial']:
            raise ValueError("Curve type must be 'parabolic' or 'polynomial'")


class CentrifugalPump:
    """
    离心泵水力计算

    离心泵通过叶轮旋转给予液体能量，是给排水、工业循环、
    灌溉排涝等系统的核心设备。

    Parameters
    ----------
    position : float
        泵站位置 (m)
    characteristics : PumpCharacteristics
        泵的特性曲线参数

    Notes
    -----
    特性曲线方程（抛物线型）：
        H = H0 - K * Q²

    其中：
        K = (H0 - H_design) / Q_design²

    扬程定义：
        H = (P_out - P_in) / (ρg) + (V_out² - V_in²) / (2g) + (Z_out - Z_in)

    效率曲线（简化抛物线）：
        η = η_max * [1 - ((Q - Q_opt) / Q_opt)²]

    轴功率：
        P_shaft = ρ * g * Q * H / η

    泵的相似定律：
        Q2/Q1 = (n2/n1)
        H2/H1 = (n2/n1)²
        P2/P1 = (n2/n1)³
    """

    def __init__(self,
                 position: float,
                 characteristics: PumpCharacteristics):
        self.position = position
        self.char = characteristics
        self.g = 9.81  # m/s²
        self.rho = 1000.0  # kg/m³

        # 当前转速（初始为额定转速）
        self._current_speed = characteristics.n_rated

        # 运行状态
        self._is_running = True

        # 计算特性曲线系数
        self._compute_curve_coefficients()

    def _compute_curve_coefficients(self):
        """计算特性曲线系数"""
        if self.char.curve_type == 'parabolic':
            # 抛物线：H = H0 - K * Q²
            self.K = (self.char.H0 - self.char.H_design) / (self.char.Q_design ** 2)
        else:  # polynomial
            # 三次多项式：H = a + b*Q + c*Q² + d*Q³
            # 简化：使用三点拟合（H0, 设计点, 高效点）
            # 这里使用抛物线作为简化
            self.K = (self.char.H0 - self.char.H_design) / (self.char.Q_design ** 2)

    def start(self):
        """启动泵"""
        self._is_running = True

    def stop(self):
        """停止泵"""
        self._is_running = False

    def is_running(self) -> bool:
        """检查泵是否运行"""
        return self._is_running

    def set_speed(self, speed_rpm: float):
        """
        设置泵的转速

        Parameters
        ----------
        speed_rpm : float
            转速 (rpm)
        """
        if speed_rpm < 0:
            raise ValueError("Speed must be non-negative")
        self._current_speed = speed_rpm

    def get_speed(self) -> float:
        """获取当前转速 (rpm)"""
        return self._current_speed

    def compute_head(self, Q: float, speed: Optional[float] = None) -> float:
        """
        计算泵在给定流量下的扬程

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        speed : float, optional
            转速 (rpm)。如为 None，使用当前转速

        Returns
        -------
        H : float
            扬程 (m)

        Notes
        -----
        如果泵停止运行，返回0。

        使用相似定律调整到给定转速：
            Q_rated = Q * (n_rated / n)
            H_rated = 计算的扬程
            H = H_rated * (n / n_rated)²

        Examples
        --------
        >>> char = PumpCharacteristics(H0=50, Q_design=0.2, H_design=45)
        >>> pump = CentrifugalPump(position=100.0, characteristics=char)
        >>> H = pump.compute_head(Q=0.15)
        >>> print(f"Head: {H:.2f} m")
        """
        if not self._is_running:
            return 0.0

        if speed is None:
            speed = self._current_speed

        # 使用相似定律转换到额定转速
        speed_ratio = speed / self.char.n_rated
        Q_rated = Q / speed_ratio if speed_ratio > 0 else 0.0

        # 在额定转速下计算扬程
        if self.char.curve_type == 'parabolic':
            H_rated = self.char.H0 - self.K * (Q_rated ** 2)
        else:
            H_rated = self.char.H0 - self.K * (Q_rated ** 2)

        # 转换回实际转速
        H = H_rated * (speed_ratio ** 2)

        # 扬程不能为负
        H = max(H, 0.0)

        return H

    def compute_efficiency(self, Q: float) -> float:
        """
        计算泵的效率

        Parameters
        ----------
        Q : float
            流量 (m³/s)

        Returns
        -------
        eta : float
            效率（0-1）

        Notes
        -----
        简化模型：效率曲线为抛物线
            η = η_max * [1 - k * ((Q - Q_opt) / Q_opt)²]

        其中：
            Q_opt = Q_design（最优流量点）
            η_max = η_design / 0.95（假设设计点为95%最大效率）
            k = 调节系数（取0.5，使得偏离±50%流量时效率降至60%）
        """
        if not self._is_running or Q <= 0:
            return 0.0

        Q_opt = self.char.Q_design
        eta_max = self.char.eta_design / 0.95  # 假设设计点为95%峰值
        eta_max = min(eta_max, 1.0)

        # 效率曲线系数
        k = 0.5

        # 计算效率
        deviation = (Q - Q_opt) / Q_opt
        eta = eta_max * (1.0 - k * (deviation ** 2))

        # 限制在合理范围
        eta = np.clip(eta, 0.1, 1.0)

        return eta

    def compute_power(self, Q: float, H: Optional[float] = None) -> float:
        """
        计算泵的轴功率

        Parameters
        ----------
        Q : float
            流量 (m³/s)
        H : float, optional
            扬程 (m)。如为 None，自动计算

        Returns
        -------
        P : float
            轴功率 (kW)

        Notes
        -----
        P_shaft = ρ * g * Q * H / η / 1000  [kW]
        """
        if not self._is_running:
            return 0.0

        if H is None:
            H = self.compute_head(Q)

        eta = self.compute_efficiency(Q)

        if eta > 0:
            P = self.rho * self.g * Q * H / eta / 1000.0  # kW
        else:
            P = 0.0

        return P

    def compute_operating_point(self,
                                system_curve: Callable[[float], float],
                                Q_initial: float = None) -> Tuple[float, float]:
        """
        计算泵的工况点（泵曲线与系统曲线交点）

        Parameters
        ----------
        system_curve : callable
            系统曲线函数 H_system = f(Q)
        Q_initial : float, optional
            初始猜测流量

        Returns
        -------
        Q : float
            工况点流量 (m³/s)
        H : float
            工况点扬程 (m)

        Notes
        -----
        求解方程：H_pump(Q) = H_system(Q)

        使用迭代法（Newton-Raphson或二分法）
        """
        if not self._is_running:
            return 0.0, 0.0

        if Q_initial is None:
            Q_initial = self.char.Q_design

        # Newton-Raphson迭代
        Q = Q_initial
        for iteration in range(50):
            H_pump = self.compute_head(Q)
            H_system = system_curve(Q)

            residual = H_pump - H_system

            if abs(residual) < 0.001:
                return Q, H_pump

            # 数值导数
            dQ = 0.001
            H_pump_perturb = self.compute_head(Q + dQ)
            H_system_perturb = system_curve(Q + dQ)

            derivative = (H_pump_perturb - H_system_perturb - residual) / dQ

            if abs(derivative) > 1e-10:
                Q -= residual / derivative
                Q = max(Q, 0.0)  # 流量非负
            else:
                break

        # 如果未收敛，返回最后的估计值
        H = self.compute_head(Q)
        return Q, H


# ============================================================================
# 泵组（Pump Array）
# ============================================================================

class PumpArray:
    """
    泵组（串联或并联运行）

    Parameters
    ----------
    pumps : List[CentrifugalPump]
        泵列表
    configuration : str
        配置类型：'series' (串联) 或 'parallel' (并联)

    Notes
    -----
    串联运行：
        - 流量相同：Q_total = Q_single
        - 扬程相加：H_total = Σ H_i

    并联运行：
        - 流量相加：Q_total = Σ Q_i
        - 扬程相同：H_total = H_single
    """

    def __init__(self,
                 pumps: List[CentrifugalPump],
                 configuration: str = 'parallel'):
        if not pumps:
            raise ValueError("Pump array must contain at least one pump")

        if configuration not in ['series', 'parallel']:
            raise ValueError("Configuration must be 'series' or 'parallel'")

        self.pumps = pumps
        self.configuration = configuration

    def compute_head(self, Q: float) -> float:
        """
        计算泵组在给定流量下的扬程

        Parameters
        ----------
        Q : float
            流量 (m³/s)

        Returns
        -------
        H : float
            扬程 (m)
        """
        if self.configuration == 'series':
            # 串联：流量相同，扬程相加
            H_total = sum(pump.compute_head(Q) for pump in self.pumps)
            return H_total

        else:  # parallel
            # 并联：扬程相同，求单泵流量
            # 简化假设：所有泵特性相同，均分流量
            n_running = sum(1 for pump in self.pumps if pump.is_running())

            if n_running == 0:
                return 0.0

            Q_single = Q / n_running

            # 计算单泵扬程（假设所有泵扬程相同）
            H = self.pumps[0].compute_head(Q_single)

            return H

    def compute_total_power(self, Q: float) -> float:
        """
        计算泵组总功率

        Parameters
        ----------
        Q : float
            总流量 (m³/s)

        Returns
        -------
        P_total : float
            总功率 (kW)
        """
        if self.configuration == 'series':
            # 串联：每台泵流量相同
            P_total = sum(pump.compute_power(Q) for pump in self.pumps)

        else:  # parallel
            # 并联：均分流量
            n_running = sum(1 for pump in self.pumps if pump.is_running())

            if n_running == 0:
                return 0.0

            Q_single = Q / n_running
            P_total = sum(pump.compute_power(Q_single)
                         for pump in self.pumps if pump.is_running())

        return P_total

    def start_pump(self, index: int):
        """启动指定泵"""
        if 0 <= index < len(self.pumps):
            self.pumps[index].start()

    def stop_pump(self, index: int):
        """停止指定泵"""
        if 0 <= index < len(self.pumps):
            self.pumps[index].stop()

    def get_running_count(self) -> int:
        """获取运行中的泵数量"""
        return sum(1 for pump in self.pumps if pump.is_running())


# ============================================================================
# 便捷函数
# ============================================================================

def create_centrifugal_pump(position: float,
                           H0: float,
                           Q_design: float,
                           H_design: float,
                           eta_design: float = 0.85,
                           n_rated: float = 1450.0) -> CentrifugalPump:
    """
    创建离心泵

    Parameters
    ----------
    position : float
        泵站位置 (m)
    H0 : float
        关死扬程 (m)
    Q_design : float
        设计流量 (m³/s)
    H_design : float
        设计扬程 (m)
    eta_design : float
        设计效率（0-1）
    n_rated : float
        额定转速 (rpm)

    Returns
    -------
    CentrifugalPump
        配置好的离心泵对象

    Examples
    --------
    >>> pump = create_centrifugal_pump(
    ...     position=100.0,
    ...     H0=50.0,
    ...     Q_design=0.2,
    ...     H_design=45.0,
    ...     eta_design=0.85
    ... )
    """
    char = PumpCharacteristics(
        H0=H0,
        Q_design=Q_design,
        H_design=H_design,
        eta_design=eta_design,
        n_rated=n_rated
    )

    return CentrifugalPump(position=position, characteristics=char)


def create_pump_array(pumps: List[CentrifugalPump],
                     configuration: str = 'parallel') -> PumpArray:
    """
    创建泵组

    Parameters
    ----------
    pumps : List[CentrifugalPump]
        泵列表
    configuration : str
        'series' (串联) 或 'parallel' (并联)

    Returns
    -------
    PumpArray
        泵组对象
    """
    return PumpArray(pumps=pumps, configuration=configuration)
