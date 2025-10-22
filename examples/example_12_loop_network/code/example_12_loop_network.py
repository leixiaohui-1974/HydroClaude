import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from solvers.coupled_solver import CoupledNetworkSolver
from utils.visualization import visualize_network

def example_loop_network():
    """示例3: 环状网络"""
    print("\n" + "="*60)
    print("示例3: 环状网络 (Loop Network)")
    print("     N1 ---- E1 ---- N2")
    print("     |               |")
    print("     E4             E2")
    print("     |               |")
    print("     N4 ---- E3 ---- N3")
    print("="*60)

    topology = NetworkTopology()

    topology.add_node(Node("N1", NodeType.SOURCE, supply=10))
    topology.add_node(Node("N2", NodeType.JUNCTION))
    topology.add_node(Node("N3", NodeType.JUNCTION))
    topology.add_node(Node("N4", NodeType.SINK, demand=10))

    topology.add_edge(Edge("E1", "N1", "N2", None, 1000))
    topology.add_edge(Edge("E2", "N2", "N3", None, 1500))
    topology.add_edge(Edge("E3", "N3", "N4", None, 1000))
    topology.add_edge(Edge("E4", "N4", "N1", None, 1500))

    info = topology.analyze_topology()

    solver = CoupledNetworkSolver(topology)
    results = solver.solve_timestep(dt=60, use_hardy_cross=True)

    print("\n环路流量分布:")
    for edge_id, flow in results['edges'].items():
        edge = topology.edges[edge_id]
        print(f"  {edge_id} ({edge.start_node}→{edge.end_node}): {flow:.2f} m³/s")

    visualize_network(topology, results)

if __name__ == "__main__":
    example_loop_network()
