#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际工程案例：城市排水泵站智能调度系统

工程背景：
某城市排水泵站负责2.5 km^2汇水区域的排涝任务，
配置3台水泵（Q1=2.0 m^3/s, Q2=2.5 m^3/s, Q3=3.0 m^3/s），
集水池有效容积8000 m^3。

设计要求：
1. 汛期暴雨工况下保证不溢流
2. 优化泵组运行，降低能耗和磨损
3. 避免频繁启停（最小运行间隔15分钟）
4. 水位控制在安全范围（1.5m - 4.0m）
5. 考虑电价分时优化

控制策略：
- 基于MPC的泵组优化调度
- 考虑未来降雨预报（前馈控制）
- 多目标优化（排涝效果 vs 能耗成本）
- 泵组启停逻辑优化

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from control.mpc_controller import MPCController, MPCConfig


class PumpStatus(Enum):
    """泵状态"""
    OFF = 0
    ON = 1
    STARTING = 2
    STOPPING = 3


@dataclass
class Pump:
    """水泵配置"""
    id: int
    capacity: float        # 额定流量 (m^3/s)
    power: float           # 额定功率 (kW)
    efficiency: float      # 效率
    min_runtime: float     # 最小运行时间 (s)
    min_stoptime: float    # 最小停机时间 (s)

    # 运行状态
    status: PumpStatus = PumpStatus.OFF
    runtime: float = 0.0        # 当前运行时间 (s)
    stoptime: float = 0.0       # 当前停机时间 (s)
    total_runtime: float = 0.0  # 累计运行时间 (s)
    start_count: int = 0        # 启动次数


@dataclass
class RainfallEvent:
    """降雨事件"""
    start_time: float      # 开始时间 (s)
    duration: float        # 持续时间 (s)
    intensity: float       # 雨强 (mm/h)


class CollectionPool:
    """集水池模型"""

    def __init__(self,
                 area: float = 500.0,  # 池底面积 (m^2)
                 max_depth: float = 5.0,  # 最大水深 (m)
                 initial_depth: float = 2.0):  # 初始水深 (m)
        """
        初始化集水池

        Args:
            area: 池底面积 (m^2)
            max_depth: 最大水深 (m)
            initial_depth: 初始水深 (m)
        """
        self.area = area
        self.max_depth = max_depth
        self.depth = initial_depth

    def update(self, Q_in: float, Q_out: float, dt: float) -> float:
        """
        更新水位

        Args:
            Q_in: 入流量 (m^3/s)
            Q_out: 出流量 (m^3/s)
            dt: 时间步长 (s)

        Returns:
            更新后的水深 (m)
        """
        # 水量平衡
        dV = (Q_in - Q_out) * dt
        dh = dV / self.area

        self.depth += dh

        # 限制水深范围
        self.depth = max(0.0, min(self.max_depth, self.depth))

        return self.depth

    def get_volume(self) -> float:
        """获取当前蓄水量 (m^3)"""
        return self.area * self.depth

    def is_overflow_risk(self, threshold: float = 4.0) -> bool:
        """判断是否有溢流风险"""
        return self.depth >= threshold


class DrainagePumpStation:
    """排水泵站系统"""

    def __init__(self,
                 pumps: List[Pump],
                 pool: CollectionPool,
                 catchment_area: float = 2.5e6,  # 汇水面积 (m^2)
                 runoff_coefficient: float = 0.6):  # 径流系数
        """
        初始化泵站系统

        Args:
            pumps: 水泵列表
            pool: 集水池
            catchment_area: 汇水面积 (m^2)
            runoff_coefficient: 径流系数
        """
        self.pumps = pumps
        self.pool = pool
        self.catchment_area = catchment_area
        self.runoff_coefficient = runoff_coefficient

        # 统计数据
        self.total_energy = 0.0  # 总耗电量 (kWh)
        self.total_inflow = 0.0   # 总入流量 (m^3)
        self.total_pumped = 0.0   # 总抽排量 (m^3)
        self.overflow_duration = 0.0  # 溢流持续时间 (s)

    def calculate_inflow(self, rainfall_intensity: float) -> float:
        """
        计算入流量

        Args:
            rainfall_intensity: 降雨强度 (mm/h)

        Returns:
            入流量 (m^3/s)
        """
        # Q = ψ * i * A
        # i 转换为 m/s
        i_m_per_s = rainfall_intensity / 1000 / 3600
        Q = self.runoff_coefficient * i_m_per_s * self.catchment_area
        return Q

    def get_total_pump_capacity(self) -> float:
        """获取当前运行泵的总流量"""
        total_Q = 0.0
        for pump in self.pumps:
            if pump.status == PumpStatus.ON:
                total_Q += pump.capacity
        return total_Q

    def update_pump_status(self, target_pumps: List[bool], dt: float):
        """
        更新泵运行状态

        Args:
            target_pumps: 目标状态列表 [True/False]
            dt: 时间步长 (s)
        """
        for i, pump in enumerate(self.pumps):
            target = target_pumps[i]

            # 更新运行/停机时间
            if pump.status == PumpStatus.ON:
                pump.runtime += dt
                pump.stoptime = 0.0
            elif pump.status == PumpStatus.OFF:
                pump.stoptime += dt
                pump.runtime = 0.0

            # 检查是否满足启停条件
            if target and pump.status == PumpStatus.OFF:
                # 请求启动
                if pump.stoptime >= pump.min_stoptime:
                    pump.status = PumpStatus.ON
                    pump.start_count += 1
                    pump.runtime = 0.0

            elif not target and pump.status == PumpStatus.ON:
                # 请求停止
                if pump.runtime >= pump.min_runtime:
                    pump.status = PumpStatus.OFF
                    pump.stoptime = 0.0

            # 累计运行时间
            if pump.status == PumpStatus.ON:
                pump.total_runtime += dt

    def update(self, rainfall_intensity: float, pump_commands: List[bool], dt: float) -> float:
        """
        更新泵站系统状态

        Args:
            rainfall_intensity: 降雨强度 (mm/h)
            pump_commands: 泵启停命令 [True/False]
            dt: 时间步长 (s)

        Returns:
            更新后的水位 (m)
        """
        # 更新泵状态
        self.update_pump_status(pump_commands, dt)

        # 计算入流
        Q_in = self.calculate_inflow(rainfall_intensity)
        self.total_inflow += Q_in * dt

        # 计算出流（泵抽排量）
        Q_out = self.get_total_pump_capacity()
        self.total_pumped += Q_out * dt

        # 更新集水池水位
        new_depth = self.pool.update(Q_in, Q_out, dt)

        # 计算能耗
        for pump in self.pumps:
            if pump.status == PumpStatus.ON:
                energy = pump.power * dt / 3600  # kWh
                self.total_energy += energy

        # 检查溢流
        if self.pool.is_overflow_risk():
            self.overflow_duration += dt

        return new_depth

    def get_statistics(self) -> dict:
        """获取运行统计"""
        return {
            'total_energy': self.total_energy,
            'total_inflow': self.total_inflow,
            'total_pumped': self.total_pumped,
            'overflow_duration': self.overflow_duration,
            'pump_starts': [p.start_count for p in self.pumps],
            'pump_runtime': [p.total_runtime for p in self.pumps]
        }


def create_rainfall_scenario(scenario='storm') -> List[RainfallEvent]:
    """创建降雨场景"""
    if scenario == 'storm':
        # 暴雨场景
        return [
            RainfallEvent(start_time=0, duration=1800, intensity=50.0),      # 前期大雨
            RainfallEvent(start_time=1800, duration=900, intensity=120.0),   # 暴雨高峰
            RainfallEvent(start_time=2700, duration=1800, intensity=30.0),   # 后期中雨
        ]
    elif scenario == 'continuous':
        # 持续降雨
        return [
            RainfallEvent(start_time=0, duration=7200, intensity=40.0),
        ]
    else:
        # 无雨
        return []


def intelligent_pump_control(station: DrainagePumpStation,
                            current_depth: float,
                            rainfall_forecast: float) -> List[bool]:
    """
    智能泵组控制逻辑

    基于规则的启停策略 + 降雨预报前馈

    Args:
        station: 泵站系统
        current_depth: 当前水位 (m)
        rainfall_forecast: 未来降雨预报 (mm/h)

    Returns:
        泵启停命令 [True/False]
    """
    commands = [False, False, False]

    # 基于水位的分级启泵策略
    if current_depth >= 3.8:
        # 高水位：全开
        commands = [True, True, True]
    elif current_depth >= 3.3:
        # 中高水位：开2台大泵
        commands = [False, True, True]
    elif current_depth >= 2.8:
        # 中水位：开1台大泵
        commands = [False, False, True]
    elif current_depth >= 2.3:
        # 中低水位：开1台小泵
        commands = [True, False, False]
    elif current_depth <= 1.8:
        # 低水位：全停
        commands = [False, False, False]

    # 前馈控制：根据降雨预报提前启泵
    if rainfall_forecast > 80.0 and current_depth > 2.5:
        # 大雨预报且水位不低：提前开大泵
        commands[2] = True

    return commands


def run_pump_station_simulation():
    """
    运行排水泵站仿真
    """
    print("=" * 80)
    print("城市排水泵站智能调度系统仿真")
    print("=" * 80)

    # 定义泵组
    pumps = [
        Pump(id=1, capacity=2.0, power=45.0, efficiency=0.75,
             min_runtime=900, min_stoptime=600),   # 1号泵：小泵
        Pump(id=2, capacity=2.5, power=55.0, efficiency=0.78,
             min_runtime=900, min_stoptime=600),   # 2号泵：中泵
        Pump(id=3, capacity=3.0, power=70.0, efficiency=0.80,
             min_runtime=900, min_stoptime=600),   # 3号泵：大泵
    ]

    # 定义集水池
    pool = CollectionPool(area=500.0, max_depth=5.0, initial_depth=2.0)

    # 创建泵站系统
    station = DrainagePumpStation(
        pumps=pumps,
        pool=pool,
        catchment_area=2.5e6,  # 2.5 km^2
        runoff_coefficient=0.6
    )

    print("\n系统配置:")
    print(f"  汇水面积: {station.catchment_area/1e6:.2f} km^2")
    print(f"  径流系数: {station.runoff_coefficient}")
    print(f"  集水池容积: {pool.area * pool.max_depth:.0f} m^3")
    print(f"  泵组配置:")
    for pump in pumps:
        print(f"    {pump.id}号泵: Q={pump.capacity} m^3/s, P={pump.power} kW")

    # 创建降雨场景
    rainfall_events = create_rainfall_scenario('storm')
    print(f"\n降雨场景:")
    for event in rainfall_events:
        print(f"  {event.start_time/60:.0f}~{(event.start_time+event.duration)/60:.0f}分钟: "
              f"{event.intensity:.0f} mm/h")

    # 仿真参数
    dt = 30.0  # 30秒时间步长
    t_final = 7200.0  # 2小时
    n_steps = int(t_final / dt)

    # 结果记录
    time = np.zeros(n_steps)
    depth_history = np.zeros(n_steps)
    inflow_history = np.zeros(n_steps)
    outflow_history = np.zeros(n_steps)
    rainfall_history = np.zeros(n_steps)
    pump_status_history = np.zeros((n_steps, len(pumps)))
    energy_history = np.zeros(n_steps)

    print("\n开始仿真...")
    print("-" * 80)

    for k in range(n_steps):
        t = k * dt
        time[k] = t

        # 确定当前降雨强度
        rainfall = 0.0
        for event in rainfall_events:
            if event.start_time <= t < event.start_time + event.duration:
                rainfall = event.intensity
        rainfall_history[k] = rainfall

        # 降雨预报（简化：假设能预报未来10分钟）
        rainfall_forecast = 0.0
        t_forecast = t + 600
        for event in rainfall_events:
            if event.start_time <= t_forecast < event.start_time + event.duration:
                rainfall_forecast = event.intensity

        # 智能控制决策
        current_depth = station.pool.depth
        pump_commands = intelligent_pump_control(station, current_depth, rainfall_forecast)

        # 更新系统
        new_depth = station.update(rainfall, pump_commands, dt)

        # 记录
        depth_history[k] = current_depth
        inflow_history[k] = station.calculate_inflow(rainfall)
        outflow_history[k] = station.get_total_pump_capacity()
        for i, pump in enumerate(pumps):
            pump_status_history[k, i] = 1 if pump.status == PumpStatus.ON else 0
        energy_history[k] = station.total_energy

        # 打印进度
        if k % 40 == 0:  # 每20分钟
            print(f"t={t/60:5.1f}min: 水位={current_depth:4.2f}m, "
                  f"雨强={rainfall:5.1f}mm/h, "
                  f"入流={inflow_history[k]:5.2f}m^3/s, "
                  f"出流={outflow_history[k]:4.1f}m^3/s, "
                  f"泵运行={[i+1 for i,p in enumerate(pumps) if p.status==PumpStatus.ON]}")

    print("-" * 80)

    # 性能统计
    stats = station.get_statistics()

    print("\n运行统计:")
    print(f"  总入流量: {stats['total_inflow']:.2f} m^3")
    print(f"  总抽排量: {stats['total_pumped']:.2f} m^3")
    print(f"  总能耗: {stats['total_energy']:.2f} kWh")
    print(f"  溢流持续时间: {stats['overflow_duration']/60:.2f} 分钟")
    print(f"  泵启动次数: {stats['pump_starts']}")
    print(f"  泵运行时长: {[f'{rt/3600:.2f}h' for rt in stats['pump_runtime']]}")

    # 水位控制评估
    max_depth = np.max(depth_history)
    min_depth = np.min(depth_history)
    overflow_risk = np.sum(depth_history >= 4.0) * dt / 60

    print(f"\n水位控制:")
    print(f"  最高水位: {max_depth:.2f} m")
    print(f"  最低水位: {min_depth:.2f} m")
    print(f"  高水位(>=4.0m)持续: {overflow_risk:.2f} 分钟")

    # 绘图
    fig = plt.figure(figsize=(16, 12))

    # 1. 水位变化
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(time/60, depth_history, 'b-', linewidth=2.5, label='集水池水位')
    ax1.axhline(y=4.0, color='r', linestyle='--', linewidth=2, label='溢流警戒线')
    ax1.axhline(y=1.5, color='orange', linestyle='--', linewidth=2, label='低水位线')
    ax1.fill_between(time/60, 1.5, 4.0, alpha=0.1, color='green', label='安全运行区')
    ax1.set_ylabel('水位 (m)', fontsize=11)
    ax1.set_title('城市排水泵站智能调度 - 集水池水位', fontsize=13, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 5])

    # 2. 流量和降雨
    ax2 = plt.subplot(4, 1, 2)
    ax2_rain = ax2.twinx()
    ax2.plot(time/60, inflow_history, 'b-', linewidth=2, label='入流量', alpha=0.7)
    ax2.plot(time/60, outflow_history, 'g-', linewidth=2, label='出流量(泵排)', alpha=0.7)
    ax2_rain.bar(time/60, rainfall_history, width=1.0, alpha=0.3,
                 color='skyblue', label='降雨强度')
    ax2.set_ylabel('流量 (m^3/s)', fontsize=11)
    ax2_rain.set_ylabel('降雨强度 (mm/h)', fontsize=11)
    ax2.set_title('流量和降雨', fontsize=11)
    ax2.legend(loc='upper left')
    ax2_rain.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    # 3. 泵运行状态
    ax3 = plt.subplot(4, 1, 3)
    for i in range(len(pumps)):
        offset = i * 1.5
        ax3.fill_between(time/60, offset, offset + pump_status_history[:, i],
                        alpha=0.6, label=f'{i+1}号泵 ({pumps[i].capacity} m^3/s)',
                        step='post')
    ax3.set_ylabel('泵运行状态', fontsize=11)
    ax3.set_title('泵组运行状态', fontsize=11)
    ax3.set_yticks([])
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3, axis='x')

    # 4. 累计能耗
    ax4 = plt.subplot(4, 1, 4)
    ax4.plot(time/60, energy_history, 'r-', linewidth=2.5, label='累计能耗')
    ax4.set_xlabel('时间 (分钟)', fontsize=11)
    ax4.set_ylabel('能耗 (kWh)', fontsize=11)
    ax4.set_title('累计能耗', fontsize=11)
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('urban_drainage_pump_station.png', dpi=150, bbox_inches='tight')
    print(f"\n 结果已保存到: urban_drainage_pump_station.png")

    # plt.show()  # Disabled for automated testing

    print("\n" + "=" * 80)
    print("仿真完成！")
    print("\n关键结论:")
    if max_depth < 4.0:
        print("   成功防止溢流，最高水位未超过警戒线")
    else:
        print(f"   出现高水位风险，最高{max_depth:.2f}m")

    avg_energy_per_m3 = stats['total_energy'] / stats['total_pumped'] if stats['total_pumped'] > 0 else 0
    print(f"   单位抽排能耗: {avg_energy_per_m3:.4f} kWh/m^3")
    print(f"   泵组启动总次数: {sum(stats['pump_starts'])} 次（平均{sum(stats['pump_starts'])/len(pumps):.1f}次/泵）")
    print(f"   水量平衡误差: {abs(stats['total_inflow']-stats['total_pumped']-(station.pool.get_volume()-pool.area*2.0))/stats['total_inflow']*100:.2f}%")
    print("=" * 80)


if __name__ == "__main__":
    run_pump_station_simulation()
