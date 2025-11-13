from typing import Dict, List, Optional
from topology.network_graph import Edge, NetworkTopology
import numpy as np

class HardyCrossSolver:
    """
    Hardy-Cross
    """

    def __init__(self, max_iter: int = 50, tolerance: float = 1e-4):
        self.max_iter = max_iter
        self.tolerance = tolerance

    def solve(self, topology: NetworkTopology,
             head_loss_func: callable) -> Dict[str, float]:
        print("\n" + "="*60)
        print("Hardy-Cross")
        print("="*60)

        self._initialize_flows(topology)

        for iteration in range(self.max_iter):
            max_correction = 0

            for loop_idx, loop in enumerate(topology.loops):
                delta_Q = self._compute_loop_correction(
                    loop, topology, head_loss_func
                )

                self._apply_correction(loop, delta_Q, topology)

                max_correction = max(max_correction, abs(delta_Q))

            if max_correction < self.tolerance:
                print(f"[OK]  {iteration+1} ")
                print(f"  : {max_correction:.6f} m³/s")
                break

            if iteration % 10 == 0:
                print(f"   {iteration}:  = {max_correction:.6f}")

        print("="*60 + "\n")

        flows = {edge_id: edge.flow for edge_id, edge in topology.edges.items()}
        return flows

    def _initialize_flows(self, topology: NetworkTopology):
        from topology.network_graph import NodeType
        for node in topology.nodes.values():
            if node.node_type == NodeType.SOURCE:
                n_out = len(node.outgoing_edges)
                if n_out > 0:
                    Q_each = node.supply / n_out
                    for edge_id in node.outgoing_edges:
                        topology.edges[edge_id].flow = Q_each

    def _compute_loop_correction(self, loop: List[str],
                                 topology: NetworkTopology,
                                 head_loss_func: callable) -> float:
        sum_h = 0
        sum_derivative = 0

        for i in range(len(loop) - 1):
            node_start = loop[i]
            node_end = loop[i + 1]

            edge = self._find_edge(node_start, node_end, topology)

            if edge:
                Q = edge.flow
                h_loss = head_loss_func(Q, edge)

                if edge.start_node == node_start:
                    direction = 1
                else:
                    direction = -1

                sum_h += direction * h_loss

                if abs(Q) > 1e-6:
                    derivative = 2 * h_loss / Q
                    sum_derivative += abs(derivative)

        if sum_derivative > 1e-10:
            delta_Q = -sum_h / sum_derivative
        else:
            delta_Q = 0

        return delta_Q

    def _find_edge(self, node1: str, node2: str,
                  topology: NetworkTopology) -> Optional[Edge]:
        for edge in topology.edges.values():
            if (edge.start_node == node1 and edge.end_node == node2) or \
               (edge.start_node == node2 and edge.end_node == node1):
                return edge
        return None

    def _apply_correction(self, loop: List[str], delta_Q: float,
                         topology: NetworkTopology):
        for i in range(len(loop) - 1):
            node_start = loop[i]
            node_end = loop[i + 1]

            edge = self._find_edge(node_start, node_end, topology)

            if edge:
                if edge.start_node == node_start:
                    edge.flow += delta_Q
                else:
                    edge.flow -= delta_Q
