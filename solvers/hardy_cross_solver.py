"""
Hardy Cross Solver Module - Hardy Cross

This module implements the Hardy Cross method for pipe network analysis.

The Hardy Cross method (1936) is an iterative technique for solving pipe
network flows by enforcing:
1. Continuity at nodes: ΣQ_in = ΣQ_out + demand
2. Energy conservation in loops: Σh_loss = 0

Classes:
    HardyCrossSolver: Hardy Cross iterative solver

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings

from network.network_topology import NetworkTopology
from network.network_node import NetworkNode, Junction, Reservoir, Tank
from network.pressure_pipe import PressurePipe


class HardyCrossSolver:
    """
    Hardy Cross  - Hardy Cross Pipe Network Solver

    The Hardy Cross method is a classical iterative technique for solving
    pipe network flows. It was developed by Hardy Cross in 1936 and remains
    widely used for water distribution network analysis.

     Principle:
    ---------------
    1. 
       Initialize flows (satisfy continuity)

    2. 
       Identify all independent loops

    3. 
       Iteratively correct flows for each loop:

       Σh_loss = 0  (energy conservation)

        Correction formula:
       ΔQ = -Σh / (n * Σ(h/Q))

        where:
       - h =  (head loss)
       - Q =  (flow rate)
       - n =  (exponent, n=2 for Darcy-Weisbach)

    4. 
       Check convergence

    Typical usage:
        >>> solver = HardyCrossSolver(network, max_iter=100, tol=1e-6)
        >>> flows, heads = solver.solve()
        >>> print(f"Converged in {solver.iteration_count} iterations")
    """

    def __init__(
        self,
        network: NetworkTopology,
        max_iter: int = 100,
        tol: float = 1e-6,
        relaxation_factor: float = 1.0,
        verbose: bool = True
    ):
        """
        Hardy Cross

        Args:
            network: 
            max_iter: 
            tol:  (m³/s)
            relaxation_factor:  (0 < α ≤ 1)
            verbose: 

        Raises:
            ValueError: 
        """
        # 
        if max_iter <= 0:
            raise ValueError(f" > 0: {max_iter}")

        if tol <= 0:
            raise ValueError(f" > 0: {tol}")

        if not (0 < relaxation_factor <= 1.0):
            raise ValueError(f"(0, 1]: {relaxation_factor}")

        # 
        is_valid, issues = network.validate()
        if not is_valid:
            raise ValueError(f": {issues}")

        # 
        self.network = network
        self.max_iter = max_iter
        self.tol = tol
        self.alpha = relaxation_factor  # 
        self.verbose = verbose

        # 
        self.iteration_count = 0
        self.converged = False
        self.flows: Dict[str, float] = {}  # {pipe_id: Q}
        self.heads: Dict[str, float] = {}  # {node_id: H}

        # 
        self.loops: List[List[str]] = []
        self.loop_matrix: np.ndarray = None
        self.pipe_ids: List[str] = []

    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        

        Returns:
            (flows, heads) 
            - flows: {pipe_id: Q (m³/s)}
            - heads: {node_id: H (m)}

        Raises:
            RuntimeError: 
        """
        if self.verbose:
            print("\n" + "="*80)
            print("Hardy Cross  - Pipe Network Analysis")
            print("="*80)

        # 1: 
        self._identify_loops()

        # 2: 
        self._initialize_flows()

        # 3: Hardy Cross
        self._hardy_cross_iteration()

        # 4: 
        self._calculate_heads()

        if self.verbose:
            print("="*80 + "\n")

        return self.flows, self.heads

    def _identify_loops(self):
        """"""
        if self.verbose:
            print("\n[1] ")

        self.loops = self.network.find_loops()

        if self.verbose:
            print(f"   {len(self.loops)} ")

        if len(self.loops) == 0:
            warnings.warn("No loops found in network - Hardy Cross method requires loop topology", stacklevel=2)

        # 
        self.loop_matrix, _, self.pipe_ids = self.network.loop_matrix()

    def _initialize_flows(self):
        """
        

        
        1. Reservoir
        2. 
        3. 
        """
        if self.verbose:
            print("\n[2] ")

        # 0
        for pipe_id in self.network.pipes:
            self.flows[pipe_id] = 0.0

        # 
        reservoirs = [node for node in self.network.nodes.values()
                     if isinstance(node, Reservoir)]

        if len(reservoirs) == 0:
            warnings.warn("(Reservoir)0")
            return

        if len(self.loops) == 0:
            self._initialize_tree_flows(reservoirs)
            if self.verbose:
                non_zero_flows = sum(1 for Q in self.flows.values() if abs(Q) > 1e-10)
                print(f"   {non_zero_flows} ")
            return

        # 
        total_demand = sum(node.demand for node in self.network.nodes.values()
                          if isinstance(node, Junction))

        if self.verbose:
            print(f"  : {len(reservoirs)}")
            print(f"  : {total_demand:.6f} m³/s")

        # 1: 
        # 
        for reservoir in reservoirs:
            # 
            pipes_from_source = []
            for pipe_id, direction in self.network.get_node_pipes(reservoir.node_id):
                if direction == 'out':
                    pipes_from_source.append(pipe_id)

            if len(pipes_from_source) > 0:
                # 
                Q_per_pipe = total_demand / (len(reservoirs) * len(pipes_from_source))
                for pipe_id in pipes_from_source:
                    self.flows[pipe_id] = Q_per_pipe

        if self.verbose:
            non_zero_flows = sum(1 for Q in self.flows.values() if abs(Q) > 1e-10)
            print(f"   {non_zero_flows} ")

    def _initialize_tree_flows(self, reservoirs: List[Reservoir]) -> None:
        """Initialize flows for an acyclic network by demand aggregation.

        For tree networks, Hardy Cross loop corrections are unavailable.
        A physically meaningful initial condition is therefore the exact
        continuity-satisfying branch flow obtained by summing downstream
        junction demands away from each reservoir.
        """
        if len(reservoirs) != 1:
            warnings.warn("Tree-flow initialization currently assumes a single reservoir")
            return

        root_id = reservoirs[0].node_id
        parent: Dict[str, Optional[str]] = {root_id: None}
        order: List[str] = []
        stack = [root_id]

        while stack:
            node_id = stack.pop()
            order.append(node_id)
            for neighbor in self.network.adjacency[node_id]:
                if neighbor in parent:
                    continue
                parent[neighbor] = node_id
                stack.append(neighbor)

        subtree_demand: Dict[str, float] = {}
        for node_id in reversed(order):
            node = self.network.nodes[node_id]
            own_demand = node.demand if isinstance(node, Junction) else 0.0
            total = own_demand
            for neighbor in self.network.adjacency[node_id]:
                if parent.get(neighbor) == node_id:
                    total += subtree_demand.get(neighbor, 0.0)
            subtree_demand[node_id] = total

        for node_id, parent_id in parent.items():
            if parent_id is None:
                continue

            pipe_id = self.network._find_pipe_between(parent_id, node_id)
            if pipe_id is None:
                continue

            flow = subtree_demand[node_id]
            from_node, to_node = self.network.pipe_connections[pipe_id]
            if from_node == parent_id and to_node == node_id:
                self.flows[pipe_id] = flow
            elif from_node == node_id and to_node == parent_id:
                self.flows[pipe_id] = -flow

    def _hardy_cross_iteration(self):
        """Hardy Cross"""
        if self.verbose:
            print("\n[3] Hardy Cross")
            print(f"  : {self.max_iter}")
            print(f"  : {self.tol:.2e} m³/s")
            print(f"  : {self.alpha:.2f}")
            print("\n  :")

        for iteration in range(self.max_iter):
            max_correction = 0.0

            # 
            for loop_idx, loop in enumerate(self.loops):
                # 
                delta_Q = self._compute_loop_correction(loop)

                # 
                delta_Q *= self.alpha

                # 
                self._apply_loop_correction(loop, delta_Q)

                # 
                max_correction = max(max_correction, abs(delta_Q))

            # 
            self.iteration_count = iteration + 1

            if self.verbose and (iteration < 10 or iteration % 10 == 0 or
                                max_correction < self.tol):
                print(f"     {iteration+1:3d}:  = {max_correction:.8f} m³/s")

            if max_correction < self.tol:
                self.converged = True
                if self.verbose:
                    print(f"\n  [OK] ")
                    print(f"    : {self.iteration_count}")
                    print(f"    : {max_correction:.10f} m³/s")
                return

        # 
        self.converged = False
        error_msg = (f"Hardy Cross:  {self.max_iter}"
                    f" {max_correction:.8f} >  {self.tol:.8f}")

        if self.verbose:
            print(f"\n  [FAIL] {error_msg}")

        raise RuntimeError(error_msg)

    def _compute_loop_correction(self, loop: List[str]) -> float:
        """
        

        : ΔQ = -Σh / (n * Σ(h/Q))

        Args:
            loop: 

        Returns:
             (m³/s)
        """
        sum_h = 0.0        # Σh
        sum_h_over_Q = 0.0 # Σ(h/Q)

        # 
        for i in range(len(loop)):
            node1 = loop[i]
            node2 = loop[(i + 1) % len(loop)]

            # 
            pipe_id = self.network._find_pipe_between(node1, node2)

            if pipe_id is None:
                continue

            pipe = self.network.pipes[pipe_id]
            Q = self.flows[pipe_id]

            #
            if abs(Q) < 1e-12:
                # 0
                continue

            h_loss = pipe.head_loss(abs(Q))

            # Determine if actual flow direction agrees with loop traversal direction
            # from_node -> to_node is the pipe's defined positive direction
            # node1 -> node2 is the loop traversal direction
            from_node, to_node = self.network.pipe_connections[pipe_id]

            if from_node == node1 and to_node == node2:
                # Pipe defined direction agrees with loop traversal
                # If Q > 0: actual flow is in pipe's defined direction = agrees with traversal → positive h_loss
                # If Q < 0: actual flow is opposite to pipe's defined direction = opposes traversal → negative h_loss
                direction = 1.0 if Q >= 0 else -1.0
            elif from_node == node2 and to_node == node1:
                # Pipe defined direction opposes loop traversal
                # If Q > 0: actual flow is in pipe's defined direction = opposes traversal → negative h_loss
                # If Q < 0: actual flow is opposite to pipe's defined direction = agrees with traversal → positive h_loss
                direction = -1.0 if Q >= 0 else 1.0
            else:
                direction = 0.0

            #
            sum_h += direction * h_loss
            sum_h_over_Q += h_loss / abs(Q)

        # 
        # ΔQ = -Σh / (n * Σ(h/Q))
        # Darcy-Weisbachn=2
        n = 2.0

        if sum_h_over_Q > 1e-12:
            delta_Q = -sum_h / (n * sum_h_over_Q)
        else:
            delta_Q = 0.0

        return delta_Q

    def _apply_loop_correction(self, loop: List[str], delta_Q: float):
        """
        

        Args:
            loop: 
            delta_Q: 
        """
        for i in range(len(loop)):
            node1 = loop[i]
            node2 = loop[(i + 1) % len(loop)]

            pipe_id = self.network._find_pipe_between(node1, node2)

            if pipe_id is None:
                continue

            # 
            from_node, to_node = self.network.pipe_connections[pipe_id]

            if from_node == node1 and to_node == node2:
                # 
                self.flows[pipe_id] += delta_Q
            elif from_node == node2 and to_node == node1:
                # 
                self.flows[pipe_id] -= delta_Q

    def _calculate_heads(self):
        """
        

        
        1. Reservoir
        2. 
        3. : H_j = H_i - h_loss
        """
        if self.verbose:
            print("\n[4] ")

        # None
        self.heads = {}

        # 
        for node_id, node in self.network.nodes.items():
            if isinstance(node, Reservoir):
                self.heads[node_id] = node.available_head()

        # BFS
        from collections import deque

        visited = set(self.heads.keys())
        queue = deque(visited)

        while queue:
            current_node = queue.popleft()
            H_current = self.heads[current_node]

            # 
            for neighbor in self.network.adjacency[current_node]:
                if neighbor in visited:
                    continue

                # 
                pipe_id = self.network._find_pipe_between(current_node, neighbor)

                if pipe_id is None:
                    continue

                pipe = self.network.pipes[pipe_id]
                Q = self.flows[pipe_id]

                # 
                h_loss = pipe.head_loss(abs(Q))

                # 
                from_node, to_node = self.network.pipe_connections[pipe_id]

                if from_node == current_node and to_node == neighbor:
                    # 
                    H_neighbor = H_current - h_loss
                elif from_node == neighbor and to_node == current_node:
                    # 
                    H_neighbor = H_current + h_loss
                else:
                    continue

                # 
                self.heads[neighbor] = H_neighbor
                visited.add(neighbor)
                queue.append(neighbor)

        # 
        missing_heads = set(self.network.nodes.keys()) - visited

        if missing_heads:
            warnings.warn(
                f": {missing_heads}"
                ""
            )

        if self.verbose:
            print(f"   {len(self.heads)}/{len(self.network.nodes)} ")

    def get_convergence_history(self) -> Dict[str, any]:
        """
        

        Returns:
            
        """
        return {
            'converged': self.converged,
            'iterations': self.iteration_count,
            'tolerance': self.tol,
            'max_iterations': self.max_iter
        }

    def get_results_summary(self) -> Dict[str, any]:
        """
        

        Returns:
            
        """
        if not self.converged:
            return {'status': 'not_converged'}

        # 
        flow_values = list(self.flows.values())
        total_flow = sum(abs(Q) for Q in flow_values)

        # 
        head_values = list(self.heads.values())

        # 
        pressures = []
        for node_id, H in self.heads.items():
            node = self.network.nodes[node_id]
            pressure = H - node.elevation
            pressures.append(pressure)

        return {
            'status': 'converged',
            'iterations': self.iteration_count,
            'num_loops': len(self.loops),
            'num_pipes': len(self.flows),
            'total_flow': total_flow,
            'flow_min': min(flow_values) if flow_values else 0.0,
            'flow_max': max(flow_values) if flow_values else 0.0,
            'head_min': min(head_values) if head_values else 0.0,
            'head_max': max(head_values) if head_values else 0.0,
            'pressure_min': min(pressures) if pressures else 0.0,
            'pressure_max': max(pressures) if pressures else 0.0,
        }

    def __repr__(self) -> str:
        status = "" if self.converged else ""
        return (f"HardyCrossSolver(iterations={self.iteration_count}, "
                f"status='{status}', loops={len(self.loops)})")
