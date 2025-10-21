"""
明渠组件 - 完整实现
"""

import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from core.enums import ComponentType

class Canal(HydraulicComponent):
    """
    明渠组件 - 包含高保真和降阶两种模式
    """

    def __init__(self, name: str, volume_min: float, volume_max: float,
                 area: float, length: float, slope: float = 0.0001,
                 manning_n: float = 0.025, n_sections: int = 11):
        """
        Args:
            name: 组件名称
            volume_min: 最小蓄水量 (m³)
            volume_max: 最大蓄水量 (m³)
            area: 断面面积 (m²)
            length: 长度 (m)
            slope: 渠底坡度
            manning_n: Manning糙率系数
            n_sections: 离散节点数（用于高保真）
        """
        super().__init__(name, ComponentType.CANAL.value)

        # 几何参数
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length
        self.slope = slope
        self.manning_n = manning_n
        self.n_sections = n_sections

        # 可辨识参数
        self.parameters = {
            'manning_n': manning_n,
            'area': area,
            'width': 10.0,  # 简化假设
            'delay': max(1, int(length / 1000))  # 估计时滞
        }

        # 初始化集总状态
        self.state = ComponentState()
        self.state.volume = (volume_min + volume_max) / 2
        self.state.level = self.state.volume / area
        self.state.flow = 5.0

        # 初始化分布状态（用于高保真）
        self.hydraulic_state = HydraulicState()
        self.hydraulic_state.h = np.ones(n_sections) * self.state.level
        self.hydraulic_state.Q = np.ones(n_sections) * self.state.flow
        self.hydraulic_state.V = self.hydraulic_state.Q / area

        # 空间离散
        self.dx = length / (n_sections - 1) if n_sections > 1 else length
        self.x = np.linspace(0, length, n_sections)

        print(f"✓ Canal '{name}' 初始化: L={length}m, A={area}m², n={n_sections}")

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真更新 - Saint-Venant方程简化版

        Args:
            dt: 时间步长
            inputs: 输入字典，包含 'inflow', 'outflow', 'disturbance'等

        Returns:
            更新后的状态
        """
        try:
            inflow = inputs.get('inflow', self.state.flow)
            outflow = inputs.get('outflow', self.state.flow)
            disturbance = inputs.get('disturbance', 0.0)

            # 简化的高保真方法（基于水量平衡 + 摩阻）
            g = 9.81
            n = self.n_sections

            h = self.hydraulic_state.h.copy()
            Q = self.hydraulic_state.Q.copy()

            # 更新边界
            Q[0] = inflow
            Q[-1] = outflow

            # 内部节点简化更新
            for i in range(1, n-1):
                # 水量平衡
                dV = (Q[i-1] - Q[i]) * dt
                h[i] += dV / (self.area * self.dx)

                # Manning摩阻
                if h[i] > 0 and Q[i] > 0:
                    V = Q[i] / self.area
                    R = h[i]  # 简化
                    Sf = (self.manning_n * V)**2 / (R**(4/3) + 1e-6)

                    # 动量方程简化
                    dQ = -g * self.area * Sf * dt
                    Q[i] = max(0, Q[i] + dQ)

            # 更新状态
            self.hydraulic_state.h = np.clip(h, 0.1, 20.0)
            self.hydraulic_state.Q = np.clip(Q, 0, 100.0)

            # 更新集总状态
            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.volume = self.state.level * self.area
            self.state.flow = np.mean(self.hydraulic_state.Q)

            return self.state

        except Exception as e:
            print(f"警告: Canal '{self.name}' 高保真更新出错: {e}")
            # 降级到简单更新
            return self.update_reduced_order(dt, inputs)

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """
        降阶模型更新 - 积分延迟模型

        Args:
            dt: 时间步长
            inputs: 输入字典

        Returns:
            更新后的状态
        """
        try:
            inflow = inputs.get('inflow', self.state.flow)
            outflow = inputs.get('outflow', self.state.flow)
            disturbance = inputs.get('disturbance', 0.0)

            # 水量平衡
            dV = (inflow - outflow - disturbance) * dt

            # 更新蓄水量
            self.state.volume += dV
            self.state.volume = np.clip(self.state.volume,
                                       self.volume_min,
                                       self.volume_max)

            # 更新水位
            self.state.level = self.state.volume / self.area

            # 更新流量（平均值）
            self.state.flow = (inflow + outflow) / 2

            # 同步到分布状态
            self.hydraulic_state.h = np.ones(self.n_sections) * self.state.level
            self.hydraulic_state.Q = np.ones(self.n_sections) * self.state.flow

            return self.state

        except Exception as e:
            print(f"错误: Canal '{self.name}' 降阶更新失败: {e}")
            return self.state

    def get_constraints(self) -> dict:
        """获取约束"""
        return {
            'volume': (self.volume_min, self.volume_max),
            'level': (self.volume_min / self.area, self.volume_max / self.area),
            'flow': (0, 100)  # 最大流量限制
        }

    def get_identifiable_parameters(self) -> dict:
        """获取可辨识参数"""
        return self.parameters.copy()

    def set_parameters(self, params: dict):
        """设置参数"""
        self.parameters.update(params)
        if 'manning_n' in params:
            self.manning_n = params['manning_n']
