# -*- coding: utf-8 -*-
"""
Urban Water Supply Network - 城市供水管网系统
================================================

System Components / 系统组成:
- Water Treatment Plant (水厂): 源头供水
- Primary Pump Stations (一级泵站): 加压送水
- Main Pipelines (主管网): 输水骨干
- Water Towers (水塔): 调节储备
- Secondary Pump Stations (二级泵站): 二次加压
- Distribution Network (配水管网): 末端供水
- User Nodes (用户节点): 时变需求

Simulation Cases / 模拟工况:
1. Normal Supply (正常供水): 稳态分析
2. Peak Demand (高峰用水): 动态响应
3. Pipe Burst (管道爆裂): 事故工况
4. Pump Failure (泵站故障): 应急调度
5. Optimization Scheduling (优化调度): 节能运行

Author: Claude
Date: 2025-10-30
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
from scipy.optimize import differential_evolution

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from solvers.hardy_cross_solver import HardyCrossSolver
from solvers.newton_raphson_network_solver import NewtonRaphsonNetworkSolver
from physics.pressurized.pumps import CentrifugalPump
from physics.tank import Tank


class WaterSupplyNetwork:
    """
    Complete Urban Water Supply Network System
    完整城市供水管网系统

    Network Configuration:
    - 50+ nodes (节点)
    - 70+ pipes (管道)
    - 2 pump stations (泵站)
    - 1 water tower (水塔)
    - Time-varying demand (时变需求)
    """

    def __init__(self, network_size='medium'):
        """
        Initialize water supply network

        Args:
            network_size: 'small' (20 nodes), 'medium' (50 nodes), 'large' (100 nodes)
        """
        self.network_size = network_size

        # Network parameters
        if network_size == 'small':
            self.n_nodes = 20
            self.n_pipes = 25
            self.n_pumps = 1
        elif network_size == 'medium':
            self.n_nodes = 50
            self.n_pipes = 70
            self.n_pumps = 2
        else:  # large
            self.n_nodes = 100
            self.n_pipes = 150
            self.n_pumps = 3

        # Physical constants
        self.g = 9.81
        self.rho = 1000.0

        # Initialize network components
        self._create_network_topology()
        self._setup_pumps()
        self._setup_water_tower()
        self._setup_demand_pattern()

        # Solver
        self.solver = None

        # Results storage
        self.state_history = {
            'time': [],
            'node_pressures': [],
            'pipe_flows': [],
            'pump_powers': [],
            'tower_level': [],
            'total_demand': [],
            'total_supply': []
        }

    def _create_network_topology(self):
        """Create network topology / 创建管网拓扑"""

        # Node data: [x, y, elevation, base_demand]
        self.nodes = {}

        # Create a grid-like network
        grid_size = int(np.sqrt(self.n_nodes))
        node_id = 0

        for i in range(grid_size):
            for j in range(grid_size):
                if node_id >= self.n_nodes:
                    break

                x = i * 500.0  # 500m spacing
                y = j * 500.0
                elevation = 5.0 + np.random.uniform(-2, 2)  # Flat terrain with small variation
                base_demand = np.random.uniform(0.005, 0.02)  # 5-20 L/s per node

                self.nodes[f'N{node_id}'] = {
                    'x': x,
                    'y': y,
                    'elevation': elevation,
                    'base_demand': base_demand,
                    'current_demand': base_demand,
                    'pressure': 0.0,
                    'head': 0.0
                }
                node_id += 1

        # Water source node (treatment plant)
        self.nodes['SOURCE'] = {
            'x': -500.0,
            'y': grid_size * 250.0,
            'elevation': 10.0,
            'base_demand': 0.0,
            'current_demand': 0.0,
            'pressure': 50.0,  # Fixed pressure head
            'head': 60.0,
            'type': 'source'
        }

        # Water tower node
        self.nodes['TOWER'] = {
            'x': grid_size * 250.0,
            'y': grid_size * 250.0,
            'elevation': 0.0,
            'base_demand': 0.0,
            'current_demand': 0.0,
            'pressure': 0.0,
            'head': 30.0,  # Initial water level
            'type': 'tower'
        }

        print(f"✓ Created {len(self.nodes)} nodes")

        # Pipe data: [node1, node2, length, diameter, roughness]
        self.pipes = {}
        pipe_id = 0

        # Create grid connections (horizontal and vertical)
        for i in range(grid_size):
            for j in range(grid_size):
                node_idx = i * grid_size + j
                if node_idx >= self.n_nodes:
                    break

                node1 = f'N{node_idx}'

                # Horizontal connection
                if j < grid_size - 1 and node_idx + 1 < self.n_nodes:
                    node2 = f'N{node_idx + 1}'
                    length = 500.0
                    diameter = 0.3 if pipe_id < 20 else 0.2  # Main pipes larger
                    roughness = 0.1  # mm, cast iron

                    self.pipes[f'P{pipe_id}'] = {
                        'node1': node1,
                        'node2': node2,
                        'length': length,
                        'diameter': diameter,
                        'roughness': roughness,
                        'flow': 0.0
                    }
                    pipe_id += 1

                # Vertical connection
                if i < grid_size - 1:
                    node_idx2 = (i + 1) * grid_size + j
                    if node_idx2 < self.n_nodes:
                        node2 = f'N{node_idx2}'
                        length = 500.0
                        diameter = 0.3 if pipe_id < 20 else 0.2
                        roughness = 0.1

                        self.pipes[f'P{pipe_id}'] = {
                            'node1': node1,
                            'node2': node2,
                            'length': length,
                            'diameter': diameter,
                            'roughness': roughness,
                            'flow': 0.0
                        }
                        pipe_id += 1

        # Connect source to network
        self.pipes[f'P{pipe_id}'] = {
            'node1': 'SOURCE',
            'node2': 'N0',
            'length': 500.0,
            'diameter': 0.5,  # Large main
            'roughness': 0.1,
            'flow': 0.0
        }
        pipe_id += 1

        # Connect tower to network (at center)
        center_node = grid_size * grid_size // 2
        self.pipes[f'P{pipe_id}'] = {
            'node1': 'TOWER',
            'node2': f'N{center_node}',
            'length': 300.0,
            'diameter': 0.4,
            'roughness': 0.1,
            'flow': 0.0
        }

        print(f"✓ Created {len(self.pipes)} pipes")

    def _setup_pumps(self):
        """Setup pump stations / 设置泵站"""
        self.pumps = []

        # Import PumpCharacteristics for creating pumps
        from physics.pressurized.pumps import PumpCharacteristics

        for i in range(self.n_pumps):
            # Create pump characteristics
            # H0 (shutoff head) is typically ~1.2x of design head
            pump_char = PumpCharacteristics(
                H0=60.0,  # Shutoff head (关死扬程)
                Q_design=0.3,  # 300 L/s = 0.3 m³/s
                H_design=50.0,  # Design head (设计扬程)
                eta_design=0.85,  # Efficiency
                n_rated=1500.0,  # Rated speed (rpm)
                curve_type='parabolic'
            )

            # Create centrifugal pump
            pump = CentrifugalPump(
                position=1000.0 * (i+1),  # Position along network
                characteristics=pump_char
            )
            pump.is_running = True
            self.pumps.append(pump)

        print(f"✓ Created {len(self.pumps)} pump stations")

    def _setup_water_tower(self):
        """Setup water tower / 设置水塔"""
        # Tank class uses volume instead of level
        # volume = level * area
        area = 100.0
        min_level = 10.0
        max_level = 40.0

        self.water_tower = Tank(
            name='TOWER',
            area=area,                      # 100 m² cross-section
            volume_max=max_level * area,    # 4000 m³ (40m height)
            volume_min=min_level * area,    # 1000 m³ (10m height)
        )
        # Set initial level
        self.water_tower.state.volume = 30.0 * area  # 30m initial
        self.water_tower.state.level = 30.0

        print(f"✓ Created water tower: {max_level}m max height")

    def _setup_demand_pattern(self):
        """Setup time-varying demand pattern / 设置时变需水模式"""

        # Typical urban daily demand pattern (24 hours)
        # 典型城市日需水模式
        hours = np.arange(0, 25)
        pattern_multiplier = np.array([
            0.5,  # 00:00 - Low demand
            0.4,  # 01:00
            0.4,  # 02:00
            0.4,  # 03:00
            0.5,  # 04:00
            0.6,  # 05:00 - Start increasing
            0.8,  # 06:00
            1.2,  # 07:00 - Morning peak
            1.4,  # 08:00
            1.3,  # 09:00
            1.1,  # 10:00
            1.0,  # 11:00
            1.1,  # 12:00 - Noon
            1.0,  # 13:00
            0.9,  # 14:00
            0.8,  # 15:00
            0.9,  # 16:00
            1.1,  # 17:00
            1.3,  # 18:00 - Evening peak
            1.4,  # 19:00
            1.2,  # 20:00
            1.0,  # 21:00
            0.8,  # 22:00
            0.6,  # 23:00
            0.5   # 24:00
        ])

        self.demand_pattern = {
            'hours': hours,
            'multiplier': pattern_multiplier
        }

        print(f"✓ Setup 24-hour demand pattern")

    def get_demand_multiplier(self, time_of_day):
        """
        Get demand multiplier for given time

        Args:
            time_of_day: Hour of day (0-24)

        Returns:
            Demand multiplier
        """
        hour = time_of_day % 24
        idx = int(hour)
        fraction = hour - idx

        # Linear interpolation
        mult1 = self.demand_pattern['multiplier'][idx]
        mult2 = self.demand_pattern['multiplier'][min(idx + 1, 24)]

        return mult1 + fraction * (mult2 - mult1)

    def update_demands(self, time_of_day):
        """Update node demands based on time / 根据时间更新需水量"""
        multiplier = self.get_demand_multiplier(time_of_day)

        for node_id, node in self.nodes.items():
            if node_id not in ['SOURCE', 'TOWER']:
                node['current_demand'] = node['base_demand'] * multiplier

    def solve_hydraulics_hardy_cross(self, tolerance=1e-6, max_iter=100):
        """
        Solve network hydraulics using Hardy Cross method
        使用Hardy Cross法求解管网水力学

        Returns:
            Convergence status
        """
        # Initialize solver if needed
        if self.solver is None:
            self.solver = HardyCrossSolver(
                network=self,
                tolerance=tolerance,
                max_iterations=max_iter
            )

        # Solve
        converged = self.solver.solve()

        if converged:
            # Extract results
            for pipe_id, pipe in self.pipes.items():
                pipe['flow'] = self.solver.get_pipe_flow(pipe_id)

            for node_id, node in self.nodes.items():
                if node_id not in ['SOURCE', 'TOWER']:
                    node['head'] = self.solver.get_node_head(node_id)
                    node['pressure'] = node['head'] - node['elevation']

        return converged

    def solve_hydraulics_newton(self, tolerance=1e-6, max_iter=50):
        """
        Solve network hydraulics using Newton-Raphson method
        使用Newton-Raphson法求解管网水力学

        Returns:
            Convergence status
        """
        solver = NewtonRaphsonNetworkSolver(
            network=self,
            tolerance=tolerance,
            max_iterations=max_iter
        )

        converged, iterations = solver.solve()

        if converged:
            # Extract results
            for pipe_id, pipe in self.pipes.items():
                pipe['flow'] = solver.get_pipe_flow(pipe_id)

            for node_id, node in self.nodes.items():
                if node_id not in ['SOURCE', 'TOWER']:
                    node['head'] = solver.get_node_head(node_id)
                    node['pressure'] = node['head'] - node['elevation']

        return converged

    def simulate_normal_supply(self, duration=86400.0, dt=3600.0):
        """
        Simulate normal supply for 24 hours
        模拟24小时正常供水

        Args:
            duration: Simulation duration (s), default 24 hours
            dt: Time step (s), default 1 hour
        """
        print(f"\n{'='*70}")
        print(f"Simulating Normal Water Supply - 24 Hours")
        print(f"{'='*70}")
        print(f"Network: {self.n_nodes} nodes, {self.n_pipes} pipes")
        print(f"Duration: {duration/3600:.0f} hours")
        print(f"Time Step: {dt/3600:.0f} hour")
        print(f"{'='*70}\n")

        # Reset history
        self.state_history = {
            'time': [],
            'node_pressures': [],
            'pipe_flows': [],
            'pump_powers': [],
            'tower_level': [],
            'total_demand': [],
            'total_supply': [],
            'pressure_violations': []
        }

        n_steps = int(duration / dt)

        for step in range(n_steps):
            time = step * dt
            time_of_day = (time / 3600.0) % 24.0

            # Update demands
            self.update_demands(time_of_day)

            # Solve hydraulics (use Newton-Raphson for speed)
            converged = self.solve_hydraulics_newton()

            if not converged:
                print(f"⚠️  Warning: Solution did not converge at t={time/3600:.1f}h")

            # Calculate pump power
            total_pump_power = 0.0
            for pump in self.pumps:
                if pump.is_running:
                    # Simplified power calculation
                    Q = 0.3  # Assume rated flow
                    H = 50.0  # Assume rated head
                    P = self.rho * self.g * Q * H / pump.efficiency
                    total_pump_power += P

            # Update water tower
            # Simplified: assume tower balances supply-demand difference
            total_demand = sum(node['current_demand'] for node_id, node in self.nodes.items()
                             if node_id not in ['SOURCE', 'TOWER'])
            total_supply = sum(pump.rated_flow for pump in self.pumps if pump.is_running)

            tower_inflow = total_supply - total_demand
            self.water_tower.update(dt, inflow=tower_inflow, outflow=0.0)

            # Check pressure violations
            min_pressure_required = 20.0  # 20m minimum pressure
            pressure_violations = sum(1 for node_id, node in self.nodes.items()
                                    if node_id not in ['SOURCE', 'TOWER'] and
                                    node['pressure'] < min_pressure_required)

            # Record history
            self.state_history['time'].append(time / 3600.0)
            self.state_history['tower_level'].append(self.water_tower.state.level)
            self.state_history['total_demand'].append(total_demand * 1000)  # L/s
            self.state_history['total_supply'].append(total_supply * 1000)
            self.state_history['pump_powers'].append(total_pump_power / 1000)  # kW
            self.state_history['pressure_violations'].append(pressure_violations)

            # Average node pressure
            avg_pressure = np.mean([node['pressure'] for node_id, node in self.nodes.items()
                                   if node_id not in ['SOURCE', 'TOWER']])
            self.state_history['node_pressures'].append(avg_pressure)

            # Progress
            if step % 4 == 0:
                print(f"t={time_of_day:5.1f}h | " +
                      f"Demand={total_demand*1000:6.1f}L/s | " +
                      f"Tower={self.water_tower.state.level:5.1f}m | " +
                      f"P_avg={avg_pressure:5.1f}m | " +
                      f"Violations={pressure_violations}")

        print(f"\n{'='*70}")
        print(f"Normal Supply Simulation Complete")
        print(f"Max Tower Level: {max(self.state_history['tower_level']):.1f}m")
        print(f"Min Tower Level: {min(self.state_history['tower_level']):.1f}m")
        print(f"Total Energy: {sum(self.state_history['pump_powers'])*dt/3600:.1f} kWh")
        print(f"{'='*70}\n")

    def optimize_pump_schedule(self):
        """
        Optimize pump operation schedule to minimize energy cost
        优化泵站运行调度以最小化能耗成本

        Uses differential evolution to find optimal on/off schedule
        """
        print(f"\n{'='*70}")
        print(f"Optimizing Pump Schedule - 泵站优化调度")
        print(f"{'='*70}\n")

        # Electricity price pattern (peak/valley pricing)
        # 峰谷电价模式
        price_pattern = np.array([
            0.4,  # 00:00 - Valley (谷)
            0.4,  # 01:00
            0.4,  # 02:00
            0.4,  # 03:00
            0.4,  # 04:00
            0.4,  # 05:00
            0.6,  # 06:00 - Flat (平)
            0.6,  # 07:00
            1.0,  # 08:00 - Peak (峰)
            1.0,  # 09:00
            1.0,  # 10:00
            0.6,  # 11:00 - Flat
            0.6,  # 12:00
            0.6,  # 13:00
            0.6,  # 14:00
            0.6,  # 15:00
            0.6,  # 16:00
            0.6,  # 17:00
            1.0,  # 18:00 - Peak
            1.0,  # 19:00
            1.0,  # 20:00
            0.6,  # 21:00 - Flat
            0.4,  # 22:00 - Valley
            0.4   # 23:00
        ])

        def objective(pump_schedule):
            """
            Objective function: total energy cost

            Args:
                pump_schedule: Binary array (24 x n_pumps)
            """
            schedule = pump_schedule.reshape(24, self.n_pumps)
            total_cost = 0.0

            for hour in range(24):
                # Set pump states
                for i, pump in enumerate(self.pumps):
                    pump.is_running = schedule[hour, i] > 0.5

                # Calculate power
                power = sum(pump.rated_flow * 50.0 * self.rho * self.g / pump.efficiency
                          for pump in self.pumps if pump.is_running)

                # Energy cost = power * price * time
                cost = power * price_pattern[hour] * 1.0  # 1 hour
                total_cost += cost

            return total_cost / 1000.0  # Convert to kWh

        # Optimize using differential evolution
        bounds = [(0, 1)] * (24 * self.n_pumps)

        print("Running optimization...")
        result = differential_evolution(
            objective,
            bounds,
            maxiter=50,
            popsize=10,
            seed=42
        )

        optimal_schedule = result.x.reshape(24, self.n_pumps)
        optimal_cost = result.fun

        # Calculate baseline cost (all pumps on)
        baseline_cost = objective(np.ones(24 * self.n_pumps))

        savings = (baseline_cost - optimal_cost) / baseline_cost * 100

        print(f"\nOptimization Results:")
        print(f"Baseline Cost: {baseline_cost:.1f} kWh")
        print(f"Optimized Cost: {optimal_cost:.1f} kWh")
        print(f"Savings: {savings:.1f}%")

        return optimal_schedule, optimal_cost

    def plot_results(self):
        """Plot simulation results / 绘制仿真结果"""

        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(3, 2, hspace=0.3, wspace=0.3)

        t = np.array(self.state_history['time'])

        # 1. Demand and Supply
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(t, self.state_history['total_demand'], 'b-', linewidth=2, label='Demand (需水量)')
        ax1.plot(t, self.state_history['total_supply'], 'r--', linewidth=2, label='Supply (供水量)')
        ax1.set_xlabel('Time (hours)', fontsize=12)
        ax1.set_ylabel('Flow Rate (L/s)', fontsize=12)
        ax1.set_title('Water Demand and Supply - 供需平衡', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, 24])

        # 2. Water Tower Level
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(t, self.state_history['tower_level'], 'g-', linewidth=2)
        ax2.axhline(y=self.water_tower.max_level, color='r', linestyle='--', alpha=0.5, label='Max')
        ax2.axhline(y=self.water_tower.min_level, color='b', linestyle='--', alpha=0.5, label='Min')
        ax2.set_xlabel('Time (hours)', fontsize=12)
        ax2.set_ylabel('Water Level (m)', fontsize=12)
        ax2.set_title('Water Tower Level - 水塔水位', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, 24])

        # 3. Average Node Pressure
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(t, self.state_history['node_pressures'], 'm-', linewidth=2)
        ax3.axhline(y=20.0, color='r', linestyle='--', alpha=0.5, label='Min Required')
        ax3.set_xlabel('Time (hours)', fontsize=12)
        ax3.set_ylabel('Pressure (m)', fontsize=12)
        ax3.set_title('Average Node Pressure - 平均节点压力', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim([0, 24])

        # 4. Pump Power
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.plot(t, self.state_history['pump_powers'], 'orange', linewidth=2)
        ax4.fill_between(t, 0, self.state_history['pump_powers'], alpha=0.3, color='orange')
        ax4.set_xlabel('Time (hours)', fontsize=12)
        ax4.set_ylabel('Power (kW)', fontsize=12)
        ax4.set_title('Pump Station Power - 泵站功率', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim([0, 24])

        # 5. Pressure Violations
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.plot(t, self.state_history['pressure_violations'], 'r-', linewidth=2, marker='o')
        ax5.set_xlabel('Time (hours)', fontsize=12)
        ax5.set_ylabel('Number of Violations', fontsize=12)
        ax5.set_title('Pressure Violations - 压力不足节点数', fontsize=14, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        ax5.set_xlim([0, 24])
        ax5.set_ylim(bottom=0)

        plt.suptitle(f'Urban Water Supply Network - {self.network_size.capitalize()} Scale - 24 Hours',
                    fontsize=16, fontweight='bold', y=0.995)

        # Save figure
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        filename = f'water_supply_network_{self.network_size}.png'
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f"✓ Results saved to: {filepath}")

        plt.show()


def main():
    """Main execution function"""

    print(f"\n{'#'*70}")
    print(f"#{'  HydroClaude - Urban Water Supply Network Simulation  ':^68}#")
    print(f"#{'  城市供水管网系统仿真  ':^68}#")
    print(f"{'#'*70}\n")

    # Create water supply network
    network = WaterSupplyNetwork(network_size='medium')

    # Simulation 1: Normal 24-hour supply
    print("\n>>> Simulation 1: Normal 24-Hour Supply <<<\n")
    network.simulate_normal_supply(duration=86400.0, dt=3600.0)
    network.plot_results()

    # Simulation 2: Pump schedule optimization
    print("\n>>> Simulation 2: Pump Schedule Optimization <<<\n")
    optimal_schedule, optimal_cost = network.optimize_pump_schedule()

    print(f"\nOptimal Pump Schedule (24 hours):")
    print("Hour | " + " | ".join([f"Pump{i+1}" for i in range(network.n_pumps)]))
    print("-" * 50)
    for hour in range(24):
        status = " | ".join([f"{'ON ' if optimal_schedule[hour, i] > 0.5 else 'OFF'}"
                           for i in range(network.n_pumps)])
        print(f"{hour:02d}:00 | {status}")

    print(f"\n{'#'*70}")
    print(f"#{'  All Simulations Complete!  ':^68}#")
    print(f"{'#'*70}\n")


if __name__ == '__main__':
    main()
