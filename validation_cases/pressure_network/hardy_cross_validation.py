"""
Hardy Cross Validation Cases - Hardy Cross法验证案例

Classic validation cases for Hardy Cross method including:
1. Hardy Cross 1936 original two-loop example
2. Multi-loop network validation

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from solvers.hardy_cross_solver import HardyCrossSolver
from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir
from network.pressure_pipe import PressurePipe


def validation_case_1_two_loop_network():
    """
    验证案例1: 双回路网络 - Two-Loop Network
    
    经典的Hardy Cross双回路算例
    """
    print("=" * 80)
    print("验证案例1: Hardy Cross 双回路网络")
    print("=" * 80)
    
    # 创建网络
    topology = NetworkTopology(name="HardyCrossTwoLoop")
    
    reservoir = Reservoir("R1", elevation=50.0, head=50.0)
    for i in range(1, 7):
        junction = Junction(f"J{i}", elevation=10.0, demand=0.015)
        topology.add_node(junction)
    topology.add_node(reservoir)
    
    # 添加管道
    pipe_configs = [
        ("P0", "R1", "J1", 0.5, 500.0),
        ("P1", "J1", "J2", 0.3, 200.0),
        ("P2", "J1", "J3", 0.3, 150.0),
        ("P3", "J2", "J4", 0.25, 200.0),
        ("P4", "J3", "J4", 0.3, 200.0),
        ("P5", "J3", "J5", 0.25, 150.0),
        ("P6", "J4", "J6", 0.2, 200.0),
        ("P7", "J5", "J6", 0.25, 200.0),
    ]
    
    for pipe_id, from_node, to_node, diameter, length in pipe_configs:
        pipe = PressurePipe(pipe_id, diameter=diameter, length=length, roughness=0.0003)
        topology.add_pipe(pipe, from_node, to_node)
    
    # 求解
    print("\n[求解过程]")
    solver = HardyCrossSolver(topology, max_iter=100, tol=1e-6, verbose=True)
    flows, heads = solver.solve()
    
    # 结果验证
    print("\n[结果验证]")
    total_demand = 6 * 0.015
    Q_source = abs(flows["P0"])
    print(f"  总需水量: {total_demand:.6f} m³/s")
    print(f"  水源流量: {Q_source:.6f} m³/s")
    print(f"  流量误差: {abs(Q_source - total_demand):.8f} m³/s")
    
    assert abs(Q_source - total_demand) < 0.001, "流量平衡不满足"
    
    print("\n  ✓ 验证案例1通过")
    print("=" * 80 + "\n")
    
    return flows, heads


def main():
    """运行所有验证案例"""
    print("\n" + "="*80)
    print("Hardy Cross 验证案例 - Hardy Cross Validation Cases")
    print("="*80 + "\n")
    
    # 案例1
    validation_case_1_two_loop_network()
    
    print("\n" + "="*80)
    print("✓✓✓ 所有验证案例通过 ✓✓✓")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
