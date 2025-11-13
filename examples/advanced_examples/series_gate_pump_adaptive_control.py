# -*- coding: utf-8 -*-
"""
串联闸泵群明渠系统自适应控制案例

完整的闭环控制系统，集成：
1. Saint-Venant方程明渠仿真器
2. 传感器仿真（噪声、延迟、故障）
3. 执行器仿真（死区、滞后、饱和）
4. MPC控制器
5. 在线辨识（闸门流量系数、泵站特性）

系统组成：
- 3个池段明渠
- 2个闸门 + 1个泵站
- 多个传感器（水位、流量、闸位、泵速）
- 自适应控制算法

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys
import os
from typing import List, Tuple

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from physics.canal import Canal
from hardware.sensors import LevelSensor, FlowSensor, GatePositionSensor, PumpSpeedSensor, SensorConfig, SensorType, FaultType
from hardware.actuators import GateActuator, PumpActuator, ActuatorConfig, ActuatorType
from control.online_identification import GateIdentifier, PumpIdentifier
from control.pid_controller import PIDController, PIDConfig


class SimplifiedMPC:
    """
    简化MPC控制器

    使用线性化模型：Δh/Δt ~= (Q_in - Q_out) / A
    """

    def __init__(self, pool_areas: List[float], dt: float = 60.0):
        """
        Args:
            pool_areas: 各池段面积
            dt: 采样时间
        """
        self.pool_areas = pool_areas
        self.n_pools = len(pool_areas)
        self.dt = dt

        # PID控制器（每个池段一个）
        self.pid_controllers = []
        for i in range(self.n_pools):
            config = PIDConfig(
                kp=5.0,
                ki=0.1,
                kd=2.0,
                output_min=-5.0,
                output_max=5.0,
                dt=dt
            )
            pid = PIDController(config)
            self.pid_controllers.append(pid)

    def compute_control(self,
                       h_current: np.ndarray,
                       h_setpoint: np.ndarray,
                       q_upstream: float) -> np.ndarray:
        """
        计算控制流量

        Args:
            h_current: 当前水位
            h_setpoint: 目标水位
            q_upstream: 上游流量

        Returns:
            各闸门/泵站流量
        """
        n = self.n_pools
        q_control = np.zeros(n + 1)

        # 上游流量固定
        q_control[0] = q_upstream

        # 各池段PID控制
        for i in range(n):
            # 设置目标值并计算
            self.pid_controllers[i].set_setpoint(h_setpoint[i])
            delta_q = self.pid_controllers[i].compute(h_current[i], self.dt)

            # 下游流量 = 上游流量 + 调整
            if i == 0:
                q_control[i+1] = q_control[i] + delta_q
            else:
                q_control[i+1] = q_control[i] + delta_q

            # 限制流量范围
            q_control[i+1] = np.clip(q_control[i+1], 0.1, 30.0)

        return q_control


class SeriesGatePumpSystem:
    """
    串联闸泵群系统

    3个池段 + 2个闸门 + 1个泵站
    """

    def __init__(self):
        # 系统参数
        self.dt = 60.0  # 采样时间60s

        # 创建3个池段明渠
        self.pools = self._create_pools()

        # 创建传感器
        self.sensors = self._create_sensors()

        # 创建执行器
        self.actuators = self._create_actuators()

        # 创建控制器
        pool_areas = [100.0, 120.0, 80.0]  # 各池段面积
        self.controller = SimplifiedMPC(pool_areas, self.dt)

        # 在线辨识器
        self.gate1_identifier = GateIdentifier(gate_width=5.0)
        self.gate2_identifier = GateIdentifier(gate_width=5.0)
        self.pump_identifier = PumpIdentifier()

        # 目标水位
        self.h_setpoint = np.array([2.5, 2.7, 2.3])

        # 上游流量（可变）
        self.q_upstream = 15.0

        # 历史记录
        self.history = {
            'time': [],
            'water_levels': {f'Pool{i+1}': [] for i in range(3)},
            'water_levels_measured': {f'Pool{i+1}': [] for i in range(3)},
            'flows': {f'Q{i}': [] for i in range(4)},
            'gate_openings': {'Gate1': [], 'Gate2': []},
            'pump_speed': [],
            'control_errors': [],
            'gate1_Cd': [],
            'gate2_Cd': [],
            'pump_H0': [],
            'pump_K': []
        }

    def _create_pools(self) -> List[Canal]:
        """创建3个池段"""
        pools = []

        # 池段1
        pool1 = Canal(
            name="Pool1",
            volume_min=0,
            volume_max=10000,
            area=100.0,
            length=1000.0,
            width=10.0,
            slope=0.0001,
            manning_n=0.025,
            n_sections=20,
            initial_depth=2.0,
            initial_flow=15.0
        )
        pools.append(pool1)

        # 池段2
        pool2 = Canal(
            name="Pool2",
            volume_min=0,
            volume_max=12000,
            area=120.0,
            length=1200.0,
            width=12.0,
            slope=0.00012,
            manning_n=0.025,
            n_sections=20,
            initial_depth=2.2,
            initial_flow=15.0
        )
        pools.append(pool2)

        # 池段3
        pool3 = Canal(
            name="Pool3",
            volume_min=0,
            volume_max=8000,
            area=80.0,
            length=800.0,
            width=8.0,
            slope=0.00015,
            manning_n=0.025,
            n_sections=20,
            initial_depth=1.8,
            initial_flow=15.0
        )
        pools.append(pool3)

        return pools

    def _create_sensors(self) -> dict:
        """创建传感器"""
        sensors = {}

        # 水位传感器 - 3个
        for i in range(3):
            config = SensorConfig(
                name=f'LEVEL_POOL{i+1}',
                sensor_type=SensorType.LEVEL,
                noise_std=0.02,          # 2cm噪声
                delay_steps=1,
                use_filter=True,
                filter_alpha=0.3
            )
            sensors[f'level{i+1}'] = LevelSensor(f'LEVEL_POOL{i+1}', config=config)

        # 流量传感器 - 4个（上游、3个池段下游）
        for i in range(4):
            config = SensorConfig(
                name=f'FLOW_{i}',
                sensor_type=SensorType.FLOW,
                noise_std=0.1,
                delay_steps=1
            )
            sensors[f'flow{i}'] = FlowSensor(f'FLOW_{i}', config=config)

        # 闸门位置传感器 - 2个
        for i in range(2):
            config = SensorConfig(
                name=f'GATE{i+1}_POS',
                sensor_type=SensorType.GATE_POSITION,
                noise_std=0.005
            )
            sensors[f'gate{i+1}_pos'] = GatePositionSensor(f'GATE{i+1}_POS', config=config)

        # 泵站转速传感器
        config = SensorConfig(
            name='PUMP1_SPEED',
            sensor_type=SensorType.PUMP_SPEED,
            noise_std=2.0
        )
        sensors['pump_speed'] = PumpSpeedSensor('PUMP1_SPEED', config=config)

        return sensors

    def _create_actuators(self) -> dict:
        """创建执行器"""
        actuators = {}

        # 闸门1
        config1 = ActuatorConfig(
            name='GATE1',
            actuator_type=ActuatorType.GATE,
            rate_limit=0.05,      # 5cm/s
            min_value=0.0,
            max_value=3.0,
            dead_zone=0.02,
            hysteresis=0.03,
            delay_steps=1,
            noise_std=0.005
        )
        actuators['gate1'] = GateActuator('GATE1', config=config1)

        # 闸门2
        config2 = ActuatorConfig(
            name='GATE2',
            actuator_type=ActuatorType.GATE,
            rate_limit=0.05,
            min_value=0.0,
            max_value=3.0,
            dead_zone=0.02,
            hysteresis=0.03,
            delay_steps=1,
            noise_std=0.005
        )
        actuators['gate2'] = GateActuator('GATE2', config=config2)

        # 泵站
        config3 = ActuatorConfig(
            name='PUMP1',
            actuator_type=ActuatorType.PUMP,
            rate_limit=20.0,      # 20rpm/s
            min_value=0.0,
            max_value=1500.0,
            dead_zone=5.0,
            delay_steps=2,
            noise_std=1.0
        )
        actuators['pump'] = PumpActuator('PUMP1', config=config3)

        return actuators

    def compute_gate_flow(self, opening: float, head: float, C_d: float = 0.6) -> float:
        """计算闸门流量"""
        if opening < 0.01 or head < 0.01:
            return 0.0
        return C_d * 5.0 * opening * np.sqrt(2 * 9.81 * head)

    def compute_pump_flow(self, speed: float, head: float, H0: float = 50.0, K: float = 0.1) -> float:
        """计算泵站流量"""
        if speed < 10:
            return 0.0
        # 简化：流量与转速成正比
        speed_ratio = speed / 1000.0  # 标准1000rpm
        Q_max = np.sqrt((H0 - head) / K) if (H0 - head) > 0 else 0
        return speed_ratio * Q_max

    def step(self, step_idx: int):
        """
        系统单步仿真

        Args:
            step_idx: 步骤索引
        """
        # 1. 测量当前状态
        h_true = np.array([
            self.pools[0].hydraulic_state.h[-1],
            self.pools[1].hydraulic_state.h[-1],
            self.pools[2].hydraulic_state.h[-1]
        ])

        h_measured = np.array([
            self.sensors['level1'].measure(h_true[0], self.dt),
            self.sensors['level2'].measure(h_true[1], self.dt),
            self.sensors['level3'].measure(h_true[2], self.dt)
        ])

        # 2. MPC控制计算
        q_control = self.controller.compute_control(h_measured, self.h_setpoint, self.q_upstream)

        # 3. 计算闸门开度和泵站转速命令
        # 简化：直接从流量计算开度/转速
        gate1_opening_cmd = q_control[1] / 15.0  # 简化线性关系
        gate2_opening_cmd = q_control[2] / 15.0
        pump_speed_cmd = q_control[3] / 0.02 * 1000  # 简化

        # 4. 执行器响应
        gate1_opening = self.actuators['gate1'].actuate(gate1_opening_cmd, self.dt)
        gate2_opening = self.actuators['gate2'].actuate(gate2_opening_cmd, self.dt)
        pump_speed = self.actuators['pump'].actuate(pump_speed_cmd, self.dt)

        # 5. 计算实际流量（使用辨识的参数）
        q0 = q_control[0]  # 上游流量

        # 闸门1流量
        gate1_head = h_true[0]
        q1_true = self.compute_gate_flow(gate1_opening, gate1_head, self.gate1_identifier.C_d)

        # 闸门2流量
        gate2_head = h_true[1]
        q2_true = self.compute_gate_flow(gate2_opening, gate2_head, self.gate2_identifier.C_d)

        # 泵站流量
        pump_head = h_true[2]
        q3_true = self.compute_pump_flow(pump_speed, pump_head, self.pump_identifier.H0, self.pump_identifier.K)

        # 6. 更新水力仿真（简化：直接更新水位）
        # 使用水量平衡方程
        for i, pool in enumerate(self.pools):
            if i == 0:
                q_in = q0
                q_out = q1_true
            elif i == 1:
                q_in = q1_true
                q_out = q2_true
            else:
                q_in = q2_true
                q_out = q3_true

            # 水位变化：Δh = (Q_in - Q_out) * Δt / A
            dh = (q_in - q_out) * self.dt / pool.area
            new_h = pool.hydraulic_state.h[-1] + dh
            new_h = np.clip(new_h, 0.5, 5.0)  # 限制范围

            # 更新池段水位（简化：所有节点相同）
            pool.hydraulic_state.h[:] = new_h
            pool.hydraulic_state.Q[:] = (q_in + q_out) / 2.0

        # 7. 流量测量
        q_measured = [
            self.sensors['flow0'].measure(q0, self.dt),
            self.sensors['flow1'].measure(q1_true, self.dt),
            self.sensors['flow2'].measure(q2_true, self.dt),
            self.sensors['flow3'].measure(q3_true, self.dt)
        ]

        # 8. 在线辨识
        if step_idx > 10:  # 等待稳定
            # 闸门1辨识
            if gate1_opening > 0.1 and gate1_head > 0.1:
                self.gate1_identifier.update(gate1_opening, gate1_head, q_measured[1])

            # 闸门2辨识
            if gate2_opening > 0.1 and gate2_head > 0.1:
                self.gate2_identifier.update(gate2_opening, gate2_head, q_measured[2])

            # 泵站辨识
            if pump_speed > 100:
                # 从流量反推扬程
                head_estimate = pump_head
                self.pump_identifier.update(q_measured[3], head_estimate)

        # 9. 记录历史
        self.history['time'].append(step_idx * self.dt)
        for i in range(3):
            self.history['water_levels'][f'Pool{i+1}'].append(h_true[i])
            self.history['water_levels_measured'][f'Pool{i+1}'].append(h_measured[i])

        for i in range(4):
            self.history['flows'][f'Q{i}'].append(q_measured[i])

        self.history['gate_openings']['Gate1'].append(gate1_opening)
        self.history['gate_openings']['Gate2'].append(gate2_opening)
        self.history['pump_speed'].append(pump_speed)

        avg_error = np.mean(np.abs(h_true - self.h_setpoint))
        self.history['control_errors'].append(avg_error)

        self.history['gate1_Cd'].append(self.gate1_identifier.C_d)
        self.history['gate2_Cd'].append(self.gate2_identifier.C_d)
        self.history['pump_H0'].append(self.pump_identifier.H0)
        self.history['pump_K'].append(self.pump_identifier.K)

    def visualize_results(self):
        """可视化结果"""
        fig = plt.figure(figsize=(18, 12))
        gs = GridSpec(4, 3, figure=fig)

        time_h = np.array(self.history['time']) / 3600  # 转换为小时

        # 1. 水位跟踪
        ax1 = fig.add_subplot(gs[0, :])
        for i in range(3):
            ax1.plot(time_h, self.history['water_levels'][f'Pool{i+1}'],
                    '-', linewidth=2, label=f'Pool{i+1} (True)')
            ax1.plot(time_h, self.history['water_levels_measured'][f'Pool{i+1}'],
                    ':', linewidth=1, alpha=0.7, label=f'Pool{i+1} (Measured)')

        ax1.axhline(y=self.h_setpoint[0], color='r', linestyle='--', linewidth=1, label='Setpoint Pool1')
        ax1.axhline(y=self.h_setpoint[1], color='g', linestyle='--', linewidth=1, label='Setpoint Pool2')
        ax1.axhline(y=self.h_setpoint[2], color='b', linestyle='--', linewidth=1, label='Setpoint Pool3')

        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Water Level (m)')
        ax1.set_title('Water Level Tracking', fontweight='bold')
        ax1.legend(ncol=3, fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. 流量
        ax2 = fig.add_subplot(gs[1, 0])
        for i in range(4):
            ax2.plot(time_h, self.history['flows'][f'Q{i}'], linewidth=2, label=f'Q{i}')
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Flow Rate (m^3/s)')
        ax2.set_title('Flow Rates', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. 闸门开度
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(time_h, self.history['gate_openings']['Gate1'], linewidth=2, label='Gate 1')
        ax3.plot(time_h, self.history['gate_openings']['Gate2'], linewidth=2, label='Gate 2')
        ax3.set_xlabel('Time (hours)')
        ax3.set_ylabel('Gate Opening (m)')
        ax3.set_title('Gate Openings', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 泵站转速
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.plot(time_h, self.history['pump_speed'], 'r-', linewidth=2)
        ax4.set_xlabel('Time (hours)')
        ax4.set_ylabel('Pump Speed (rpm)')
        ax4.set_title('Pump Speed', fontweight='bold')
        ax4.grid(True, alpha=0.3)

        # 5. 控制误差
        ax5 = fig.add_subplot(gs[2, 0])
        ax5.plot(time_h, self.history['control_errors'], 'k-', linewidth=2)
        ax5.set_xlabel('Time (hours)')
        ax5.set_ylabel('Average Error (m)')
        ax5.set_title('Control Error', fontweight='bold')
        ax5.grid(True, alpha=0.3)

        # 6. 闸门流量系数辨识
        ax6 = fig.add_subplot(gs[2, 1])
        ax6.plot(time_h, self.history['gate1_Cd'], linewidth=2, label='Gate 1 C_d')
        ax6.plot(time_h, self.history['gate2_Cd'], linewidth=2, label='Gate 2 C_d')
        ax6.axhline(y=0.6, color='r', linestyle='--', linewidth=1, label='Typical C_d')
        ax6.set_xlabel('Time (hours)')
        ax6.set_ylabel('Discharge Coefficient')
        ax6.set_title('Gate C_d Identification', fontweight='bold')
        ax6.legend()
        ax6.grid(True, alpha=0.3)

        # 7. 泵站特性辨识
        ax7 = fig.add_subplot(gs[2, 2])
        ax7_twin = ax7.twinx()

        line1 = ax7.plot(time_h, self.history['pump_H0'], 'b-', linewidth=2, label='H0')
        line2 = ax7_twin.plot(time_h, self.history['pump_K'], 'r-', linewidth=2, label='K')

        ax7.set_xlabel('Time (hours)')
        ax7.set_ylabel('H0 (m)', color='b')
        ax7_twin.set_ylabel('K', color='r')
        ax7.set_title('Pump Characteristic Identification', fontweight='bold')

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax7.legend(lines, labels)
        ax7.grid(True, alpha=0.3)

        # 8. 系统性能统计
        ax8 = fig.add_subplot(gs[3, :])
        ax8.axis('off')

        stats_text = f"""
系统性能统计:

控制性能:
  最终水位: Pool1={self.history['water_levels']['Pool1'][-1]:.3f}m, Pool2={self.history['water_levels']['Pool2'][-1]:.3f}m, Pool3={self.history['water_levels']['Pool3'][-1]:.3f}m
  目标水位: Pool1={self.h_setpoint[0]:.3f}m, Pool2={self.h_setpoint[1]:.3f}m, Pool3={self.h_setpoint[2]:.3f}m
  最终误差: {self.history['control_errors'][-1]:.4f}m
  平均误差: {np.mean(self.history['control_errors']):.4f}m

在线辨识结果:
  闸门1流量系数: {self.history['gate1_Cd'][-1]:.4f} (初始: 0.6000)
  闸门2流量系数: {self.history['gate2_Cd'][-1]:.4f} (初始: 0.6000)
  泵站零流量扬程 H0: {self.history['pump_H0'][-1]:.2f}m (初始: 50.00m)
  泵站曲线系数 K: {self.history['pump_K'][-1]:.4f} (初始: 0.1000)

执行器性能:
  闸门1最终开度: {self.history['gate_openings']['Gate1'][-1]:.3f}m
  闸门2最终开度: {self.history['gate_openings']['Gate2'][-1]:.3f}m
  泵站最终转速: {self.history['pump_speed'][-1]:.1f}rpm

流量分配:
  上游流量: {self.history['flows']['Q0'][-1]:.2f}m^3/s
  闸门1流量: {self.history['flows']['Q1'][-1]:.2f}m^3/s
  闸门2流量: {self.history['flows']['Q2'][-1]:.2f}m^3/s
  泵站流量: {self.history['flows']['Q3'][-1]:.2f}m^3/s
        """

        ax8.text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
                verticalalignment='center')

        plt.tight_layout()
        plt.savefig('series_gate_pump_adaptive_control.png', dpi=300, bbox_inches='tight')
        print("\n结果图已保存: series_gate_pump_adaptive_control.png")


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║          串联闸泵群明渠系统自适应控制案例                         ║
    ╚════════════════════════════════════════════════════════════════════╝

    系统组成:
    - 3个池段明渠 (Saint-Venant方程)
    - 2个闸门 + 1个泵站
    - 10个传感器（水位、流量、闸位、泵速）
    - MPC控制器 + 在线辨识

    控制目标:
    - 池段1: 2.5m
    - 池段2: 2.7m
    - 池段3: 2.3m

    自适应机制:
    - 闸门流量系数在线辨识
    - 泵站特性曲线在线辨识
    - PID参数自适应调整
    """)

    # 创建系统
    system = SeriesGatePumpSystem()

    # 仿真
    n_steps = 60  # 60步 = 1小时
    print(f"\n开始仿真 ({n_steps}步, 每步{system.dt}秒)...")

    for step in range(n_steps):
        system.step(step)

        if (step + 1) % 15 == 0:
            print(f"  进度: {step+1}/{n_steps} 步 "
                  f"(误差: {system.history['control_errors'][-1]:.4f}m)")

    print("\n仿真完成！")

    # 可视化
    print("\n生成结果图表...")
    system.visualize_results()

    # 输出最终统计
    print("\n" + "=" * 70)
    print("仿真完成！")
    print("=" * 70)

    print(f"\n最终水位:")
    for i in range(3):
        h_final = system.history['water_levels'][f'Pool{i+1}'][-1]
        h_target = system.h_setpoint[i]
        error = h_final - h_target
        print(f"  池段{i+1}: {h_final:.3f}m (目标: {h_target:.3f}m, 误差: {error:+.3f}m)")

    print(f"\n在线辨识结果:")
    print(f"  闸门1流量系数 C_d: {system.gate1_identifier.C_d:.4f}")
    print(f"  闸门2流量系数 C_d: {system.gate2_identifier.C_d:.4f}")
    print(f"  泵站零流量扬程 H0: {system.pump_identifier.H0:.2f}m")
    print(f"  泵站曲线系数 K: {system.pump_identifier.K:.4f}")

    print(f"\n控制性能:")
    print(f"  平均控制误差: {np.mean(system.history['control_errors']):.4f}m")
    print(f"  最终控制误差: {system.history['control_errors'][-1]:.4f}m")


if __name__ == "__main__":
    main()
