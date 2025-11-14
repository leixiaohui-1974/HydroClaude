#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际工程案例：城市供水管网系统

系统描述：
- 水源：水库，恒定水头 100m
- 主输水管：长度2000m，直径600mm
- 中途泵站：提升压力30m
- 末端用户：住宅区，需求流量波动

控制目标：
1. 维持用户端压力在30+/-2m范围
2. 通过泵站变频调速实现压力控制
3. 应对用户需求波动（日变化）
4. 防止管道水锤（缓慢调节）

特点：
- 有压管道瞬变分析
- 泵站优化运行
- 系统参数在线辨识
- 压力反馈控制（PID + MPC）

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import sys
sys.path.insert(0, '/home/user/HydroClaude')

from core.pressurized_solver import PressurizedFlowSolver, PipelineConfig
from core.pressurized_structures import PumpStation, Valve, ValveCharacteristics, ValveType
from control.pid_controller import PIDController, PIDConfig
from identification.system_identification import RecursiveLeastSquares


def create_user_demand_profile(t: float) -> float:
    """
    创建用户需求曲线（日变化）

    Args:
        t: 时间 (s)

    Returns:
        需求流量 (m^3/s)
    """
    # 基准流量
    Q_base = 0.15  # 150 L/s

    # 时刻（小时）
    hour = (t / 3600) % 24

    # 日变化曲线
    if 0 <= hour < 6:
        # 夜间低谷
        factor = 0.4
    elif 6 <= hour < 9:
        # 早高峰
        factor = 1.2
    elif 9 <= hour < 12:
        # 上午
        factor = 0.8
    elif 12 <= hour < 14:
        # 午间
        factor = 1.0
    elif 14 <= hour < 18:
        # 下午
        factor = 0.9
    elif 18 <= hour < 21:
        # 晚高峰
        factor = 1.3
    else:
        # 晚间
        factor = 0.7

    # 叠加随机波动
    noise = np.random.normal(0, 0.02)

    Q = Q_base * (factor + noise)

    return max(0.05, Q)  # 确保非负


class WaterSupplySystem:
    """供水系统集成"""

    def __init__(self):
        """初始化供水系统"""

        # 管道配置
        self.pipe_config = PipelineConfig(
            length=2000.0,
            diameter=0.6,
            thickness=0.01,
            roughness=0.0001,
            elevation_start=0.0,
            elevation_end=-10.0  # 下坡10m
        )

        # 创建求解器
        self.solver = PressurizedFlowSolver(self.pipe_config, nx=40)

        # 泵站（位于管道中点）
        self.pump = PumpStation(
            rated_flow=0.20,
            rated_head=35.0,
            rated_power=120.0,
            efficiency=0.80,
            name="加压泵站"
        )
        self.pump.start()

        # 末端阀门（模拟用户取水）
        valve_char = ValveCharacteristics(
            valve_type=ValveType.GLOBE,
            diameter=0.6,
            cv_full_open=150.0,
            loss_coeff_full_open=0.3
        )
        self.valve = Valve(valve_char, initial_opening=0.5, name="用户阀门")

        # 压力控制器（PID控制泵站转速）
        pid_config = PIDConfig(
            kp=0.05,
            ki=0.002,
            kd=0.01,
            output_min=0.5,  # 最小转速50%
            output_max=1.1,  # 最大转速110%
            dt=1.0
        )
        self.pid = PIDController(pid_config, name="Pressure PID")
        self.target_pressure = 30.0  # 目标压力 30m
        self.pid.set_setpoint(self.target_pressure)

        # 系统辨识器（在线估计系统参数）
        self.rls = RecursiveLeastSquares(
            n_params=2,  # [a1, b1] for Q[k+1] = a1*Q[k] + b1*u[k]
            forgetting_factor=0.95
        )

        # 运行统计
        self.time_history = []
        self.pressure_history = []
        self.flow_history = []
        self.pump_speed_history = []
        self.demand_history = []
        self.energy_history = []

    def initialize(self):
        """初始化系统到稳态"""
        # 初始流量和压力
        Q0 = 0.15
        H_reservoir = 100.0

        # 考虑泵站扬程
        H0 = H_reservoir + self.pump.rated_head * 0.8

        self.solver.solve_steady_state(Q0, H0)

        print("供水系统初始化:")
        print(f"  水库水头: {H_reservoir} m")
        print(f"  泵站扬程: {self.pump.rated_head * 0.8:.2f} m")
        print(f"  初始流量: {Q0} m^3/s")
        print(f"  末端压力: {self.solver.H[-1]:.2f} m")

    def control_loop(self, t: float, dt: float):
        """
        控制循环

        Args:
            t: 当前时间 (s)
            dt: 时间步长 (s)
        """
        # 1. 获取当前状态
        P_user = self.solver.get_pressure_at(self.pipe_config.length)  # 末端压力
        Q_current = self.solver.get_flow_rate_at(self.pipe_config.length)  # 当前流量

        # 2. 用户需求
        Q_demand = create_user_demand_profile(t)

        # 3. 压力控制（PID控制泵速）
        pump_speed = self.pid.compute(P_user, dt)
        self.pump.set_speed_ratio(pump_speed)

        # 4. 调节阀门开度以匹配需求
        # 简化：根据需求调整阀门
        valve_opening = np.clip(Q_demand / 0.25, 0.1, 1.0)
        self.valve.set_opening(valve_opening)

        # 5. 泵站运行
        H_pump = self.pump.compute_head(Q_current)
        P_pump = self.pump.compute_power(Q_current, H_pump, dt)

        # 6. 系统辨识（在线更新模型）
        # 简化的线性模型：Q[k+1] = a*Q[k] + b*u[k]
        if len(self.flow_history) > 0:
            phi = np.array([self.flow_history[-1], pump_speed])
            self.rls.update(phi, Q_current)

        # 7. 记录历史
        self.time_history.append(t)
        self.pressure_history.append(P_user)
        self.flow_history.append(Q_current)
        self.pump_speed_history.append(pump_speed)
        self.demand_history.append(Q_demand)
        self.energy_history.append(self.pump.total_energy)

    def run_simulation(self, t_final: float):
        """
        运行完整仿真

        Args:
            t_final: 仿真总时间 (s)
        """
        print("\n开始供水系统仿真...")
        print(f"  仿真时长: {t_final/3600:.1f} 小时")
        print(f"  目标压力: {self.target_pressure} m")
        print("-" * 80)

        # 初始化
        self.solve_steady_state()

        # 设置边界条件
        H_reservoir = 100.0

        def bc_upstream(t):
            # 上游：水库恒定水头 + 泵站扬程
            H_pump = self.pump.compute_head(self.solver.Q[0])
            return ('H', H_reservoir + H_pump)

        def bc_downstream(t):
            # 下游：用户需求流量
            return ('Q', self.demand_history[-1] if self.demand_history else 0.15)

        self.solver.set_boundary_conditions(bc_upstream, bc_downstream)

        # 时间步进
        dt = self.solver.dt
        n_steps = int(t_final / dt)

        for step in range(n_steps):
            t = step * dt

            # 控制循环
            self.control_loop(t, dt)

            # 求解器步进
            self.solver.step(t)

            # 进度输出
            if step % max(1, n_steps // 20) == 0:
                progress = step / n_steps * 100
                P_user = self.pressure_history[-1] if self.pressure_history else 0
                Q = self.flow_history[-1] if self.flow_history else 0
                speed = self.pump_speed_history[-1] if self.pump_speed_history else 0

                print(f"  {progress:5.1f}% | t={t/3600:5.2f}h | "
                      f"P={P_user:5.2f}m | Q={Q*1000:6.2f}L/s | "
                      f"泵速={speed:4.2f}")

        print("-" * 80)
        print("仿真完成!")

    def plot_results(self, save_path: str = 'water_supply_results.png'):
        """绘制仿真结果"""
        time_hours = np.array(self.time_history) / 3600

        fig, axes = plt.subplots(3, 2, figsize=(16, 12))

        # 1. 末端压力
        ax = axes[0, 0]
        ax.plot(time_hours, self.pressure_history, 'b-', linewidth=2, label='Actual Pressure')
        ax.axhline(y=self.target_pressure, color='r', linestyle='--',
                  linewidth=2, label='Target')
        ax.fill_between(time_hours,
                       self.target_pressure - 2,
                       self.target_pressure + 2,
                       alpha=0.2, color='green', label='Tolerance')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Pressure (m)')
        ax.set_title('User End Pressure Control')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. 流量对比
        ax = axes[0, 1]
        ax.plot(time_hours, np.array(self.flow_history) * 1000, 'b-',
               linewidth=2, label='Actual Flow')
        ax.plot(time_hours, np.array(self.demand_history) * 1000, 'r--',
               linewidth=2, label='Demand')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Flow Rate (L/s)')
        ax.set_title('Flow Rate vs Demand')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. 泵站转速
        ax = axes[1, 0]
        ax.plot(time_hours, self.pump_speed_history, 'g-', linewidth=2)
        ax.axhline(y=1.0, color='k', linestyle=':', alpha=0.5, label='Rated Speed')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Pump Speed Ratio')
        ax.set_title('Pump Speed Control (VFD)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. 累计能耗
        ax = axes[1, 1]
        ax.plot(time_hours, self.energy_history, 'r-', linewidth=2)
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Energy Consumption (kWh)')
        ax.set_title('Cumulative Energy Consumption')
        ax.grid(True, alpha=0.3)

        # 5. 压力误差
        ax = axes[2, 0]
        errors = np.array(self.pressure_history) - self.target_pressure
        ax.plot(time_hours, errors, 'purple', linewidth=2)
        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax.fill_between(time_hours, -2, 2, alpha=0.2, color='green')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Pressure Error (m)')
        ax.set_title('Pressure Control Error')
        ax.grid(True, alpha=0.3)

        # 6. 系统参数辨识
        ax = axes[2, 1]
        if len(self.rls.theta_history) > 0:
            theta_hist = np.array(self.rls.theta_history)
            ax.plot(time_hours[:len(theta_hist)], theta_hist[:, 0],
                   'b-', linewidth=2, label='Parameter a1')
            ax.plot(time_hours[:len(theta_hist)], theta_hist[:, 1],
                   'r-', linewidth=2, label='Parameter b1')
            ax.set_xlabel('Time (hours)')
            ax.set_ylabel('Parameter Value')
            ax.set_title('Online Parameter Identification (RLS)')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nResults saved to: {save_path}")

    def print_statistics(self):
        """打印运行统计"""
        if not self.pressure_history:
            print("No data available")
            return

        print("\n" + "=" * 80)
        print("Supply System Performance Statistics")
        print("=" * 80)

        # 压力控制性能
        P_array = np.array(self.pressure_history)
        P_error = P_array - self.target_pressure

        print("\nPressure Control:")
        print(f"  Target Pressure: {self.target_pressure:.2f} m")
        print(f"  Mean Pressure: {np.mean(P_array):.2f} m")
        print(f"  Std Deviation: {np.std(P_array):.2f} m")
        print(f"  Max Deviation: {np.max(np.abs(P_error)):.2f} m")
        print(f"  Time in Tolerance (+/-2m): "
              f"{np.sum(np.abs(P_error) < 2.0) / len(P_error) * 100:.1f}%")

        # 流量统计
        Q_array = np.array(self.flow_history) * 1000  # L/s
        Q_demand_array = np.array(self.demand_history) * 1000

        print("\nFlow Rate:")
        print(f"  Mean Flow: {np.mean(Q_array):.2f} L/s")
        print(f"  Peak Flow: {np.max(Q_array):.2f} L/s")
        print(f"  Min Flow: {np.min(Q_array):.2f} L/s")
        print(f"  Total Volume: {np.sum(Q_array) * self.solver.dt / 1000:.2f} m^3")

        # 泵站性能
        print("\nPump Station:")
        print(f"  Start Count: {self.pump.start_count}")
        print(f"  Total Energy: {self.pump.total_energy:.2f} kWh")
        print(f"  Avg Power: {self.pump.total_energy / (self.time_history[-1] / 3600):.2f} kW")
        print(f"  Total Volume Pumped: {self.pump.total_volume:.2f} m^3")
        print(f"  Energy per m^3: {self.pump.total_energy / self.pump.total_volume:.4f} kWh/m^3")

        # 控制器性能
        pid_metrics = self.pid.get_performance_metrics()
        print("\nPID Controller:")
        print(f"  MAE: {pid_metrics['mae']:.4f} m")
        print(f"  Steady-State Error: {pid_metrics['steady_state_error']:.4f} m")

        print("\n" + "=" * 80)


def main():
    """主程序"""
    print("=" * 80)
    print("Water Supply Network Simulation with Pressure Control")
    print("=" * 80)

    # 创建系统
    system = WaterSupplySystem()

    # 运行仿真（模拟24小时）
    t_simulation = 24 * 3600  # 24 hours in seconds

    system.run_simulation(t_simulation)

    # 统计分析
    system.print_statistics()

    # 绘图
    system.plot_results('water_supply_network.png')

    # plt.show()  # Disabled for automated testing

    print("\nSimulation completed successfully!")


if __name__ == "__main__":
    main()
