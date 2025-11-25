# -*- coding: utf-8 -*-
import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from solvers.coupled_solver import CoupledNetworkSolver

def example_tree_network():
    """示例2: 树杈型网络"""
    print("\n" + "="*60)
    print("示例2: 树杈型网络 (Tree Network)")
    print("           水库")
    print("            |")
    print("          主干渠")
    print("         /  |  \\")
    print("      支渠1 支渠2 支渠3")
    print("       |    |    |")
    print("      池1  池2  池3")
    print("="*60)

    topology = NetworkTopology()

    topology.add_node(Node("水库", NodeType.SOURCE, supply=15))
    topology.add_node(Node("主干渠头", NodeType.JUNCTION))
    topology.add_node(Node("分水口", NodeType.BRANCH))
    topology.add_node(Node("支渠1末", NodeType.JUNCTION))
    topology.add_node(Node("支渠2末", NodeType.JUNCTION))
    topology.add_node(Node("支渠3末", NodeType.JUNCTION))
    topology.add_node(Node("水池1", NodeType.SINK, demand=5))
    topology.add_node(Node("水池2", NodeType.SINK, demand=6))
    topology.add_node(Node("水池3", NodeType.SINK, demand=4))

    topology.add_edge(Edge("主干", "水库", "主干渠头", None, 2000))
    topology.add_edge(Edge("主至分", "主干渠头", "分水口", None, 3000))
    topology.add_edge(Edge("支渠1", "分水口", "支渠1末", None, 1500))
    topology.add_edge(Edge("支渠2", "分水口", "支渠2末", None, 2000))
    topology.add_edge(Edge("支渠3", "分水口", "支渠3末", None, 1000))
    topology.add_edge(Edge("末至池1", "支渠1末", "水池1", None, 500))
    topology.add_edge(Edge("末至池2", "支渠2末", "水池2", None, 500))
    topology.add_edge(Edge("末至池3", "支渠3末", "水池3", None, 500))

    info = topology.analyze_topology()

    solver = CoupledNetworkSolver(topology)
    results = solver.solve_timestep(dt=60)

    print("\n分支节点流量分配:")
    branch_node = topology.nodes["分水口"]
    # print(f"入流: {sum(topology.edges[e].flow for e in branch_node.incoming_edges):.2f} m^3/s")
    for edge_id in branch_node.outgoing_edges:
        edge = topology.edges[edge_id]
        print(f"  {edge_id}: {edge.flow:.2f} m^3/s")

if __name__ == "__main__":
    example_tree_network()
