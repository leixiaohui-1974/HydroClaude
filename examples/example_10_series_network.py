import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from solvers.coupled_solver import CoupledNetworkSolver

def example_series_network():
    """示例1: 串联网络"""
    print("\n" + "="*60)
    print("示例1: 串联网络 (Series Network)")
    print("水库 → 渠道1 → 闸门 → 渠道2 → 泵站 → 管道 → 水池")
    print("="*60)

    topology = NetworkTopology()

    topology.add_node(Node("N0_水库", NodeType.SOURCE, elevation=100, supply=10))
    topology.add_node(Node("N1_渠首", NodeType.JUNCTION, elevation=95))
    topology.add_node(Node("N2_闸前", NodeType.JUNCTION, elevation=90))
    topology.add_node(Node("N3_闸后", NodeType.JUNCTION, elevation=88))
    topology.add_node(Node("N4_泵前", NodeType.JUNCTION, elevation=85))
    topology.add_node(Node("N5_泵后", NodeType.JUNCTION, elevation=110))
    topology.add_node(Node("N6_管末", NodeType.JUNCTION, elevation=108))
    topology.add_node(Node("N7_水池", NodeType.SINK, elevation=105, demand=8))

    topology.add_edge(Edge("E1", "N0_水库", "N1_渠首", None, 1000))
    topology.add_edge(Edge("E2", "N1_渠首", "N2_闸前", None, 3000))
    topology.add_edge(Edge("E3", "N2_闸前", "N3_闸后", None, 10))
    topology.add_edge(Edge("E4", "N3_闸后", "N4_泵前", None, 2000))
    topology.add_edge(Edge("E5", "N4_泵前", "N5_泵后", None, 5))
    topology.add_edge(Edge("E6", "N5_泵后", "N6_管末", None, 5000))
    topology.add_edge(Edge("E7", "N6_管末", "N7_水池", None, 1000))

    info = topology.analyze_topology()

    solver = CoupledNetworkSolver(topology)
    results = solver.solve_timestep(dt=60)

    print("\n求解结果:")
    print("节点水头:")
    for node_id, head in results['nodes'].items():
        print(f"  {node_id}: {head:.2f} m")
    print("\n管段流量:")
    for edge_id, flow in results['edges'].items():
        print(f"  {edge_id}: {flow:.2f} m³/s")

if __name__ == "__main__":
    example_series_network()
