"""
Hardy Cross Solver Module - Hardy Cross管网平差求解器

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
    Hardy Cross 管网平差求解器 - Hardy Cross Pipe Network Solver

    The Hardy Cross method is a classical iterative technique for solving
    pipe network flows. It was developed by Hardy Cross in 1936 and remains
    widely used for water distribution network analysis.

    原理 Principle:
    ---------------
    1. 初始流量分配（满足连续性方程）
       Initialize flows (satisfy continuity)

    2. 识别所有独立回路
       Identify all independent loops

    3. 对每个回路迭代修正流量
       Iteratively correct flows for each loop:

       Σh_loss = 0  (energy conservation)

       修正公式 Correction formula:
       ΔQ = -Σh / (n * Σ(h/Q))

       其中 where:
       - h = 水头损失 (head loss)
       - Q = 流量 (flow rate)
       - n = 指数 (exponent, n=2 for Darcy-Weisbach)

    4. 检查收敛
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
        初始化Hardy Cross求解器

        Args:
            network: 管网拓扑对象
            max_iter: 最大迭代次数
            tol: 收敛容差 (m³/s)
            relaxation_factor: 松弛因子 (0 < α ≤ 1)，用于提高收敛性
            verbose: 是否打印迭代信息

        Raises:
            ValueError: 如果网络无效或参数不合理
        """
        # 参数验证
        if max_iter <= 0:
            raise ValueError(f"最大迭代次数必须 > 0，当前值: {max_iter}")

        if tol <= 0:
            raise ValueError(f"收敛容差必须 > 0，当前值: {tol}")

        if not (0 < relaxation_factor <= 1.0):
            raise ValueError(f"松弛因子必须在(0, 1]范围内，当前值: {relaxation_factor}")

        # 网络验证
        is_valid, issues = network.validate()
        if not is_valid:
            raise ValueError(f"网络无效: {issues}")

        # 存储参数
        self.network = network
        self.max_iter = max_iter
        self.tol = tol
        self.alpha = relaxation_factor  # 松弛因子
        self.verbose = verbose

        # 求解状态
        self.iteration_count = 0
        self.converged = False
        self.flows: Dict[str, float] = {}  # {pipe_id: Q}
        self.heads: Dict[str, float] = {}  # {node_id: H}

        # 回路信息
        self.loops: List[List[str]] = []
        self.loop_matrix: np.ndarray = None
        self.pipe_ids: List[str] = []

    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        求解管网流量和水头分布

        Returns:
            (flows, heads) 元组
            - flows: {pipe_id: Q (m³/s)}
            - heads: {node_id: H (m)}

        Raises:
            RuntimeError: 如果迭代不收敛
        """
        if self.verbose:
            print("\n" + "="*80)
            print("Hardy Cross 管网平差求解 - Pipe Network Analysis")
            print("="*80)

        # 步骤1: 识别回路
        self._identify_loops()

        # 步骤2: 初始流量分配
        self._initialize_flows()

        # 步骤3: Hardy Cross迭代
        self._hardy_cross_iteration()

        # 步骤4: 计算节点水头
        self._calculate_heads()

        if self.verbose:
            print("="*80 + "\n")

        return self.flows, self.heads

    def _identify_loops(self):
        """识别管网中的所有独立回路"""
        if self.verbose:
            print("\n[步骤1] 识别回路")

        self.loops = self.network.find_loops()

        if self.verbose:
            print(f"  识别到 {len(self.loops)} 个独立回路")

        if len(self.loops) == 0:
            warnings.warn("网络中没有回路，Hardy Cross法可能不适用")

        # 构造回路矩阵
        self.loop_matrix, _, self.pipe_ids = self.network.loop_matrix()

    def _initialize_flows(self):
        """
        初始流量分配策略

        策略：
        1. 找到所有水源节点（Reservoir）
        2. 从水源均匀分配流量到下游
        3. 确保满足节点连续性方程
        """
        if self.verbose:
            print("\n[步骤2] 初始流量分配")

        # 初始化所有管道流量为0
        for pipe_id in self.network.pipes:
            self.flows[pipe_id] = 0.0

        # 找到所有水源节点
        reservoirs = [node for node in self.network.nodes.values()
                     if isinstance(node, Reservoir)]

        if len(reservoirs) == 0:
            warnings.warn("网络中没有水源节点(Reservoir)，初始流量全部为0")
            return

        # 计算总需水量
        total_demand = sum(node.demand for node in self.network.nodes.values()
                          if isinstance(node, Junction))

        if self.verbose:
            print(f"  水源数量: {len(reservoirs)}")
            print(f"  总需水量: {total_demand:.6f} m³/s")

        # 策略1: 简单均匀分配（从每个水源）
        # 更好的策略可以考虑管道阻力
        for reservoir in reservoirs:
            # 获取从水源流出的管道
            pipes_from_source = []
            for pipe_id, direction in self.network.get_node_pipes(reservoir.node_id):
                if direction == 'out':
                    pipes_from_source.append(pipe_id)

            if len(pipes_from_source) > 0:
                # 均匀分配流量
                Q_per_pipe = total_demand / (len(reservoirs) * len(pipes_from_source))
                for pipe_id in pipes_from_source:
                    self.flows[pipe_id] = Q_per_pipe

        if self.verbose:
            non_zero_flows = sum(1 for Q in self.flows.values() if abs(Q) > 1e-10)
            print(f"  初始化 {non_zero_flows} 根管道流量")

    def _hardy_cross_iteration(self):
        """Hardy Cross迭代主循环"""
        if self.verbose:
            print("\n[步骤3] Hardy Cross迭代")
            print(f"  最大迭代次数: {self.max_iter}")
            print(f"  收敛容差: {self.tol:.2e} m³/s")
            print(f"  松弛因子: {self.alpha:.2f}")
            print("\n  迭代进度:")

        for iteration in range(self.max_iter):
            max_correction = 0.0

            # 对每个回路计算流量修正
            for loop_idx, loop in enumerate(self.loops):
                # 计算回路水头损失
                delta_Q = self._compute_loop_correction(loop)

                # 应用修正（带松弛因子）
                delta_Q *= self.alpha

                # 应用到回路中的所有管道
                self._apply_loop_correction(loop, delta_Q)

                # 记录最大修正量
                max_correction = max(max_correction, abs(delta_Q))

            # 检查收敛
            self.iteration_count = iteration + 1

            if self.verbose and (iteration < 10 or iteration % 10 == 0 or
                                max_correction < self.tol):
                print(f"    迭代 {iteration+1:3d}: 最大修正量 = {max_correction:.8f} m³/s")

            if max_correction < self.tol:
                self.converged = True
                if self.verbose:
                    print(f"\n  ✓ 收敛成功！")
                    print(f"    迭代次数: {self.iteration_count}")
                    print(f"    最终修正量: {max_correction:.10f} m³/s")
                return

        # 未收敛
        self.converged = False
        error_msg = (f"Hardy Cross法未收敛: 达到最大迭代次数 {self.max_iter}，"
                    f"最大修正量 {max_correction:.8f} > 容差 {self.tol:.8f}")

        if self.verbose:
            print(f"\n  ✗ {error_msg}")

        raise RuntimeError(error_msg)

    def _compute_loop_correction(self, loop: List[str]) -> float:
        """
        计算回路流量修正量

        公式: ΔQ = -Σh / (n * Σ(h/Q))

        Args:
            loop: 回路节点列表

        Returns:
            流量修正量 (m³/s)
        """
        sum_h = 0.0        # Σh
        sum_h_over_Q = 0.0 # Σ(h/Q)

        # 遍历回路中的每条边
        for i in range(len(loop)):
            node1 = loop[i]
            node2 = loop[(i + 1) % len(loop)]

            # 查找连接这两个节点的管道
            pipe_id = self.network._find_pipe_between(node1, node2)

            if pipe_id is None:
                continue

            pipe = self.network.pipes[pipe_id]
            Q = self.flows[pipe_id]

            # 计算水头损失（始终为正值）
            if abs(Q) < 1e-12:
                # 流量接近0，跳过（避免除零）
                continue

            h_loss = pipe.head_loss(abs(Q))

            # 确定流向（顺时针为正，逆时针为负）
            from_node, to_node = self.network.pipe_connections[pipe_id]

            if from_node == node1 and to_node == node2:
                # 流向与回路方向一致
                direction = 1.0
            elif from_node == node2 and to_node == node1:
                # 流向与回路方向相反
                direction = -1.0
            else:
                # 理论上不应该到这里
                direction = 0.0

            # 考虑流量符号
            if Q < 0:
                direction *= -1.0

            # 累加
            sum_h += direction * h_loss
            sum_h_over_Q += h_loss / abs(Q)

        # 计算修正量
        # ΔQ = -Σh / (n * Σ(h/Q))
        # 对于Darcy-Weisbach公式，n=2
        n = 2.0

        if sum_h_over_Q > 1e-12:
            delta_Q = -sum_h / (n * sum_h_over_Q)
        else:
            delta_Q = 0.0

        return delta_Q

    def _apply_loop_correction(self, loop: List[str], delta_Q: float):
        """
        将流量修正应用到回路中的所有管道

        Args:
            loop: 回路节点列表
            delta_Q: 流量修正量
        """
        for i in range(len(loop)):
            node1 = loop[i]
            node2 = loop[(i + 1) % len(loop)]

            pipe_id = self.network._find_pipe_between(node1, node2)

            if pipe_id is None:
                continue

            # 确定修正方向
            from_node, to_node = self.network.pipe_connections[pipe_id]

            if from_node == node1 and to_node == node2:
                # 管道方向与回路方向一致
                self.flows[pipe_id] += delta_Q
            elif from_node == node2 and to_node == node1:
                # 管道方向与回路方向相反
                self.flows[pipe_id] -= delta_Q

    def _calculate_heads(self):
        """
        根据流量分布计算节点水头

        策略：
        1. 固定水头边界条件（Reservoir）
        2. 从已知水头节点向下游传播
        3. 使用能量方程: H_j = H_i - h_loss
        """
        if self.verbose:
            print("\n[步骤4] 计算节点水头")

        # 初始化所有节点水头为None
        self.heads = {}

        # 设置水源节点的已知水头
        for node_id, node in self.network.nodes.items():
            if isinstance(node, Reservoir):
                self.heads[node_id] = node.available_head()

        # 使用BFS从已知水头节点传播
        from collections import deque

        visited = set(self.heads.keys())
        queue = deque(visited)

        while queue:
            current_node = queue.popleft()
            H_current = self.heads[current_node]

            # 遍历相邻节点
            for neighbor in self.network.adjacency[current_node]:
                if neighbor in visited:
                    continue

                # 查找连接管道
                pipe_id = self.network._find_pipe_between(current_node, neighbor)

                if pipe_id is None:
                    continue

                pipe = self.network.pipes[pipe_id]
                Q = self.flows[pipe_id]

                # 计算水头损失
                h_loss = pipe.head_loss(abs(Q))

                # 确定水头传播方向
                from_node, to_node = self.network.pipe_connections[pipe_id]

                if from_node == current_node and to_node == neighbor:
                    # 流向下游，水头降低
                    H_neighbor = H_current - h_loss
                elif from_node == neighbor and to_node == current_node:
                    # 流向上游，水头升高
                    H_neighbor = H_current + h_loss
                else:
                    continue

                # 更新邻居节点水头
                self.heads[neighbor] = H_neighbor
                visited.add(neighbor)
                queue.append(neighbor)

        # 检查是否所有节点都有水头值
        missing_heads = set(self.network.nodes.keys()) - visited

        if missing_heads:
            warnings.warn(
                f"无法计算以下节点的水头: {missing_heads}，"
                "可能是网络不连通或缺少水源"
            )

        if self.verbose:
            print(f"  计算了 {len(self.heads)}/{len(self.network.nodes)} 个节点的水头")

    def get_convergence_history(self) -> Dict[str, any]:
        """
        获取收敛历史信息

        Returns:
            收敛信息字典
        """
        return {
            'converged': self.converged,
            'iterations': self.iteration_count,
            'tolerance': self.tol,
            'max_iterations': self.max_iter
        }

    def get_results_summary(self) -> Dict[str, any]:
        """
        获取求解结果摘要

        Returns:
            结果摘要字典
        """
        if not self.converged:
            return {'status': 'not_converged'}

        # 流量统计
        flow_values = list(self.flows.values())
        total_flow = sum(abs(Q) for Q in flow_values)

        # 水头统计
        head_values = list(self.heads.values())

        # 节点压力统计
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
        status = "已收敛" if self.converged else "未收敛"
        return (f"HardyCrossSolver(iterations={self.iteration_count}, "
                f"status='{status}', loops={len(self.loops)})")
