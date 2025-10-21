"""
IDZ (Integrator Delay Zero) 模型
适用于长时间步长（小时级）的明渠仿真
基于Saint-Venant方程的线性化简化
"""
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class IDZParameters:
    """IDZ模型参数"""
    delay: float  # 延迟时间 (s)
    tau: float    # 时间常数 (s)
    gain: float   # 增益
    A: float      # 渠道截面积 (m²)
    L: float      # 渠道长度 (m)

class IDZModel:
    """
    IDZ模型: G(s) = K * exp(-τd*s) / (τ*s)

    状态空间形式:
    dx/dt = A*x + B*u
    y = C*x + D*u

    其中包含延迟处理
    """

    def __init__(self, params: IDZParameters, dt: float):
        self.params = params
        self.dt = dt

        # 延迟步数
        self.delay_steps = int(params.delay / dt)

        # 输入历史缓冲区（用于延迟）
        self.input_buffer = np.zeros(max(self.delay_steps + 1, 2))
        self.buffer_index = 0

        # 积分器状态
        self.integrator_state = 0.0

        # 零点补偿状态
        self.zero_state = 0.0

    def update(self, u: float) -> float:
        """
        更新模型状态并返回输出

        Args:
            u: 输入流量变化 (m³/s)

        Returns:
            y: 输出水位变化 (m)
        """
        # 存储当前输入
        self.input_buffer[self.buffer_index] = u

        # 获取延迟后的输入
        delayed_index = (self.buffer_index - self.delay_steps) % len(self.input_buffer)
        u_delayed = self.input_buffer[delayed_index]

        # 更新缓冲区索引
        self.buffer_index = (self.buffer_index + 1) % len(self.input_buffer)

        # 积分器: dx/dt = (K/τ) * u_delayed
        integrator_rate = (self.params.gain / self.params.tau) * u_delayed
        self.integrator_state += integrator_rate * self.dt

        # 零点效应（可选，用于更精确的模型）
        # 这里简化处理
        output = self.integrator_state

        return output

    def get_steady_state_gain(self) -> float:
        """计算稳态增益"""
        return self.params.gain

    def reset(self):
        """重置模型状态"""
        self.input_buffer.fill(0)
        self.buffer_index = 0
        self.integrator_state = 0.0
        self.zero_state = 0.0


class CanalIDZModel:
    """明渠IDZ模型 - 基于物理参数自动计算IDZ参数"""

    def __init__(self, length: float, width: float, slope: float,
                 manning_n: float, nominal_depth: float, dt: float):
        """
        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            slope: 渠道坡度
            manning_n: Manning糙率系数
            nominal_depth: 标称水深 (m)
            dt: 时间步长 (s)
        """
        self.length = length
        self.width = width
        self.slope = slope
        self.manning_n = manning_n
        self.nominal_depth = nominal_depth
        self.dt = dt

        # 计算IDZ参数
        params = self._calculate_idz_parameters()
        self.model = IDZModel(params, dt)

        # 当前状态
        self.current_depth = nominal_depth
        self.current_flow = self._calculate_nominal_flow()

    def _calculate_nominal_flow(self) -> float:
        """计算标称流量（均匀流）"""
        A = self.width * self.nominal_depth
        P = self.width + 2 * self.nominal_depth
        R = A / P  # 水力半径

        # Manning公式
        v = (1 / self.manning_n) * R**(2/3) * self.slope**0.5
        Q = v * A
        return Q

    def _calculate_idz_parameters(self) -> IDZParameters:
        """基于物理参数计算IDZ模型参数"""
        g = 9.81

        # 标称流速
        v0 = self._calculate_nominal_flow() / (self.width * self.nominal_depth)

        # 波速
        c0 = np.sqrt(g * self.nominal_depth)

        # 延迟时间：渠道传播时间
        delay = self.length / (v0 + c0)

        # 时间常数：与渠道长度和流速有关
        tau = self.length / v0

        # 增益：流量变化对水位变化的影响
        A_section = self.width * self.nominal_depth
        gain = self.length / self.width  # 简化：ΔV/A = L*ΔQ/(W*Q0)

        return IDZParameters(
            delay=delay,
            tau=tau,
            gain=gain,
            A=A_section,
            L=self.length
        )

    def update(self, dt: float, inflow: float, outflow: float) -> Dict[str, float]:
        """
        更新明渠状态

        Args:
            dt: 时间步长（必须与构造时一致）
            inflow: 上游入流 (m³/s)
            outflow: 下游出流 (m³/s)

        Returns:
            状态字典 {depth, flow, volume}
        """
        # 净流量变化
        net_flow = inflow - outflow

        # IDZ模型更新
        depth_change = self.model.update(net_flow)

        # 更新水深
        self.current_depth += depth_change
        self.current_depth = max(0.1, self.current_depth)  # 确保正值

        # 更新流量（简化：取上下游平均）
        self.current_flow = (inflow + outflow) / 2

        # 计算体积
        volume = self.width * self.length * self.current_depth

        return {
            'depth': self.current_depth,
            'flow': self.current_flow,
            'volume': volume,
            'level': self.current_depth
        }

    def get_parameters(self) -> IDZParameters:
        """获取IDZ参数"""
        return self.model.params

    def reset(self):
        """重置模型"""
        self.model.reset()
        self.current_depth = self.nominal_depth
        self.current_flow = self._calculate_nominal_flow()
