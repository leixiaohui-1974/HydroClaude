"""
网络拓扑验证工具

提供完整的网络拓扑验证、物理合理性检查和可视化增强功能。

主要功能:
1. 拓扑完整性验证
2. 物理合理性检查（高程、流向、初始条件）
3. 网络健康评分
4. 增强可视化（高程剖面、流量分布）

Stage 3 - Task 3.1.3

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt


class NetworkValidator:
    """
    网络拓扑验证器

    提供全面的网络验证功能，包括：
    - 拓扑完整性检查
    - 物理合理性验证
    - 网络健康评分
    - 详细错误报告
    """

    def __init__(self, network):
        """
        初始化验证器

        Args:
            network: RiverNetwork实例
        """
        self.network = network
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_all(self, verbose: bool = True) -> Tuple[bool, float]:
        """
        执行所有验证检查

        Args:
            verbose: 是否打印详细信息

        Returns:
            (is_valid, health_score): 是否通过验证，健康评分(0-100)
        """
        self.errors = []
        self.warnings = []
        self.info = []

        # 1. 拓扑完整性
        self._check_topology_completeness()

        # 2. 节点连接性
        self._check_node_connectivity()

        # 3. 高程一致性
        self._check_elevation_consistency()

        # 4. 边界条件
        self._check_boundary_conditions()

        # 5. 初始条件
        self._check_initial_conditions()

        # 计算健康评分
        health_score = self._compute_health_score()

        # 是否通过验证（无错误）
        is_valid = len(self.errors) == 0

        if verbose:
            self.print_report()

        return is_valid, health_score

    def _check_topology_completeness(self):
        """检查拓扑完整性"""
        # 检查空网络
        if len(self.network.nodes) == 0:
            self.errors.append("Network has no nodes")
            return

        if len(self.network.reaches) == 0:
            self.errors.append("Network has no reaches")
            return

        self.info.append(f"Network has {len(self.network.nodes)} nodes, "
                        f"{len(self.network.reaches)} reaches")

        # 检查拓扑排序
        try:
            order = self.network.build_topology()
            self.info.append(f"Topological order: {len(order)} reaches")
        except ValueError as e:
            self.errors.append(f"Topology error: {str(e)}")
            return

        # 检查孤立节点
        isolated_nodes = []
        for node_id, node in self.network.nodes.items():
            if len(node.upstream_reaches) == 0 and len(node.downstream_reaches) == 0:
                isolated_nodes.append(node_id)

        if isolated_nodes:
            self.errors.append(f"Isolated nodes found: {isolated_nodes}")

    def _check_node_connectivity(self):
        """检查节点连接性"""
        # 检查入口和出口
        upstream_nodes = self.network.get_upstream_nodes()
        downstream_nodes = self.network.get_downstream_nodes()

        if len(upstream_nodes) == 0:
            self.errors.append("No upstream inlet nodes")
        else:
            self.info.append(f"Upstream inlets: {[n.id for n in upstream_nodes]}")

        if len(downstream_nodes) == 0:
            self.errors.append("No downstream outlet nodes")
        else:
            self.info.append(f"Downstream outlets: {[n.id for n in downstream_nodes]}")

        # 检查汇流节点
        junction_nodes = self.network.get_junction_nodes()
        if junction_nodes:
            self.info.append(f"Junction nodes: {len(junction_nodes)}")
            for node in junction_nodes:
                if len(node.upstream_reaches) < 2:
                    self.warnings.append(
                        f"Junction '{node.id}' has only {len(node.upstream_reaches)} "
                        f"upstream reaches (expected >= 2)"
                    )

    def _check_elevation_consistency(self):
        """检查高程一致性"""
        problems = []

        for reach_id, reach in self.network.reaches.items():
            upstream_node = self.network.nodes[reach.upstream]
            downstream_node = self.network.nodes[reach.downstream]

            z_up = upstream_node.elevation
            z_down = downstream_node.elevation

            # 上游应该高于或等于下游
            if z_up < z_down:
                delta_z = z_down - z_up
                problems.append(
                    f"Reach '{reach_id}': Upstream elevation ({z_up:.2f}m) < "
                    f"Downstream elevation ({z_down:.2f}m), Δz={delta_z:.2f}m"
                )

            # 计算坡度
            if reach.length and reach.length > 0:
                slope = (z_up - z_down) / reach.length
                if slope < 0:
                    self.errors.append(
                        f"Reach '{reach_id}': Negative slope {slope:.6f}"
                    )
                elif slope == 0:
                    self.warnings.append(
                        f"Reach '{reach_id}': Zero slope (horizontal)"
                    )
                elif slope > 0.1:
                    self.warnings.append(
                        f"Reach '{reach_id}': Very steep slope {slope:.4f} (>10%)"
                    )

        if problems:
            for problem in problems:
                self.errors.append(problem)

    def _check_boundary_conditions(self):
        """检查边界条件"""
        # 检查上游边界
        upstream_nodes = self.network.get_upstream_nodes()
        for node in upstream_nodes:
            if node.type == 'boundary':
                # 检查是否有边界条件定义
                if not hasattr(node, 'bc_variable'):
                    self.warnings.append(
                        f"Upstream boundary '{node.id}' has no BC defined"
                    )
            else:
                self.warnings.append(
                    f"Upstream node '{node.id}' is not a boundary node (type: {node.type})"
                )

        # 检查下游边界
        downstream_nodes = self.network.get_downstream_nodes()
        for node in downstream_nodes:
            if node.type == 'boundary':
                if not hasattr(node, 'bc_variable'):
                    self.warnings.append(
                        f"Downstream boundary '{node.id}' has no BC defined"
                    )
            else:
                self.warnings.append(
                    f"Downstream node '{node.id}' is not a boundary node (type: {node.type})"
                )

    def _check_initial_conditions(self):
        """检查初始条件"""
        reaches_without_ic = []

        for reach_id, reach in self.network.reaches.items():
            solver = reach.solver
            if solver is None:
                self.errors.append(f"Reach '{reach_id}' has no solver")
                continue

            # 检查是否有初始条件
            if not hasattr(solver, 'h') or solver.h is None:
                reaches_without_ic.append(reach_id)
                continue

            # 检查初始条件合理性
            h = solver.h
            if np.any(h < 0):
                self.errors.append(
                    f"Reach '{reach_id}': Negative water depth in initial conditions"
                )

            if np.any(np.isnan(h)) or np.any(np.isinf(h)):
                self.errors.append(
                    f"Reach '{reach_id}': Invalid values (NaN/Inf) in initial conditions"
                )

            # 检查流量
            if hasattr(solver, 'Q') and solver.Q is not None:
                Q = solver.Q
                if np.any(np.isnan(Q)) or np.any(np.isinf(Q)):
                    self.errors.append(
                        f"Reach '{reach_id}': Invalid values (NaN/Inf) in initial Q"
                    )

        if reaches_without_ic:
            self.warnings.append(
                f"Reaches without initial conditions: {reaches_without_ic}"
            )

    def _compute_health_score(self) -> float:
        """
        计算网络健康评分 (0-100)

        评分标准:
        - 每个错误 -20分
        - 每个警告 -5分
        - 基础分 100分
        """
        score = 100.0
        score -= len(self.errors) * 20
        score -= len(self.warnings) * 5
        score = max(0.0, min(100.0, score))
        return score

    def print_report(self):
        """打印验证报告"""
        print("\n" + "="*80)
        print("网络拓扑验证报告")
        print("="*80)

        # 错误
        if self.errors:
            print(f"\n 错误 ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        else:
            print("\n 无错误")

        # 警告
        if self.warnings:
            print(f"\n️  警告 ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        else:
            print("\n 无警告")

        # 信息
        if self.info:
            print(f"\nℹ️  信息:")
            for info in self.info:
                print(f"  - {info}")

        # 健康评分
        health_score = self._compute_health_score()
        print(f"\n 网络健康评分: {health_score:.1f}/100")

        if health_score >= 90:
            print("   评级: 优秀 ⭐⭐⭐⭐⭐")
        elif health_score >= 75:
            print("   评级: 良好 ⭐⭐⭐⭐")
        elif health_score >= 60:
            print("   评级: 合格 ⭐⭐⭐")
        elif health_score >= 40:
            print("   评级: 需改进 ⭐⭐")
        else:
            print("   评级: 不合格 ⭐")

        print("="*80)

    def get_validation_summary(self) -> Dict:
        """
        获取验证摘要

        Returns:
            字典包含: errors, warnings, info, health_score, is_valid
        """
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'health_score': self._compute_health_score(),
            'is_valid': len(self.errors) == 0
        }


class NetworkVisualizer:
    """
    网络可视化增强工具

    提供多种可视化方式：
    - 拓扑图（节点-河段）
    - 高程剖面图
    - 流量分布图
    - 水位分布图
    """

    def __init__(self, network):
        """
        初始化可视化工具

        Args:
            network: RiverNetwork实例
        """
        self.network = network

    def plot_elevation_profile(self,
                               path: Optional[List[str]] = None,
                               figsize: Tuple[int, int] = (14, 6)) -> plt.Figure:
        """
        绘制高程剖面图

        Args:
            path: 河段ID列表（指定路径），None则使用拓扑顺序
            figsize: 图形大小

        Returns:
            matplotlib Figure对象
        """
        if path is None:
            # 使用拓扑排序顺序
            if not self.network._topology_built:
                self.network.build_topology()
            path = self.network.topological_order

        if not path:
            print("No reaches to plot")
            return None

        # 收集数据
        distances = [0.0]
        elevations_bed = []
        elevations_water = []
        reach_names = []

        cumulative_distance = 0.0

        for reach_id in path:
            reach = self.network.reaches[reach_id]

            # 上游节点
            upstream_node = self.network.nodes[reach.upstream]
            z_up = upstream_node.elevation
            h_up = reach.get_upstream_h() if reach.solver else 0.0

            # 下游节点
            downstream_node = self.network.nodes[reach.downstream]
            z_down = downstream_node.elevation
            h_down = reach.get_downstream_h() if reach.solver else 0.0

            # 河段长度
            length = reach.length if reach.length else 100.0

            # 添加数据点（上游）
            elevations_bed.append(z_up)
            elevations_water.append(z_up + h_up)

            # 添加数据点（下游）
            cumulative_distance += length
            distances.append(cumulative_distance)
            elevations_bed.append(z_down)
            elevations_water.append(z_down + h_down)

            reach_names.append(reach_id)

        # 绘图
        fig, ax = plt.subplots(figsize=figsize)

        # 河床高程
        ax.plot(distances, elevations_bed, 'k-', linewidth=2, label='河床高程')
        ax.fill_between(distances, 0, elevations_bed, alpha=0.3, color='brown')

        # 水面高程
        ax.plot(distances, elevations_water, 'b-', linewidth=2, label='水面高程')
        ax.fill_between(distances, elevations_bed, elevations_water,
                       alpha=0.4, color='cyan')

        # 节点标记
        for i, (dist, z_bed, z_water) in enumerate(zip(distances, elevations_bed, elevations_water)):
            if i % 2 == 0:  # 只标记河段起点
                ax.plot(dist, z_bed, 'ko', markersize=6)
                ax.plot(dist, z_water, 'bo', markersize=6)

        ax.set_xlabel('距离 (m)', fontsize=12)
        ax.set_ylabel('高程 (m)', fontsize=12)
        ax.set_title(f'{self.network.name} - 高程剖面图', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_flow_distribution(self,
                               figsize: Tuple[int, int] = (14, 6)) -> plt.Figure:
        """
        绘制流量分布图

        Returns:
            matplotlib Figure对象
        """
        if not self.network._topology_built:
            self.network.build_topology()

        # 收集数据
        reach_ids = []
        flow_upstream = []
        flow_downstream = []
        flow_average = []

        for reach_id in self.network.topological_order:
            reach = self.network.reaches[reach_id]
            reach_ids.append(reach_id)

            Q_up = reach.get_upstream_Q()
            Q_down = reach.get_downstream_Q()
            Q_avg = reach.get_average_Q()

            flow_upstream.append(Q_up)
            flow_downstream.append(Q_down)
            flow_average.append(Q_avg)

        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

        x = np.arange(len(reach_ids))
        width = 0.35

        # 子图1: 上下游流量对比
        ax1.bar(x - width/2, flow_upstream, width, label='上游', alpha=0.8)
        ax1.bar(x + width/2, flow_downstream, width, label='下游', alpha=0.8)
        ax1.set_ylabel('流量 (m³/s)', fontsize=11)
        ax1.set_title(f'{self.network.name} - 流量分布', fontsize=13, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(reach_ids, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # 子图2: 平均流量
        ax2.plot(x, flow_average, 'o-', linewidth=2, markersize=8, label='平均流量')
        ax2.fill_between(x, 0, flow_average, alpha=0.3)
        ax2.set_xlabel('河段', fontsize=11)
        ax2.set_ylabel('流量 (m³/s)', fontsize=11)
        ax2.set_xticks(x)
        ax2.set_xticklabels(reach_ids, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_network_summary(self,
                            figsize: Tuple[int, int] = (16, 10)) -> plt.Figure:
        """
        绘制网络综合摘要图

        包含:
        - 拓扑图
        - 高程剖面
        - 流量分布

        Returns:
            matplotlib Figure对象
        """
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. 拓扑图（左上，占两格）
        try:
            import networkx as nx
            ax_topo = fig.add_subplot(gs[0, :])
            self._plot_topology_on_axis(ax_topo)
        except ImportError:
            ax_topo = fig.add_subplot(gs[0, :])
            ax_topo.text(0.5, 0.5, 'NetworkX not installed\nCannot plot topology',
                        ha='center', va='center', fontsize=14)
            ax_topo.axis('off')

        # 2. 高程剖面（左下）
        ax_elev = fig.add_subplot(gs[1, 0])
        self._plot_elevation_profile_on_axis(ax_elev)

        # 3. 流量分布（右下）
        ax_flow = fig.add_subplot(gs[1, 1])
        self._plot_flow_distribution_on_axis(ax_flow)

        fig.suptitle(f'{self.network.name} - 网络综合摘要',
                    fontsize=16, fontweight='bold')

        return fig

    def _plot_topology_on_axis(self, ax):
        """在指定axis上绘制拓扑图"""
        import networkx as nx

        G = nx.DiGraph()

        # 添加节点
        for node_id, node in self.network.nodes.items():
            node_colors = {
                'boundary': 'lightgreen',
                'junction': 'lightblue',
                'bifurcation': 'lightyellow',
                'reservoir': 'lightcoral'
            }
            color = node_colors.get(node.type, 'gray')
            G.add_node(node_id, pos=(node.x, node.y), color=color)

        # 添加边
        for reach_id, reach in self.network.reaches.items():
            G.add_edge(reach.upstream, reach.downstream, label=reach_id)

        pos = nx.get_node_attributes(G, 'pos')
        if not pos or all(x == 0 and y == 0 for x, y in pos.values()):
            pos = nx.spring_layout(G, k=2, iterations=50)

        colors = [G.nodes[n]['color'] for n in G.nodes()]

        nx.draw(G, pos, ax=ax, with_labels=True,
               node_color=colors, node_size=800,
               font_size=9, arrows=True, arrowsize=15,
               edge_color='gray')

        ax.set_title('网络拓扑', fontsize=12, fontweight='bold')
        ax.axis('off')

    def _plot_elevation_profile_on_axis(self, ax):
        """在指定axis上绘制高程剖面（简化版）"""
        if not self.network.topological_order:
            self.network.build_topology()

        distances = [0]
        elevations = []
        cum_dist = 0

        for reach_id in self.network.topological_order:
            reach = self.network.reaches[reach_id]
            upstream_node = self.network.nodes[reach.upstream]
            downstream_node = self.network.nodes[reach.downstream]

            elevations.append(upstream_node.elevation)
            length = reach.length if reach.length else 100
            cum_dist += length
            distances.append(cum_dist)
            elevations.append(downstream_node.elevation)

        ax.plot(distances, elevations, 'k-', linewidth=2)
        ax.fill_between(distances, 0, elevations, alpha=0.3, color='brown')
        ax.set_xlabel('距离 (m)', fontsize=10)
        ax.set_ylabel('高程 (m)', fontsize=10)
        ax.set_title('高程剖面', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)

    def _plot_flow_distribution_on_axis(self, ax):
        """在指定axis上绘制流量分布（简化版）"""
        if not self.network.topological_order:
            self.network.build_topology()

        reach_ids = []
        flows = []

        for reach_id in self.network.topological_order:
            reach = self.network.reaches[reach_id]
            reach_ids.append(reach_id[:8])  # 截断名称
            flows.append(reach.get_average_Q())

        x = np.arange(len(reach_ids))
        ax.bar(x, flows, alpha=0.7)
        ax.set_xlabel('河段', fontsize=10)
        ax.set_ylabel('流量 (m³/s)', fontsize=10)
        ax.set_title('流量分布', fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(reach_ids, rotation=45, ha='right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')


# 便捷函数
def validate_network(network, verbose: bool = True) -> Tuple[bool, float]:
    """
    验证网络拓扑（便捷函数）

    Args:
        network: RiverNetwork实例
        verbose: 是否打印详细信息

    Returns:
        (is_valid, health_score): 是否通过验证，健康评分
    """
    validator = NetworkValidator(network)
    return validator.validate_all(verbose=verbose)


def visualize_network(network, plot_type: str = 'summary',
                     figsize: Optional[Tuple[int, int]] = None):
    """
    可视化网络（便捷函数）

    Args:
        network: RiverNetwork实例
        plot_type: 绘图类型
            - 'summary': 综合摘要（默认）
            - 'elevation': 高程剖面
            - 'flow': 流量分布
        figsize: 图形大小

    Returns:
        matplotlib Figure对象
    """
    visualizer = NetworkVisualizer(network)

    if plot_type == 'elevation':
        figsize = figsize or (14, 6)
        return visualizer.plot_elevation_profile(figsize=figsize)
    elif plot_type == 'flow':
        figsize = figsize or (14, 6)
        return visualizer.plot_flow_distribution(figsize=figsize)
    else:  # 'summary'
        figsize = figsize or (16, 10)
        return visualizer.plot_network_summary(figsize=figsize)


if __name__ == "__main__":
    """简单测试"""
    print("Network Validation Module")
    print("Provides comprehensive validation and visualization tools")
    print()
    print("Main classes:")
    print("  - NetworkValidator: 拓扑和物理验证")
    print("  - NetworkVisualizer: 增强可视化")
    print()
    print("Convenience functions:")
    print("  - validate_network(network)")
    print("  - visualize_network(network, plot_type='summary')")
