"""
Unit Tests for Newton-Raphson Network Solver
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
try:
    from solvers.newton_raphson_network_solver import NewtonRaphsonNetworkSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir
from network.pressure_pipe import PressurePipe


class TestNewtonRaphsonSolver:
    """测试Newton-Raphson求解器"""

    def test_simple_network(self):
        """测试简单网络"""
        topology = NetworkTopology()
        r1 = Reservoir("R1", elevation=50.0, head=50.0)
        j1 = Junction("J1", elevation=10.0, demand=0.05)
        topology.add_node(r1)
        topology.add_node(j1)
        
        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(p1, "R1", "J1")
        
        solver = NewtonRaphsonNetworkSolver(topology, verbose=False)
        flows, heads = solver.solve()
        
        assert solver.converged
        assert abs(flows["P1"] - 0.05) < 0.01
    
    def test_solver_initialization(self):
        """测试求解器初始化"""
        topology = NetworkTopology()
        r1 = Reservoir("R1", elevation=50.0, head=50.0)
        topology.add_node(r1)
        
        solver = NewtonRaphsonNetworkSolver(topology, max_iter=50, tol=1e-6)
        assert solver.max_iter == 50
        assert solver.tol == 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
