"""
Newton-Raphson Network Solver - Newton-Raphson

Global Newton-Raphson method for pipe network analysis.
Solves for flows Q and heads H simultaneously.

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Dict, List, Tuple
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

from network.network_topology import NetworkTopology
from network.network_node import Reservoir, Junction


class NewtonRaphsonNetworkSolver:
    """
    Newton-Raphson
    
    QHNewton-Raphson:
    X_{k+1} = X_k - J^{-1} * F(X_k)
    
     Equations:
    1. : H_i - H_j - h_loss(Q_ij) = 0
    2. : ΣQ_in - ΣQ_out - demand = 0
    """

    def __init__(self, network: NetworkTopology, max_iter: int = 50,
                 tol: float = 1e-6, verbose: bool = True,
                 use_hardy_cross_init: bool = False,
                 damping_factor: float = 0.5,
                 adaptive_damping: bool = True):
        """
        Newton-Raphson

        Args:
            network: 
            max_iter: 
            tol: 
            verbose: 
            use_hardy_cross_init: Hardy Cross
                                 ()
            damping_factor:  (0 < α ≤ 1)
                           X_{k+1} = X_k - α * dX
            adaptive_damping: 
        """
        self.network = network
        self.max_iter = max_iter
        self.tol = tol
        self.verbose = verbose
        self.use_hardy_cross_init = use_hardy_cross_init
        self.damping_factor = damping_factor
        self.adaptive_damping = adaptive_damping

        self.iteration_count = 0
        self.converged = False
        self.flows: Dict[str, float] = {}
        self.heads: Dict[str, float] = {}

        # 
        self.pipe_ids = sorted(network.pipes.keys())
        self.node_ids = sorted(network.nodes.keys())
        self.pipe_idx = {pid: i for i, pid in enumerate(self.pipe_ids)}
        self.node_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        
    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """"""
        if self.verbose:
            print("\n" + "="*80)
            print("Newton-Raphson  ()")
            print("="*80)
            if self.adaptive_damping:
                print(f"  :  (α={self.damping_factor})")
            else:
                print(f"  : α={self.damping_factor}")

        # 
        Q, H = self._initialize()

        # Newton-Raphson
        prev_residual = float('inf')
        alpha = self.damping_factor  # 

        for iteration in range(self.max_iter):
            # Jacobian
            F = self._build_equations(Q, H)
            J = self._build_jacobian(Q, H)

            # : J * dX = -F
            dX = spsolve(J, -F)

            # 
            n_pipes = len(self.pipe_ids)
            Q += alpha * dX[:n_pipes]
            H += alpha * dX[n_pipes:]

            # 
            max_residual = np.max(np.abs(F))
            self.iteration_count = iteration + 1

            # 
            if self.adaptive_damping and iteration > 0:
                if max_residual > prev_residual:
                    # 
                    alpha *= 0.5
                    alpha = max(alpha, 0.01)  # 
                elif max_residual < 0.5 * prev_residual:
                    # 
                    alpha = min(alpha * 1.2, 1.0)

            if self.verbose and (iteration < 5 or iteration % 5 == 0):
                if self.adaptive_damping:
                    print(f"   {iteration+1}: ={max_residual:.8e}, α={alpha:.3f}")
                else:
                    print(f"   {iteration+1}:  = {max_residual:.8e}")

            if max_residual < self.tol:
                self.converged = True
                if self.verbose:
                    print(f"\n  [OK] ! : {self.iteration_count}")
                    if self.adaptive_damping:
                        print(f"  : α={alpha:.3f}")
                break

            prev_residual = max_residual

        # 
        for i, pid in enumerate(self.pipe_ids):
            self.flows[pid] = Q[i]
        for i, nid in enumerate(self.node_ids):
            self.heads[nid] = H[i]

        if self.verbose:
            print("="*80 + "\n")

        return self.flows, self.heads
    
    def _initialize(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        

         Strategy:
        1. use_hardy_cross_init=True: Hardy Cross
           If use_hardy_cross_init=True: Use Hardy Cross solution as initial guess
        2. 
           Otherwise use simple estimation

        Returns:
            Q:  (Initial flow array)
            H:  (Initial head array)
        """
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)

        Q = np.zeros(n_pipes)
        H = np.zeros(n_nodes)

        if self.use_hardy_cross_init:
            # 1: Hardy Cross
            try:
                from solvers.hardy_cross_solver import HardyCrossSolver

                if self.verbose:
                    print("  Hardy Cross...")

                hc_solver = HardyCrossSolver(self.network, verbose=False,
                                            max_iter=100, tol=1e-6)
                hc_flows, hc_heads = hc_solver.solve()

                if hc_solver.converged:
                    # HC
                    for i, pid in enumerate(self.pipe_ids):
                        Q[i] = hc_flows.get(pid, 0.0)
                    for i, nid in enumerate(self.node_ids):
                        H[i] = hc_heads.get(nid, self.network.nodes[nid].elevation + 20.0)

                    if self.verbose:
                        print(f"  [OK] Hardy Cross ({hc_solver.iteration_count})")

                    return Q, H
                else:
                    if self.verbose:
                        print("  [WARN] Hardy Cross")
            except Exception as e:
                if self.verbose:
                    print(f"  [WARN] Hardy Cross: {e}")
                    print("  ")

        # 2: 
        # 
        for i, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            if isinstance(node, Reservoir):
                H[i] = node.available_head()
            else:
                H[i] = node.elevation + 20.0  # 20m

        # 
        total_demand = sum(n.demand for n in self.network.nodes.values()
                          if isinstance(n, Junction))
        for i in range(n_pipes):
            Q[i] = total_demand / n_pipes if n_pipes > 0 else 0.0

        return Q, H
    
    def _build_equations(self, Q: np.ndarray, H: np.ndarray) -> np.ndarray:
        """"""
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)
        
        F = np.zeros(n_pipes + n_nodes)
        
        #  ()
        for i, pid in enumerate(self.pipe_ids):
            pipe = self.network.pipes[pid]
            from_node, to_node = self.network.pipe_connections[pid]
            
            i_from = self.node_idx[from_node]
            i_to = self.node_idx[to_node]
            
            h_loss = pipe.head_loss(abs(Q[i]))
            if Q[i] < 0:
                h_loss = -h_loss
            
            F[i] = H[i_from] - H[i_to] - h_loss
        
        #  ()
        for j, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            
            if isinstance(node, Reservoir):
                # 
                F[n_pipes + j] = H[j] - node.available_head()
            else:
                # 
                inflow = 0.0
                outflow = 0.0
                
                for pipe_id, direction in self.network.get_node_pipes(nid):
                    i = self.pipe_idx[pipe_id]
                    if direction == 'in':
                        inflow += Q[i]
                    else:
                        outflow += Q[i]
                
                demand = node.demand if isinstance(node, Junction) else 0.0
                F[n_pipes + j] = inflow - outflow - demand
        
        return F
    
    def _build_jacobian(self, Q: np.ndarray, H: np.ndarray) -> lil_matrix:
        """Jacobian"""
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)
        n_total = n_pipes + n_nodes
        
        J = lil_matrix((n_total, n_total))
        
        # 
        for i, pid in enumerate(self.pipe_ids):
            pipe = self.network.pipes[pid]
            from_node, to_node = self.network.pipe_connections[pid]
            
            i_from = self.node_idx[from_node]
            i_to = self.node_idx[to_node]
            
            # ∂F/∂Q: 
            dQ = max(abs(Q[i]) * 1e-6, 1e-9)
            h1 = pipe.head_loss(abs(Q[i]))
            h2 = pipe.head_loss(abs(Q[i] + dQ))
            dh_dQ = (h2 - h1) / dQ
            
            J[i, i] = -dh_dQ
            
            # ∂F/∂H
            J[i, n_pipes + i_from] = 1.0
            J[i, n_pipes + i_to] = -1.0
        
        # 
        for j, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            
            if isinstance(node, Reservoir):
                # 
                J[n_pipes + j, n_pipes + j] = 1.0
            else:
                # 
                for pipe_id, direction in self.network.get_node_pipes(nid):
                    i = self.pipe_idx[pipe_id]
                    if direction == 'in':
                        J[n_pipes + j, i] = 1.0
                    else:
                        J[n_pipes + j, i] = -1.0
        
        return J.tocsr()


def compare_solvers(network: NetworkTopology):
    """Hardy CrossNewton-Raphson"""
    from solvers.hardy_cross_solver import HardyCrossSolver
    
    print("\n" + "="*80)
    print(" - Solver Comparison")
    print("="*80)
    
    # Hardy Cross
    print("\n[1] Hardy Cross ")
    hc_solver = HardyCrossSolver(network, verbose=False)
    hc_flows, hc_heads = hc_solver.solve()
    print(f"  : {hc_solver.iteration_count}")
    print(f"  : {'' if hc_solver.converged else ''}")
    
    # Newton-Raphson
    print("\n[2] Newton-Raphson ")
    nr_solver = NewtonRaphsonNetworkSolver(network, verbose=False)
    nr_flows, nr_heads = nr_solver.solve()
    print(f"  : {nr_solver.iteration_count}")
    print(f"  : {'' if nr_solver.converged else ''}")
    
    # 
    print("\n[3] ")
    flow_diff = np.mean([abs(hc_flows[p] - nr_flows[p]) for p in hc_flows])
    print(f"  : {flow_diff:.8f} m³/s")
    
    print("="*80 + "\n")
    
    return hc_solver, nr_solver
