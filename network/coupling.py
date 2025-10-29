"""
河段耦合器

实现多河段间的边界条件传递和耦合计算。

主要功能:
1. 河段间边界条件传递
2. 串联河段耦合
3. 并联河段耦合（汇流/分流）
4. 水位和流量连续性保证

Stage 3 - Task 3.2.1

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import List, Tuple, Optional, Dict


class ReachCoupler:
    """
    河段耦合器

    负责两个相邻河段之间的边界条件传递和耦合计算。

    耦合原则:
    - 上游河段下游BC ← 下游河段上游水位
    - 下游河段上游BC ← 上游河段下游流量
    - 保证质量守恒和水位连续性

    Attributes:
        upstream_reach: 上游河段
        downstream_reach: 下游河段
        coupling_node: 耦合节点
        coupling_method: 耦合方法 ('simple', 'iterative')
    """

    def __init__(self,
                 upstream_reach,
                 downstream_reach,
                 coupling_node,
                 coupling_method: str = 'simple'):
        """
        初始化河段耦合器

        Args:
            upstream_reach: 上游河段（Reach对象）
            downstream_reach: 下游河段（Reach对象）
            coupling_node: 耦合节点（Node对象）
            coupling_method: 耦合方法
                - 'simple': 简单直接传递（默认）
                - 'iterative': 迭代耦合
        """
        self.upstream = upstream_reach
        self.downstream = downstream_reach
        self.node = coupling_node
        self.method = coupling_method

        # 耦合状态
        self.Q_coupling = None  # 耦合点流量
        self.h_coupling = None  # 耦合点水深
        self.is_consistent = False  # 是否一致

    def transfer_boundary_conditions(self) -> Tuple[float, float]:
        """
        传递边界条件

        从一个河段提取边界值，设置到相邻河段。

        Returns:
            (Q_coupling, h_coupling): 耦合点流量和水深
        """
        # 获取上游河段下游状态
        h_up_downstream = self.upstream.get_downstream_h()
        Q_up_downstream = self.upstream.get_downstream_Q()

        # 获取下游河段上游状态
        h_down_upstream = self.downstream.get_upstream_h()
        Q_down_upstream = self.downstream.get_upstream_Q()

        if self.method == 'simple':
            # 简单传递：
            # 上游河段下游BC = 下游河段上游水深
            # 下游河段上游BC = 上游河段下游流量

            self.Q_coupling = Q_up_downstream
            self.h_coupling = h_down_upstream

            # 设置边界条件
            self.upstream.solver.bc_right = {'type': 'h', 'value': h_down_upstream}
            self.downstream.solver.bc_left = {'type': 'Q', 'value': Q_up_downstream}

        elif self.method == 'iterative':
            # 迭代耦合：取平均值
            Q_avg = (Q_up_downstream + Q_down_upstream) / 2.0
            h_avg = (h_up_downstream + h_down_upstream) / 2.0

            self.Q_coupling = Q_avg
            self.h_coupling = h_avg

            self.upstream.solver.bc_right = {'type': 'h', 'value': h_avg}
            self.downstream.solver.bc_left = {'type': 'Q', 'value': Q_avg}

        return self.Q_coupling, self.h_coupling

    def check_compatibility(self, tol_h: float = 0.01, tol_Q: float = 0.1) -> Tuple[bool, Dict]:
        """
        检查耦合兼容性

        验证：
        1. 水位连续性：h_up_downstream ≈ h_down_upstream
        2. 流量连续性：Q_up_downstream ≈ Q_down_upstream

        Args:
            tol_h: 水位容差 (m)
            tol_Q: 流量容差 (m³/s)

        Returns:
            (is_compatible, metrics): 是否兼容，兼容性指标
        """
        # 获取状态
        h_up = self.upstream.get_downstream_h()
        h_down = self.downstream.get_upstream_h()
        Q_up = self.upstream.get_downstream_Q()
        Q_down = self.downstream.get_upstream_Q()

        # 计算差异
        delta_h = abs(h_up - h_down)
        delta_Q = abs(Q_up - Q_down)

        # 相对误差
        h_ref = max(abs(h_up), abs(h_down), 1e-6)
        Q_ref = max(abs(Q_up), abs(Q_down), 1e-6)

        error_h_rel = (delta_h / h_ref) * 100  # %
        error_Q_rel = (delta_Q / Q_ref) * 100  # %

        # 判断
        compatible_h = delta_h < tol_h
        compatible_Q = delta_Q < tol_Q

        is_compatible = compatible_h and compatible_Q

        metrics = {
            'h_upstream': h_up,
            'h_downstream': h_down,
            'delta_h': delta_h,
            'error_h_percent': error_h_rel,
            'Q_upstream': Q_up,
            'Q_downstream': Q_down,
            'delta_Q': delta_Q,
            'error_Q_percent': error_Q_rel,
            'compatible': is_compatible
        }

        self.is_consistent = is_compatible

        return is_compatible, metrics

    def print_status(self):
        """打印耦合状态"""
        print(f"\n河段耦合器状态:")
        print(f"  上游河段: {self.upstream.id}")
        print(f"  下游河段: {self.downstream.id}")
        print(f"  耦合节点: {self.node.id}")
        print(f"  耦合方法: {self.method}")

        if self.Q_coupling is not None:
            print(f"  耦合流量: {self.Q_coupling:.3f} m³/s")
        if self.h_coupling is not None:
            print(f"  耦合水深: {self.h_coupling:.3f} m")

        # 兼容性
        is_compatible, metrics = self.check_compatibility()
        print(f"  水位连续性: Δh = {metrics['delta_h']:.4f}m ({metrics['error_h_percent']:.2f}%)")
        print(f"  流量连续性: ΔQ = {metrics['delta_Q']:.4f}m³/s ({metrics['error_Q_percent']:.2f}%)")
        print(f"  兼容性: {'✅ 兼容' if is_compatible else '❌ 不兼容'}")


class JunctionCoupler:
    """
    汇流节点耦合器

    处理多条河段汇入一点的耦合：
    - 多条上游河段 → 1个汇流节点 → 1条下游河段

    质量守恒: ΣQ_in = Q_out
    能量守恒: 计算汇流点水位
    """

    def __init__(self,
                 junction_node,
                 upstream_reaches: List,
                 downstream_reach):
        """
        初始化汇流耦合器

        Args:
            junction_node: 汇流节点（JunctionNode对象）
            upstream_reaches: 上游河段列表
            downstream_reach: 下游河段
        """
        self.junction = junction_node
        self.upstreams = upstream_reaches
        self.downstream = downstream_reach

    def couple(self) -> Tuple[float, float]:
        """
        执行汇流耦合

        Returns:
            (h_junction, Q_total): 汇流点水位，总流量
        """
        # 收集上游信息
        h_list = []
        Q_list = []
        A_list = []

        for reach in self.upstreams:
            h = reach.get_downstream_h()
            Q = reach.get_downstream_Q()
            # 简化：假设矩形断面
            width = reach.solver.width if hasattr(reach.solver, 'width') else 10.0
            A = width * h
            h_list.append(h)
            Q_list.append(Q)
            A_list.append(A)

        # 使用JunctionNode计算汇流点水位
        h_junction = self.junction.compute_junction_water_level(h_list, Q_list, A_list)

        # 总流量
        Q_total = sum(Q_list)

        # 设置边界条件
        # 上游河段：设置下游水深
        for reach in self.upstreams:
            h_coupling = h_junction - self.junction.elevation  # 水深
            reach.solver.bc_right = {'type': 'h', 'value': h_coupling}

        # 下游河段：设置上游流量
        self.downstream.solver.bc_left = {'type': 'Q', 'value': Q_total}

        # 更新节点状态
        self.junction.Q_in = Q_list
        self.junction.Q_out = [Q_total]
        self.junction.h = h_junction - self.junction.elevation

        return h_junction, Q_total

    def check_mass_balance(self, tol: float = 1e-3) -> Tuple[bool, float]:
        """
        检查质量平衡

        Args:
            tol: 容差 (m³/s)

        Returns:
            (is_balanced, error): 是否平衡，误差值
        """
        return self.junction.check_mass_balance(tol=tol)


class BifurcationCoupler:
    """
    分流节点耦合器

    处理一条河段分为多条的耦合：
    - 1条上游河段 → 1个分流节点 → 多条下游河段

    质量守恒: Q_in = ΣQ_out
    分流规则: 固定比例或动态分流
    """

    def __init__(self,
                 bifurcation_node,
                 upstream_reach,
                 downstream_reaches: List):
        """
        初始化分流耦合器

        Args:
            bifurcation_node: 分流节点（BifurcationNode对象）
            upstream_reach: 上游河段
            downstream_reaches: 下游河段列表
        """
        self.bifurcation = bifurcation_node
        self.upstream = upstream_reach
        self.downstreams = downstream_reaches

    def couple(self) -> Tuple[float, List[float]]:
        """
        执行分流耦合

        Returns:
            (Q_total, Q_split_list): 总流量，分流列表
        """
        # 上游流量
        Q_total = self.upstream.get_downstream_Q()
        h_upstream = self.upstream.get_downstream_h()

        # 下游水位（动态分流时使用）
        h_downstream_list = None
        if self.bifurcation.split_method == 'dynamic':
            h_downstream_list = [reach.get_upstream_h() for reach in self.downstreams]

        # 计算分流
        Q_split_list = self.bifurcation.compute_split_flows(Q_total, h_downstream_list)

        # 设置边界条件
        # 上游河段：可以设置下游平均水深
        h_down_avg = np.mean([reach.get_upstream_h() for reach in self.downstreams])
        self.upstream.solver.bc_right = {'type': 'h', 'value': h_down_avg}

        # 下游河段：设置上游流量
        for reach, Q_split in zip(self.downstreams, Q_split_list):
            reach.solver.bc_left = {'type': 'Q', 'value': Q_split}

        # 更新节点状态
        self.bifurcation.Q_in = [Q_total]
        self.bifurcation.Q_out = Q_split_list
        self.bifurcation.h = h_upstream

        return Q_total, Q_split_list

    def check_mass_balance(self, tol: float = 1e-3) -> Tuple[bool, float]:
        """
        检查质量平衡

        Args:
            tol: 容差 (m³/s)

        Returns:
            (is_balanced, error): 是否平衡，误差值
        """
        return self.bifurcation.check_mass_balance(tol=tol)


# 便捷函数
def create_reach_coupler(upstream_reach, downstream_reach, coupling_node) -> ReachCoupler:
    """
    创建河段耦合器（便捷函数）

    Args:
        upstream_reach: 上游河段
        downstream_reach: 下游河段
        coupling_node: 耦合节点

    Returns:
        ReachCoupler实例
    """
    return ReachCoupler(upstream_reach, downstream_reach, coupling_node)


def create_junction_coupler(junction_node, upstream_reaches, downstream_reach) -> JunctionCoupler:
    """
    创建汇流耦合器（便捷函数）

    Args:
        junction_node: 汇流节点
        upstream_reaches: 上游河段列表
        downstream_reach: 下游河段

    Returns:
        JunctionCoupler实例
    """
    return JunctionCoupler(junction_node, upstream_reaches, downstream_reach)


def create_bifurcation_coupler(bifurcation_node, upstream_reach,
                               downstream_reaches) -> BifurcationCoupler:
    """
    创建分流耦合器（便捷函数）

    Args:
        bifurcation_node: 分流节点
        upstream_reach: 上游河段
        downstream_reaches: 下游河段列表

    Returns:
        BifurcationCoupler实例
    """
    return BifurcationCoupler(bifurcation_node, upstream_reach, downstream_reaches)


if __name__ == "__main__":
    """简单测试"""
    print("Network Coupling Module")
    print("Provides reach coupling and boundary condition transfer")
    print()
    print("Main classes:")
    print("  - ReachCoupler: 串联河段耦合")
    print("  - JunctionCoupler: 汇流节点耦合")
    print("  - BifurcationCoupler: 分流节点耦合")
    print()
    print("Convenience functions:")
    print("  - create_reach_coupler()")
    print("  - create_junction_coupler()")
    print("  - create_bifurcation_coupler()")
