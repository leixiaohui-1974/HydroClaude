from typing import List, Dict, Optional
from topology.network_graph import Node, Edge, NetworkTopology

class NodeProcessor:
    """节点处理器 - 处理多路节点的内边界条件"""

    @staticmethod
    def solve_junction_node(node: Node, edges: Dict[str, Edge],
                           topology: NetworkTopology) -> Dict[str, float]:
        """
        求解连接节点
        连续性方程: Σ Q_in = Σ Q_out + demand
        能量方程: H_in = H_out (忽略局部损失时)
        """
        incoming_flows = []
        outgoing_flows = []

        for edge_id in node.incoming_edges:
            edge = edges[edge_id]
            incoming_flows.append(edge.flow)

        for edge_id in node.outgoing_edges:
            edge = edges[edge_id]
            outgoing_flows.append(edge.flow)

        Q_in = sum(incoming_flows)
        Q_out = sum(outgoing_flows)
        Q_demand = node.demand

        residual = Q_in - Q_out - Q_demand

        return {
            'flow_residual': residual,
            'head': node.head
        }

    @staticmethod
    def solve_branch_node(node: Node, edges: Dict[str, Edge],
                         split_ratios: Optional[List[float]] = None) -> Dict[str, float]:
        """
        求解分支节点（一入多出）
        """
        Q_in = 0
        for edge_id in node.incoming_edges:
            Q_in += edges[edge_id].flow

        n_out = len(node.outgoing_edges)

        if split_ratios is None:
            split_ratios = [1.0 / n_out] * n_out

        Q_out = []
        for i, edge_id in enumerate(node.outgoing_edges):
            Q_i = Q_in * split_ratios[i]
            Q_out.append(Q_i)
            edges[edge_id].flow = Q_i

        return {
            'outflows': Q_out,
            'head': node.head
        }

    @staticmethod
    def solve_merge_node(node: Node, edges: Dict[str, Edge], topology: NetworkTopology) -> Dict[str, float]:
        """
        求解汇合节点（多入一出）
        """
        Q_in_total = 0
        H_weighted = 0

        for edge_id in node.incoming_edges:
            edge = edges[edge_id]
            Q_in = edge.flow
            H_in = topology.nodes[edge.start_node].head

            Q_in_total += Q_in
            H_weighted += Q_in * H_in

        if Q_in_total > 0:
            node.head = H_weighted / Q_in_total

        for edge_id in node.outgoing_edges:
            edges[edge_id].flow = Q_in_total

        return {
            'total_inflow': Q_in_total,
            'mixed_head': node.head
        }
