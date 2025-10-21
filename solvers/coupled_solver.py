from typing import List, Dict, Tuple
from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from topology.node_processor import NodeProcessor
from solvers.hardy_cross import HardyCrossSolver
from collections import deque
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
import warnings

class CoupledNetworkSolver:
    """全局耦合求解器"""

    def __init__(self, topology: NetworkTopology):
        self.topology = topology
        self.node_processor = NodeProcessor()

    def solve_timestep(self, dt: float, use_hardy_cross: bool = False) -> Dict:
        if self.topology.is_tree:
            return self._solve_tree_network(dt)
        elif self.topology.is_loop and use_hardy_cross:
            return self._solve_loop_network_hardy_cross(dt)
        else:
            return self._solve_global_newton(dt)

    def _solve_tree_network(self, dt: float) -> Dict:
        """
        树状网络求解 - 从源节点到汇节点按拓扑顺序求解
        1. 初始化源节点水头和供水流量
        2. 按拓扑顺序计算每个管段的流量和水头损失
        3. 计算每个节点的水头
        """
        sorted_nodes = self._topological_sort()

        # 初始化源节点
        for node_id in sorted_nodes:
            node = self.topology.nodes[node_id]
            if node.node_type == NodeType.SOURCE:
                node.head = node.elevation + 10.0  # 源节点水头 = 高程 + 10m
                # 从源节点出发的初始流量设为供水量
                for edge_id in node.outgoing_edges:
                    self.topology.edges[edge_id].flow = node.supply

        # 按拓扑顺序求解
        for node_id in sorted_nodes:
            node = self.topology.nodes[node_id]

            if node.node_type == NodeType.SOURCE:
                continue

            # 计算节点水头（从上游节点和水头损失）
            if node.incoming_edges:
                total_inflow = 0
                weighted_head = 0

                for edge_id in node.incoming_edges:
                    edge = self.topology.edges[edge_id]
                    upstream_node = self.topology.nodes[edge.start_node]

                    # 计算水头损失
                    Q = edge.flow
                    L = edge.length
                    D = 1.0
                    C = 100
                    K = 10.67 * L / (C**1.852 * D**4.87)

                    if abs(Q) > 1e-6:
                        h_loss = K * abs(Q)**1.852
                    else:
                        h_loss = 0

                    edge.head_loss = h_loss

                    # 节点水头 = 上游节点水头 - 水头损失
                    node_head = upstream_node.head - h_loss

                    total_inflow += edge.flow
                    weighted_head += edge.flow * node_head

                if total_inflow > 0:
                    node.head = weighted_head / total_inflow
                else:
                    node.head = 0

            # 处理不同类型的节点
            if node.node_type == NodeType.JUNCTION:
                # 连接节点：流量守恒
                total_outflow = sum(self.topology.edges[e].flow for e in node.incoming_edges)
                if node.outgoing_edges:
                    for edge_id in node.outgoing_edges:
                        self.topology.edges[edge_id].flow = total_outflow

            elif node.node_type == NodeType.BRANCH:
                # 分支节点：流量分配
                total_inflow = sum(self.topology.edges[e].flow for e in node.incoming_edges)
                n_out = len(node.outgoing_edges)
                if n_out > 0:
                    flow_per_branch = total_inflow / n_out
                    for edge_id in node.outgoing_edges:
                        self.topology.edges[edge_id].flow = flow_per_branch

            elif node.node_type == NodeType.MERGE:
                # 汇合节点：流量汇总
                total_inflow = sum(self.topology.edges[e].flow for e in node.incoming_edges)
                for edge_id in node.outgoing_edges:
                    self.topology.edges[edge_id].flow = total_inflow

            elif node.node_type == NodeType.SINK:
                # 汇节点：终点
                pass

        return self._collect_results()

    def _solve_loop_network_hardy_cross(self, dt: float) -> Dict:
        def head_loss(Q: float, edge: Edge) -> float:
            L = edge.length
            D = 1.0
            C = 100

            K = 10.67 * L / (C**1.852 * D**4.87)
            h = K * abs(Q)**1.852 * np.sign(Q)
            return h

        hardy_cross = HardyCrossSolver()
        flows = hardy_cross.solve(self.topology, head_loss)

        for edge_id, flow in flows.items():
            self.topology.edges[edge_id].flow = flow

        self._solve_heads_from_flows()

        return self._collect_results()

    def _solve_global_newton(self, dt: float) -> Dict:
        n_nodes = len(self.topology.nodes)
        n_edges = len(self.topology.edges)

        x = np.zeros(n_nodes + n_edges)

        for i, node in enumerate(self.topology.nodes.values()):
            x[i] = node.head
        for i, edge in enumerate(self.topology.edges.values()):
            x[n_nodes + i] = edge.flow

        for iteration in range(20):
            J, R = self._build_global_system(x)

            try:
                dx = spsolve(J, -R)
                x += dx

                if np.linalg.norm(R) < 1e-6:
                    print(f"全局Newton收敛于第 {iteration+1} 次迭代")
                    break
            except:
                print("全局Newton求解失败")
                break

        for i, node in enumerate(self.topology.nodes.values()):
            node.head = x[i]
        for i, edge in enumerate(self.topology.edges.values()):
            edge.flow = x[n_nodes + i]

        return self._collect_results()

    def _build_global_system(self, x: np.ndarray) -> Tuple[csr_matrix, np.ndarray]:
        n_nodes = len(self.topology.nodes)
        n_edges = len(self.topology.edges)
        n_total = n_nodes + n_edges

        J = lil_matrix((n_total, n_total))
        R = np.zeros(n_total)

        node_list = list(self.topology.nodes.keys())
        edge_list = list(self.topology.edges.keys())

        node_idx = {node_id: i for i, node_id in enumerate(node_list)}
        edge_idx = {edge_id: i for i, edge_id in enumerate(edge_list)}

        # 节点流量平衡方程 (前n_nodes个方程)
        for i, node_id in enumerate(node_list):
            node = self.topology.nodes[node_id]

            if node.node_type == NodeType.SOURCE:
                # 源节点：固定水头
                J[i, i] = 1.0
                R[i] = x[i] - (node.elevation + 10.0)  # 假设源头10m水头
            else:
                # 其他节点：流量连续性
                Q_in = 0
                Q_out = 0

                for edge_id in node.incoming_edges:
                    edge = self.topology.edges[edge_id]
                    edge_i = edge_idx[edge_id]
                    Q_in += x[n_nodes + edge_i]
                    # dR/dQ
                    J[i, n_nodes + edge_i] = 1.0

                for edge_id in node.outgoing_edges:
                    edge = self.topology.edges[edge_id]
                    edge_i = edge_idx[edge_id]
                    Q_out += x[n_nodes + edge_i]
                    # dR/dQ
                    J[i, n_nodes + edge_i] = -1.0

                if node.node_type == NodeType.SINK:
                    R[i] = Q_in - Q_out - node.demand
                else:
                    R[i] = Q_in - Q_out

        # 管段能量方程 (后n_edges个方程)
        for j, edge_id in enumerate(edge_list):
            edge = self.topology.edges[edge_id]
            eq_i = n_nodes + j

            start_node_i = node_idx[edge.start_node]
            end_node_i = node_idx[edge.end_node]

            H_start = x[start_node_i]
            H_end = x[end_node_i]
            Q = x[n_nodes + j]

            # 水头损失计算 (Hazen-Williams公式)
            L = edge.length
            D = 1.0  # 假设直径1m
            C = 100  # Hazen-Williams系数

            K = 10.67 * L / (C**1.852 * D**4.87)

            if abs(Q) > 1e-6:
                h_loss = K * abs(Q)**1.852 * np.sign(Q)
                dh_dQ = K * 1.852 * abs(Q)**0.852
            else:
                h_loss = 0
                dh_dQ = 0

            # 方程: H_start - H_end - h_loss = 0
            R[eq_i] = H_start - H_end - h_loss

            # 雅可比矩阵
            J[eq_i, start_node_i] = 1.0
            J[eq_i, end_node_i] = -1.0
            J[eq_i, n_nodes + j] = -dh_dQ

        return J.tocsr(), R

    def _topological_sort(self) -> List[str]:
        in_degree = {node_id: len(node.incoming_edges)
                    for node_id, node in self.topology.nodes.items()}

        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)

            for neighbor in self.topology.adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_nodes

    def _solve_heads_from_flows(self):
        for node in self.topology.nodes.values():
            if node.node_type == NodeType.SOURCE:
                continue

            if node.incoming_edges:
                edge_id = node.incoming_edges[0]
                edge = self.topology.edges[edge_id]
                start_node = self.topology.nodes[edge.start_node]

                node.head = start_node.head - edge.head_loss

    def _collect_results(self) -> Dict:
        return {
            'nodes': {nid: n.head for nid, n in self.topology.nodes.items()},
            'edges': {eid: e.flow for eid, e in self.topology.edges.items()}
        }
