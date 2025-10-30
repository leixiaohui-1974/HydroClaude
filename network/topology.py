"""
河网拓扑结构

定义网络的基本构建块：节点（Node）和河段（Reach）

主要类:
- Node: 网络节点（物理点或虚拟点）
- Reach: 河段（连接两个节点）
- RiverNetwork: 河网拓扑管理器

Stage 3 - Task 3.1.1

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt


class Node:
    """
    网络节点（物理点或虚拟点）

    节点可以是:
    - 边界节点（boundary）: 上游入口或下游出口
    - 汇流节点（junction）: 多条河段汇入
    - 分流节点（bifurcation）: 一条河段分为多条
    - 水库节点（reservoir）: 大水体

    Attributes:
        id (str): 节点唯一标识
        type (str): 节点类型
        elevation (float): 节点高程 (m)
        x, y (float): 平面坐标 (m)
        h (float): 当前水位 (m)
        Q_in (list): 入流列表 (m³/s)
        Q_out (list): 出流列表 (m³/s)
    """

    def __init__(self,
                 node_id: str,
                 node_type: str = "junction",
                 elevation: float = 0.0,
                 x: float = 0.0,
                 y: float = 0.0):
        """
        初始化节点

        Args:
            node_id: 节点唯一标识
            node_type: 节点类型 ('boundary', 'junction', 'bifurcation', 'reservoir')
            elevation: 节点高程 (m)
            x, y: 平面坐标 (m)
        """
        # 验证节点类型
        valid_types = ['boundary', 'junction', 'bifurcation', 'reservoir']
        if node_type not in valid_types:
            raise ValueError(f"Invalid node type: {node_type}. "
                           f"Must be one of {valid_types}")

        self.id = node_id
        self.type = node_type
        self.elevation = elevation
        self.x = x
        self.y = y

        # 水力状态
        self.h = None  # 水位 (m)
        self.Q_in = []  # 入流 (m³/s)
        self.Q_out = []  # 出流 (m³/s)

        # 连接信息（由RiverNetwork管理）
        self.upstream_reaches = []  # 上游河段ID列表
        self.downstream_reaches = []  # 下游河段ID列表

        # 内部建筑物（可选）
        self.internal_structure = None  # InternalStructure对象

    def check_mass_balance(self, tol: float = 1e-6) -> Tuple[bool, float]:
        """
        检查节点质量平衡

        Args:
            tol: 容差 (m³/s)

        Returns:
            (is_balanced, error): 是否平衡，误差值
        """
        sum_in = sum(self.Q_in) if self.Q_in else 0.0
        sum_out = sum(self.Q_out) if self.Q_out else 0.0
        error = abs(sum_in - sum_out)

        return error < tol, error

    def get_mass_balance_error(self) -> float:
        """
        获取质量平衡误差（相对误差 %）

        Returns:
            相对误差 (%)
        """
        sum_in = sum(self.Q_in) if self.Q_in else 0.0
        sum_out = sum(self.Q_out) if self.Q_out else 0.0

        Q_ref = max(abs(sum_in), abs(sum_out), 1e-9)
        error_abs = abs(sum_in - sum_out)
        error_rel = (error_abs / Q_ref) * 100.0

        return error_rel

    def __repr__(self) -> str:
        return (f"Node(id='{self.id}', type='{self.type}', "
                f"z={self.elevation:.2f}m, pos=({self.x:.1f}, {self.y:.1f}))")


class Reach:
    """
    河段（连接两个节点）

    河段包含一个求解器实例，负责计算该段的水力状态。

    Attributes:
        id (str): 河段唯一标识
        upstream (str): 上游节点ID
        downstream (str): 下游节点ID
        solver: 该河段的求解器实例（GodunvFVMSolver）
        length (float): 河段长度 (m)
        internal_structures (list): 内部建筑物列表（堰、闸等）
    """

    def __init__(self,
                 reach_id: str,
                 upstream_node: str,
                 downstream_node: str,
                 solver):
        """
        初始化河段

        Args:
            reach_id: 河段唯一标识
            upstream_node: 上游节点ID
            downstream_node: 下游节点ID
            solver: 该河段的求解器实例（GodunvFVMSolver）
        """
        self.id = reach_id
        self.upstream = upstream_node
        self.downstream = downstream_node
        self.solver = solver

        # 提取几何信息
        # 注意：GodunvFVMSolver使用self.L，旧版求解器可能使用self.length
        if hasattr(solver, 'length'):
            self.length = solver.length
        elif hasattr(solver, 'L'):
            self.length = solver.L
        else:
            self.length = None

        # 内部边界条件（可选）
        self.internal_structures = []  # 堰、闸等

    def get_upstream_Q(self) -> float:
        """
        获取河段上游流量

        Returns:
            上游流量 (m³/s)
        """
        if hasattr(self.solver, 'Q') and self.solver.Q is not None:
            return float(self.solver.Q[0])
        return 0.0

    def get_upstream_h(self) -> float:
        """
        获取河段上游水深

        Returns:
            上游水深 (m)
        """
        if hasattr(self.solver, 'h') and self.solver.h is not None:
            return float(self.solver.h[0])
        return 0.0

    def get_downstream_Q(self) -> float:
        """
        获取河段下游流量

        Returns:
            下游流量 (m³/s)
        """
        if hasattr(self.solver, 'Q') and self.solver.Q is not None:
            return float(self.solver.Q[-1])
        return 0.0

    def get_downstream_h(self) -> float:
        """
        获取河段下游水深

        Returns:
            下游水深 (m)
        """
        if hasattr(self.solver, 'h') and self.solver.h is not None:
            return float(self.solver.h[-1])
        return 0.0

    def get_average_Q(self) -> float:
        """获取河段平均流量"""
        if hasattr(self.solver, 'Q') and self.solver.Q is not None:
            return float(np.mean(self.solver.Q))
        return 0.0

    def get_average_h(self) -> float:
        """获取河段平均水深"""
        if hasattr(self.solver, 'h') and self.solver.h is not None:
            return float(np.mean(self.solver.h))
        return 0.0

    def __repr__(self) -> str:
        return (f"Reach(id='{self.id}', {self.upstream}→{self.downstream}, "
                f"L={self.length:.0f}m)")


class RiverNetwork:
    """
    河网拓扑管理器

    管理网络中的所有节点和河段，提供拓扑分析和可视化功能。

    Attributes:
        name (str): 网络名称
        nodes (dict): 节点字典 {node_id: Node}
        reaches (dict): 河段字典 {reach_id: Reach}
        adjacency (dict): 邻接表 {node_id: [connected_reach_ids]}
        topological_order (list): 拓扑排序后的河段顺序
    """

    def __init__(self, name: str = "River Network"):
        """
        初始化河网

        Args:
            name: 网络名称
        """
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.reaches: Dict[str, Reach] = {}

        # 拓扑信息
        self.adjacency: Dict[str, List[str]] = {}  # {node_id: [downstream_reach_ids]}
        self.topological_order: List[str] = []  # 拓扑排序后的河段顺序

        self._topology_built = False

    def add_node(self, node: Node) -> None:
        """
        添加节点到网络

        Args:
            node: Node实例

        Raises:
            ValueError: 如果节点ID已存在
        """
        if node.id in self.nodes:
            raise ValueError(f"Node '{node.id}' already exists in network")

        self.nodes[node.id] = node
        self.adjacency[node.id] = []
        self._topology_built = False  # 需要重新构建拓扑

    def add_reach(self, reach: Reach) -> None:
        """
        添加河段到网络

        Args:
            reach: Reach实例

        Raises:
            ValueError: 如果河段ID已存在或节点不存在
        """
        if reach.id in self.reaches:
            raise ValueError(f"Reach '{reach.id}' already exists in network")

        # 检查节点是否存在
        if reach.upstream not in self.nodes:
            raise ValueError(f"Upstream node '{reach.upstream}' not found in network")
        if reach.downstream not in self.nodes:
            raise ValueError(f"Downstream node '{reach.downstream}' not found in network")

        self.reaches[reach.id] = reach

        # 更新节点的连接信息
        self.nodes[reach.upstream].downstream_reaches.append(reach.id)
        self.nodes[reach.downstream].upstream_reaches.append(reach.id)

        # 更新邻接表（上游节点 → 河段）
        self.adjacency[reach.upstream].append(reach.id)

        self._topology_built = False

    def add_internal_structure(self, node_id: str, internal_structure) -> None:
        """
        添加内部建筑物到节点

        内部建筑物（堰、闸）将作为特殊的耦合器，连接上下游河段。

        Args:
            node_id: 节点ID
            internal_structure: InternalStructure实例
                (InternalWeir, InternalGate, InternalOrifice)

        Raises:
            ValueError: 如果节点不存在或节点不是串联节点

        示例:
            from network.structures import InternalWeir
            from physics.hydraulic_structures import BroadCrestedWeir

            # 创建堰
            weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)

            # 创建内部堰（连接reach1和reach2）
            internal_weir = InternalWeir(weir, reach1, reach2, node)

            # 添加到网络
            network.add_internal_structure('middle_node', internal_weir)
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not found in network")

        node = self.nodes[node_id]

        # 验证节点连接（必须是1入1出的串联节点）
        n_upstream = len(node.upstream_reaches)
        n_downstream = len(node.downstream_reaches)

        if n_upstream != 1 or n_downstream != 1:
            raise ValueError(
                f"Internal structure can only be added to serial nodes (1 upstream, 1 downstream). "
                f"Node '{node_id}' has {n_upstream} upstream and {n_downstream} downstream reaches."
            )

        # 附加内部建筑物
        node.internal_structure = internal_structure

    def build_topology(self) -> List[str]:
        """
        构建拓扑关系并进行拓扑排序

        使用DFS进行拓扑排序，保证上游河段在下游河段之前求解。

        Returns:
            拓扑排序后的河段ID列表（上游→下游）

        Raises:
            ValueError: 如果网络中存在环路
        """
        visited = set()
        temp = set()  # 用于检测环路
        order = []

        def visit(node_id: str):
            """DFS访问节点"""
            if node_id in temp:
                raise ValueError(f"Cycle detected in network at node '{node_id}'")
            if node_id in visited:
                return

            temp.add(node_id)

            # 访问所有下游节点
            for reach_id in self.adjacency.get(node_id, []):
                reach = self.reaches[reach_id]
                visit(reach.downstream)

            temp.remove(node_id)
            visited.add(node_id)

            # 添加该节点的所有出边（河段）到排序结果
            for reach_id in self.adjacency.get(node_id, []):
                if reach_id not in order:
                    order.append(reach_id)

        # 从所有未访问节点开始DFS
        for node_id in self.nodes:
            if node_id not in visited:
                visit(node_id)

        # 反转得到上游→下游顺序
        self.topological_order = order[::-1]
        self._topology_built = True

        return self.topological_order

    def get_upstream_nodes(self) -> List[Node]:
        """
        获取所有上游边界节点（没有上游河段的节点）

        Returns:
            上游节点列表
        """
        upstream = []
        for node in self.nodes.values():
            if len(node.upstream_reaches) == 0:
                upstream.append(node)
        return upstream

    def get_downstream_nodes(self) -> List[Node]:
        """
        获取所有下游边界节点（没有下游河段的节点）

        Returns:
            下游节点列表
        """
        downstream = []
        for node in self.nodes.values():
            if len(node.downstream_reaches) == 0:
                downstream.append(node)
        return downstream

    def get_junction_nodes(self) -> List[Node]:
        """
        获取所有汇流节点（多个上游河段汇入）

        Returns:
            汇流节点列表
        """
        junctions = []
        for node in self.nodes.values():
            if len(node.upstream_reaches) > 1:
                junctions.append(node)
        return junctions

    def validate_topology(self) -> Tuple[bool, List[str]]:
        """
        验证网络拓扑的完整性和合理性

        检查:
        1. 无孤立节点
        2. 无孤立河段
        3. 拓扑排序成功（无环路）
        4. 至少有一个入口和一个出口

        Returns:
            (is_valid, error_messages): 是否有效，错误信息列表
        """
        errors = []

        # 检查是否为空网络
        if len(self.nodes) == 0:
            errors.append("Network has no nodes")
        if len(self.reaches) == 0:
            errors.append("Network has no reaches")

        if errors:
            return False, errors

        # 检查孤立节点
        for node_id, node in self.nodes.items():
            if len(node.upstream_reaches) == 0 and len(node.downstream_reaches) == 0:
                errors.append(f"Isolated node: '{node_id}'")

        # 检查拓扑排序（自动检测环路）
        try:
            self.build_topology()
        except ValueError as e:
            errors.append(str(e))

        # 检查边界节点
        upstream_nodes = self.get_upstream_nodes()
        downstream_nodes = self.get_downstream_nodes()

        if len(upstream_nodes) == 0:
            errors.append("No upstream boundary nodes (inlet)")
        if len(downstream_nodes) == 0:
            errors.append("No downstream boundary nodes (outlet)")

        is_valid = len(errors) == 0
        return is_valid, errors

    def check_global_mass_balance(self) -> Tuple[float, float, float]:
        """
        检查全局质量平衡

        Returns:
            (Q_in_total, Q_out_total, error_percent): 总入流、总出流、误差百分比
        """
        # 计算总入流（上游边界节点）
        Q_in_total = 0.0
        for node in self.get_upstream_nodes():
            for reach_id in node.downstream_reaches:
                reach = self.reaches[reach_id]
                Q_in_total += reach.get_upstream_Q()

        # 计算总出流（下游边界节点）
        Q_out_total = 0.0
        for node in self.get_downstream_nodes():
            for reach_id in node.upstream_reaches:
                reach = self.reaches[reach_id]
                Q_out_total += reach.get_downstream_Q()

        # 计算误差
        Q_ref = max(abs(Q_in_total), abs(Q_out_total), 1e-9)
        error = abs(Q_in_total - Q_out_total)
        error_percent = (error / Q_ref) * 100.0

        return Q_in_total, Q_out_total, error_percent

    def visualize(self,
                  show_labels: bool = True,
                  show_flow: bool = False,
                  figsize: Tuple[int, int] = (12, 8)) -> plt.Figure:
        """
        可视化网络拓扑

        Args:
            show_labels: 是否显示节点和河段标签
            show_flow: 是否显示流量信息
            figsize: 图形大小

        Returns:
            matplotlib Figure对象
        """
        try:
            import networkx as nx
        except ImportError:
            print("Warning: networkx not installed. Cannot visualize network.")
            print("Install with: pip install networkx")
            return None

        G = nx.DiGraph()

        # 添加节点
        for node_id, node in self.nodes.items():
            # 节点颜色根据类型
            node_colors = {
                'boundary': 'lightgreen',
                'junction': 'lightblue',
                'bifurcation': 'lightyellow',
                'reservoir': 'lightcoral'
            }
            color = node_colors.get(node.type, 'gray')

            G.add_node(node_id,
                      pos=(node.x, node.y),
                      node_type=node.type,
                      color=color)

        # 添加边（河段）
        for reach_id, reach in self.reaches.items():
            label = reach_id
            if show_flow:
                Q = reach.get_average_Q()
                label = f"{reach_id}\nQ={Q:.2f}"

            G.add_edge(reach.upstream, reach.downstream,
                      reach_id=reach_id,
                      label=label)

        # 绘制
        fig, ax = plt.subplots(figsize=figsize)

        pos = nx.get_node_attributes(G, 'pos')
        colors = [G.nodes[n]['color'] for n in G.nodes()]

        # 如果没有指定坐标，使用自动布局
        if not pos or all(x == 0 and y == 0 for x, y in pos.values()):
            pos = nx.spring_layout(G, k=2, iterations=50)

        nx.draw(G, pos,
               with_labels=show_labels,
               node_color=colors,
               node_size=1000,
               font_size=10,
               font_weight='bold',
               arrows=True,
               arrowsize=20,
               arrowstyle='->',
               edge_color='gray',
               ax=ax)

        if show_labels:
            edge_labels = nx.get_edge_attributes(G, 'label')
            nx.draw_networkx_edge_labels(G, pos, edge_labels,
                                         font_size=8, ax=ax)

        ax.set_title(f"{self.name}\n{len(self.nodes)} nodes, "
                    f"{len(self.reaches)} reaches", fontsize=14)
        ax.axis('equal')
        ax.axis('off')

        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='lightgreen', label='Boundary'),
            Patch(facecolor='lightblue', label='Junction'),
            Patch(facecolor='lightyellow', label='Bifurcation'),
            Patch(facecolor='lightcoral', label='Reservoir')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        return fig

    def print_summary(self) -> None:
        """打印网络摘要信息"""
        print("="*60)
        print(f"River Network: {self.name}")
        print("="*60)
        print(f"Nodes: {len(self.nodes)}")
        print(f"  - Boundary: {sum(1 for n in self.nodes.values() if n.type == 'boundary')}")
        print(f"  - Junction: {sum(1 for n in self.nodes.values() if n.type == 'junction')}")
        print(f"  - Bifurcation: {sum(1 for n in self.nodes.values() if n.type == 'bifurcation')}")
        print(f"  - Reservoir: {sum(1 for n in self.nodes.values() if n.type == 'reservoir')}")
        print(f"Reaches: {len(self.reaches)}")
        print(f"Upstream boundaries: {len(self.get_upstream_nodes())}")
        print(f"Downstream boundaries: {len(self.get_downstream_nodes())}")

        # 拓扑验证
        is_valid, errors = self.validate_topology()
        if is_valid:
            print("✅ Topology: Valid")
            if self._topology_built:
                print(f"✅ Topological order: {len(self.topological_order)} reaches")
        else:
            print("❌ Topology: Invalid")
            for error in errors:
                print(f"   - {error}")

        # 质量平衡
        try:
            Q_in, Q_out, error = self.check_global_mass_balance()
            print(f"Global mass balance:")
            print(f"  - Total inflow: {Q_in:.3f} m³/s")
            print(f"  - Total outflow: {Q_out:.3f} m³/s")
            print(f"  - Error: {error:.4f}%")
        except:
            print("Global mass balance: Not available (solve first)")

        print("="*60)

    def __repr__(self) -> str:
        return (f"RiverNetwork(name='{self.name}', "
                f"nodes={len(self.nodes)}, reaches={len(self.reaches)})")


if __name__ == "__main__":
    """简单测试示例"""
    print("Testing Network Topology Module...")
    print()

    # 创建简单的3节点2河段串联网络
    network = RiverNetwork("Test Network")

    # 添加节点
    n1 = Node("N1", "boundary", elevation=100.0, x=0, y=0)
    n2 = Node("N2", "junction", elevation=95.0, x=100, y=0)
    n3 = Node("N3", "boundary", elevation=90.0, x=200, y=0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 创建模拟求解器（这里用None代替，实际需要GodunvFVMSolver实例）
    class DummySolver:
        def __init__(self, length):
            self.length = length
            self.h = np.array([2.0, 2.0, 2.0])
            self.Q = np.array([10.0, 10.0, 10.0])

    solver1 = DummySolver(100.0)
    solver2 = DummySolver(100.0)

    # 添加河段
    r1 = Reach("R1", "N1", "N2", solver1)
    r2 = Reach("R2", "N2", "N3", solver2)

    network.add_reach(r1)
    network.add_reach(r2)

    # 构建拓扑
    order = network.build_topology()
    print(f"Topological order: {order}")
    print()

    # 打印摘要
    network.print_summary()
    print()

    # 测试通过
    print("✅ Network topology module test passed!")
