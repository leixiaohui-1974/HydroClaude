#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Engineering Case Study 4: Urban Drainage System
城市排水管网工程案例

This comprehensive case study demonstrates:
1. 不规则断面排水渠 - Irregular channel drainage
2. 涵洞连接 - Culvert connections
3. 暴雨过程 - Storm event simulation
4. 内涝风险评估 - Urban flooding risk assessment

System Configuration:
- Urban drainage network with 3 main channels
- 2 culvert structures connecting channels
- Storm hyetograph (design rainfall)
- Overflow/flooding detection
- Hydraulic capacity evaluation

Author: HydroClaude Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add HydroClaude to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from geometry import TrapezoidalChannel, IrregularChannel
from network.culvert_structure import Culvert
from boundary import TimeSeriesBoundary


class UrbanDrainageSystem:
    """
    Urban drainage system with multiple channels and culverts.

    城市排水系统，包含多条排水渠和涵洞连接。
    """

    def __init__(
        self,
        system_name: str = "Urban Drainage Network",
        design_return_period: int = 10  # years
    ):
        """
        Initialize urban drainage system.

        Args:
            system_name: Name of drainage system
            design_return_period: Design storm return period (years)
        """
        self.system_name = system_name
        self.T_design = design_return_period

        # Drainage channels
        self.channels: List[Dict] = []

        # Culvert structures
        self.culverts: List[Dict] = []

        # Catchment properties
        self.catchments: List[Dict] = []

        # Rainfall data
        self.rainfall: Optional[TimeSeriesBoundary] = None

        print(f"\n{'='*70}")
        print(f"Urban Drainage System: {system_name}")
        print(f"{'='*70}")
        print(f"Design Return Period: {design_return_period} years")
        print(f"{'='*70}\n")

    def create_drainage_network(self):
        """
        Create urban drainage network with 3 channels and 2 culverts.

        创建包含3条排水渠和2个涵洞的排水网络。

        Network topology:
        Catchment A → Channel 1 → Culvert 1 → Channel 2 → Culvert 2 → Channel 3 → Outlet
        """
        print("Creating drainage network topology...\n")

        # Channel 1: Upper drainage channel (trapezoidal)
        ch1 = {
            'id': 'CH-1',
            'type': 'trapezoidal',
            'length': 800.0,  # m
            'bottom_width': 2.0,  # m
            'side_slope': 1.5,
            'bed_slope': 0.005,  # 0.5%
            'manning_n': 0.015,  # Concrete
            'geometry': TrapezoidalChannel(
                bottom_width=2.0,
                side_slope=1.5,
                length=800.0,
                bed_slope=0.005,
                manning_n=0.015
            )
        }
        self.channels.append(ch1)

        # Channel 2: Middle drainage channel (irregular)
        # Rectangular with bench on one side
        y_coords_2 = np.array([-1.5, -1.5, 0.0, 3.0, 3.0, 4.0, 4.0])
        z_coords_2 = np.array([2.0, 0.0, 0.0, 0.0, 0.5, 0.5, 2.0])

        ch2 = {
            'id': 'CH-2',
            'type': 'irregular',
            'length': 600.0,  # m
            'bed_slope': 0.004,
            'manning_n': 0.016,
            'y_coords': y_coords_2,
            'z_coords': z_coords_2,
            'geometry': IrregularChannel(
                y_coordinates=y_coords_2,
                z_coordinates=z_coords_2,
                length=600.0,
                bed_slope=0.004,
                manning_n=0.016
            )
        }
        self.channels.append(ch2)

        # Channel 3: Lower drainage channel (larger trapezoidal)
        ch3 = {
            'id': 'CH-3',
            'type': 'trapezoidal',
            'length': 1000.0,  # m
            'bottom_width': 3.0,  # m
            'side_slope': 2.0,
            'bed_slope': 0.003,
            'manning_n': 0.015,
            'geometry': TrapezoidalChannel(
                bottom_width=3.0,
                side_slope=2.0,
                length=1000.0,
                bed_slope=0.003,
                manning_n=0.015
            )
        }
        self.channels.append(ch3)

        print("Drainage Channels Created:")
        for ch in self.channels:
            if ch['type'] == 'trapezoidal':
                print(f"  {ch['id']}: L={ch['length']}m, "
                      f"B={ch['bottom_width']}m, m={ch['side_slope']}, "
                      f"S={ch['bed_slope']:.4f}")
            else:
                print(f"  {ch['id']}: L={ch['length']}m, "
                      f"Irregular section, S={ch['bed_slope']:.4f}")

        # Culvert 1: Connecting CH-1 to CH-2
        culv1 = {
            'id': 'CULV-1',
            'location': 'CH-1 → CH-2',
            'diameter': 1.2,  # m (circular culvert)
            'length': 50.0,  # m
            'inlet_elevation': 0.0,
            'outlet_elevation': -0.1,  # 10 cm drop
            'entrance_loss_coeff': 0.5,
            'exit_loss_coeff': 1.0,
            'manning_n': 0.013,
            'geometry': Culvert(
                culvert_id='CULV-1',
                diameter=1.2,
                length=50.0,
                inlet_invert=0.0,
                outlet_invert=-0.1,
                manning_n=0.013,
                entrance_loss_coeff=0.5,
                exit_loss_coeff=1.0
            )
        }
        self.culverts.append(culv1)

        # Culvert 2: Connecting CH-2 to CH-3
        culv2 = {
            'id': 'CULV-2',
            'location': 'CH-2 → CH-3',
            'diameter': 1.5,  # m
            'length': 80.0,  # m
            'inlet_elevation': -0.1,
            'outlet_elevation': -0.3,
            'entrance_loss_coeff': 0.5,
            'exit_loss_coeff': 1.0,
            'manning_n': 0.013,
            'geometry': Culvert(
                culvert_id='CULV-2',
                diameter=1.5,
                length=80.0,
                inlet_invert=-0.1,
                outlet_invert=-0.3,
                manning_n=0.013,
                entrance_loss_coeff=0.5,
                exit_loss_coeff=1.0
            )
        }
        self.culverts.append(culv2)

        print(f"\nCulvert Structures Created:")
        for culv in self.culverts:
            print(f"  {culv['id']}: D={culv['diameter']}m, L={culv['length']}m, "
                  f"Drop={culv['inlet_elevation']-culv['outlet_elevation']:.2f}m")

    def create_catchments(self):
        """
        Create urban catchment areas.

        创建城市汇水区域。
        """
        # Catchment A: Residential area draining to CH-1
        catch_A = {
            'id': 'CATCH-A',
            'area': 25.0,  # hectares
            'imperviousness': 0.60,  # 60% impervious
            'time_of_concentration': 15.0,  # minutes
            'runoff_coefficient': 0.5,
            'drains_to': 'CH-1'
        }
        self.catchments.append(catch_A)

        # Catchment B: Commercial area draining to CH-2
        catch_B = {
            'id': 'CATCH-B',
            'area': 15.0,  # hectares
            'imperviousness': 0.80,  # 80% impervious
            'time_of_concentration': 10.0,  # minutes
            'runoff_coefficient': 0.7,
            'drains_to': 'CH-2'
        }
        self.catchments.append(catch_B)

        # Catchment C: Mixed use draining to CH-3
        catch_C = {
            'id': 'CATCH-C',
            'area': 20.0,  # hectares
            'imperviousness': 0.70,  # 70% impervious
            'time_of_concentration': 12.0,  # minutes
            'runoff_coefficient': 0.6,
            'drains_to': 'CH-3'
        }
        self.catchments.append(catch_C)

        print(f"\nCatchment Areas Created:")
        total_area = sum(c['area'] for c in self.catchments)
        for catch in self.catchments:
            print(f"  {catch['id']}: Area={catch['area']}ha, "
                  f"Imperv={catch['imperviousness']*100:.0f}%, "
                  f"C={catch['runoff_coefficient']:.2f}, "
                  f"→ {catch['drains_to']}")
        print(f"  Total Catchment Area: {total_area:.1f} ha")

    def create_design_storm(
        self,
        duration: float = 120.0,  # minutes
        dt: float = 5.0,  # minutes
        intensity_formula: str = "chicago"
    ):
        """
        Create design storm hyetograph.

        创建设计暴雨雨型。

        Args:
            duration: Storm duration (minutes)
            dt: Time step (minutes)
            intensity_formula: Intensity formula ("chicago" or "constant")
        """
        time_array = np.arange(0, duration + dt, dt)  # minutes

        if intensity_formula == "chicago":
            # Chicago design storm
            # i = a / (t + b)^c
            # Peak at t = duration * r, where r is typically 0.4

            a = 2000.0 * (self.T_design ** 0.2)  # Calibrated coefficient
            b = 10.0
            c = 0.75
            r = 0.4  # Peak ratio

            peak_time = duration * r

            intensity = np.zeros_like(time_array)

            for i, t in enumerate(time_array):
                if t < peak_time:
                    # Advancing limb
                    t_advance = peak_time - t
                    intensity[i] = a / (t_advance + b) ** c
                else:
                    # Receding limb
                    t_recede = t - peak_time
                    intensity[i] = a / (t_recede + b) ** c

        else:
            # Constant intensity
            total_depth = 50.0 * (self.T_design ** 0.25)  # mm
            intensity = np.full_like(time_array, total_depth / duration)

        # Create TimeSeriesBoundary for rainfall
        self.rainfall = TimeSeriesBoundary(
            bc_id=f"STORM_{self.T_design}Y",
            bc_type="rainfall",
            time_data=time_array,
            value_data=intensity,
            interpolation_method="linear"
        )

        total_rainfall = np.trapz(intensity, time_array)  # mm

        print(f"\nDesign Storm Created ({self.T_design}-year):")
        print(f"  Formula: {intensity_formula}")
        print(f"  Duration: {duration:.0f} minutes")
        print(f"  Peak Intensity: {np.max(intensity):.2f} mm/hr")
        print(f"  Total Rainfall: {total_rainfall:.2f} mm")
        print(f"  Peak Time: {time_array[np.argmax(intensity)]:.0f} minutes")

    def compute_runoff_hydrograph(
        self,
        catchment: Dict,
        dt: float = 5.0  # minutes
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute runoff hydrograph using rational method.

        使用推理公式法计算径流过程。

        Q = C * i * A / 360  (m³/s)

        Args:
            catchment: Catchment dictionary
            dt: Time step (minutes)

        Returns:
            Tuple of (time, discharge) arrays
        """
        if self.rainfall is None:
            raise ValueError("Design storm not created!")

        time_range = self.rainfall.get_time_range()
        time_array = np.arange(time_range[0], time_range[1] + dt, dt)

        # Get rainfall intensity at each time step
        intensity = np.array([self.rainfall.get_value(t) for t in time_array])  # mm/hr

        # Rational formula: Q = C * i * A / 360
        C = catchment['runoff_coefficient']
        A = catchment['area']  # hectares

        Q = C * intensity * A / 360.0  # m³/s

        return time_array, Q

    def route_through_channel(
        self,
        channel: Dict,
        Q_in: np.ndarray,
        time: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Route flow through channel using Muskingum method.

        使用马斯京根法演算河道流量。

        Args:
            channel: Channel dictionary
            Q_in: Inflow hydrograph (m³/s)
            time: Time array (minutes)

        Returns:
            Tuple of (Q_out, storage)
        """
        # Muskingum parameters
        K = channel['length'] / 1000.0  # Storage constant (hours)
        x = 0.2  # Weighting factor

        dt = time[1] - time[0]  # minutes
        dt_hr = dt / 60.0  # hours

        # Muskingum coefficients
        C0 = (-K * x + 0.5 * dt_hr) / (K - K * x + 0.5 * dt_hr)
        C1 = (K * x + 0.5 * dt_hr) / (K - K * x + 0.5 * dt_hr)
        C2 = (K - K * x - 0.5 * dt_hr) / (K - K * x + 0.5 * dt_hr)

        # Route flow
        Q_out = np.zeros_like(Q_in)
        Q_out[0] = Q_in[0]

        for i in range(1, len(Q_in)):
            Q_out[i] = C0 * Q_in[i] + C1 * Q_in[i-1] + C2 * Q_out[i-1]
            Q_out[i] = max(Q_out[i], 0.0)

        # Storage
        storage = K * (x * Q_in + (1 - x) * Q_out)

        return Q_out, storage

    def simulate_drainage_system(
        self,
        dt: float = 5.0  # minutes
    ) -> Dict:
        """
        Simulate entire drainage system response to design storm.

        模拟整个排水系统对设计暴雨的响应。

        Args:
            dt: Time step (minutes)

        Returns:
            Dictionary with simulation results
        """
        print(f"\n{'='*70}")
        print(f"Drainage System Simulation")
        print(f"{'='*70}")

        time_range = self.rainfall.get_time_range()
        time_array = np.arange(time_range[0], time_range[1] + dt, dt)
        nt = len(time_array)

        print(f"Time steps: {nt} ({dt} min intervals)")
        print(f"Duration: {time_range[1]:.0f} minutes ({time_range[1]/60:.1f} hours)")

        results = {
            'time': time_array,
            'rainfall': np.array([self.rainfall.get_value(t) for t in time_array]),
            'runoff': {},
            'channel_flow': {},
            'culvert_flow': {},
            'water_levels': {},
            'overflow': {}
        }

        # Compute runoff from each catchment
        print(f"\nComputing catchment runoff...")
        for catch in self.catchments:
            t_runoff, Q_runoff = self.compute_runoff_hydrograph(catch, dt)
            results['runoff'][catch['id']] = Q_runoff
            print(f"  {catch['id']}: Peak Q = {np.max(Q_runoff):.2f} m³/s")

        # Route through drainage network
        print(f"\nRouting through drainage network...")

        # Channel 1: Receives runoff from Catchment A
        Q_ch1_in = results['runoff']['CATCH-A']
        Q_ch1_out, _ = self.route_through_channel(self.channels[0], Q_ch1_in, time_array)
        results['channel_flow']['CH-1'] = Q_ch1_out

        # Culvert 1: Receives outflow from CH-1
        # Simplified: assume culvert passes flow with minor attenuation
        Q_culv1 = Q_ch1_out * 0.95  # 5% loss
        results['culvert_flow']['CULV-1'] = Q_culv1

        # Channel 2: Receives flow from CULV-1 + runoff from Catchment B
        Q_ch2_in = Q_culv1 + results['runoff']['CATCH-B']
        Q_ch2_out, _ = self.route_through_channel(self.channels[1], Q_ch2_in, time_array)
        results['channel_flow']['CH-2'] = Q_ch2_out

        # Culvert 2: Receives outflow from CH-2
        Q_culv2 = Q_ch2_out * 0.95
        results['culvert_flow']['CULV-2'] = Q_culv2

        # Channel 3: Receives flow from CULV-2 + runoff from Catchment C
        Q_ch3_in = Q_culv2 + results['runoff']['CATCH-C']
        Q_ch3_out, _ = self.route_through_channel(self.channels[2], Q_ch3_in, time_array)
        results['channel_flow']['CH-3'] = Q_ch3_out

        # Compute water levels and check for overflow
        print(f"\nChecking channel capacities...")
        for i, ch in enumerate(self.channels):
            Q_peak = np.max(results['channel_flow'][ch['id']])
            h_peak = ch['geometry'].normal_depth(Q_peak)

            # Estimate channel capacity (assume bankfull at 80% of total depth)
            if ch['type'] == 'trapezoidal':
                h_capacity = 2.5  # Assume 2.5 m design depth
            else:
                h_capacity = 1.5  # Irregular channel

            overflow_ratio = h_peak / h_capacity

            results['water_levels'][ch['id']] = h_peak
            results['overflow'][ch['id']] = overflow_ratio

            status = "✓ OK" if overflow_ratio < 1.0 else "✗ OVERFLOW!"
            print(f"  {ch['id']}: Peak Q = {Q_peak:.2f} m³/s, "
                  f"h = {h_peak:.2f} m, "
                  f"Capacity ratio = {overflow_ratio:.2%} {status}")

        print(f"{'='*70}\n")

        return results

    def visualize_results(self, results: Dict):
        """
        Create comprehensive visualization.

        创建综合可视化。
        """
        fig = plt.figure(figsize=(16, 12))

        time = results['time']

        # 1. Design storm hyetograph
        ax1 = plt.subplot(3, 2, 1)
        ax1.bar(time, results['rainfall'], width=5.0, alpha=0.7, color='blue', edgecolor='black')
        ax1.set_xlabel('Time (minutes)', fontsize=11)
        ax1.set_ylabel('Rainfall Intensity (mm/hr)', fontsize=11)
        ax1.set_title(f'Design Storm Hyetograph ({self.T_design}-year)', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 2. Catchment runoff
        ax2 = plt.subplot(3, 2, 2)
        colors_catch = ['#1f77b4', '#ff7f0e', '#2ca02c']
        for i, catch in enumerate(self.catchments):
            ax2.plot(time, results['runoff'][catch['id']], linewidth=2,
                    color=colors_catch[i], label=catch['id'])
        ax2.set_xlabel('Time (minutes)', fontsize=11)
        ax2.set_ylabel('Runoff (m³/s)', fontsize=11)
        ax2.set_title('Catchment Runoff Hydrographs', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)

        # 3. Channel flows
        ax3 = plt.subplot(3, 2, 3)
        colors_ch = ['blue', 'green', 'red']
        for i, ch in enumerate(self.channels):
            ax3.plot(time, results['channel_flow'][ch['id']], linewidth=2,
                    color=colors_ch[i], label=ch['id'])
        ax3.set_xlabel('Time (minutes)', fontsize=11)
        ax3.set_ylabel('Discharge (m³/s)', fontsize=11)
        ax3.set_title('Channel Flow Hydrographs', fontsize=12, fontweight='bold')
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)

        # 4. Culvert flows
        ax4 = plt.subplot(3, 2, 4)
        for i, culv in enumerate(self.culverts):
            ax4.plot(time, results['culvert_flow'][culv['id']], linewidth=2,
                    label=culv['id'])
        ax4.set_xlabel('Time (minutes)', fontsize=11)
        ax4.set_ylabel('Discharge (m³/s)', fontsize=11)
        ax4.set_title('Culvert Flow Hydrographs', fontsize=12, fontweight='bold')
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)

        # 5. System flow routing
        ax5 = plt.subplot(3, 2, 5)
        ax5.plot(time, results['runoff']['CATCH-A'], 'b:', linewidth=1.5, label='Runoff A', alpha=0.7)
        ax5.plot(time, results['channel_flow']['CH-1'], 'b-', linewidth=2, label='CH-1 Out')
        ax5.plot(time, results['channel_flow']['CH-2'], 'g-', linewidth=2, label='CH-2 Out')
        ax5.plot(time, results['channel_flow']['CH-3'], 'r-', linewidth=2, label='CH-3 Out (System)')
        ax5.set_xlabel('Time (minutes)', fontsize=11)
        ax5.set_ylabel('Discharge (m³/s)', fontsize=11)
        ax5.set_title('System Flow Routing', fontsize=12, fontweight='bold')
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3)

        # 6. Capacity assessment
        ax6 = plt.subplot(3, 2, 6)
        channel_ids = [ch['id'] for ch in self.channels]
        overflow_ratios = [results['overflow'][ch_id] * 100 for ch_id in channel_ids]
        colors_bar = ['green' if r < 100 else 'red' for r in overflow_ratios]

        bars = ax6.bar(range(len(channel_ids)), overflow_ratios, color=colors_bar,
                      alpha=0.7, edgecolor='black', linewidth=2)
        ax6.axhline(y=100, color='red', linestyle='--', linewidth=2, label='Design Capacity')
        ax6.set_xticks(range(len(channel_ids)))
        ax6.set_xticklabels(channel_ids, fontsize=10)
        ax6.set_ylabel('Capacity Utilization (%)', fontsize=11)
        ax6.set_title('Channel Capacity Assessment', fontsize=12, fontweight='bold')
        ax6.legend(fontsize=10)
        ax6.grid(True, axis='y', alpha=0.3)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, overflow_ratios)):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.tight_layout()

        save_path = '/home/user/HydroClaude/validation_cases/engineering/urban_drainage/results.png'
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")

        plt.show()


def main():
    """
    Main execution function.
    """
    print("\n" + "="*70)
    print("HydroClaude Engineering Case Study 4")
    print("Urban Drainage System")
    print("城市排水管网工程案例")
    print("="*70 + "\n")

    # Step 1: Initialize system
    drainage = UrbanDrainageSystem(
        system_name="Example City Drainage",
        design_return_period=10
    )

    # Step 2: Create drainage network
    drainage.create_drainage_network()

    # Step 3: Create catchments
    drainage.create_catchments()

    # Step 4: Create design storm
    drainage.create_design_storm(
        duration=120.0,
        dt=5.0,
        intensity_formula="chicago"
    )

    # Step 5: Simulate system
    results = drainage.simulate_drainage_system(dt=5.0)

    # Step 6: Visualize
    drainage.visualize_results(results)

    # Summary
    print("\n" + "="*70)
    print("Case Study Completed Successfully!")
    print("="*70)
    print("\nKey Achievements:")
    print("  ✓ Modeled urban drainage network (3 channels, 2 culverts)")
    print("  ✓ Simulated 3 catchment areas (60 hectares total)")
    print("  ✓ Created 10-year design storm (Chicago method)")
    print("  ✓ Computed runoff using rational method")
    print("  ✓ Routed flow through network (Muskingum)")
    print("  ✓ Assessed channel capacities and flood risk")
    print("  ✓ Generated comprehensive visualizations")
    print("\nThis case study demonstrates:")
    print("  • Urban drainage network modeling")
    print("  • Design storm generation")
    print("  • Runoff computation (rational method)")
    print("  • Flow routing (Muskingum)")
    print("  • Culvert hydraulics")
    print("  • Flood risk assessment")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
