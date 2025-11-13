#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM V2 - 

Phase 1
-  
-  
-  
-  


1. JUNCTION + 
2. BIFURCATION + 
3. 
4. 

: HydroClaude Team
: 2025-10-27
: V2 (Phase 1)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


class NodeType(Enum):
    """"""
    SOURCE = "source"
    SINK = "sink"
    JUNCTION = "junction"
    BIFURCATION = "bifurcation"
    INTERNAL = "internal"


class Node:
    """"""
    
    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        x: float = 0.0,
        y: float = 0.0,
        elevation: float = 0.0,
        bc_value: Optional[float] = None
    ):
        self.id = node_id
        self.type = node_type
        self.x = x
        self.y = y
        self.elevation = elevation
        self.bc_value = bc_value
        
        self.inflow_edges = []
        self.outflow_edges = []
        
        self.h = 0.0
        self.Q = 0.0


class Edge:
    """"""
    
    def __init__(
        self,
        edge_id: str,
        from_node: Node,
        to_node: Node,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        solver: Optional[GodunvFVMSolver] = None
    ):
        self.id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        
        from_node.outflow_edges.append(self)
        to_node.inflow_edges.append(self)
        
        if solver is None:
            self.solver = GodunvFVMSolver(
                width=width, length=length, n_cells=n_cells,
                manning_n=manning_n, slope=slope,
                cfl=0.5, order=1
            )
        else:
            self.solver = solver
        
        self.initialized = False
    
    def initialize(self, h_init, Q_init, bc_left, bc_right):
        self.solver.initialize(h_init, Q_init, bc_left, bc_right)
        self.initialized = True
    
    def step(self, dt: Optional[float] = None):
        return self.solver.step(dt)
    
    def get_upstream_state(self) -> Tuple[float, float]:
        return self.solver.h[0], self.solver.Q[0]
    
    def get_downstream_state(self) -> Tuple[float, float]:
        return self.solver.h[-1], self.solver.Q[-1]
    
    def set_upstream_bc(self, h: Optional[float] = None, Q: Optional[float] = None):
        if h is not None:
            self.solver.bc_left = {'type': 'h', 'value': h}
        elif Q is not None:
            self.solver.bc_left = {'type': 'Q', 'value': Q}
    
    def set_downstream_bc(self, h: Optional[float] = None, Q: Optional[float] = None):
        if h is not None:
            self.solver.bc_right = {'type': 'h', 'value': h}
        elif Q is not None:
            self.solver.bc_right = {'type': 'Q', 'value': Q}


class GodunvFVMNetworkV2:
    """
    Godunov-FVM V2 - 
    
    
    1. 
    2. 
    3. 
    4. 
    """
    
    def __init__(self, g: float = 9.81, relaxation: float = 0.5, update_interval: int = 10):
        """
        
        
        Args:
            g: 
            relaxation: 0-1
            update_interval: 
        """
        self.g = g
        self.relaxation = relaxation  # 
        self.update_interval = update_interval  # 
        
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        
        self.t = 0.0
        self.dt = 0.0
        self.step_count = 0
        
        self.initial_mass = 0.0
        
        # 
        self.prev_node_h = {}
        
        print(" Godunov-FVM V2 ")
        print(f"  : {self.relaxation}")
        print(f"  : {self.update_interval}")
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        x: float = 0.0,
        y: float = 0.0,
        elevation: float = 0.0,
        bc_value: Optional[float] = None
    ) -> Node:
        node = Node(node_id, node_type, x, y, elevation, bc_value)
        self.nodes[node_id] = node
        self.prev_node_h[node_id] = 1.0  # 
        return node
    
    def add_edge(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float
    ) -> Edge:
        from_node = self.nodes[from_node_id]
        to_node = self.nodes[to_node_id]
        
        edge = Edge(
            edge_id, from_node, to_node,
            width, length, n_cells, manning_n, slope
        )
        
        self.edges[edge_id] = edge
        return edge
    
    def initialize_network(self, h_default: float = 1.0, Q_default: float = 0.0):
        print(f"\n:")
        print(f"  : {len(self.nodes)}")
        print(f"  : {len(self.edges)}")
        
        for edge_id, edge in self.edges.items():
            n = edge.solver.n_cells
            h_init = np.ones(n) * h_default
            Q_init = np.ones(n) * Q_default
            
            bc_left = {'type': 'h', 'value': h_default}
            bc_right = {'type': 'h', 'value': h_default}
            
            edge.initialize(h_init, Q_init, bc_left, bc_right)
        
        self.initial_mass = self._compute_total_mass()
        print(f"  : {self.initial_mass:.2f} m³")
    
    def step(self):
        """"""
        # 1. 
        if self.step_count % self.update_interval == 0:
            self._update_boundary_conditions_conservative()
        
        # 2. 
        dt_min = float('inf')
        for edge in self.edges.values():
            dt_edge = edge.solver.compute_dt()
            dt_min = min(dt_min, dt_edge)
        
        self.dt = dt_min
        
        for edge in self.edges.values():
            edge.step(self.dt)
        
        # 3. 
        self._update_node_states()
        
        self.t += self.dt
        self.step_count += 1
    
    def _update_boundary_conditions_conservative(self):
        """
        
        
        
        1.  = 
        2. JUNCTIONQ = Q
        3. BIFURCATIONQ
        4. 
        """
        for node_id, node in self.nodes.items():
            if node.type == NodeType.SOURCE:
                # 
                Q_source = node.bc_value if node.bc_value is not None else 0.0
                n_out = len(node.outflow_edges)
                for edge in node.outflow_edges:
                    edge.set_upstream_bc(Q=Q_source / n_out)
            
            elif node.type == NodeType.SINK:
                # 
                h_sink = node.bc_value if node.bc_value is not None else 1.0
                for edge in node.inflow_edges:
                    edge.set_downstream_bc(h=h_sink)
            
            elif node.type == NodeType.JUNCTION:
                # 
                self._handle_junction_conservative(node)
            
            elif node.type == NodeType.BIFURCATION:
                # 
                self._handle_bifurcation_conservative(node)
            
            elif node.type == NodeType.INTERNAL:
                # 
                self._handle_internal(node)
    
    def _handle_junction_conservative(self, node: Node):
        """
        
        
        
        1.  = 
        2.  = 
        3. 
        """
        if len(node.inflow_edges) == 0 or len(node.outflow_edges) == 0:
            return
        
        # 1. 
        h_list = []
        Q_list = []
        
        for in_edge in node.inflow_edges:
            h, Q = in_edge.get_downstream_state()
            if not np.isnan(h) and h > 0.01:
                h_list.append(h)
            if not np.isnan(Q):
                Q_list.append(Q)
        
        if len(h_list) == 0:
            h_list = [0.5]
        
        h_node_new = np.mean(h_list)
        h_node_new = max(h_node_new, 0.1)  # 
        
        # 2. 
        h_node_old = self.prev_node_h.get(node.id, h_node_new)
        h_node = self.relaxation * h_node_new + (1 - self.relaxation) * h_node_old
        self.prev_node_h[node.id] = h_node
        
        # 3. 
        for out_edge in node.outflow_edges:
            out_edge.set_upstream_bc(h=h_node)
        
        # 4. 
        for in_edge in node.inflow_edges:
            in_edge.set_downstream_bc(h=h_node)
    
    def _handle_bifurcation_conservative(self, node: Node):
        """
        
        
        
        1.  = 
        2. Q = 1/(n*sqrt(L))
        3.  sum(Q_out) = Q_in
        """
        if len(node.inflow_edges) == 0 or len(node.outflow_edges) == 0:
            return
        
        in_edge = node.inflow_edges[0]
        h_in, Q_in = in_edge.get_downstream_state()
        
        if np.isnan(h_in) or h_in < 0.01:
            h_in = 0.5
        if np.isnan(Q_in):
            Q_in = 0.0
        
        h_node_new = max(h_in, 0.1)
        
        # 
        h_node_old = self.prev_node_h.get(node.id, h_node_new)
        h_node = self.relaxation * h_node_new + (1 - self.relaxation) * h_node_old
        self.prev_node_h[node.id] = h_node
        
        # 
        weights = []
        for out_edge in node.outflow_edges:
            # 
            #  ∝ 1 / (n * sqrt(L))
            weight = 1.0 / (out_edge.solver.n * np.sqrt(out_edge.solver.L))
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight < 1e-10:
            # 0
            weights = [1.0 / len(node.outflow_edges)] * len(node.outflow_edges)
        else:
            weights = [w / total_weight for w in weights]
        
        # 
        for i, out_edge in enumerate(node.outflow_edges):
            out_edge.set_upstream_bc(h=h_node)
        
        # 
        in_edge.set_downstream_bc(h=h_node)
    
    def _handle_internal(self, node: Node):
        """"""
        if len(node.inflow_edges) > 0 and len(node.outflow_edges) > 0:
            in_edge = node.inflow_edges[0]
            out_edge = node.outflow_edges[0]
            
            h_in, Q_in = in_edge.get_downstream_state()
            h_in = max(h_in, 0.1)
            
            # 
            h_node_old = self.prev_node_h.get(node.id, h_in)
            h_node = self.relaxation * h_in + (1 - self.relaxation) * h_node_old
            self.prev_node_h[node.id] = h_node
            
            out_edge.set_upstream_bc(h=h_node)
            in_edge.set_downstream_bc(h=h_node)
    
    def _update_node_states(self):
        """"""
        for node_id, node in self.nodes.items():
            h_list = []
            Q_list = []
            
            for edge in node.inflow_edges:
                h, Q = edge.get_downstream_state()
                h_list.append(h)
                Q_list.append(Q)
            
            for edge in node.outflow_edges:
                h, Q = edge.get_upstream_state()
                h_list.append(h)
                Q_list.append(-Q)
            
            if len(h_list) > 0:
                node.h = np.mean([h for h in h_list if not np.isnan(h)])
                node.Q = np.sum([Q for Q in Q_list if not np.isnan(Q)])
    
    def _compute_total_mass(self) -> float:
        """"""
        total_mass = 0.0
        for edge in self.edges.values():
            mass = np.sum(edge.solver.h * edge.solver.B * edge.solver.dx)
            total_mass += mass
        return total_mass
    
    def get_mass_conservation_error(self) -> float:
        """%"""
        current_mass = self._compute_total_mass()
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_node_mass_balance(self, node_id: str) -> Dict:
        """"""
        node = self.nodes[node_id]
        
        Q_in_total = 0.0
        Q_out_total = 0.0
        
        for edge in node.inflow_edges:
            _, Q = edge.get_downstream_state()
            if not np.isnan(Q):
                Q_in_total += Q
        
        for edge in node.outflow_edges:
            _, Q = edge.get_upstream_state()
            if not np.isnan(Q):
                Q_out_total += Q
        
        balance_error = abs(Q_in_total - Q_out_total)
        relative_error = balance_error / (abs(Q_in_total) + 1e-10) * 100
        
        return {
            'Q_in': Q_in_total,
            'Q_out': Q_out_total,
            'balance_error': balance_error,
            'relative_error': relative_error
        }
    
    def get_network_state(self) -> Dict:
        """"""
        node_states = {}
        for node_id, node in self.nodes.items():
            balance = self.get_node_mass_balance(node_id)
            node_states[node_id] = {
                'h': node.h,
                'Q': node.Q,
                'type': node.type.value,
                'Q_balance': balance
            }
        
        edge_states = {}
        for edge_id, edge in self.edges.items():
            state = edge.solver.get_state()
            edge_states[edge_id] = {
                'x': state['x'],
                'h': state['h'],
                'Q': state['Q'],
                'mass_error': state['mass_error']
            }
        
        return {
            'time': self.t,
            'step': self.step_count,
            'network_mass_error': self.get_mass_conservation_error(),
            'nodes': node_states,
            'edges': edge_states
        }


if __name__ == '__main__':
    print("=" * 80)
    print("Godunov-FVM V2 - ")
    print("=" * 80)
    print("\n")
    print("   ")
    print("   ")
    print("   ")
    print("   ")
    print("\n...")
