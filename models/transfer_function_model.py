"""
传递函数降阶模型
支持一阶、二阶、高阶传递函数
适用于中等时间步长（分钟级）的仿真
"""
import numpy as np
from scipy import signal
from typing import List, Tuple, Optional

class TransferFunctionModel:
    """
    传递函数模型：G(s) = num(s) / den(s)

    使用状态空间形式进行离散化和仿真
    """

    def __init__(self, numerator: List[float], denominator: List[float], dt: float):
        """
        Args:
            numerator: 分子多项式系数 [b_n, b_{n-1}, ..., b_1, b_0]
            denominator: 分母多项式系数 [a_m, a_{m-1}, ..., a_1, a_0]
            dt: 采样时间 (s)
        """
        self.num = np.array(numerator)
        self.den = np.array(denominator)
        self.dt = dt

        # 创建连续传递函数
        self.sys_c = signal.TransferFunction(self.num, self.den)

        # 离散化
        self.sys_d = signal.cont2discrete((self.num, self.den), dt, method='zoh')

        # 状态空间表示
        self.A, self.B, self.C, self.D = signal.tf2ss(self.num, self.den)

        # 离散状态空间
        sys_ss_c = signal.StateSpace(self.A, self.B, self.C, self.D)
        sys_ss_d = sys_ss_c.to_discrete(dt)

        self.Ad = sys_ss_d.A
        self.Bd = sys_ss_d.B
        self.Cd = sys_ss_d.C
        self.Dd = sys_ss_d.D

        # 状态向量
        self.x = np.zeros((self.Ad.shape[0], 1))

    def update(self, u: float) -> float:
        """
        更新状态并计算输出

        Args:
            u: 输入

        Returns:
            y: 输出
        """
        u_vec = np.array([[u]])

        # 状态更新：x[k+1] = A*x[k] + B*u[k]
        x_next = self.Ad @ self.x + self.Bd @ u_vec

        # 输出：y[k] = C*x[k] + D*u[k]
        y = (self.Cd @ self.x + self.Dd @ u_vec)[0, 0]

        self.x = x_next

        return y

    def reset(self):
        """重置状态"""
        self.x = np.zeros_like(self.x)

    @staticmethod
    def first_order(K: float, tau: float, dt: float) -> 'TransferFunctionModel':
        """
        创建一阶传递函数：G(s) = K / (tau*s + 1)

        Args:
            K: 增益
            tau: 时间常数
            dt: 采样时间

        Returns:
            TransferFunctionModel实例
        """
        return TransferFunctionModel([K], [tau, 1], dt)

    @staticmethod
    def second_order(K: float, wn: float, zeta: float, dt: float) -> 'TransferFunctionModel':
        """
        创建二阶传递函数：G(s) = K*wn² / (s² + 2*zeta*wn*s + wn²)

        Args:
            K: 增益
            wn: 自然频率
            zeta: 阻尼比
            dt: 采样时间

        Returns:
            TransferFunctionModel实例
        """
        num = [K * wn**2]
        den = [1, 2*zeta*wn, wn**2]
        return TransferFunctionModel(num, den, dt)

    @staticmethod
    def integrator_delay(K: float, delay: float, tau: float, dt: float,
                        delay_order: int = 1) -> 'TransferFunctionModel':
        """
        创建积分延迟模型（Pade近似）

        Args:
            K: 增益
            delay: 延迟时间
            tau: 时间常数
            dt: 采样时间
            delay_order: Pade近似阶数

        Returns:
            TransferFunctionModel实例
        """
        # Pade近似: exp(-delay*s) ≈ (1 - delay*s/2) / (1 + delay*s/2)
        if delay_order == 1:
            num_delay = [1, -delay/2]
            den_delay = [1, delay/2]
        else:
            # 使用scipy的pade函数
            num_delay, den_delay = signal.pade(delay, delay_order)

        # 组合：G(s) = K * exp(-delay*s) / (tau*s)
        # 近似为：K * num_delay / (den_delay * tau * s)
        num = np.polymul([K], num_delay)
        den = np.polymul(np.polymul([tau, 0], den_delay), [1])  # tau*s * den_delay

        return TransferFunctionModel(num.tolist(), den.tolist(), dt)


class CanalTransferFunctionModel:
    """明渠传递函数模型"""

    def __init__(self, length: float, width: float, slope: float,
                 manning_n: float, nominal_depth: float, dt: float,
                 model_type: str = 'first_order'):
        """
        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            slope: 坡度
            manning_n: Manning系数
            nominal_depth: 标称水深 (m)
            dt: 时间步长 (s)
            model_type: 模型类型 ('first_order', 'second_order', 'idz')
        """
        self.length = length
        self.width = width
        self.nominal_depth = nominal_depth
        self.dt = dt

        # 计算物理参数
        g = 9.81
        A = width * nominal_depth
        P = width + 2 * nominal_depth
        R = A / P
        v = (1/manning_n) * R**(2/3) * slope**0.5
        c = np.sqrt(g * nominal_depth)

        # 根据模型类型创建传递函数
        if model_type == 'first_order':
            # 一阶模型
            tau = length / v
            K = length / width
            self.tf_model = TransferFunctionModel.first_order(K, tau, dt)

        elif model_type == 'second_order':
            # 二阶模型（考虑波动）
            wn = np.sqrt(g / nominal_depth) / length
            zeta = v / (2 * c)
            K = length / width
            self.tf_model = TransferFunctionModel.second_order(K, wn, zeta, dt)

        elif model_type == 'idz':
            # IDZ模型
            delay = length / (v + c)
            tau = length / v
            K = length / width
            self.tf_model = TransferFunctionModel.integrator_delay(K, delay, tau, dt)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # 当前状态
        self.current_depth = nominal_depth
        self.current_flow = v * A

    def update(self, dt: float, upstream_flow: float, downstream_flow: float) -> dict:
        """
        更新模型

        Args:
            dt: 时间步长（必须与构造时一致）
            upstream_flow: 上游流量 (m³/s)
            downstream_flow: 下游流量 (m³/s)

        Returns:
            状态字典
        """
        # 净流量
        net_flow = upstream_flow - downstream_flow

        # 传递函数更新
        depth_change = self.tf_model.update(net_flow)

        # 更新水深
        self.current_depth += depth_change
        self.current_depth = max(0.1, self.current_depth)

        # 更新流量
        self.current_flow = (upstream_flow + downstream_flow) / 2

        volume = self.width * self.length * self.current_depth

        return {
            'depth': self.current_depth,
            'level': self.current_depth,
            'flow': self.current_flow,
            'volume': volume
        }

    def reset(self):
        """重置模型"""
        self.tf_model.reset()
        self.current_depth = self.nominal_depth
