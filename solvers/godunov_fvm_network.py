#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - Phase 1


1.  
2.  /
3.  source, sink, junction, bifurcation
4.  
5.  


- Godunov-FVM Order 1
- 
- 
- 

: HydroClaude Team
: 2025-10-27
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


class NodeType(Enum):
    """"""
    SOURCE = "source"          # 
    SINK = "sink"              # 
    JUNCTION = "junction"      # 
    BIFURCATION = "bifurcation"  # 
    INTERNAL = "internal"      # 


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
        """
        
        
        Args:
            node_id: ID
            node_type: 
            x, y: 
            elevation: 
            bc_value: SOURCE/SINK
        """
        self.id = node_id
        self.type = node_type
        self.x = x
        self.y = y
        self.elevation = elevation
        self.bc_value = bc_value
        
        # 
        self.inflow_edges = []   # 
        self.outflow_edges = []  # 
        
        # 
        self.h = 0.0  # 
        self.Q = 0.0  # 


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
        """
        
        
        Args:
            edge_id: ID
            from_node: 
            to_node: 
            width, length: 
            n_cells: 
            manning_n: 
            slope: 
            solver: Godunov
        """
        self.id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        
        # 
        from_node.outflow_edges.append(self)
        to_node.inflow_edges.append(self)
        
        # 
        if solver is None:
            self.solver = GodunvFVMSolver(
                width=width,
                length=length,
                n_cells=n_cells,
                manning_n=manning_n,
                slope=slope,
                cfl=0.5,
                order=1  # Phase 0Order 1
            )
        else:
            self.solver = solver
        
        self.initialized = False
    
    def initialize(self, h_init, Q_init, bc_left, bc_right):
        """"""
        self.solver.initialize(h_init, Q_init, bc_left, bc_right)
        self.initialized = True
    
    def step(self, dt: Optional[float] = None):
        """"""
        return self.solver.step(dt)
    
    def get_upstream_state(self) -> Tuple[float, float]:
        """h, Q"""
        return self.solver.h[0], self.solver.Q[0]
    
    def get_downstream_state(self) -> Tuple[float, float]:
        """h, Q"""
        return self.solver.h[-1], self.solver.Q[-1]
    
    def set_upstream_bc(self, h: Optional[float] = None, Q: Optional[float] = None):
        """"""
        if h is not None:
            self.solver.bc_left = {'type': 'h', 'value': h}
        elif Q is not None:
            self.solver.bc_left = {'type': 'Q', 'value': Q}
    
    def set_downstream_bc(self, h: Optional[float] = None, Q: Optional[float] = None):
        """"""
        if h is not None:
            self.solver.bc_right = {'type': 'h', 'value': h}
        elif Q is not None:
            self.solver.bc_right = {'type': 'Q', 'value': Q}


class GodunvFVMNetwork:
    """
    Godunov-FVM
    
    
    """
    
    def __init__(self, g: float = 9.81):
        """"""
        self.g = g
        
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        
        self.t = 0.0
        self.dt = 0.0
        self.step_count = 0
        
        self.initial_mass = 0.0
        
        print(" Godunov-FVM")
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        x: float = 0.0,
        y: float = 0.0,
        elevation: float = 0.0,
        bc_value: Optional[float] = None
    ) -> Node:
        """"""
        node = Node(node_id, node_type, x, y, elevation, bc_value)
        self.nodes[node_id] = node
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
        """"""
        from_node = self.nodes[from_node_id]
        to_node = self.nodes[to_node_id]
        
        edge = Edge(
            edge_id, from_node, to_node,
            width, length, n_cells, manning_n, slope
        )
        
        self.edges[edge_id] = edge
        return edge
    
    def initialize_network(self, h_default: float = 1.0, Q_default: float = 0.0):
        """"""
        print(f"\n:")
        print(f"  : {len(self.nodes)}")
        print(f"  : {len(self.edges)}")
        
        # 
        for edge_id, edge in self.edges.items():
            n = edge.solver.n_cells
            h_init = np.ones(n) * h_default
            Q_init = np.ones(n) * Q_default
            
            # 
            bc_left = {'type': 'h', 'value': h_default}
            bc_right = {'type': 'h', 'value': h_default}
            
            edge.initialize(h_init, Q_init, bc_left, bc_right)
        
        # 
        self.initial_mass = self._compute_total_mass()
        print(f"  : {self.initial_mass:.2f} m³")
    
    def step(self):
        """"""
        # 1. 
        self._update_boundary_conditions()
        
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
    
    def _update_boundary_conditions(self):
        """ → - """
        for node_id, node in self.nodes.items():
            if node.type == NodeType.SOURCE:
                # 
                Q_source = node.bc_value if node.bc_value is not None else 0.0
                for edge in node.outflow_edges:
                    edge.set_upstream_bc(Q=Q_source / len(node.outflow_edges))
            
            elif node.type == NodeType.SINK:
                # 
                h_sink = node.bc_value if node.bc_value is not None else 1.0
                for edge in node.inflow_edges:
                    edge.set_downstream_bc(h=h_sink)
            
            elif node.type == NodeType.JUNCTION:
                # 
                if len(node.outflow_edges) > 0 and len(node.inflow_edges) > 0:
                    out_edge = node.outflow_edges[0]
                    
                    # 
                    h_list = [e.get_downstream_state()[0] for e in node.inflow_edges]
                    h_avg = np.mean([h for h in h_list if not np.isnan(h) and h > 0])
                    
                    #  = 
                    out_edge.set_upstream_bc(h=max(h_avg, 0.1))
                    
                    #  = 
                    for in_edge in node.inflow_edges:
                        in_edge.set_downstream_bc(h=max(h_avg, 0.1))
            
            elif node.type == NodeType.BIFURCATION:
                #  + 
                if len(node.inflow_edges) > 0 and len(node.outflow_edges) > 0:
                    in_edge = node.inflow_edges[0]
                    h_in, Q_in = in_edge.get_downstream_state()
                    
                    # 
                    in_edge.set_downstream_bc(h=max(h_in, 0.1))
                    
                    # 
                    for out_edge in node.outflow_edges:
                        out_edge.set_upstream_bc(h=max(h_in, 0.1))
            
            elif node.type == NodeType.INTERNAL:
                # 
                if len(node.inflow_edges) > 0 and len(node.outflow_edges) > 0:
                    in_edge = node.inflow_edges[0]
                    out_edge = node.outflow_edges[0]
                    
                    h_in, Q_in = in_edge.get_downstream_state()
                    
                    # 
                    out_edge.set_upstream_bc(h=max(h_in, 0.1))
                    in_edge.set_downstream_bc(h=max(h_in, 0.1))
    
    def _update_node_states(self):
        """ → """
        for node_id, node in self.nodes.items():
            # 
            h_list = []
            Q_list = []
            
            for edge in node.inflow_edges:
                h, Q = edge.get_downstream_state()
                h_list.append(h)
                Q_list.append(Q)
            
            for edge in node.outflow_edges:
                h, Q = edge.get_upstream_state()
                h_list.append(h)
                Q_list.append(-Q)  # 
            
            if len(h_list) > 0:
                node.h = np.mean(h_list)
                node.Q = np.sum(Q_list)  # 
    
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
    
    def get_network_state(self) -> Dict:
        """"""
        node_states = {}
        for node_id, node in self.nodes.items():
            node_states[node_id] = {
                'h': node.h,
                'Q': node.Q,
                'type': node.type.value
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
            't': self.t,
            'dt': self.dt,
            'step': self.step_count,
            'mass_error': self.get_mass_conservation_error(),
            'nodes': node_states,
            'edges': edge_states
        }
    
    def print_summary(self):
        """"""
        print(f"\n @ t={self.t:.2f}s ({self.step_count}):")
        print(f"  : {self.get_mass_conservation_error():.6f}%")
        
        print(f"\n  :")
        for node_id, node in self.nodes.items():
            print(f"    {node_id} ({node.type.value}): h={node.h:.3f}m, Q={node.Q:.2f}m³/s")
        
        print(f"\n  :")
        for edge_id, edge in self.edges.items():
            state = edge.solver.get_state()
            print(f"    {edge_id}: ={state['mass_error']:.4f}%")


# ==========  ==========

if __name__ == "__main__":
    print("="*80)
    print("Godunov-FVM - ")
    print("="*80)
    
    # 1: Y12
    print("\n1Y")
    print("-"*80)
    
    network = GodunvFVMNetwork()
    
    # 
    n1 = network.add_node("N1", NodeType.SOURCE, x=0, y=0, bc_value=100.0)
    n2 = network.add_node("N2", NodeType.BIFURCATION, x=500, y=0)
    n3 = network.add_node("N3", NodeType.SINK, x=1000, y=100, bc_value=2.0)
    n4 = network.add_node("N4", NodeType.SINK, x=1000, y=-100, bc_value=2.0)
    
    # 
    e1 = network.add_edge("E1", "N1", "N2", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    e2 = network.add_edge("E2", "N2", "N3", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    e3 = network.add_edge("E3", "N2", "N4", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    
    # 
    network.initialize_network(h_default=2.0, Q_default=50.0)
    
    # 
    print(f"\n500...")
    for _ in range(500):
        network.step()
        if network.step_count % 100 == 0:
            print(f"  {network.step_count}: ={network.get_mass_conservation_error():.4f}%")
    
    network.print_summary()
    
    # 
    state = network.get_network_state()
    mass_error = abs(state['mass_error'])
    
    print(f"\n:")
    print(f"  : {mass_error:.4f}% (<1%)")
    print(f"  {' ' if mass_error < 1.0 else ' '}")
    
    # 2: T21
    print("\n" + "="*80)
    print("2T")
    print("-"*80)
    
    network2 = GodunvFVMNetwork()
    
    # 
    n1 = network2.add_node("N1", NodeType.SOURCE, x=0, y=100, bc_value=50.0)
    n2 = network2.add_node("N2", NodeType.SOURCE, x=0, y=-100, bc_value=50.0)
    n3 = network2.add_node("N3", NodeType.JUNCTION, x=500, y=0)
    n4 = network2.add_node("N4", NodeType.SINK, x=1000, y=0, bc_value=2.0)
    
    # 
    e1 = network2.add_edge("E1", "N1", "N3", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    e2 = network2.add_edge("E2", "N2", "N3", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    e3 = network2.add_edge("E3", "N3", "N4", width=10.0, length=500.0, n_cells=50, manning_n=0.025, slope=0.001)
    
    # 
    network2.initialize_network(h_default=2.0, Q_default=50.0)
    
    # 
    print(f"\n500...")
    for _ in range(500):
        network2.step()
        if network2.step_count % 100 == 0:
            print(f"  {network2.step_count}: ={network2.get_mass_conservation_error():.4f}%")
    
    network2.print_summary()
    
    # 
    state2 = network2.get_network_state()
    mass_error2 = abs(state2['mass_error'])
    
    print(f"\n:")
    print(f"  : {mass_error2:.4f}% (<1%)")
    print(f"  {' ' if mass_error2 < 1.0 else ' '}")
    
    # 
    print("\n" + "="*80)
    print("[SUCCESS] ")
    print("="*80)
    
    if mass_error < 1.0 and mass_error2 < 1.0:
        print(" ")
        print(" ")
        print(" Phase 1 1")
    else:
        print("[WARN] ")
