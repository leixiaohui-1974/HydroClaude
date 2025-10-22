#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
管网节点 (Junction)

节点是管网系统中多根管道的连接点，满足质量守恒和能量守恒。

节点类型：
1. 三通 (Tee Junction): 3根管道连接
2. 四通 (Cross Junction): 4根管道连接
3. 多通 (Multi-way Junction): n根管道连接

质量守恒：
    ∑Q_in = ∑Q_out
    或：∑Q_i = 0 (流入为正，流出为负)

能量方程（考虑局部损失）：
    H_i = H_node - K_i * V_i² / (2g)
    其中 K_i 是该支管的局部损失系数

局部损失系数经验值：
- 三通主管: K ≈ 0.2
- 三通支管: K ≈ 0.5-1.0
- 四通: K ≈ 0.3-0.8

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import List, Dict, Optional, Tuple


class Junction:
    """
    管网节点基类

    支持多根管道连接，自动满足质量守恒
    """

    def __init__(self, name: str, elevation: float = 0.0,
                 loss_coefficients: Optional[Dict[str, float]] = None):
        """
        初始化节点

        Args:
            name: 节点名称
            elevation: 节点高程 (m)
            loss_coefficients: 各支管的局部损失系数字典 {'pipe_id': K}
        """
        self.name = name
        self.elevation = elevation
        self.loss_coefficients = loss_coefficients or {}

        # 节点状态
        self.pressure = 0.0  # 节点压力 (Pa)
        self.head = 0.0      # 节点水头 (m)

        # 连接的管道
        self.connected_pipes = []  # [(pipe_id, direction), ...]
        # direction: 'in' 表示流入节点，'out' 表示流出节点

    def add_pipe(self, pipe_id: str, direction: str, loss_coefficient: float = 0.0):
        """
        添加连接的管道

        Args:
            pipe_id: 管道ID
            direction: 流动方向 ('in' 或 'out')
            loss_coefficient: 局部损失系数
        """
        if direction not in ['in', 'out']:
            raise ValueError(f"Direction must be 'in' or 'out', got '{direction}'")

        self.connected_pipes.append((pipe_id, direction))
        self.loss_coefficients[pipe_id] = loss_coefficient

    def calculate_mass_balance(self, flows: Dict[str, float]) -> float:
        """
        计算质量平衡残差

        Args:
            flows: 各管道流量字典 {'pipe_id': Q}
                  流入为正，流出为负

        Returns:
            残差: ∑Q (应接近0)
        """
        total_flow = 0.0
        for pipe_id, direction in self.connected_pipes:
            Q = flows.get(pipe_id, 0.0)
            # 统一为：流入为正，流出为负
            if direction == 'out':
                Q = -Q
            total_flow += Q

        return total_flow

    def calculate_head_loss(self, pipe_id: str, velocity: float, g: float = 9.81) -> float:
        """
        计算管道在节点处的局部损失

        h_loss = K * V² / (2g)

        Args:
            pipe_id: 管道ID
            velocity: 管道流速 (m/s)
            g: 重力加速度 (m/s²)

        Returns:
            局部损失水头 (m)
        """
        K = self.loss_coefficients.get(pipe_id, 0.0)
        h_loss = K * velocity**2 / (2.0 * g)
        return h_loss

    def update_node_pressure(self, pressure: float):
        """
        更新节点压力

        Args:
            pressure: 节点压力 (Pa)
        """
        self.pressure = pressure
        # 计算水头 (假设水密度 ρ = 1000 kg/m³)
        rho = 1000.0
        g = 9.81
        self.head = pressure / (rho * g) + self.elevation

    def __repr__(self) -> str:
        n_pipes = len(self.connected_pipes)
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"elevation={self.elevation:.2f}m, "
                f"n_pipes={n_pipes}, P={self.pressure/1e3:.2f}kPa)")


class TeeJunction(Junction):
    """
    三通节点

    连接3根管道，常见配置：
    1. 一进两出（分流）
    2. 两进一出（汇流）

    局部损失系数经验值：
    - 主管: K ≈ 0.2
    - 支管（与主管成90°）: K ≈ 0.5-1.0
    """

    def __init__(self, name: str, elevation: float = 0.0,
                 main_pipe_loss: float = 0.2,
                 branch_pipe_loss: float = 0.8):
        """
        初始化三通节点

        Args:
            name: 节点名称
            elevation: 节点高程 (m)
            main_pipe_loss: 主管局部损失系数
            branch_pipe_loss: 支管局部损失系数
        """
        super().__init__(name, elevation)
        self.main_pipe_loss = main_pipe_loss
        self.branch_pipe_loss = branch_pipe_loss

        # 三通默认配置：管道1和管道2为主管，管道3为支管
        self.main_pipes = []
        self.branch_pipe = None

    def setup_configuration(self, main_pipe_1: str, main_pipe_2: str, branch_pipe: str):
        """
        设置三通配置

        Args:
            main_pipe_1: 主管1 ID
            main_pipe_2: 主管2 ID
            branch_pipe: 支管 ID
        """
        self.main_pipes = [main_pipe_1, main_pipe_2]
        self.branch_pipe = branch_pipe

        # 设置损失系数
        self.loss_coefficients[main_pipe_1] = self.main_pipe_loss
        self.loss_coefficients[main_pipe_2] = self.main_pipe_loss
        self.loss_coefficients[branch_pipe] = self.branch_pipe_loss


class CrossJunction(Junction):
    """
    四通节点

    连接4根管道，常见配置：
    1. 十字交叉（主管和支管各2根）
    2. 其他任意配置

    局部损失系数经验值：
    - 直通: K ≈ 0.3
    - 转角: K ≈ 0.5-0.8
    """

    def __init__(self, name: str, elevation: float = 0.0,
                 straight_loss: float = 0.3,
                 turning_loss: float = 0.6):
        """
        初始化四通节点

        Args:
            name: 节点名称
            elevation: 节点高程 (m)
            straight_loss: 直通管道损失系数
            turning_loss: 转角管道损失系数
        """
        super().__init__(name, elevation)
        self.straight_loss = straight_loss
        self.turning_loss = turning_loss


class MultiWayJunction(Junction):
    """
    多通节点

    连接 n 根管道（n >= 3）

    适用于复杂管网系统
    """

    def __init__(self, name: str, n_pipes: int, elevation: float = 0.0,
                 default_loss: float = 0.5):
        """
        初始化多通节点

        Args:
            name: 节点名称
            n_pipes: 管道数量
            elevation: 节点高程 (m)
            default_loss: 默认损失系数
        """
        super().__init__(name, elevation)
        self.n_pipes = n_pipes
        self.default_loss = default_loss


def test_junction():
    """测试节点类"""
    print("=" * 80)
    print("管网节点测试")
    print("=" * 80)
    print()

    # 测试1: 三通节点（一进两出，分流）
    print("【测试1】三通节点 - 一进两出（分流）")
    print("-" * 80)

    tee = TeeJunction(name="Tee-1", elevation=10.0)
    tee.setup_configuration(
        main_pipe_1="Pipe-In",
        main_pipe_2="Pipe-Out1",
        branch_pipe="Pipe-Out2"
    )

    # 添加管道连接
    tee.add_pipe("Pipe-In", "in", loss_coefficient=0.2)
    tee.add_pipe("Pipe-Out1", "out", loss_coefficient=0.2)
    tee.add_pipe("Pipe-Out2", "out", loss_coefficient=0.8)

    print(f"三通节点: {tee}")
    print(f"连接管道: {tee.connected_pipes}")
    print()

    # 测试质量守恒
    flows = {
        "Pipe-In": 10.0,      # 流入 10 m³/s
        "Pipe-Out1": 6.0,     # 流出 6 m³/s
        "Pipe-Out2": 4.0,     # 流出 4 m³/s
    }

    residual = tee.calculate_mass_balance(flows)
    print(f"流量分配:")
    print(f"  流入: {flows['Pipe-In']} m³/s")
    print(f"  流出1: {flows['Pipe-Out1']} m³/s")
    print(f"  流出2: {flows['Pipe-Out2']} m³/s")
    print(f"质量平衡残差: {residual:.6f} m³/s")

    if abs(residual) < 1e-6:
        print("  ✓ 质量守恒满足！")
    else:
        print(f"  ✗ 质量不守恒，残差 = {residual}")
    print()

    # 测试局部损失
    print("局部损失计算:")
    # 假设管径 D = 0.5m, 流速 = Q / A
    D = 0.5
    A = np.pi * (D/2)**2

    for pipe_id, Q in flows.items():
        V = abs(Q) / A
        h_loss = tee.calculate_head_loss(pipe_id, V)
        print(f"  {pipe_id}: V={V:.3f} m/s, h_loss={h_loss:.4f} m")

    print()

    # 测试2: 四通节点（十字交叉）
    print("【测试2】四通节点 - 十字交叉")
    print("-" * 80)

    cross = CrossJunction(name="Cross-1", elevation=5.0)

    # 添加4根管道
    cross.add_pipe("Pipe-N", "in", loss_coefficient=0.3)   # 北侧流入
    cross.add_pipe("Pipe-S", "out", loss_coefficient=0.3)  # 南侧流出（直通）
    cross.add_pipe("Pipe-E", "in", loss_coefficient=0.6)   # 东侧流入
    cross.add_pipe("Pipe-W", "out", loss_coefficient=0.6)  # 西侧流出（转角）

    print(f"四通节点: {cross}")
    print(f"连接管道: {cross.connected_pipes}")
    print()

    # 测试质量守恒
    flows_cross = {
        "Pipe-N": 8.0,   # 北侧流入
        "Pipe-E": 5.0,   # 东侧流入
        "Pipe-S": 9.0,   # 南侧流出
        "Pipe-W": 4.0,   # 西侧流出
    }

    residual_cross = cross.calculate_mass_balance(flows_cross)
    print(f"流量分配:")
    for pipe_id, Q in flows_cross.items():
        direction = dict(cross.connected_pipes)[pipe_id]
        print(f"  {pipe_id} ({direction}): {Q:.1f} m³/s")
    print(f"质量平衡残差: {residual_cross:.6f} m³/s")

    if abs(residual_cross) < 1e-6:
        print("  ✓ 质量守恒满足！")
    else:
        print(f"  ✗ 质量不守恒，残差 = {residual_cross}")
    print()

    # 测试3: 节点压力更新
    print("【测试3】节点压力更新")
    print("-" * 80)

    tee.update_node_pressure(500000.0)  # 500 kPa
    print(f"三通节点压力更新: {tee}")
    print(f"  压力: {tee.pressure/1e3:.2f} kPa")
    print(f"  水头: {tee.head:.2f} m (包含高程)")
    print()

    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_junction()
