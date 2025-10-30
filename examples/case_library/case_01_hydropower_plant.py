# -*- coding: utf-8 -*-
"""
Complete Hydropower Plant System - 完整水电站系统
==================================================

System Components / 系统组成:
- Reservoir (水库): 上游蓄水调节
- Headrace Tunnel (引水隧洞): 长距离有压输水
- Surge Tank (调压井): 缓冲水击压力
- Penstock (压力管道): 高压输水
- Turbine (水轮机): 能量转换
- Tailrace (尾水渠): 下游排水

Simulation Cases / 模拟工况:
1. Normal Operation (正常发电)
2. Load Increase (负荷突增)
3. Load Rejection (甩负荷)
4. Water Hammer Protection (水锤保护)

Author: Claude
Date: 2025-10-30
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from physics.reservoir import Reservoir
from physics.pipe import Pipe
from physics.surge_tank import SimpleSurgeTank, ThrottledSurgeTank
from physics.turbine import FrancisTurbine, KaplanTurbine
from physics.canal import Canal


class HydropowerPlant:
    """
    Complete Hydropower Plant System
    完整水电站系统

    Typical Chinese hydropower plant configuration:
    - Head: 50-200m (中低水头)
    - Capacity: 50-500MW
    - Type: Francis or Kaplan turbine
    """

    def __init__(self, plant_type='francis', capacity_mw=100.0):
        """
        Initialize hydropower plant

        Args:
            plant_type: Turbine type ('francis' or 'kaplan')
            capacity_mw: Installed capacity (MW)
        """
        self.plant_type = plant_type
        self.capacity_mw = capacity_mw

        # Physical constants
        self.g = 9.81
        self.rho = 1000.0

        # Initialize components
        self._setup_reservoir()
        self._setup_headrace_tunnel()
        self._setup_surge_tank()
        self._setup_penstock()
        self._setup_turbine()
        self._setup_tailrace()

        # State variables
        self.time = 0.0
        self.state_history = {
            'time': [],
            'reservoir_level': [],
            'surge_tank_level': [],
            'penstock_pressure': [],
            'turbine_flow': [],
            'turbine_power': [],
            'turbine_efficiency': []
        }

    def _setup_reservoir(self):
        """Setup upstream reservoir / 设置上游水库"""
        # 水库特征水位和库容参数
        normal_level = 100.0  # 正常蓄水位 (m)
        dead_level = 50.0     # 死水位 (m)
        flood_limit_level = 105.0  # 防洪限制水位 (m)
        design_level = 110.0  # 设计水位 (m)

        # 根据平均深度估算库容（假设平均深度30m，水面面积5 km²）
        total_capacity = 5e6 * 30.0  # 150 million m³
        dead_storage = 5e6 * dead_level * 0.3  # 死库容（粗略估算）

        self.reservoir = Reservoir(
            reservoir_id="Upstream_Reservoir",
            total_capacity=total_capacity,
            dead_storage=dead_storage,
            min_level=dead_level,
            normal_level=normal_level,
            flood_limit_level=flood_limit_level,
            design_level=design_level,
            catchment_area=5e6,  # 5 km² 流域面积
            has_turbine=True,
            turbine_capacity=100.0,  # 100 MW
            hydraulic_head=normal_level - 50.0  # 净水头约50m
        )
        # Initial condition
        self.reservoir.state.water_level = 95.0  # 初始水位

    def _setup_headrace_tunnel(self):
        """Setup headrace tunnel / 设置引水隧洞"""
        self.headrace = Pipe(
            name="Headrace Tunnel",
            length=3000.0,        # 3 km (中等长度)
            diameter=6.0,         # 6 m diameter (大直径)
            roughness=0.014,      # Concrete lining (混凝土衬砌)
            n_sections=31,        # Discretization
            method='rk4'
        )
        # Initial condition
        self.headrace.Q = np.ones(31) * 150.0  # 初始流量 150 m³/s

    def _setup_surge_tank(self):
        """Setup surge tank / 设置调压井"""
        if self.plant_type == 'francis':
            # Throttled surge tank for medium/high head
            # If we want area = 80 m², then diameter = sqrt(4 * 80 / π) ≈ 10.1 m
            import math
            diameter = math.sqrt(4 * 80.0 / math.pi)

            self.surge_tank = ThrottledSurgeTank(
                position=3000.0,      # At end of tunnel
                diameter=diameter,    # ~10.1 m (for 80 m² area)
                min_level=50.0,       # 最低水位
                max_level=110.0,      # 最高水位
                orifice_diameter=2.5, # 阻抗孔直径
                loss_coefficient=2.0, # 阻力系数
                initial_level=92.0    # 初始水位
            )
        else:
            # Simple surge tank for low head
            # If we want area = 100 m², then diameter = sqrt(4 * 100 / π) ≈ 11.28 m
            import math
            diameter_simple = math.sqrt(4 * 100.0 / math.pi)

            self.surge_tank = SimpleSurgeTank(
                position=3000.0,
                diameter=diameter_simple,  # ~11.28 m (for 100 m² area)
                min_level=45.0,
                max_level=105.0,
                initial_level=90.0
            )

    def _setup_penstock(self):
        """Setup penstock / 设置压力管道"""
        self.penstock = Pipe(
            name="Penstock",
            length=400.0,         # 400 m (较短)
            diameter=3.5,         # 3.5 m diameter
            roughness=0.012,      # Steel pipe (钢管)
            wave_speed=1200.0,    # 水击波速 (m/s)
            n_sections=41,
            method='rk4'
        )
        # Initial condition
        self.penstock.Q = np.ones(41) * 150.0

    def _setup_turbine(self):
        """Setup hydraulic turbine / 设置水轮机"""
        if self.plant_type == 'francis':
            # Francis turbine (混流式) - medium head
            self.turbine = FrancisTurbine(
                position=3400.0,
                rated_power=self.capacity_mw,  # MW
                rated_head=85.0,               # 设计水头 (m)
                rated_flow=150.0,              # 设计流量 (m³/s)
                rated_speed=500.0              # 额定转速 (rpm)
            )
        else:
            # Kaplan turbine (轴流式) - low head
            self.turbine = KaplanTurbine(
                position=3400.0,
                rated_power=self.capacity_mw,
                rated_head=45.0,
                rated_flow=280.0,
                rated_speed=150.0
            )

        # Operating state
        self.guide_vane_opening = 0.7  # 70% opening
        self.turbine_speed = self.turbine.rated_speed

    def _setup_tailrace(self):
        """Setup tailrace channel / 设置尾水渠"""
        # Canal parameters
        length = 1000.0
        width = 25.0
        h_normal = 3.0  # Normal depth
        area = width * h_normal  # Cross-section area
        volume_min = area * length * 0.5  # Minimum volume (half depth)
        volume_max = area * length * 2.0  # Maximum volume (double depth)

        self.tailrace = Canal(
            name="Tailrace",
            volume_min=volume_min,
            volume_max=volume_max,
            area=area,
            length=length,
            width=width,
            slope=0.001,
            manning_n=0.025,
            n_sections=51,  # Number of spatial nodes
            method='preissmann'  # Canal only supports preissmann method
        )
        # Initial condition - normal depth
        self.tailrace.h = np.ones(51) * h_normal
        self.tailrace.Q = np.ones(51) * 150.0

    def calculate_net_head(self):
        """
        Calculate net head on turbine
        计算水轮机净水头

        H_net = H_reservoir - H_surge - H_friction - H_tailrace
        """
        # Upstream head (reservoir to surge tank)
        H_reservoir = self.reservoir.state.water_level

        # Surge tank level
        H_surge = self.surge_tank.water_level

        # Friction losses in headrace (simplified estimate)
        # For a long, low-velocity tunnel, losses are typically small
        h_loss_headrace = 0.5  # m (simplified estimate)

        # Pressure at penstock inlet (surge tank outlet)
        H_penstock_inlet = H_surge

        # Friction losses in penstock (simplified estimate)
        # Darcy-Weisbach: h_f = f * (L/D) * (V²/(2g))
        # For penstock: L=400m, D=3m, V≈20m/s, f≈0.02
        # h_f ≈ 0.02 * (400/3) * (20²/(2*9.81)) ≈ 54m
        h_loss_penstock = 5.0  # m (simplified estimate, assuming lower velocity)

        # Tailrace water level (approximate)
        H_tailrace = self.tailrace.h.mean()

        # Net head
        H_net = H_penstock_inlet - h_loss_penstock - H_tailrace

        return H_net

    def simulate_normal_operation(self, duration=600.0, dt=0.1):
        """
        Simulate normal operation
        模拟正常运行工况

        Args:
            duration: Simulation duration (s)
            dt: Time step (s)
        """
        print(f"\n{'='*70}")
        print(f"Simulating Normal Operation - 正常运行工况")
        print(f"{'='*70}")
        print(f"Plant Type: {self.plant_type.capitalize()} Turbine")
        print(f"Capacity: {self.capacity_mw} MW")
        print(f"Duration: {duration} s")
        print(f"Time Step: {dt} s")
        print(f"{'='*70}\n")

        # Reset time
        self.time = 0.0
        self.state_history = {
            'time': [],
            'reservoir_level': [],
            'surge_tank_level': [],
            'penstock_pressure': [],
            'turbine_flow': [],
            'turbine_power': [],
            'turbine_efficiency': []
        }

        # Simulation loop
        n_steps = int(duration / dt)

        for step in range(n_steps):
            self.time += dt

            # Calculate turbine flow and power
            H_net = self.calculate_net_head()
            Q_turbine = self.guide_vane_opening * self.turbine.rated_flow
            P, eta, mode = self.turbine.calculate_power(
                Q_turbine, H_net,
                n=self.turbine_speed,
                opening=self.guide_vane_opening
            )

            # Update reservoir (outflow = Q_turbine)
            Q_reservoir_out = Q_turbine
            inputs_reservoir = {'inflow': 0.0, 'outflow': Q_reservoir_out}
            self.reservoir.update_high_fidelity(dt, inputs_reservoir)

            # Update headrace tunnel
            # Simplified: assume quasi-steady
            self.headrace.Q[:] = Q_turbine

            # Update surge tank
            Q_tunnel = Q_turbine
            Q_penstock = Q_turbine
            self.surge_tank.update_water_level(dt, Q_tunnel, Q_penstock)

            # Update penstock
            self.penstock.Q[:] = Q_turbine

            # Record history
            if step % 10 == 0:  # Record every 10 steps
                self.state_history['time'].append(self.time)
                self.state_history['reservoir_level'].append(self.reservoir.state.water_level)
                self.state_history['surge_tank_level'].append(self.surge_tank.water_level)
                self.state_history['penstock_pressure'].append(
                    self.rho * self.g * H_net / 1e6  # MPa
                )
                self.state_history['turbine_flow'].append(Q_turbine)
                self.state_history['turbine_power'].append(P / 1e6)  # MW
                self.state_history['turbine_efficiency'].append(eta)

            # Progress
            if step % 1000 == 0:
                print(f"t={self.time:6.1f}s | " +
                      f"H_res={self.reservoir.state.water_level:6.2f}m | " +
                      f"H_surge={self.surge_tank.water_level:6.2f}m | " +
                      f"Q={Q_turbine:6.1f}m³/s | " +
                      f"P={P/1e6:6.1f}MW | " +
                      f"η={eta*100:5.1f}%")

        print(f"\n{'='*70}")
        print(f"Normal Operation Simulation Complete")
        print(f"{'='*70}\n")

    def simulate_load_rejection(self, duration=120.0, dt=0.01):
        """
        Simulate load rejection (甩负荷)

        Sudden closure of guide vanes causing:
        - Pressure surge in penstock
        - Water level surge in surge tank
        - Flow oscillation

        Args:
            duration: Simulation duration (s)
            dt: Time step (s)
        """
        print(f"\n{'='*70}")
        print(f"Simulating Load Rejection - 甩负荷工况")
        print(f"{'='*70}")
        print(f"Event: Guide vane sudden closure at t=10s")
        print(f"Initial Opening: {self.guide_vane_opening*100:.0f}%")
        print(f"Final Opening: 10%")
        print(f"Closure Time: 5s")
        print(f"{'='*70}\n")

        # Reset
        self.time = 0.0
        self.state_history = {
            'time': [],
            'reservoir_level': [],
            'surge_tank_level': [],
            'penstock_pressure': [],
            'turbine_flow': [],
            'turbine_power': [],
            'turbine_efficiency': [],
            'guide_vane_opening': []
        }

        # Initial steady state
        Q_initial = self.guide_vane_opening * self.turbine.rated_flow
        self.headrace.Q[:] = Q_initial
        self.penstock.Q[:] = Q_initial
        self.surge_tank.water_level = 92.0

        # Simulation loop
        n_steps = int(duration / dt)

        for step in range(n_steps):
            self.time += dt

            # Guide vane closure schedule
            if self.time < 10.0:
                # Before event
                opening = 0.7
            elif self.time < 15.0:
                # Linear closure over 5 seconds
                opening = 0.7 - (0.7 - 0.1) * (self.time - 10.0) / 5.0
            else:
                # After closure
                opening = 0.1

            self.guide_vane_opening = opening

            # Calculate turbine operating point
            H_net = self.calculate_net_head()
            Q_turbine = opening * self.turbine.rated_flow * \
                       np.sqrt(max(0.1, H_net / self.turbine.rated_head))

            P, eta, mode = self.turbine.calculate_power(
                Q_turbine, H_net,
                n=self.turbine_speed,
                opening=opening
            )

            # Update surge tank (key component for load rejection)
            Q_tunnel = Q_initial  # Tunnel flow can't change instantly
            Q_penstock = Q_turbine
            self.surge_tank.update_water_level(dt, Q_tunnel, Q_penstock)

            # Gradually adjust tunnel flow
            Q_initial += (Q_turbine - Q_initial) * dt / 10.0  # Time constant ~10s

            # Record history
            if step % 100 == 0:
                self.state_history['time'].append(self.time)
                self.state_history['surge_tank_level'].append(self.surge_tank.water_level)
                self.state_history['turbine_flow'].append(Q_turbine)
                self.state_history['turbine_power'].append(P / 1e6)
                self.state_history['guide_vane_opening'].append(opening)

        print(f"\n{'='*70}")
        print(f"Load Rejection Simulation Complete")
        print(f"Max Surge Tank Level: {max(self.state_history['surge_tank_level']):.2f} m")
        print(f"Min Surge Tank Level: {min(self.state_history['surge_tank_level']):.2f} m")
        print(f"{'='*70}\n")

    def plot_results(self, case_name='normal'):
        """
        Plot simulation results
        绘制仿真结果

        Args:
            case_name: Case identifier ('normal' or 'load_rejection')
        """
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(3, 2, hspace=0.3, wspace=0.3)

        t = np.array(self.state_history['time'])

        if case_name == 'normal':
            # Normal operation plots
            # 1. Reservoir and surge tank levels
            ax1 = fig.add_subplot(gs[0, :])
            ax1.plot(t, self.state_history['reservoir_level'],
                    'b-', linewidth=2, label='Reservoir Level')
            ax1.plot(t, self.state_history['surge_tank_level'],
                    'r-', linewidth=2, label='Surge Tank Level')
            ax1.set_xlabel('Time (s)', fontsize=12)
            ax1.set_ylabel('Water Level (m)', fontsize=12)
            ax1.set_title('Water Levels - 水位变化', fontsize=14, fontweight='bold')
            ax1.legend(fontsize=11)
            ax1.grid(True, alpha=0.3)

            # 2. Turbine flow
            ax2 = fig.add_subplot(gs[1, 0])
            ax2.plot(t, self.state_history['turbine_flow'],
                    'g-', linewidth=2)
            ax2.set_xlabel('Time (s)', fontsize=12)
            ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
            ax2.set_title('Turbine Flow - 水轮机流量', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)

            # 3. Turbine power
            ax3 = fig.add_subplot(gs[1, 1])
            ax3.plot(t, self.state_history['turbine_power'],
                    'm-', linewidth=2)
            ax3.set_xlabel('Time (s)', fontsize=12)
            ax3.set_ylabel('Power (MW)', fontsize=12)
            ax3.set_title('Turbine Power - 水轮机功率', fontsize=14, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # 4. Efficiency
            ax4 = fig.add_subplot(gs[2, 0])
            ax4.plot(t, np.array(self.state_history['turbine_efficiency']) * 100,
                    'c-', linewidth=2)
            ax4.set_xlabel('Time (s)', fontsize=12)
            ax4.set_ylabel('Efficiency (%)', fontsize=12)
            ax4.set_title('Turbine Efficiency - 水轮机效率', fontsize=14, fontweight='bold')
            ax4.grid(True, alpha=0.3)

            # 5. Penstock pressure
            ax5 = fig.add_subplot(gs[2, 1])
            ax5.plot(t, self.state_history['penstock_pressure'],
                    'orange', linewidth=2)
            ax5.set_xlabel('Time (s)', fontsize=12)
            ax5.set_ylabel('Pressure (MPa)', fontsize=12)
            ax5.set_title('Penstock Pressure - 压力管道压力', fontsize=14, fontweight='bold')
            ax5.grid(True, alpha=0.3)

        else:  # load_rejection
            # Load rejection plots
            # 1. Surge tank level
            ax1 = fig.add_subplot(gs[0, :])
            ax1.plot(t, self.state_history['surge_tank_level'],
                    'r-', linewidth=2)
            ax1.axhline(y=self.surge_tank.max_level, color='r',
                       linestyle='--', label='Max Level')
            ax1.axhline(y=self.surge_tank.min_level, color='b',
                       linestyle='--', label='Min Level')
            ax1.set_xlabel('Time (s)', fontsize=12)
            ax1.set_ylabel('Water Level (m)', fontsize=12)
            ax1.set_title('Surge Tank Level During Load Rejection - 甩负荷时调压井水位',
                         fontsize=14, fontweight='bold')
            ax1.legend(fontsize=11)
            ax1.grid(True, alpha=0.3)

            # 2. Turbine flow
            ax2 = fig.add_subplot(gs[1, 0])
            ax2.plot(t, self.state_history['turbine_flow'],
                    'g-', linewidth=2)
            ax2.set_xlabel('Time (s)', fontsize=12)
            ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
            ax2.set_title('Turbine Flow - 水轮机流量', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)

            # 3. Guide vane opening
            ax3 = fig.add_subplot(gs[1, 1])
            ax3.plot(t, np.array(self.state_history['guide_vane_opening']) * 100,
                    'purple', linewidth=2)
            ax3.set_xlabel('Time (s)', fontsize=12)
            ax3.set_ylabel('Opening (%)', fontsize=12)
            ax3.set_title('Guide Vane Opening - 导叶开度', fontsize=14, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # 4. Turbine power
            ax4 = fig.add_subplot(gs[2, :])
            ax4.plot(t, self.state_history['turbine_power'],
                    'm-', linewidth=2)
            ax4.set_xlabel('Time (s)', fontsize=12)
            ax4.set_ylabel('Power (MW)', fontsize=12)
            ax4.set_title('Turbine Power - 水轮机功率', fontsize=14, fontweight='bold')
            ax4.grid(True, alpha=0.3)

        plt.suptitle(f'{self.plant_type.capitalize()} Hydropower Plant - ' +
                    f'{self.capacity_mw} MW - {case_name.replace("_", " ").title()}',
                    fontsize=16, fontweight='bold', y=0.995)

        # Save figure
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        filename = f'hydropower_{case_name}_{self.plant_type}.png'
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f"✓ Results saved to: {filepath}")

        plt.show()


def main():
    """Main execution function"""

    print(f"\n{'#'*70}")
    print(f"#{'  HydroClaude - Complete Hydropower Plant Simulation  ':^68}#")
    print(f"#{'  完整水电站系统仿真  ':^68}#")
    print(f"{'#'*70}\n")

    # Create hydropower plant
    plant = HydropowerPlant(plant_type='francis', capacity_mw=100.0)

    # Simulation 1: Normal Operation
    print("\n>>> Simulation 1: Normal Operation <<<\n")
    plant.simulate_normal_operation(duration=600.0, dt=0.1)
    plant.plot_results(case_name='normal')

    # Simulation 2: Load Rejection
    print("\n>>> Simulation 2: Load Rejection <<<\n")
    plant.simulate_load_rejection(duration=120.0, dt=0.01)
    plant.plot_results(case_name='load_rejection')

    print(f"\n{'#'*70}")
    print(f"#{'  All Simulations Complete!  ':^68}#")
    print(f"{'#'*70}\n")


if __name__ == '__main__':
    main()
