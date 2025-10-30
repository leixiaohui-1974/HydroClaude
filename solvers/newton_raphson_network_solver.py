"""
Newton-Raphson Network Solver - Newton-Raphson管网求解器

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
    Newton-Raphson全局法管网求解器
    
    同时求解流量Q和水头H，使用Newton-Raphson迭代:
    X_{k+1} = X_k - J^{-1} * F(X_k)
    
    方程组 Equations:
    1. 能量方程: H_i - H_j - h_loss(Q_ij) = 0
    2. 连续性方程: ΣQ_in - ΣQ_out - demand = 0
    """

    def __init__(self, network: NetworkTopology, max_iter: int = 50, 
                 tol: float = 1e-6, verbose: bool = True):
        self.network = network
        self.max_iter = max_iter
        self.tol = tol
        self.verbose = verbose
        
        self.iteration_count = 0
        self.converged = False
        self.flows: Dict[str, float] = {}
        self.heads: Dict[str, float] = {}
        
        # 索引映射
        self.pipe_ids = sorted(network.pipes.keys())
        self.node_ids = sorted(network.nodes.keys())
        self.pipe_idx = {pid: i for i, pid in enumerate(self.pipe_ids)}
        self.node_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        
    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """求解管网"""
        if self.verbose:
            print("\n" + "="*80)
            print("Newton-Raphson 管网求解")
            print("="*80)
        
        # 初始化
        Q, H = self._initialize()
        
        # Newton-Raphson迭代
        for iteration in range(self.max_iter):
            # 构造方程和Jacobian
            F = self._build_equations(Q, H)
            J = self._build_jacobian(Q, H)
            
            # 求解: J * dX = -F
            dX = spsolve(J, -F)
            
            # 更新
            n_pipes = len(self.pipe_ids)
            Q += dX[:n_pipes]
            H += dX[n_pipes:]
            
            # 检查收敛
            max_residual = np.max(np.abs(F))
            self.iteration_count = iteration + 1
            
            if self.verbose and (iteration < 5 or iteration % 5 == 0):
                print(f"  迭代 {iteration+1}: 最大残差 = {max_residual:.8e}")
            
            if max_residual < self.tol:
                self.converged = True
                if self.verbose:
                    print(f"\n  ✓ 收敛! 迭代次数: {self.iteration_count}")
                break
        
        # 保存结果
        for i, pid in enumerate(self.pipe_ids):
            self.flows[pid] = Q[i]
        for i, nid in enumerate(self.node_ids):
            self.heads[nid] = H[i]
            
        if self.verbose:
            print("="*80 + "\n")
        
        return self.flows, self.heads
    
    def _initialize(self) -> Tuple[np.ndarray, np.ndarray]:
        """初始化流量和水头"""
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)
        
        Q = np.zeros(n_pipes)
        H = np.zeros(n_nodes)
        
        # 初始化水头（水源节点）
        for i, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            if isinstance(node, Reservoir):
                H[i] = node.available_head()
            else:
                H[i] = node.elevation + 20.0  # 默认20m压力
        
        # 初始化流量（简单估计）
        total_demand = sum(n.demand for n in self.network.nodes.values() 
                          if isinstance(n, Junction))
        for i in range(n_pipes):
            Q[i] = total_demand / n_pipes if n_pipes > 0 else 0.0
        
        return Q, H
    
    def _build_equations(self, Q: np.ndarray, H: np.ndarray) -> np.ndarray:
        """构造方程组残差"""
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)
        
        F = np.zeros(n_pipes + n_nodes)
        
        # 能量方程 (每根管道)
        for i, pid in enumerate(self.pipe_ids):
            pipe = self.network.pipes[pid]
            from_node, to_node = self.network.pipe_connections[pid]
            
            i_from = self.node_idx[from_node]
            i_to = self.node_idx[to_node]
            
            h_loss = pipe.head_loss(abs(Q[i]))
            if Q[i] < 0:
                h_loss = -h_loss
            
            F[i] = H[i_from] - H[i_to] - h_loss
        
        # 连续性方程 (每个节点)
        for j, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            
            if isinstance(node, Reservoir):
                # 水源节点：固定水头
                F[n_pipes + j] = H[j] - node.available_head()
            else:
                # 其他节点：流量守恒
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
        """构造Jacobian矩阵"""
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)
        n_total = n_pipes + n_nodes
        
        J = lil_matrix((n_total, n_total))
        
        # 能量方程的导数
        for i, pid in enumerate(self.pipe_ids):
            pipe = self.network.pipes[pid]
            from_node, to_node = self.network.pipe_connections[pid]
            
            i_from = self.node_idx[from_node]
            i_to = self.node_idx[to_node]
            
            # ∂F/∂Q: 数值导数
            dQ = max(abs(Q[i]) * 1e-6, 1e-9)
            h1 = pipe.head_loss(abs(Q[i]))
            h2 = pipe.head_loss(abs(Q[i] + dQ))
            dh_dQ = (h2 - h1) / dQ
            
            J[i, i] = -dh_dQ
            
            # ∂F/∂H
            J[i, n_pipes + i_from] = 1.0
            J[i, n_pipes + i_to] = -1.0
        
        # 连续性方程的导数
        for j, nid in enumerate(self.node_ids):
            node = self.network.nodes[nid]
            
            if isinstance(node, Reservoir):
                # 水源节点
                J[n_pipes + j, n_pipes + j] = 1.0
            else:
                # 其他节点
                for pipe_id, direction in self.network.get_node_pipes(nid):
                    i = self.pipe_idx[pipe_id]
                    if direction == 'in':
                        J[n_pipes + j, i] = 1.0
                    else:
                        J[n_pipes + j, i] = -1.0
        
        return J.tocsr()


def compare_solvers(network: NetworkTopology):
    """比较Hardy Cross和Newton-Raphson求解器"""
    from solvers.hardy_cross_solver import HardyCrossSolver
    
    print("\n" + "="*80)
    print("求解器对比 - Solver Comparison")
    print("="*80)
    
    # Hardy Cross
    print("\n[1] Hardy Cross 求解器")
    hc_solver = HardyCrossSolver(network, verbose=False)
    hc_flows, hc_heads = hc_solver.solve()
    print(f"  迭代次数: {hc_solver.iteration_count}")
    print(f"  收敛状态: {'成功' if hc_solver.converged else '失败'}")
    
    # Newton-Raphson
    print("\n[2] Newton-Raphson 求解器")
    nr_solver = NewtonRaphsonNetworkSolver(network, verbose=False)
    nr_flows, nr_heads = nr_solver.solve()
    print(f"  迭代次数: {nr_solver.iteration_count}")
    print(f"  收敛状态: {'成功' if nr_solver.converged else '失败'}")
    
    # 对比结果
    print("\n[3] 结果对比")
    flow_diff = np.mean([abs(hc_flows[p] - nr_flows[p]) for p in hc_flows])
    print(f"  流量平均差异: {flow_diff:.8f} m³/s")
    
    print("="*80 + "\n")
    
    return hc_solver, nr_solver
