#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""



- 
- /
- 
- 



: Claude
: 2025-10-23
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import HydraulicStructure


class CanalSegment:
    """"""

    def __init__(self, segment_id: str, solver: HydrostaticCanalSolver,
                 upstream_node: str, downstream_node: str):
        """
        Args:
            segment_id: ID
            solver: 
            upstream_node: ID
            downstream_node: ID
        """
        self.id = segment_id
        self.solver = solver
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node

    def __repr__(self):
        return f"CanalSegment(id={self.id}, {self.upstream_node}→{self.downstream_node})"


class NetworkNode:
    """

    
    - source: 
    - sink: 
    - junction: 
    - bifurcation: 
    - internal: 
    """

    def __init__(self, node_id: str, node_type: str,
                 boundary_condition: Optional[Dict] = None):
        """
        Args:
            node_id: ID
            node_type: 
            boundary_condition: 
        """
        self.id = node_id
        self.type = node_type
        self.boundary_condition = boundary_condition or {}

        # 
        self.inlet_segments: List[CanalSegment] = []
        self.outlet_segments: List[CanalSegment] = []

        # 
        self.h = 0.0  # 
        self.Q_in = 0.0  # 
        self.Q_out = 0.0  # 

    def add_inlet_segment(self, segment: CanalSegment):
        """"""
        self.inlet_segments.append(segment)

    def add_outlet_segment(self, segment: CanalSegment):
        """"""
        self.outlet_segments.append(segment)

    def compute_mass_balance(self) -> float:
        """
        

        Returns:
            residual: Q_in - Q_out
        """
        Q_in = sum(seg.solver.get_Q()[-1] for seg in self.inlet_segments)
        Q_out = sum(seg.solver.get_Q()[0] for seg in self.outlet_segments)
        return Q_in - Q_out

    def __repr__(self):
        return (f"NetworkNode(id={self.id}, type={self.type}, "
                f"in={len(self.inlet_segments)}, out={len(self.outlet_segments)})")


class CanalNetworkSolver:
    """"""

    def __init__(self):
        """"""
        self.segments: Dict[str, CanalSegment] = {}
        self.nodes: Dict[str, NetworkNode] = {}
        self.g = 9.81

    def add_node(self, node_id: str, node_type: str,
                boundary_condition: Optional[Dict] = None):
        """
        

        Args:
            node_id: ID
            node_type:  ('source', 'sink', 'junction', 'bifurcation', 'internal')
            boundary_condition: 
        """
        node = NetworkNode(node_id, node_type, boundary_condition)
        self.nodes[node_id] = node

    def add_canal_segment(self, segment_id: str, upstream_node: str,
                         downstream_node: str, length: float, nx: int,
                         B: float, S0: float, n: float,
                         internal_structures: Optional[List] = None):
        """
        

        Args:
            segment_id: ID
            upstream_node: ID
            downstream_node: ID
            length:  (m)
            nx: 
            B:  (m)
            S0: 
            n: 
            internal_structures: 
        """
        # 
        if upstream_node not in self.nodes:
            raise ValueError(f"Upstream node {upstream_node} not found")
        if downstream_node not in self.nodes:
            raise ValueError(f"Downstream node {downstream_node} not found")

        # 
        solver = HydrostaticCanalSolver(
            length=length, nx=nx, B=B, S0=S0, n=n,
            internal_structures=internal_structures
        )

        # 
        segment = CanalSegment(segment_id, solver, upstream_node, downstream_node)
        self.segments[segment_id] = segment

        # 
        self.nodes[upstream_node].add_outlet_segment(segment)
        self.nodes[downstream_node].add_inlet_segment(segment)

    def initialize_network(self, h_initial: float = 1.0, Q_initial: float = 5.0):
        """
        

        Args:
            h_initial:  (m)
            Q_initial:  (m³/s)
        """
        for segment in self.segments.values():
            solver = segment.solver
            solver.h = np.ones(solver.nx) * h_initial
            solver.hu = np.ones(solver.nx) * Q_initial / solver.B

        print(f"")
        print(f"  : {len(self.nodes)}")
        print(f"  : {len(self.segments)}")

    def _distribute_flow_at_bifurcation(self, node: NetworkNode, Q_in: float):
        """
        

        

        Args:
            node: 
            Q_in: 

        Returns:
            Q_
        """
        if len(node.outlet_segments) == 0:
            return {}

        # 
        B_total = sum(seg.solver.B for seg in node.outlet_segments)

        Q_distribution = {}
        for segment in node.outlet_segments:
            Q_branch = Q_in * (segment.solver.B / B_total)
            Q_distribution[segment.id] = Q_branch

        return Q_distribution

    def solve_network_steady(self, max_iterations: int = 100,
                            tolerance: float = 0.01, verbose: bool = True):
        """
        

        

        Args:
            max_iterations: 
            tolerance: 
            verbose: 

        Returns:
            converged: 
        """
        if verbose:
            print(f"\n:")
            print(f"  : {max_iterations}")
            print(f"  : {tolerance} m³/s")

        # 
        flow_distribution = {}

        for iteration in range(max_iterations):
            # 1. 
            for segment in self.segments.values():
                # 
                upstream_node = self.nodes[segment.upstream_node]
                downstream_node = self.nodes[segment.downstream_node]

                #  - 
                if upstream_node.type == 'source':
                    Q_in = upstream_node.boundary_condition.get('Q', 5.0)
                elif upstream_node.type == 'bifurcation':
                    # 
                    if segment.upstream_node not in flow_distribution:
                        # 
                        Q_total_in = sum(s.solver.get_Q()[-1]
                                       for s in upstream_node.inlet_segments)
                        if Q_total_in < 0.1:
                            Q_total_in = 5.0
                        # 
                        flow_distribution[segment.upstream_node] = \
                            self._distribute_flow_at_bifurcation(upstream_node, Q_total_in)

                    Q_in = flow_distribution[segment.upstream_node].get(segment.id, 5.0)
                else:
                    # 
                    if len(upstream_node.inlet_segments) > 0:
                        Q_in = sum(s.solver.get_Q()[-1]
                                 for s in upstream_node.inlet_segments)
                    else:
                        Q_in = 5.0

                if downstream_node.type == 'sink':
                    h_out = downstream_node.boundary_condition.get('h', 1.0)
                else:
                    # 
                    if len(downstream_node.outlet_segments) > 0:
                        h_out = np.mean([s.solver.h[0]
                                       for s in downstream_node.outlet_segments])
                    else:
                        h_out = 1.0

                # 
                segment.solver.solve_steady_state(
                    Q_target=Q_in,
                    h_downstream=h_out,
                    max_iterations=100,
                    verbose=False
                )

            # 2. 
            for node_id, node in self.nodes.items():
                if node.type == 'bifurcation' and len(node.inlet_segments) > 0:
                    Q_total_in = sum(s.solver.get_Q()[-1]
                                   for s in node.inlet_segments)
                    flow_distribution[node_id] = \
                        self._distribute_flow_at_bifurcation(node, Q_total_in)

            # 3. 
            max_residual = 0.0
            for node in self.nodes.values():
                if node.type not in ['source', 'sink']:
                    residual = abs(node.compute_mass_balance())
                    max_residual = max(max_residual, residual)

            # 4. 
            if verbose and (iteration % 10 == 0 or iteration < 5):
                print(f"   {iteration}:  = {max_residual:.4e} m³/s")

            # 5. 
            if max_residual < tolerance:
                if verbose:
                    print(f"   {iteration}")
                return True

        if verbose:
            print(f"   {max_residual:.4e} m³/s")
        return False

    def get_network_state(self) -> Dict:
        """
        

        Returns:
            state: 
        """
        state = {
            'segments': {},
            'nodes': {}
        }

        # 
        for seg_id, segment in self.segments.items():
            state['segments'][seg_id] = {
                'x': segment.solver.x.copy(),
                'h': segment.solver.h.copy(),
                'Q': segment.solver.get_Q().copy(),
                'upstream_node': segment.upstream_node,
                'downstream_node': segment.downstream_node
            }

        # 
        for node_id, node in self.nodes.items():
            Q_in = sum(seg.solver.get_Q()[-1] for seg in node.inlet_segments)
            Q_out = sum(seg.solver.get_Q()[0] for seg in node.outlet_segments)
            h_avg = 0.0
            if node.inlet_segments:
                h_avg = np.mean([seg.solver.h[-1] for seg in node.inlet_segments])
            elif node.outlet_segments:
                h_avg = np.mean([seg.solver.h[0] for seg in node.outlet_segments])

            state['nodes'][node_id] = {
                'type': node.type,
                'h': h_avg,
                'Q_in': Q_in,
                'Q_out': Q_out,
                'balance': Q_in - Q_out
            }

        return state

    def print_network_summary(self):
        """"""
        state = self.get_network_state()

        print(f"\n" + "=" * 60)
        print("")
        print("=" * 60)

        print(f"\n")
        for node_id, node_state in state['nodes'].items():
            print(f"  {node_id} ({node_state['type']}):")
            print(f"    : {node_state['h']:.3f} m")
            print(f"    : {node_state['Q_in']:.3f} m³/s")
            print(f"    : {node_state['Q_out']:.3f} m³/s")
            print(f"    : {node_state['balance']:.4e} m³/s")

        print(f"\n")
        for seg_id, seg_state in state['segments'].items():
            Q_mean = np.mean(seg_state['Q'])
            h_mean = np.mean(seg_state['h'])
            print(f"  {seg_id} ({seg_state['upstream_node']}→{seg_state['downstream_node']}):")
            print(f"    : {h_mean:.3f} m")
            print(f"    : {Q_mean:.3f} m³/s")

    def __repr__(self):
        return (f"CanalNetworkSolver(nodes={len(self.nodes)}, "
                f"segments={len(self.segments)})")


# 
if __name__ == "__main__":
    print("=" * 60)
    print("")
    print("=" * 60)

    # 
    network = CanalNetworkSolver()

    # 
    network.add_node('N1', 'source', {'Q': 10.0})
    network.add_node('N2', 'internal')
    network.add_node('N3', 'internal')
    network.add_node('N4', 'sink', {'h': 1.0})

    # 
    network.add_canal_segment('C1', 'N1', 'N2',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)
    network.add_canal_segment('C2', 'N2', 'N3',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)
    network.add_canal_segment('C3', 'N3', 'N4',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)

    # 
    network.initialize_network(h_initial=1.0, Q_initial=10.0)

    # 
    converged = network.solve_network_steady(max_iterations=50, verbose=True)

    # 
    network.print_network_summary()

    print(f"\n: {' ' if converged else ' '}")
