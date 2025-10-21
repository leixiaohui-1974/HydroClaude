from typing import List, Dict, Tuple
from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from topology.node_processor import NodeProcessor
from solvers.hardy_cross import HardyCrossSolver
from collections import deque
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve

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
        sorted_nodes = self._topological_sort()

        for node_id in sorted_nodes:
            node = self.topology.nodes[node_id]

            if node.node_type == NodeType.SOURCE:
                pass

            elif node.node_type == NodeType.JUNCTION:
                self.node_processor.solve_junction_node(
                    node, self.topology.edges, self.topology
                )

            elif node.node_type == NodeType.BRANCH:
                self.node_processor.solve_branch_node(
                    node, self.topology.edges
                )

            elif node.node_type == NodeType.MERGE:
                self.node_processor.solve_merge_node(
                    node, self.topology.edges, self.topology
                )

            for edge_id in node.outgoing_edges:
                edge = self.topology.edges[edge_id]

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

        eq_idx = 0
        for node_id, node in self.topology.nodes.items():
            eq_idx += 1

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
