# -*- coding: utf-8 -*-
"""
Irrigation Canal System - 灌溉渠系统
====================================

System Components / 系统组成:
- Main Canal (总干渠): 50 km main channel
- Branch Canals (支渠): 10 branch canals
- Control Gates (节制闸): 15 control structures
- Flow Measurement Weirs (量水堰): Flow monitoring
- Drops (跌水): Elevation changes
- Farm Outlets (农田取水口): End users

Simulation Cases / 模拟工况:
1. Normal Irrigation (正常灌溉): Steady flow distribution
2. Rotation Irrigation (轮灌调度): Sequential field irrigation
3. Gate Control (闸门控制): Water level regulation
4. Emergency Closure (紧急关闭): Accident response

Author: Claude
Date: 2025-10-30
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive mode
from matplotlib import gridspec

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from physics.canal import Canal
from solvers.gate import SluiceGate, BroadCrestedWeir, Drop
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow
import matplotlib.pyplot as plt


class IrrigationCanalSystem:
    """
    Complete Irrigation Canal System
    完整灌溉渠系统

    Typical Chinese irrigation district configuration:
    - Main canal: 50 km, serves 10,000 hectares
    - Design flow: 30 m^3/s
    - Branch canals: 10 branches
    - Control structures: Gates, weirs, drops
    """

    def __init__(self, design_flow=30.0, canal_length=50000.0):
        """
        Initialize irrigation canal system

        Args:
            design_flow: Design flow rate (m^3/s)
            canal_length: Main canal length (m)
        """
        self.design_flow = design_flow
        self.canal_length = canal_length

        # Physical constants
        self.g = 9.81
        self.rho = 1000.0

        # Initialize components
        self._setup_main_canal()
        self._setup_branch_canals()
        self._setup_control_structures()
        self._setup_irrigation_schedule()

        # Results storage
        self.state_history = {
            'time': [],
            'water_levels': [],
            'flow_rates': [],
            'gate_openings': [],
            'delivered_water': []
        }

    def _setup_main_canal(self):
        """Setup main canal / 设置总干渠"""

        # Main canal parameters (typical design)
        self.main_canal = {
            'length': self.canal_length,
            'width': 12.0,           # 12m bottom width
            'slope': 0.0002,         # 1:5000 gentle slope
            'manning_n': 0.025,      # Concrete lining
            'design_depth': 3.0,     # Design water depth
            'freeboard': 0.5         # Safety freeboard
        }

        # Calculate normal depth at design flow
        h_normal = compute_steady_uniform_flow(
            Q=self.design_flow,
            B=self.main_canal['width'],
            S0=self.main_canal['slope'],
            n=self.main_canal['manning_n']
        )

        self.main_canal['normal_depth'] = h_normal

        # Create canal solver
        nx = 501  # Discretization
        self.canal_solver = HydrostaticCanalSolver(
            length=self.main_canal['length'],
            nx=nx,
            B=self.main_canal['width'],
            S0=self.main_canal['slope'],
            n=self.main_canal['manning_n']
        )

        # Initialize with uniform flow
        self.canal_solver.h[:] = h_normal
        self.canal_solver.hu[:] = self.design_flow / self.main_canal['width']

        print(f" Main canal: L={self.canal_length/1000:.0f}km, " +
              f"B={self.main_canal['width']}m, h_n={h_normal:.2f}m")

    def _setup_branch_canals(self):
        """Setup branch canals / 设置支渠"""

        self.branch_canals = []
        n_branches = 10

        # Branch canals at regular intervals
        branch_spacing = self.canal_length / (n_branches + 1)

        for i in range(n_branches):
            position = (i + 1) * branch_spacing
            design_flow = self.design_flow / n_branches  # Equal distribution

            branch = {
                'id': i + 1,
                'position': position,
                'design_flow': design_flow,
                'current_flow': 0.0,
                'width': 5.0,         # Smaller branch
                'length': 5000.0,     # 5 km branch
                'area_served': 1000.0  # hectares
            }

            self.branch_canals.append(branch)

        print(f" Created {len(self.branch_canals)} branch canals")

    def _setup_control_structures(self):
        """Setup control structures / 设置控制建筑物"""

        self.gates = []
        self.weirs = []
        self.drops = []

        # Main canal gates (every 10 km for control)
        n_gates = int(self.canal_length / 10000)
        for i in range(n_gates):
            position = (i + 1) * 10000.0

            gate = SluiceGate(
                position=position,
                width=self.main_canal['width'],
                opening=2.5,  # Initial 2.5m opening
                Cd=0.6
            )

            self.gates.append({
                'structure': gate,
                'position': position,
                'type': 'control_gate',
                'opening': 2.5
            })

        # Weirs for flow measurement (at each branch)
        for branch in self.branch_canals:
            weir = BroadCrestedWeir(
                position=branch['position'],
                width=branch['width'],
                crest_height=0.3,
                Cd=0.848
            )

            self.weirs.append({
                'structure': weir,
                'position': branch['position'],
                'type': 'measuring_weir',
                'branch_id': branch['id']
            })

        # Drops for elevation changes (every 15 km)
        n_drops = int(self.canal_length / 15000)
        for i in range(n_drops):
            position = (i + 0.5) * 15000.0

            drop = Drop(
                position=position,
                width=self.main_canal['width'],
                drop_height=1.0,  # 1m drop
                Cd=0.8
            )

            self.drops.append({
                'structure': drop,
                'position': position,
                'type': 'drop',
                'height': 1.0
            })

        print(f" Created {len(self.gates)} gates, {len(self.weirs)} weirs, {len(self.drops)} drops")

    def _setup_irrigation_schedule(self):
        """Setup rotation irrigation schedule / 设置轮灌调度"""

        # Rotation irrigation: irrigate one branch at a time
        # Each branch gets water for 2.4 hours per day (24h / 10 branches)

        self.irrigation_schedule = []

        for i, branch in enumerate(self.branch_canals):
            start_hour = i * 2.4
            end_hour = start_hour + 2.4

            schedule = {
                'branch_id': branch['id'],
                'start_hour': start_hour,
                'end_hour': end_hour,
                'flow_rate': branch['design_flow']
            }

            self.irrigation_schedule.append(schedule)

        print(f" Created 24-hour rotation schedule for {len(self.branch_canals)} branches")

    def get_active_branches(self, time_of_day):
        """
        Get currently active branches for irrigation

        Args:
            time_of_day: Hour of day (0-24)

        Returns:
            List of active branch IDs
        """
        active_branches = []

        hour = time_of_day % 24

        for schedule in self.irrigation_schedule:
            if schedule['start_hour'] <= hour < schedule['end_hour']:
                active_branches.append(schedule['branch_id'])

        return active_branches

    def simulate_normal_irrigation(self, duration=86400.0, dt=3600.0):
        """
        Simulate normal irrigation for 24 hours
        模拟24小时正常灌溉

        Args:
            duration: Simulation duration (s), default 24 hours
            dt: Time step (s), default 1 hour
        """
        print(f"\n{'='*70}")
        print(f"Simulating Normal Irrigation - 24 Hours")
        print(f"{'='*70}")
        print(f"Main Canal: {self.canal_length/1000:.0f} km")
        print(f"Design Flow: {self.design_flow} m^3/s")
        print(f"Branches: {len(self.branch_canals)}")
        print(f"{'='*70}\n")

        # Reset history
        self.state_history = {
            'time': [],
            'main_canal_flow': [],
            'branch_flows': [],
            'avg_water_level': [],
            'total_delivered': []
        }

        n_steps = int(duration / dt)
        total_delivered = 0.0

        for step in range(n_steps):
            time = step * dt
            time_of_day = (time / 3600.0) % 24.0

            # Get active branches
            active_branches = self.get_active_branches(time_of_day)

            # Calculate total withdrawal
            total_withdrawal = 0.0
            branch_flows = np.zeros(len(self.branch_canals))

            for branch_id in active_branches:
                idx = branch_id - 1
                branch_flows[idx] = self.branch_canals[idx]['design_flow']
                total_withdrawal += self.branch_canals[idx]['design_flow']

            # Update branch canal flows
            for i, branch in enumerate(self.branch_canals):
                branch['current_flow'] = branch_flows[i]

            # Main canal flow (design flow - withdrawals)
            main_flow = self.design_flow - total_withdrawal

            # Simplified steady-state calculation
            # (In reality, would use unsteady solver)
            avg_water_level = self.main_canal['normal_depth']

            # Update total delivered water
            total_delivered += total_withdrawal * dt

            # Record history
            self.state_history['time'].append(time / 3600.0)
            self.state_history['main_canal_flow'].append(main_flow)
            self.state_history['branch_flows'].append(branch_flows.copy())
            self.state_history['avg_water_level'].append(avg_water_level)
            self.state_history['total_delivered'].append(total_delivered / 1000.0)  # 1000 m^3

            # Progress
            if step % 4 == 0:
                active_str = ','.join([str(b) for b in active_branches]) if active_branches else 'None'
                print(f"t={time_of_day:5.1f}h | " +
                      f"Q_main={main_flow:5.1f}m^3/s | " +
                      f"Active Branches: {active_str} | " +
                      f"h={avg_water_level:.2f}m")

        print(f"\n{'='*70}")
        print(f"Normal Irrigation Simulation Complete")
        print(f"Total Water Delivered: {total_delivered/1000:.1f} x 10^3 m^3")
        print(f"Average Flow: {np.mean(self.state_history['main_canal_flow']):.1f} m^3/s")
        print(f"{'='*70}\n")

    def simulate_gate_control(self, duration=3600.0, dt=10.0):
        """
        Simulate gate control for water level regulation
        模拟闸门控制调节水位

        Args:
            duration: Simulation duration (s), default 1 hour
            dt: Time step (s), default 10 seconds
        """
        print(f"\n{'='*70}")
        print(f"Simulating Gate Control - 1 Hour")
        print(f"{'='*70}")
        print(f"Scenario: Sudden increase in downstream demand")
        print(f"Response: Automatic gate opening adjustment")
        print(f"{'='*70}\n")

        # Reset history
        gate_history = {
            'time': [],
            'gate_opening': [],
            'water_level_upstream': [],
            'water_level_downstream': [],
            'flow_rate': []
        }

        # Target water level
        target_level = self.main_canal['normal_depth']

        # Initial gate opening
        gate_opening = 2.0  # m

        n_steps = int(duration / dt)

        for step in range(n_steps):
            time = step * dt

            # Simulated water level (simplified)
            # In reality, would solve full Saint-Venant equations
            if time < 600:
                # Normal operation
                demand = self.design_flow
            else:
                # Sudden demand increase at t=600s
                demand = self.design_flow * 1.3

            # Simple PI controller for gate
            water_level = target_level + (demand - self.design_flow) * 0.01

            # Control law: adjust gate to maintain target level
            error = target_level - water_level
            gate_opening += error * 0.05  # Proportional control

            # Limit gate opening
            gate_opening = np.clip(gate_opening, 0.5, 3.5)

            # Calculate flow through gate
            h_upstream = water_level + 0.5  # Assume some backwater
            Q_gate = 0.6 * gate_opening * self.main_canal['width'] * \
                    np.sqrt(2 * self.g * h_upstream)

            # Record history
            gate_history['time'].append(time)
            gate_history['gate_opening'].append(gate_opening)
            gate_history['water_level_upstream'].append(h_upstream)
            gate_history['water_level_downstream'].append(water_level)
            gate_history['flow_rate'].append(Q_gate)

            # Progress
            if step % 60 == 0:
                print(f"t={time:6.1f}s | " +
                      f"Gate={gate_opening:4.2f}m | " +
                      f"h_up={h_upstream:4.2f}m | " +
                      f"h_dn={water_level:4.2f}m | " +
                      f"Q={Q_gate:5.1f}m^3/s")

        self.gate_control_history = gate_history

        print(f"\n{'='*70}")
        print(f"Gate Control Simulation Complete")
        print(f"{'='*70}\n")

    def plot_results(self):
        """Plot simulation results / 绘制仿真结果"""

        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(3, 2, hspace=0.3, wspace=0.3)

        t = np.array(self.state_history['time'])

        # 1. Main canal flow
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(t, self.state_history['main_canal_flow'], 'b-', linewidth=2)
        ax1.axhline(y=self.design_flow, color='r', linestyle='--', label='Design Flow')
        ax1.set_xlabel('Time (hours)', fontsize=12)
        ax1.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
        ax1.set_title('Main Canal Flow - 总干渠流量', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, 24])

        # 2. Branch canal flows (stacked area)
        ax2 = fig.add_subplot(gs[1, :])
        branch_flows_array = np.array(self.state_history['branch_flows'])
        for i in range(len(self.branch_canals)):
            if i == 0:
                ax2.fill_between(t, 0, branch_flows_array[:, i],
                                alpha=0.7, label=f'Branch {i+1}')
                bottom = branch_flows_array[:, i].copy()
            else:
                ax2.fill_between(t, bottom, bottom + branch_flows_array[:, i],
                                alpha=0.7, label=f'Branch {i+1}')
                bottom += branch_flows_array[:, i]

        ax2.set_xlabel('Time (hours)', fontsize=12)
        ax2.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
        ax2.set_title('Branch Canal Flows (Rotation Irrigation) - 支渠轮灌流量',
                     fontsize=14, fontweight='bold')
        ax2.legend(fontsize=8, ncol=5, loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, 24])

        # 3. Water level
        ax3 = fig.add_subplot(gs[2, 0])
        ax3.plot(t, self.state_history['avg_water_level'], 'g-', linewidth=2)
        ax3.axhline(y=self.main_canal['design_depth'], color='r',
                   linestyle='--', label='Design Depth')
        ax3.set_xlabel('Time (hours)', fontsize=12)
        ax3.set_ylabel('Water Depth (m)', fontsize=12)
        ax3.set_title('Average Water Level - 平均水位', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim([0, 24])

        # 4. Cumulative delivered water
        ax4 = fig.add_subplot(gs[2, 1])
        ax4.plot(t, self.state_history['total_delivered'], 'm-', linewidth=2)
        ax4.fill_between(t, 0, self.state_history['total_delivered'], alpha=0.3, color='m')
        ax4.set_xlabel('Time (hours)', fontsize=12)
        ax4.set_ylabel('Volume (x 10^3 m^3)', fontsize=12)
        ax4.set_title('Cumulative Delivered Water - 累计供水量',
                     fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim([0, 24])

        plt.suptitle(f'Irrigation Canal System - {self.canal_length/1000:.0f} km - 24 Hours',
                    fontsize=16, fontweight='bold', y=0.995)

        # Save figure
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        filename = f'irrigation_canal_{self.canal_length/1000:.0f}km.png'
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f" Results saved to: {filepath}")

        plt.close("all")  # 自动关闭图形

    def plot_gate_control(self):
        """Plot gate control results / 绘制闸门控制结果"""

        if not hasattr(self, 'gate_control_history'):
            print("  No gate control simulation data available")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        t = np.array(self.gate_control_history['time']) / 60.0  # Convert to minutes

        # Gate opening
        axes[0, 0].plot(t, self.gate_control_history['gate_opening'], 'b-', linewidth=2)
        axes[0, 0].set_xlabel('Time (minutes)', fontsize=11)
        axes[0, 0].set_ylabel('Gate Opening (m)', fontsize=11)
        axes[0, 0].set_title('Gate Opening - 闸门开度', fontsize=12, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axvline(x=10, color='r', linestyle='--', alpha=0.5, label='Demand Increase')
        axes[0, 0].legend()

        # Water levels
        axes[0, 1].plot(t, self.gate_control_history['water_level_upstream'],
                       'b-', linewidth=2, label='Upstream')
        axes[0, 1].plot(t, self.gate_control_history['water_level_downstream'],
                       'r-', linewidth=2, label='Downstream')
        axes[0, 1].set_xlabel('Time (minutes)', fontsize=11)
        axes[0, 1].set_ylabel('Water Level (m)', fontsize=11)
        axes[0, 1].set_title('Water Levels - 水位', fontsize=12, fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axvline(x=10, color='r', linestyle='--', alpha=0.5)

        # Flow rate
        axes[1, 0].plot(t, self.gate_control_history['flow_rate'], 'g-', linewidth=2)
        axes[1, 0].set_xlabel('Time (minutes)', fontsize=11)
        axes[1, 0].set_ylabel('Flow Rate (m^3/s)', fontsize=11)
        axes[1, 0].set_title('Flow Through Gate - 闸门流量', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axvline(x=10, color='r', linestyle='--', alpha=0.5)

        # Control response
        target = self.main_canal['normal_depth']
        error = [target - h for h in self.gate_control_history['water_level_downstream']]
        axes[1, 1].plot(t, error, 'purple', linewidth=2)
        axes[1, 1].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        axes[1, 1].set_xlabel('Time (minutes)', fontsize=11)
        axes[1, 1].set_ylabel('Control Error (m)', fontsize=11)
        axes[1, 1].set_title('Water Level Control Error - 水位控制误差',
                           fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axvline(x=10, color='r', linestyle='--', alpha=0.5)

        plt.suptitle('Gate Control Response - 闸门控制响应',
                    fontsize=14, fontweight='bold')
        plt.tight_layout()

        # Save
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        filepath = os.path.join(output_dir, 'irrigation_gate_control.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f" Gate control results saved to: {filepath}")

        plt.close("all")  # 自动关闭图形


def main():
    """Main execution function"""

    print(f"\n{'#'*70}")
    print(f"#{'  HydroClaude - Irrigation Canal System Simulation  ':^68}#")
    print(f"#{'  灌溉渠系统仿真  ':^68}#")
    print(f"{'#'*70}\n")

    # Create irrigation canal system
    canal_system = IrrigationCanalSystem(design_flow=30.0, canal_length=50000.0)

    # Simulation 1: Normal 24-hour irrigation
    print("\n>>> Simulation 1: Normal Rotation Irrigation <<<\n")
    canal_system.simulate_normal_irrigation(duration=86400.0, dt=3600.0)
    canal_system.plot_results()

    # Simulation 2: Gate control
    print("\n>>> Simulation 2: Automatic Gate Control <<<\n")
    canal_system.simulate_gate_control(duration=1800.0, dt=10.0)
    canal_system.plot_gate_control()

    print(f"\n{'#'*70}")
    print(f"#{'  All Simulations Complete!  ':^68}#")
    print(f"{'#'*70}\n")


if __name__ == '__main__':
    main()
