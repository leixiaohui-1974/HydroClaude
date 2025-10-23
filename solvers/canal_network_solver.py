#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复杂渠系网络求解器

支持：
- 多渠道网络
- 节点汇合/分流
- 复杂边界条件
- 结构物控制

基于静水重构方法

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import HydraulicStructure


class CanalSegment:
    """渠道段类"""

    def __init__(self, segment_id: str, solver: HydrostaticCanalSolver,
                 upstream_node: str, downstream_node: str):
        """
        Args:
            segment_id: 渠段ID
            solver: 单渠段求解器
            upstream_node: 上游节点ID
            downstream_node: 下游节点ID
        """
        self.id = segment_id
        self.solver = solver
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node

    def __repr__(self):
        return f"CanalSegment(id={self.id}, {self.upstream_node}→{self.downstream_node})"


class NetworkNode:
    """网络节点类

    节点类型：
    - source: 源节点（入流）
    - sink: 汇节点（出流）
    - junction: 汇合点（多入一出）
    - bifurcation: 分流点（一入多出）
    - internal: 内部节点（一入一出）
    """

    def __init__(self, node_id: str, node_type: str,
                 boundary_condition: Optional[Dict] = None):
        """
        Args:
            node_id: 节点ID
            node_type: 节点类型
            boundary_condition: 边界条件字典
        """
        self.id = node_id
        self.type = node_type
        self.boundary_condition = boundary_condition or {}

        # 连接的渠段
        self.inlet_segments: List[CanalSegment] = []
        self.outlet_segments: List[CanalSegment] = []

        # 节点状态
        self.h = 0.0  # 水深
        self.Q_in = 0.0  # 入流
        self.Q_out = 0.0  # 出流

    def add_inlet_segment(self, segment: CanalSegment):
        """添加入流渠段"""
        self.inlet_segments.append(segment)

    def add_outlet_segment(self, segment: CanalSegment):
        """添加出流渠段"""
        self.outlet_segments.append(segment)

    def compute_mass_balance(self) -> float:
        """
        计算质量平衡残差

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
    """渠系网络求解器"""

    def __init__(self):
        """初始化网络求解器"""
        self.segments: Dict[str, CanalSegment] = {}
        self.nodes: Dict[str, NetworkNode] = {}
        self.g = 9.81

    def add_node(self, node_id: str, node_type: str,
                boundary_condition: Optional[Dict] = None):
        """
        添加节点

        Args:
            node_id: 节点ID
            node_type: 节点类型 ('source', 'sink', 'junction', 'bifurcation', 'internal')
            boundary_condition: 边界条件
        """
        node = NetworkNode(node_id, node_type, boundary_condition)
        self.nodes[node_id] = node

    def add_canal_segment(self, segment_id: str, upstream_node: str,
                         downstream_node: str, length: float, nx: int,
                         B: float, S0: float, n: float,
                         internal_structures: Optional[List] = None):
        """
        添加渠段

        Args:
            segment_id: 渠段ID
            upstream_node: 上游节点ID
            downstream_node: 下游节点ID
            length: 渠段长度 (m)
            nx: 网格点数
            B: 渠宽 (m)
            S0: 底坡
            n: 糙率
            internal_structures: 内部结构列表
        """
        # 检查节点存在
        if upstream_node not in self.nodes:
            raise ValueError(f"Upstream node {upstream_node} not found")
        if downstream_node not in self.nodes:
            raise ValueError(f"Downstream node {downstream_node} not found")

        # 创建求解器
        solver = HydrostaticCanalSolver(
            length=length, nx=nx, B=B, S0=S0, n=n,
            internal_structures=internal_structures
        )

        # 创建渠段
        segment = CanalSegment(segment_id, solver, upstream_node, downstream_node)
        self.segments[segment_id] = segment

        # 连接到节点
        self.nodes[upstream_node].add_outlet_segment(segment)
        self.nodes[downstream_node].add_inlet_segment(segment)

    def initialize_network(self, h_initial: float = 1.0, Q_initial: float = 5.0):
        """
        初始化整个网络

        Args:
            h_initial: 初始水深 (m)
            Q_initial: 初始流量 (m³/s)
        """
        for segment in self.segments.values():
            solver = segment.solver
            solver.h = np.ones(solver.nx) * h_initial
            solver.hu = np.ones(solver.nx) * Q_initial / solver.B

        print(f"网络初始化完成：")
        print(f"  节点数: {len(self.nodes)}")
        print(f"  渠段数: {len(self.segments)}")

    def _distribute_flow_at_bifurcation(self, node: NetworkNode, Q_in: float):
        """
        在分流节点分配流量

        使用等比能原理：各分支按断面能力分配

        Args:
            node: 分流节点
            Q_in: 总入流

        Returns:
            Q_分支字典
        """
        if len(node.outlet_segments) == 0:
            return {}

        # 按渠道宽度比例分配流量
        B_total = sum(seg.solver.B for seg in node.outlet_segments)

        Q_distribution = {}
        for segment in node.outlet_segments:
            Q_branch = Q_in * (segment.solver.B / B_total)
            Q_distribution[segment.id] = Q_branch

        return Q_distribution

    def solve_network_steady(self, max_iterations: int = 100,
                            tolerance: float = 0.01, verbose: bool = True):
        """
        求解网络稳态

        使用迭代方法求解整个网络的稳态解

        Args:
            max_iterations: 最大迭代次数
            tolerance: 收敛容差（质量平衡）
            verbose: 是否打印进度

        Returns:
            converged: 是否收敛
        """
        if verbose:
            print(f"\n网络稳态求解:")
            print(f"  最大迭代: {max_iterations}")
            print(f"  容差: {tolerance} m³/s")

        # 初始化分流节点的流量分配
        flow_distribution = {}

        for iteration in range(max_iterations):
            # 1. 更新所有渠段的内部解
            for segment in self.segments.values():
                # 获取上下游边界条件
                upstream_node = self.nodes[segment.upstream_node]
                downstream_node = self.nodes[segment.downstream_node]

                # 从节点获取边界条件 - 上游流量
                if upstream_node.type == 'source':
                    Q_in = upstream_node.boundary_condition.get('Q', 5.0)
                elif upstream_node.type == 'bifurcation':
                    # 分流节点：使用分配的流量
                    if segment.upstream_node not in flow_distribution:
                        # 计算总入流
                        Q_total_in = sum(s.solver.get_Q()[-1]
                                       for s in upstream_node.inlet_segments)
                        if Q_total_in < 0.1:
                            Q_total_in = 5.0
                        # 计算分配
                        flow_distribution[segment.upstream_node] = \
                            self._distribute_flow_at_bifurcation(upstream_node, Q_total_in)

                    Q_in = flow_distribution[segment.upstream_node].get(segment.id, 5.0)
                else:
                    # 汇合或内部节点
                    if len(upstream_node.inlet_segments) > 0:
                        Q_in = sum(s.solver.get_Q()[-1]
                                 for s in upstream_node.inlet_segments)
                    else:
                        Q_in = 5.0

                if downstream_node.type == 'sink':
                    h_out = downstream_node.boundary_condition.get('h', 1.0)
                else:
                    # 从下游渠段平均
                    if len(downstream_node.outlet_segments) > 0:
                        h_out = np.mean([s.solver.h[0]
                                       for s in downstream_node.outlet_segments])
                    else:
                        h_out = 1.0

                # 求解单渠段
                segment.solver.solve_steady_state(
                    Q_target=Q_in,
                    h_downstream=h_out,
                    max_iterations=100,
                    verbose=False
                )

            # 2. 更新分流节点的流量分配
            for node_id, node in self.nodes.items():
                if node.type == 'bifurcation' and len(node.inlet_segments) > 0:
                    Q_total_in = sum(s.solver.get_Q()[-1]
                                   for s in node.inlet_segments)
                    flow_distribution[node_id] = \
                        self._distribute_flow_at_bifurcation(node, Q_total_in)

            # 3. 检查节点质量平衡
            max_residual = 0.0
            for node in self.nodes.values():
                if node.type not in ['source', 'sink']:
                    residual = abs(node.compute_mass_balance())
                    max_residual = max(max_residual, residual)

            # 4. 进度输出
            if verbose and (iteration % 10 == 0 or iteration < 5):
                print(f"  迭代 {iteration}: 最大质量残差 = {max_residual:.4e} m³/s")

            # 5. 检查收敛
            if max_residual < tolerance:
                if verbose:
                    print(f"  收敛于迭代 {iteration}")
                return True

        if verbose:
            print(f"  未收敛：最大残差 {max_residual:.4e} m³/s")
        return False

    def get_network_state(self) -> Dict:
        """
        获取网络状态

        Returns:
            state: 包含所有渠段和节点状态的字典
        """
        state = {
            'segments': {},
            'nodes': {}
        }

        # 渠段状态
        for seg_id, segment in self.segments.items():
            state['segments'][seg_id] = {
                'x': segment.solver.x.copy(),
                'h': segment.solver.h.copy(),
                'Q': segment.solver.get_Q().copy(),
                'upstream_node': segment.upstream_node,
                'downstream_node': segment.downstream_node
            }

        # 节点状态
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
        """打印网络摘要"""
        state = self.get_network_state()

        print(f"\n" + "=" * 60)
        print("网络状态摘要")
        print("=" * 60)

        print(f"\n节点状态：")
        for node_id, node_state in state['nodes'].items():
            print(f"  {node_id} ({node_state['type']}):")
            print(f"    水深: {node_state['h']:.3f} m")
            print(f"    入流: {node_state['Q_in']:.3f} m³/s")
            print(f"    出流: {node_state['Q_out']:.3f} m³/s")
            print(f"    平衡: {node_state['balance']:.4e} m³/s")

        print(f"\n渠段状态：")
        for seg_id, seg_state in state['segments'].items():
            Q_mean = np.mean(seg_state['Q'])
            h_mean = np.mean(seg_state['h'])
            print(f"  {seg_id} ({seg_state['upstream_node']}→{seg_state['downstream_node']}):")
            print(f"    平均水深: {h_mean:.3f} m")
            print(f"    平均流量: {Q_mean:.3f} m³/s")

    def __repr__(self):
        return (f"CanalNetworkSolver(nodes={len(self.nodes)}, "
                f"segments={len(self.segments)})")


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("渠系网络求解器测试")
    print("=" * 60)

    # 创建简单三渠段串联网络
    network = CanalNetworkSolver()

    # 添加节点
    network.add_node('N1', 'source', {'Q': 10.0})
    network.add_node('N2', 'internal')
    network.add_node('N3', 'internal')
    network.add_node('N4', 'sink', {'h': 1.0})

    # 添加渠段
    network.add_canal_segment('C1', 'N1', 'N2',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)
    network.add_canal_segment('C2', 'N2', 'N3',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)
    network.add_canal_segment('C3', 'N3', 'N4',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)

    # 初始化
    network.initialize_network(h_initial=1.0, Q_initial=10.0)

    # 求解稳态
    converged = network.solve_network_steady(max_iterations=50, verbose=True)

    # 打印结果
    network.print_network_summary()

    print(f"\n收敛状态: {'✅ 收敛' if converged else '❌ 未收敛'}")
