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
                 tol: float = 1e-6, verbose: bool = True,
                 use_hardy_cross_init: bool = False,
                 damping_factor: float = 0.5,
                 adaptive_damping: bool = True):
        """
        初始化Newton-Raphson求解器

        Args:
            network: 管网拓扑对象
            max_iter: 最大迭代次数
            tol: 收敛容差
            verbose: 是否打印详细信息
            use_hardy_cross_init: 是否使用Hardy Cross结果作为初始猜测
                                 (可显著提高收敛性，特别是对复杂网络)
            damping_factor: 阻尼因子 (0 < α ≤ 1)，用于稳定迭代
                           X_{k+1} = X_k - α * dX
            adaptive_damping: 是否使用自适应阻尼（根据残差变化自动调整）
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

        # 索引映射
        self.pipe_ids = sorted(network.pipes.keys())
        self.node_ids = sorted(network.nodes.keys())
        self.pipe_idx = {pid: i for i, pid in enumerate(self.pipe_ids)}
        self.node_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        
    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """求解管网"""
        if self.verbose:
            print("\n" + "="*80)
            print("Newton-Raphson 管网求解 (带阻尼)")
            print("="*80)
            if self.adaptive_damping:
                print(f"  阻尼策略: 自适应 (初始α={self.damping_factor})")
            else:
                print(f"  阻尼因子: α={self.damping_factor}")

        # 初始化
        Q, H = self._initialize()

        # Newton-Raphson迭代
        prev_residual = float('inf')
        alpha = self.damping_factor  # 当前阻尼因子

        for iteration in range(self.max_iter):
            # 构造方程和Jacobian
            F = self._build_equations(Q, H)
            J = self._build_jacobian(Q, H)

            # 求解: J * dX = -F
            dX = spsolve(J, -F)

            # 应用阻尼更新
            n_pipes = len(self.pipe_ids)
            Q += alpha * dX[:n_pipes]
            H += alpha * dX[n_pipes:]

            # 检查收敛
            max_residual = np.max(np.abs(F))
            self.iteration_count = iteration + 1

            # 自适应阻尼调整
            if self.adaptive_damping and iteration > 0:
                if max_residual > prev_residual:
                    # 残差增大，减小阻尼因子
                    alpha *= 0.5
                    alpha = max(alpha, 0.01)  # 最小阻尼因子
                elif max_residual < 0.5 * prev_residual:
                    # 残差快速下降，可以增大阻尼因子
                    alpha = min(alpha * 1.2, 1.0)

            if self.verbose and (iteration < 5 or iteration % 5 == 0):
                if self.adaptive_damping:
                    print(f"  迭代 {iteration+1}: 残差={max_residual:.8e}, α={alpha:.3f}")
                else:
                    print(f"  迭代 {iteration+1}: 最大残差 = {max_residual:.8e}")

            if max_residual < self.tol:
                self.converged = True
                if self.verbose:
                    print(f"\n  ✓ 收敛! 迭代次数: {self.iteration_count}")
                    if self.adaptive_damping:
                        print(f"  最终阻尼因子: α={alpha:.3f}")
                break

            prev_residual = max_residual

        # 保存结果
        for i, pid in enumerate(self.pipe_ids):
            self.flows[pid] = Q[i]
        for i, nid in enumerate(self.node_ids):
            self.heads[nid] = H[i]

        if self.verbose:
            print("="*80 + "\n")

        return self.flows, self.heads
    
    def _initialize(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        初始化流量和水头

        策略 Strategy:
        1. 如果use_hardy_cross_init=True: 使用Hardy Cross结果作为初始猜测
           If use_hardy_cross_init=True: Use Hardy Cross solution as initial guess
        2. 否则使用简单估计
           Otherwise use simple estimation

        Returns:
            Q: 初始流量数组 (Initial flow array)
            H: 初始水头数组 (Initial head array)
        """
        n_pipes = len(self.pipe_ids)
        n_nodes = len(self.node_ids)

        Q = np.zeros(n_pipes)
        H = np.zeros(n_nodes)

        if self.use_hardy_cross_init:
            # 策略1: 使用Hardy Cross求解器获得初始值
            try:
                from solvers.hardy_cross_solver import HardyCrossSolver

                if self.verbose:
                    print("  使用Hardy Cross结果初始化...")

                hc_solver = HardyCrossSolver(self.network, verbose=False,
                                            max_iter=100, tol=1e-6)
                hc_flows, hc_heads = hc_solver.solve()

                if hc_solver.converged:
                    # 使用HC结果
                    for i, pid in enumerate(self.pipe_ids):
                        Q[i] = hc_flows.get(pid, 0.0)
                    for i, nid in enumerate(self.node_ids):
                        H[i] = hc_heads.get(nid, self.network.nodes[nid].elevation + 20.0)

                    if self.verbose:
                        print(f"  ✓ Hardy Cross收敛 ({hc_solver.iteration_count}次迭代)")

                    return Q, H
                else:
                    if self.verbose:
                        print("  ⚠ Hardy Cross未收敛，使用简单初始化")
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠ Hardy Cross初始化失败: {e}")
                    print("  使用简单初始化")

        # 策略2: 简单初始化
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
