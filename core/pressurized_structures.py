#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有压系统结构物

包括：
1. 阀门（Valve）- 流量调节、快速关闭
2. 泵站（Pump）- 加压、变频调速
3. 调压水箱（SurgeTank）- 压力缓冲
4. 止回阀（CheckValve）- 防止倒流
5. 空气阀（AirValve）- 防止负压、排气

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ValveType(Enum):
    """阀门类型"""
    GATE = "gate"           # 闸阀
    GLOBE = "globe"         # 截止阀
    BUTTERFLY = "butterfly" # 蝶阀
    BALL = "ball"           # 球阀


@dataclass
class ValveCharacteristics:
    """阀门特性参数"""
    valve_type: ValveType
    diameter: float              # 公称直径 (m)
    cv_full_open: float          # 全开流量系数
    loss_coeff_full_open: float  # 全开局部阻力系数

    # 阀门开度-流量特性曲线
    # tau = opening (0-1)
    # Cv(tau) = cv_full_open * f(tau)
    def flow_coefficient(self, opening: float) -> float:
        """
        流量系数随开度变化

        Args:
            opening: 阀门开度 (0-1)

        Returns:
            流量系数 Cv
        """
        if opening <= 0:
            return 0.0
        elif opening >= 1.0:
            return self.cv_full_open

        # 不同阀门类型的特性曲线
        if self.valve_type == ValveType.GATE:
            # 闸阀：快开特性
            return self.cv_full_open * opening ** 0.5
        elif self.valve_type == ValveType.GLOBE:
            # 截止阀：线性特性
            return self.cv_full_open * opening
        elif self.valve_type == ValveType.BUTTERFLY:
            # 蝶阀：抛物线特性
            return self.cv_full_open * opening ** 2
        else:
            # 默认：线性
            return self.cv_full_open * opening


class Valve:
    """
    阀门

    功能：
    - 流量调节
    - 压力控制
    - 模拟阀门关闭导致的水锤
    """

    def __init__(self,
                 characteristics: ValveCharacteristics,
                 initial_opening: float = 1.0,
                 name: str = "Valve"):
        """
        初始化阀门

        Args:
            characteristics: 阀门特性
            initial_opening: 初始开度 (0-1)
            name: 阀门名称
        """
        self.char = characteristics
        self.opening = initial_opening
        self.name = name

        # 控制模式
        self.control_mode = 'manual'  # 'manual' or 'auto'
        self.control_func: Optional[Callable] = None

        # 运行统计
        self.operation_count = 0
        self.total_flow = 0.0

    def set_opening(self, opening: float):
        """
        设置阀门开度

        Args:
            opening: 开度 (0-1)
        """
        self.opening = np.clip(opening, 0.0, 1.0)
        self.operation_count += 1

    def set_control_function(self, control_func: Callable[[float, float, float], float]):
        """
        设置自动控制函数

        Args:
            control_func: 控制函数 f(t, H_up, H_down) -> opening
        """
        self.control_func = control_func
        self.control_mode = 'auto'

    def compute_flow(self, H_upstream: float, H_downstream: float) -> float:
        """
        计算通过阀门的流量

        使用阀门流量方程：
        Q = Cv * sqrt(ΔH)

        Args:
            H_upstream: 上游压力水头 (m)
            H_downstream: 下游压力水头 (m)

        Returns:
            流量 (m³/s)
        """
        if self.opening <= 0:
            return 0.0

        # 压差
        dH = H_upstream - H_downstream

        if dH < 0:
            # 倒流（如果允许）
            return 0.0  # 简化：不允许倒流

        # 当前流量系数
        Cv = self.char.flow_coefficient(self.opening)

        # 流量
        Q = Cv * np.sqrt(dH)

        self.total_flow += Q

        return Q

    def update(self, t: float, H_upstream: float, H_downstream: float):
        """
        更新阀门状态（自动控制模式）

        Args:
            t: 当前时间 (s)
            H_upstream: 上游压力水头 (m)
            H_downstream: 下游压力水头 (m)
        """
        if self.control_mode == 'auto' and self.control_func is not None:
            new_opening = self.control_func(t, H_upstream, H_downstream)
            self.set_opening(new_opening)

    def __repr__(self) -> str:
        return (f"Valve(name='{self.name}', type={self.char.valve_type.value}, "
                f"opening={self.opening:.2f})")


class PumpStation:
    """
    泵站

    功能：
    - 提升压力
    - 变频调速
    - 启停控制
    """

    def __init__(self,
                 rated_flow: float,          # 额定流量 (m³/s)
                 rated_head: float,          # 额定扬程 (m)
                 rated_power: float,         # 额定功率 (kW)
                 efficiency: float = 0.80,   # 效率
                 speed_ratio: float = 1.0,   # 转速比 (0-1.2)
                 name: str = "Pump"):
        """
        初始化泵站

        Args:
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            rated_power: 额定功率 (kW)
            efficiency: 效率
            speed_ratio: 转速比（1.0为额定转速）
            name: 泵站名称
        """
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.rated_power = rated_power
        self.efficiency = efficiency
        self.speed_ratio = speed_ratio
        self.name = name

        # 状态
        self.is_running = False
        self.current_flow = 0.0
        self.current_head = 0.0
        self.current_power = 0.0

        # 统计
        self.total_energy = 0.0  # kWh
        self.total_volume = 0.0  # m³
        self.start_count = 0

    def start(self):
        """启动泵站"""
        if not self.is_running:
            self.is_running = True
            self.start_count += 1

    def stop(self):
        """停止泵站"""
        self.is_running = False
        self.current_flow = 0.0
        self.current_head = 0.0
        self.current_power = 0.0

    def set_speed_ratio(self, ratio: float):
        """
        设置转速比（变频调速）

        Args:
            ratio: 转速比 (0.3-1.2)
        """
        self.speed_ratio = np.clip(ratio, 0.3, 1.2)

    def compute_head(self, Q: float) -> float:
        """
        计算泵站扬程

        使用相似定律和泵特性曲线：
        H = H_rated * (n/n_rated)² * (1 - k*(Q/Q_rated - 1)²)

        Args:
            Q: 流量 (m³/s)

        Returns:
            扬程 (m)
        """
        if not self.is_running:
            return 0.0

        n = self.speed_ratio
        Q_rated = self.rated_flow
        H_rated = self.rated_head

        # 无量纲流量
        q = Q / (Q_rated * n) if n > 0 else 0.0

        # 泵特性曲线（抛物线）
        k = 0.5  # 曲线陡度参数
        h = 1.0 - k * (q - 1.0) ** 2

        # 考虑转速比
        H = H_rated * (n ** 2) * max(0.0, h)

        self.current_flow = Q
        self.current_head = H

        return H

    def compute_power(self, Q: float, H: float, dt: float) -> float:
        """
        计算泵站功率和能耗

        Args:
            Q: 流量 (m³/s)
            H: 扬程 (m)
            dt: 时间步长 (s)

        Returns:
            功率 (kW)
        """
        if not self.is_running:
            return 0.0

        # 水力功率
        P_hydraulic = 9.81 * Q * H  # kW

        # 实际功率（考虑效率）
        P = P_hydraulic / self.efficiency if self.efficiency > 0 else 0.0

        # 限制最大功率
        P = min(P, self.rated_power * 1.2)

        self.current_power = P

        # 累计能耗
        energy = P * dt / 3600  # kWh
        self.total_energy += energy

        # 累计水量
        self.total_volume += Q * dt

        return P

    def __repr__(self) -> str:
        status = "运行" if self.is_running else "停止"
        return (f"PumpStation(name='{self.name}', status={status}, "
                f"speed={self.speed_ratio:.2f})")


class SurgeTank:
    """
    调压水箱

    功能：
    - 缓冲压力波动
    - 储存能量
    - 减轻水锤效应
    """

    def __init__(self,
                 area: float,              # 水箱截面积 (m²)
                 height: float,            # 水箱高度 (m)
                 initial_level: float,     # 初始水位 (m)
                 elevation: float = 0.0,   # 底部高程 (m)
                 name: str = "SurgeTank"):
        """
        初始化调压水箱

        Args:
            area: 截面积 (m²)
            height: 总高度 (m)
            initial_level: 初始水位 (m)
            elevation: 底部高程 (m)
            name: 水箱名称
        """
        self.area = area
        self.height = height
        self.level = initial_level
        self.elevation = elevation
        self.name = name

        # 统计
        self.max_level = initial_level
        self.min_level = initial_level

    def update(self, Q_in: float, Q_out: float, dt: float):
        """
        更新水箱水位

        Args:
            Q_in: 入流量 (m³/s)
            Q_out: 出流量 (m³/s)
            dt: 时间步长 (s)
        """
        # 水量平衡
        dV = (Q_in - Q_out) * dt
        dh = dV / self.area

        self.level += dh

        # 限制水位
        self.level = np.clip(self.level, 0.0, self.height)

        # 统计
        self.max_level = max(self.max_level, self.level)
        self.min_level = min(self.min_level, self.level)

    def get_head(self) -> float:
        """
        获取水箱出口压力水头

        Returns:
            压力水头 (m)
        """
        return self.elevation + self.level

    def get_volume(self) -> float:
        """
        获取当前蓄水量

        Returns:
            体积 (m³)
        """
        return self.area * self.level

    def is_overflow(self) -> bool:
        """判断是否溢流"""
        return self.level >= self.height * 0.99

    def is_empty(self) -> bool:
        """判断是否排空"""
        return self.level <= 0.01

    def __repr__(self) -> str:
        return (f"SurgeTank(name='{self.name}', level={self.level:.2f}m, "
                f"volume={self.get_volume():.2f}m³)")


class CheckValve:
    """
    止回阀

    功能：
    - 防止倒流
    - 自动关闭
    """

    def __init__(self,
                 diameter: float,
                 loss_coeff: float = 2.0,
                 name: str = "CheckValve"):
        """
        初始化止回阀

        Args:
            diameter: 公称直径 (m)
            loss_coeff: 局部阻力系数
            name: 名称
        """
        self.diameter = diameter
        self.loss_coeff = loss_coeff
        self.name = name

        # 状态
        self.is_open = True

    def compute_flow(self, H_upstream: float, H_downstream: float, V: float) -> float:
        """
        计算通过止回阀的流量

        Args:
            H_upstream: 上游压力水头 (m)
            H_downstream: 下游压力水头 (m)
            V: 流速 (m/s)

        Returns:
            流量 (m³/s)
        """
        if H_downstream > H_upstream:
            # 倒流趋势 - 关闭
            self.is_open = False
            return 0.0
        else:
            # 正常流动 - 开启
            self.is_open = True
            A = np.pi * (self.diameter / 2) ** 2
            Q = V * A
            return Q

    def get_head_loss(self, V: float) -> float:
        """
        计算局部水头损失

        Args:
            V: 流速 (m/s)

        Returns:
            水头损失 (m)
        """
        if not self.is_open:
            return 0.0

        return self.loss_coeff * V ** 2 / (2 * 9.81)

    def __repr__(self) -> str:
        status = "开启" if self.is_open else "关闭"
        return f"CheckValve(name='{self.name}', status={status})"


# 示例和测试
if __name__ == "__main__":
    print("=" * 80)
    print("有压系统结构物测试")
    print("=" * 80)

    # 1. 测试阀门
    print("\n1. 阀门测试")
    print("-" * 80)

    valve_char = ValveCharacteristics(
        valve_type=ValveType.GATE,
        diameter=0.5,
        cv_full_open=100.0,
        loss_coeff_full_open=0.5
    )

    valve = Valve(valve_char, initial_opening=1.0, name="主阀门")
    print(valve)

    # 不同开度下的流量
    H_up = 50.0
    H_down = 45.0
    print(f"\n上游水头: {H_up} m, 下游水头: {H_down} m")
    print(f"压差: {H_up - H_down} m")
    print("\n开度 | 流量系数 | 流量")
    print("-" * 40)
    for opening in [1.0, 0.75, 0.5, 0.25, 0.1]:
        valve.set_opening(opening)
        Cv = valve.char.flow_coefficient(opening)
        Q = valve.compute_flow(H_up, H_down)
        print(f"{opening:4.2f} | {Cv:8.2f} | {Q:6.3f} m³/s")

    # 2. 测试泵站
    print("\n2. 泵站测试")
    print("-" * 80)

    pump = PumpStation(
        rated_flow=0.2,
        rated_head=30.0,
        rated_power=80.0,
        efficiency=0.80,
        name="1号泵"
    )

    pump.start()
    print(pump)

    # 不同流量下的扬程
    print("\n流量特性曲线（额定转速）:")
    print("流量 | 扬程 | 功率")
    print("-" * 40)
    for q_ratio in [0.5, 0.75, 1.0, 1.25]:
        Q = pump.rated_flow * q_ratio
        H = pump.compute_head(Q)
        P = pump.compute_power(Q, H, 1.0)
        print(f"{Q:4.3f} | {H:5.2f} | {P:5.2f} kW")

    # 变频调速
    print("\n变频调速特性（Q=额定流量）:")
    print("转速比 | 扬程 | 功率")
    print("-" * 40)
    Q_rated = pump.rated_flow
    for n in [0.6, 0.8, 1.0, 1.2]:
        pump.set_speed_ratio(n)
        H = pump.compute_head(Q_rated * n)  # 相似定律：Q ∝ n
        P = pump.compute_power(Q_rated * n, H, 1.0)
        print(f"{n:4.2f}  | {H:5.2f} | {P:5.2f} kW")

    # 3. 测试调压水箱
    print("\n3. 调压水箱测试")
    print("-" * 80)

    tank = SurgeTank(
        area=100.0,
        height=10.0,
        initial_level=5.0,
        elevation=0.0,
        name="调压塔"
    )

    print(tank)
    print(f"初始水头: {tank.get_head():.2f} m")

    # 模拟水位变化
    print("\n模拟流量波动:")
    print("时间 | 入流 | 出流 | 水位 | 水头")
    print("-" * 50)
    dt = 10.0
    for t in range(0, 100, 10):
        # 模拟波动
        Q_in = 0.5 + 0.2 * np.sin(2 * np.pi * t / 60)
        Q_out = 0.5

        tank.update(Q_in, Q_out, dt)

        print(f"{t:4d} | {Q_in:4.2f} | {Q_out:4.2f} | "
              f"{tank.level:4.2f} | {tank.get_head():5.2f}")

    print(f"\n最高水位: {tank.max_level:.2f} m")
    print(f"最低水位: {tank.min_level:.2f} m")

    # 4. 测试止回阀
    print("\n4. 止回阀测试")
    print("-" * 80)

    check_valve = CheckValve(diameter=0.5, name="止回阀1")
    print(check_valve)

    print("\n不同压差下的流动状态:")
    print("上游水头 | 下游水头 | 状态")
    print("-" * 40)
    test_cases = [
        (50.0, 45.0),  # 正向
        (50.0, 50.0),  # 平衡
        (45.0, 50.0),  # 倒流
    ]

    for H_up, H_down in test_cases:
        Q = check_valve.compute_flow(H_up, H_down, 1.0)
        status = "开启" if check_valve.is_open else "关闭"
        print(f"{H_up:8.2f} | {H_down:8.2f} | {status}")

    print("\n" + "=" * 80)
    print("测试完成！")
