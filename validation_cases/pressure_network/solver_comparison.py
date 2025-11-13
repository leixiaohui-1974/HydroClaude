"""
Solver Comparison - 求解器对比验证
Compare Hardy Cross and Newton-Raphson solvers
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from solvers.newton_raphson_network_solver import compare_solvers
from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir
from network.pressure_pipe import PressurePipe


def main():
    print("\n" + "="*80)
    print("求解器对比验证 - Solver Comparison Validation")
    print("="*80)
    
    # 创建测试网络
    topology = NetworkTopology()
    r1 = Reservoir("R1", elevation=50.0, head=50.0)
    j1 = Junction("J1", elevation=10.0, demand=0.03)
    j2 = Junction("J2", elevation=12.0, demand=0.04)
    
    topology.add_node(r1)
    topology.add_node(j1)
    topology.add_node(j2)
    
    p1 = PressurePipe("P1", diameter=0.4, length=300.0, roughness=0.0003)
    p2 = PressurePipe("P2", diameter=0.3, length=200.0, roughness=0.0003)
    
    topology.add_pipe(p1, "R1", "J1")
    topology.add_pipe(p2, "J1", "J2")
    
    # 对比求解器
    hc, nr = compare_solvers(topology)
    
    print("\n 验证完成")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
