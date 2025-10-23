#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泵站类（用于明渠系统求解器）

提供简化的泵站模型，兼容HydrostaticCanalSolver
支持固定转速下的泵站运行

作者: Claude
日期: 2025-10-23
"""

import sys
import os
import numpy as np
from typing import Optional

# Add project root to path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

from solvers.gate import HydraulicStructure


class PumpStation(HydraulicStructure):
    """泵站类（简化模型）

    在固定转速下，泵站提供额定流量和扬程。
    简化模型假设：
    1. 泵站在额定转速下运行
    2. 流量由泵特性曲线和上游水位决定
    3. 泵站增加水头（下游可以高于上游）

    模型：
    - 当上游水位足够：Q = Q_rated
    - 当上游水位不足：Q = Q_rated * (h_upstream / h_min)^0.5
    - 扬程：H_pump = H_rated（固定）
    """

    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position: 泵站位置 (m)
            width: 泵站宽度 (m)
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            min_suction_head: 最小吸入水头 (m)，低于此值流量减少
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head

        # 泵站运行状态（固定转速）
        self.is_running = True

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算泵站过流量

        简化模型：
        1. 如果上游水位 >= min_suction_head：Q = Q_rated
        2. 如果上游水位 < min_suction_head：Q = Q_rated * sqrt(h_upstream / min_suction_head)
        3. 泵站不依赖下游水位（主动提水）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)（泵站不依赖此值）
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        if not self.is_running:
            return 0.0, 'pump_off'

        # 检查最小吸入水头
        if h_upstream < 0.1:  # 极低水位，泵站停止
            return 0.0, 'insufficient_water'

        if h_upstream >= self.min_suction_head:
            # 正常运行：额定流量
            discharge = self.rated_flow
            flow_type = 'rated'
        else:
            # 低水位：流量按平方根减少
            # Q = Q_rated * sqrt(h_up / h_min)
            ratio = np.sqrt(h_upstream / self.min_suction_head)
            discharge = self.rated_flow * ratio
            flow_type = 'reduced'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算泵站流量对水深的导数（解析）

        泵站特点：
        1. 在正常运行时（h >= h_min），流量不依赖水位：dQ/dh = 0
        2. 在低水位时（h < h_min），流量与水位相关：dQ/dh_up > 0
        3. 流量不依赖下游水位：dQ/dh_down = 0

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0

        if h_upstream >= self.min_suction_head:
            # 正常运行：流量恒定，导数为零
            dQ_dh_up = 0.0
        else:
            # 低水位：Q = Q_rated * sqrt(h_up / h_min)
            # dQ/dh_up = Q_rated / (2 * sqrt(h_up * h_min))
            dQ_dh_up = self.rated_flow / (2.0 * np.sqrt(h_upstream * self.min_suction_head))

        # 泵站不依赖下游水位（主动提水）
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def set_running_state(self, is_running: bool):
        """
        设置泵站运行状态

        Args:
            is_running: True=运行，False=停止
        """
        self.is_running = is_running

    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStation(position={self.position}m, Q_rated={self.rated_flow}m³/s, "
                f"H_rated={self.rated_head}m, state={state})")


if __name__ == "__main__":
    """测试泵站类"""
    print("=" * 80)
    print("PumpStation Class Test")
    print("=" * 80)

    # 创建泵站
    pump = PumpStation(
        position=5000.0,
        width=10.0,
        rated_flow=30.0,
        rated_head=5.0,
        min_suction_head=2.0
    )

    print(f"\n泵站参数:")
    print(f"  {pump}")
    print(f"  额定流量: {pump.rated_flow} m³/s")
    print(f"  额定扬程: {pump.rated_head} m")
    print(f"  最小吸入水头: {pump.min_suction_head} m")
    print()

    # 测试不同上游水位
    print("测试不同上游水位下的泵站性能:")
    print(f"{'上游水深(m)':>12} {'流量(m³/s)':>12} {'流态':>15} {'dQ/dh_up':>12}")
    print("-" * 55)

    h_ups = [0.05, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
    h_down = 3.0  # 下游水深（泵站不依赖）

    for h_up in h_ups:
        Q, flow_type = pump.calculate_discharge(h_up, h_down)
        dQ_up, dQ_down = pump.calculate_discharge_derivatives(h_up, h_down)
        print(f"{h_up:12.2f} {Q:12.2f} {flow_type:>15} {dQ_up:12.4f}")

    # 测试泵站开关
    print(f"\n测试泵站开关:")
    print(f"  当前状态: 运行")
    Q_on, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  流量: {Q_on:.2f} m³/s")

    pump.set_running_state(False)
    print(f"  关闭泵站...")
    Q_off, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  流量: {Q_off:.2f} m³/s")

    pump.set_running_state(True)
    print(f"  开启泵站...")
    Q_on2, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  流量: {Q_on2:.2f} m³/s")

    print(f"\n泵站类测试完成!")
    print("=" * 80)
