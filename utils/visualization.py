import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict
from topology.network_graph import NetworkTopology, NodeType

def visualize_network(topology: NetworkTopology, results: Dict = None):
    """可视化网络拓扑"""
    G = nx.DiGraph()

    for node_id, node in topology.nodes.items():
        G.add_node(node_id, type=node.node_type.value)

    for edge in topology.edges.values():
        G.add_edge(edge.start_node, edge.end_node,
                  flow=edge.flow, id=edge.id)

    pos = nx.spring_layout(G, k=2, iterations=50)

    plt.figure(figsize=(14, 10))

    node_colors = []
    for node_id in G.nodes():
        node = topology.nodes[node_id]
        if node.node_type == NodeType.SOURCE:
            node_colors.append('lightblue')
        elif node.node_type == NodeType.SINK:
            node_colors.append('lightcoral')
        elif node.node_type == NodeType.BRANCH:
            node_colors.append('lightgreen')
        else:
            node_colors.append('lightgray')

    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                          node_size=800, alpha=0.9)

    nx.draw_networkx_edges(G, pos, edge_color='gray',
                          arrows=True, arrowsize=20, width=2)

    nx.draw_networkx_labels(G, pos, font_size=8)

    if results:
        edge_labels = {}
        for edge_id, flow in results['edges'].items():
            edge = topology.edges[edge_id]
            edge_labels[(edge.start_node, edge.end_node)] = f"{flow:.1f}"
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7)

    plt.title("水网拓扑结构", fontsize=14, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('network_topology.png', dpi=150, bbox_inches='tight')
    print("\n✓ 拓扑图已保存: network_topology.png")
