#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
气压罐 (Air Vessel)

气压罐是管网系统中重要的水锤防护设备，通过气液两相的压缩和膨胀
来吸收和释放能量，缓冲压力波动。

工作原理：
- 正常运行: 气压罐中水位维持在设定值
- 压力升高: 水被压入气压罐，气体压缩，吸收能量
- 压力降低: 气体膨胀，将水压回管道，补充能量

气体状态方程 (多变过程):
    P * V^n = const
    其中 n 是多变指数 (1.0-1.4)

作者: Claude
日期: 2025-10-22
"""

import numpy as np


class AirVessel:
    """
    气压罐组件

    模拟气压罐对水锤的缓冲作用
    """

    def __init__(self, name: str, volume: float, initial_pressure: float,
                 initial_water_level: float = 0.5,
                 polytropic_index: float = 1.2,
                 connection_diameter: float = 0.2):
        """
        Args:
            name: 气压罐名称
            volume: 总容积 (m³)
            initial_pressure: 初始压力 (Pa)
            initial_water_level: 初始水位比 (0-1)
            polytropic_index: 多变指数 (1.0等温, 1.4绝热, 1.2常用)
            connection_diameter: 连接管直径 (m)
        """
        self.name = name
        self.volume = volume
        self.P0 = initial_pressure
        self.water_level_0 = initial_water_level
        self.n = polytropic_index
        self.D_conn = connection_diameter

        # 当前状态
        self.pressure = initial_pressure
        self.water_level = initial_water_level
        self.water_volume = volume * initial_water_level
        self.air_volume = volume * (1 - initial_water_level)

        # 初始气体状态常数
        self.PV_n_const = self.P0 * (self.air_volume ** self.n)

    def update_state(self, Q_in: float, dt: float, P_main: float):
        """
        更新气压罐状态

        Args:
            Q_in: 流入气压罐的流量 (m³/s), 正为流入，负为流出
            dt: 时间步长 (s)
            P_main: 主管压力 (Pa)

        Returns:
            更新后的气压罐压力 (Pa)
        """
        # 更新水体积
        self.water_volume += Q_in * dt
        self.water_volume = np.clip(self.water_volume, 0, self.volume * 0.99)

        # 更新气体体积
        self.air_volume = self.volume - self.water_volume

        # 根据多变过程计算新压力
        if self.air_volume > 0:
            self.pressure = self.PV_n_const / (self.air_volume ** self.n)
        else:
            self.pressure = P_main * 10  # 气体被完全压缩

        # 更新水位
        self.water_level = self.water_volume / self.volume

        return self.pressure

    def calculate_flow_to_vessel(self, P_main: float, rho: float = 1000.0) -> float:
        """
        计算流向气压罐的流量

        Q = A * sqrt(2 * ΔP / ρ) * sign(ΔP)

        Args:
            P_main: 主管压力 (Pa)
            rho: 水密度 (kg/m³)

        Returns:
            流量 (m³/s), 正为流入气压罐
        """
        delta_P = P_main - self.pressure
        A_conn = np.pi * (self.D_conn / 2)**2

        if abs(delta_P) < 1:
            return 0.0

        Q = A_conn * np.sqrt(2 * abs(delta_P) / rho) * np.sign(delta_P)
        return Q

    def get_damping_coefficient(self) -> float:
        """
        获取阻尼系数

        气压罐对压力波动的阻尼能力

        Returns:
            阻尼系数 (m³/Pa)
        """
        # dV/dP = -V/(n*P)
        damping = self.air_volume / (self.n * self.pressure)
        return damping

    def __repr__(self):
        return (f"AirVessel(name='{self.name}', V={self.volume}m³, "
                f"P={self.pressure/1e5:.2f}bar, level={self.water_level*100:.1f}%)")


if __name__ == "__main__":
    print("气压罐测试:")
    vessel = AirVessel("AV1", volume=10.0, initial_pressure=500000)
    print(f"  初始: {vessel}")

    # 模拟压力波动
    P_main = 600000  # 主管压力升高
    Q_in = vessel.calculate_flow_to_vessel(P_main)
    print(f"  主管压力升高到{P_main/1e5:.2f}bar, 流入气压罐: {Q_in:.4f} m³/s")

    # 更新状态
    dt = 1.0
    vessel.update_state(Q_in, dt, P_main)
    print(f"  更新后: {vessel}")
    print(f"  阻尼系数: {vessel.get_damping_coefficient():.6f} m³/Pa")
    print("   气压罐组件测试通过")
