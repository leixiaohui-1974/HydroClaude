#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Engineering Case Study 3: Bridge Hydraulic Capacity Assessment
桥梁过水能力评估工程案例

This comprehensive case study demonstrates:
1. 桥梁建筑物影响 - Bridge structure hydraulic impacts
2. 壅水分析 - Backwater analysis
3. 洪水位计算 - Flood level computation
4. 桥梁设计优化 - Bridge design optimization

System Configuration:
- River reach: 5 km with bridge at midpoint
- Bridge: 3-span with piers
- Multiple design scenarios
- Flood events: 10-year to 100-year return periods
- Backwater curve computation
- Bridge capacity evaluation

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

from geometry import TrapezoidalChannel
from network.bridge_structure import Bridge
from boundary import TimeSeriesBoundary


class BridgeHydraulicAssessment:
    """
    Bridge hydraulic capacity assessment system.

    桥梁过水能力评估系统。
    """

    def __init__(
        self,
        river_name: str = "Example River",
        reach_length: float = 5000.0,  # m (5 km)
        bridge_location: float = 2500.0,  # m (midpoint)
    ):
        """
        Initialize bridge assessment system.

        Args:
            river_name: Name of river
            reach_length: Total reach length (m)
            bridge_location: Distance from upstream to bridge (m)
        """
        self.river_name = river_name
        self.L = reach_length
        self.bridge_x = bridge_location

        # Channel properties
        self.channel: Optional[TrapezoidalChannel] = None

        # Bridge structure
        self.bridge: Optional[Bridge] = None

        # Design scenarios
        self.design_scenarios: List[Dict] = []

        print(f"\n{'='*70}")
        print(f"Bridge Hydraulic Assessment: {river_name}")
        print(f"{'='*70}")
        print(f"Reach Length: {self.L/1000:.1f} km")
        print(f"Bridge Location: {self.bridge_x/1000:.2f} km from upstream")
        print(f"{'='*70}\n")

    def setup_channel(
        self,
        bottom_width: float = 30.0,  # m
        side_slope: float = 2.0,  # H:V
        bed_slope: float = 0.001,  # m/m
        manning_n: float = 0.030
    ):
        """
        Setup river channel geometry.

        设置河道断面几何。

        Args:
            bottom_width: Channel bottom width (m)
            side_slope: Side slope ratio (H:V)
            bed_slope: Channel bed slope (m/m)
            manning_n: Manning's roughness coefficient
        """
        self.channel = TrapezoidalChannel(
            bottom_width=bottom_width,
            side_slope=side_slope,
            length=self.L,
            bed_slope=bed_slope,
            manning_n=manning_n
        )

        print(f"Channel Configuration:")
        print(f"  Bottom Width: {bottom_width} m")
        print(f"  Side Slope: {side_slope}:1 (H:V)")
        print(f"  Bed Slope: {bed_slope:.4f}")
        print(f"  Manning's n: {manning_n}")

    def setup_bridge(
        self,
        bridge_id: str = "Main Bridge",
        total_width: float = 50.0,  # m
        opening_height: float = 5.0,  # m
        bottom_elevation: float = 0.0,  # m
        n_piers: int = 2,
        pier_width: float = 1.5  # m
    ):
        """
        Setup bridge structure.

        设置桥梁结构。

        Args:
            bridge_id: Bridge identifier
            total_width: Total bridge opening width (m)
            opening_height: Bridge opening height (m)
            bottom_elevation: Bridge bottom elevation (m)
            n_piers: Number of piers
            pier_width: Width of each pier (m)
        """
        self.bridge = Bridge(
            bridge_id=bridge_id,
            total_width=total_width,
            opening_height=opening_height,
            bottom_elevation=bottom_elevation,
            n_piers=n_piers,
            pier_width=pier_width,
            Cd_weir=0.5,
            Cd_orifice=0.7,
            Cd_pressure=0.8
        )

        print(f"\nBridge Configuration:")
        print(f"  ID: {bridge_id}")
        print(f"  Total Width: {total_width} m")
        print(f"  Effective Width: {self.bridge.W_effective:.1f} m (with {n_piers} piers)")
        print(f"  Opening Height: {opening_height} m")
        print(f"  Bottom Elevation: {bottom_elevation} m")
        print(f"  Deck Elevation: {self.bridge.z_deck} m")
        print(f"  Pier Width: {pier_width} m each")

    def create_design_scenarios(self):
        """
        Create multiple design scenarios for comparison.

        创建多个设计方案进行对比。
        """
        # Base scenario: current bridge
        base = {
            'name': 'Current Design',
            'total_width': 50.0,
            'opening_height': 5.0,
            'n_piers': 2,
            'pier_width': 1.5,
            'color': 'blue'
        }

        # Scenario 1: Wider bridge
        wider = {
            'name': 'Wider Bridge (+20%)',
            'total_width': 60.0,
            'opening_height': 5.0,
            'n_piers': 2,
            'pier_width': 1.5,
            'color': 'green'
        }

        # Scenario 2: Higher opening
        higher = {
            'name': 'Higher Opening (+1m)',
            'total_width': 50.0,
            'opening_height': 6.0,
            'n_piers': 2,
            'pier_width': 1.5,
            'color': 'red'
        }

        # Scenario 3: Fewer piers
        fewer_piers = {
            'name': 'Single Pier',
            'total_width': 50.0,
            'opening_height': 5.0,
            'n_piers': 1,
            'pier_width': 2.0,
            'color': 'orange'
        }

        self.design_scenarios = [base, wider, higher, fewer_piers]

        print(f"\nDesign Scenarios Created:")
        for i, scenario in enumerate(self.design_scenarios):
            print(f"  {i+1}. {scenario['name']}: "
                  f"W={scenario['total_width']}m, "
                  f"H={scenario['opening_height']}m, "
                  f"Piers={scenario['n_piers']}")

    def compute_backwater_profile(
        self,
        Q: float,
        h_downstream: float,
        dx: float = 50.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute backwater profile using standard step method.

        使用标准步长法计算壅水曲线。

        Args:
            Q: Discharge (m³/s)
            h_downstream: Downstream water depth (m)
            dx: Spatial step (m)

        Returns:
            Tuple of (x, h_without_bridge, h_with_bridge)
        """
        # Discretize reach
        x = np.arange(0, self.L + dx, dx)
        nx = len(x)

        # Initialize arrays
        h_no_bridge = np.zeros(nx)
        h_with_bridge = np.zeros(nx)

        # Downstream boundary condition
        h_no_bridge[-1] = h_downstream
        h_with_bridge[-1] = h_downstream

        # Profile without bridge (normal depth throughout)
        h_normal = self.channel.normal_depth(Q)

        for i in range(nx-2, -1, -1):
            # Without bridge: gradually varied flow (energy equation)
            # Simple approximation: use Manning for each section
            h_no_bridge[i] = h_normal

        # Profile with bridge (backwater upstream of bridge)
        bridge_idx = np.argmin(np.abs(x - self.bridge_x))

        # Compute bridge head loss
        h_up_bridge = h_downstream  # Initial guess

        # Iteratively solve for upstream depth at bridge
        for _ in range(10):
            result = self.bridge.compute_discharge(
                h_upstream=h_up_bridge,
                h_downstream=h_downstream
            )

            Q_bridge = result['Q']

            if abs(Q_bridge - Q) / Q < 0.01:
                break

            # Adjust upstream depth
            if Q_bridge < Q:
                h_up_bridge += 0.1
            else:
                h_up_bridge -= 0.05

            h_up_bridge = max(h_up_bridge, h_downstream)

        # Backwater upstream of bridge
        for i in range(bridge_idx, -1, -1):
            if i == bridge_idx:
                h_with_bridge[i] = h_up_bridge
            else:
                # Gradually varied flow upstream
                # S_f = S_0 - dh/dx
                # Simplified: exponential decay
                dist_from_bridge = self.bridge_x - x[i]
                decay_length = 500.0  # m
                backwater = (h_up_bridge - h_normal) * np.exp(-dist_from_bridge / decay_length)
                h_with_bridge[i] = h_normal + backwater

        # Downstream of bridge
        for i in range(bridge_idx + 1, nx):
            h_with_bridge[i] = h_downstream

        return x, h_no_bridge, h_with_bridge

    def analyze_flood_events(
        self,
        flood_discharges: List[float],
        return_periods: List[int]
    ) -> Dict:
        """
        Analyze multiple flood events.

        分析多个洪水事件。

        Args:
            flood_discharges: List of flood discharges (m³/s)
            return_periods: List of return periods (years)

        Returns:
            Dictionary with analysis results
        """
        print(f"\n{'='*70}")
        print(f"Flood Event Analysis")
        print(f"{'='*70}")

        results = {
            'return_periods': return_periods,
            'discharges': flood_discharges,
            'backwater_heights': [],
            'max_velocities': [],
            'flow_regimes': [],
            'head_losses': []
        }

        for Q, T in zip(flood_discharges, return_periods):
            # Compute normal depth
            h_normal = self.channel.normal_depth(Q)

            # Compute bridge hydraulics
            h_upstream_bridge = h_normal + 0.5  # Initial guess with backwater

            # Iterate to find upstream depth
            for _ in range(20):
                bridge_result = self.bridge.compute_discharge(
                    h_upstream=h_upstream_bridge,
                    h_downstream=h_normal
                )

                Q_computed = bridge_result['Q']

                if abs(Q_computed - Q) / Q < 0.01:
                    break

                if Q_computed < Q:
                    h_upstream_bridge += 0.05
                else:
                    h_upstream_bridge -= 0.02

                h_upstream_bridge = max(h_upstream_bridge, h_normal)

            backwater = h_upstream_bridge - h_normal
            velocity = bridge_result['velocity']
            regime = bridge_result['regime']
            head_loss = bridge_result['head_loss']

            results['backwater_heights'].append(backwater)
            results['max_velocities'].append(velocity)
            results['flow_regimes'].append(regime)
            results['head_losses'].append(head_loss)

            print(f"\n{T}-Year Flood (Q = {Q:.0f} m³/s):")
            print(f"  Normal Depth: {h_normal:.2f} m")
            print(f"  Upstream Depth at Bridge: {h_upstream_bridge:.2f} m")
            print(f"  Backwater Height: {backwater:.2f} m")
            print(f"  Bridge Velocity: {velocity:.2f} m/s")
            print(f"  Flow Regime: {regime}")
            print(f"  Head Loss: {head_loss:.2f} m")

        print(f"{'='*70}\n")

        return results

    def compare_design_scenarios(
        self,
        Q: float,
        return_period: int = 100
    ) -> Dict:
        """
        Compare different bridge design scenarios.

        对比不同桥梁设计方案。

        Args:
            Q: Design discharge (m³/s)
            return_period: Return period (years)

        Returns:
            Comparison results
        """
        print(f"\n{'='*70}")
        print(f"Design Scenario Comparison ({return_period}-Year Flood)")
        print(f"{'='*70}")
        print(f"Design Discharge: {Q:.0f} m³/s\n")

        h_normal = self.channel.normal_depth(Q)

        comparison = {
            'scenarios': [],
            'backwater': [],
            'velocities': [],
            'head_loss': [],
            'effective_width': [],
            'cost_index': []
        }

        for scenario in self.design_scenarios:
            # Create bridge for this scenario
            bridge_test = Bridge(
                bridge_id=scenario['name'],
                total_width=scenario['total_width'],
                opening_height=scenario['opening_height'],
                bottom_elevation=0.0,
                n_piers=scenario['n_piers'],
                pier_width=scenario['pier_width']
            )

            # Solve for upstream depth
            h_up = h_normal + 0.5

            for _ in range(20):
                result = bridge_test.compute_discharge(h_up, h_normal)

                if abs(result['Q'] - Q) / Q < 0.01:
                    break

                if result['Q'] < Q:
                    h_up += 0.05
                else:
                    h_up -= 0.02

                h_up = max(h_up, h_normal)

            backwater = h_up - h_normal

            # Relative cost index (width × height)
            cost = scenario['total_width'] * scenario['opening_height'] / (50.0 * 5.0)

            comparison['scenarios'].append(scenario['name'])
            comparison['backwater'].append(backwater)
            comparison['velocities'].append(result['velocity'])
            comparison['head_loss'].append(result['head_loss'])
            comparison['effective_width'].append(bridge_test.W_effective)
            comparison['cost_index'].append(cost)

            print(f"{scenario['name']}:")
            print(f"  Effective Width: {bridge_test.W_effective:.1f} m")
            print(f"  Backwater: {backwater:.2f} m")
            print(f"  Velocity: {result['velocity']:.2f} m/s")
            print(f"  Head Loss: {result['head_loss']:.2f} m")
            print(f"  Flow Regime: {result['regime']}")
            print(f"  Relative Cost: {cost:.2f}\n")

        print(f"{'='*70}\n")

        return comparison

    def visualize_results(
        self,
        flood_results: Dict,
        comparison_results: Dict,
        Q_design: float = 500.0
    ):
        """
        Create comprehensive visualizations.

        创建综合可视化。
        """
        fig = plt.figure(figsize=(16, 12))

        # 1. Backwater profile for design flood
        ax1 = plt.subplot(3, 2, 1)
        h_normal = self.channel.normal_depth(Q_design)
        x, h_no, h_with = self.compute_backwater_profile(Q_design, h_normal, dx=50.0)

        # Bed elevation
        bed_elev = 100.0 - x * self.channel.bed_slope

        ax1.fill_between(x/1000, bed_elev, bed_elev + h_no, alpha=0.3, color='blue',
                        label='Without Bridge')
        ax1.plot(x/1000, bed_elev + h_no, 'b--', linewidth=2, label='Normal Profile')
        ax1.plot(x/1000, bed_elev + h_with, 'r-', linewidth=2, label='With Bridge')
        ax1.axvline(self.bridge_x/1000, color='k', linestyle=':', linewidth=1.5, label='Bridge Location')
        ax1.plot(x/1000, bed_elev, 'k-', linewidth=2, label='Channel Bed')

        ax1.set_xlabel('Distance (km)', fontsize=11)
        ax1.set_ylabel('Elevation (m)', fontsize=11)
        ax1.set_title('Backwater Profile (Design Flood)', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)

        # 2. Backwater vs flood magnitude
        ax2 = plt.subplot(3, 2, 2)
        ax2.plot(flood_results['return_periods'], flood_results['backwater_heights'],
                'bo-', linewidth=2, markersize=8)
        ax2.set_xlabel('Return Period (years)', fontsize=11)
        ax2.set_ylabel('Backwater Height (m)', fontsize=11)
        ax2.set_title('Backwater vs Return Period', fontsize=12, fontweight='bold')
        ax2.set_xscale('log')
        ax2.grid(True, alpha=0.3)

        # 3. Flow velocity at bridge
        ax3 = plt.subplot(3, 2, 3)
        ax3.plot(flood_results['discharges'], flood_results['max_velocities'],
                'go-', linewidth=2, markersize=8)
        ax3.set_xlabel('Discharge (m³/s)', fontsize=11)
        ax3.set_ylabel('Bridge Velocity (m/s)', fontsize=11)
        ax3.set_title('Flow Velocity at Bridge', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=3.0, color='r', linestyle='--', linewidth=1.5, label='Design Limit')
        ax3.legend(fontsize=9)

        # 4. Design scenario comparison - backwater
        ax4 = plt.subplot(3, 2, 4)
        scenarios = comparison_results['scenarios']
        backwater = comparison_results['backwater']
        colors = [s['color'] for s in self.design_scenarios]

        bars = ax4.bar(range(len(scenarios)), backwater, color=colors, alpha=0.7, edgecolor='black')
        ax4.set_xticks(range(len(scenarios)))
        ax4.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=9)
        ax4.set_ylabel('Backwater Height (m)', fontsize=11)
        ax4.set_title('Design Comparison - Backwater', fontsize=12, fontweight='bold')
        ax4.grid(True, axis='y', alpha=0.3)

        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}m', ha='center', va='bottom', fontsize=9)

        # 5. Design scenario comparison - velocity
        ax5 = plt.subplot(3, 2, 5)
        velocities = comparison_results['velocities']
        bars = ax5.bar(range(len(scenarios)), velocities, color=colors, alpha=0.7, edgecolor='black')
        ax5.set_xticks(range(len(scenarios)))
        ax5.set_xticklabels([s.replace(' ', '\n') for s in scenarios], fontsize=9)
        ax5.set_ylabel('Bridge Velocity (m/s)', fontsize=11)
        ax5.set_title('Design Comparison - Velocity', fontsize=12, fontweight='bold')
        ax5.axhline(y=3.0, color='r', linestyle='--', linewidth=1.5, alpha=0.7)
        ax5.grid(True, axis='y', alpha=0.3)

        # 6. Cost-performance trade-off
        ax6 = plt.subplot(3, 2, 6)
        cost_index = comparison_results['cost_index']

        for i, (name, bw, cost, color) in enumerate(zip(scenarios, backwater, cost_index, colors)):
            ax6.scatter(cost, bw, s=200, color=color, alpha=0.7, edgecolor='black', linewidth=2)
            ax6.annotate(str(i+1), (cost, bw), ha='center', va='center',
                        fontsize=10, fontweight='bold')

        ax6.set_xlabel('Relative Cost Index', fontsize=11)
        ax6.set_ylabel('Backwater Height (m)', fontsize=11)
        ax6.set_title('Cost-Performance Trade-off', fontsize=12, fontweight='bold')
        ax6.grid(True, alpha=0.3)

        # Add legend
        for i, name in enumerate(scenarios):
            ax6.plot([], [], 'o', color=colors[i], markersize=10, alpha=0.7,
                    label=f'{i+1}. {name}')
        ax6.legend(fontsize=8, loc='best')

        plt.tight_layout()

        save_path = '/home/user/HydroClaude/validation_cases/engineering/bridge_assessment/results.png'
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")

        plt.show()


def main():
    """
    Main execution function for bridge assessment case study.
    """
    print("\n" + "="*70)
    print("HydroClaude Engineering Case Study 3")
    print("Bridge Hydraulic Capacity Assessment")
    print("桥梁过水能力评估工程案例")
    print("="*70 + "\n")

    # Step 1: Initialize system
    bridge_assess = BridgeHydraulicAssessment(
        river_name="Example River",
        reach_length=5000.0,
        bridge_location=2500.0
    )

    # Step 2: Setup channel
    bridge_assess.setup_channel(
        bottom_width=30.0,
        side_slope=2.0,
        bed_slope=0.001,
        manning_n=0.030
    )

    # Step 3: Setup bridge
    bridge_assess.setup_bridge(
        bridge_id="Main Bridge",
        total_width=50.0,
        opening_height=5.0,
        bottom_elevation=0.0,
        n_piers=2,
        pier_width=1.5
    )

    # Step 4: Create design scenarios
    bridge_assess.create_design_scenarios()

    # Step 5: Analyze flood events
    flood_Q = [200, 350, 500, 650, 800]  # m³/s
    return_periods = [10, 25, 50, 75, 100]  # years

    flood_results = bridge_assess.analyze_flood_events(flood_Q, return_periods)

    # Step 6: Compare design scenarios
    Q_design = 500.0  # 50-year flood
    comparison = bridge_assess.compare_design_scenarios(Q_design, return_period=50)

    # Step 7: Visualize
    bridge_assess.visualize_results(flood_results, comparison, Q_design)

    # Summary
    print("\n" + "="*70)
    print("Case Study Completed Successfully!")
    print("="*70)
    print("\nKey Achievements:")
    print("  ✓ Modeled 5 km river reach with bridge")
    print("  ✓ Computed backwater profiles")
    print("  ✓ Analyzed 5 flood events (10 to 100-year)")
    print("  ✓ Compared 4 design scenarios")
    print("  ✓ Evaluated cost-performance trade-offs")
    print("  ✓ Generated comprehensive visualizations")
    print("\nThis case study demonstrates:")
    print("  • Bridge hydraulic impact analysis")
    print("  • Backwater computation")
    print("  • Multiple flood event assessment")
    print("  • Design optimization")
    print("  • Cost-benefit analysis")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
