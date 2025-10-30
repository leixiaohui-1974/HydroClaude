"""
Network Topology Module - 管网拓扑模块

This module implements network topology analysis for pressurized pipe networks.

Classes:
    NetworkTopology: Network topology analyzer
    NetworkGraph: Graph representation helper

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Optional, List, Dict, Tuple, Set
from collections import deque, defaultdict
import warnings

# 导入节点和管道类
from network.network_node import NetworkNode, Junction, Reservoir, Tank
from network.pressure_pipe import PressurePipe


class NetworkTopology:
    """
    管网拓扑结构分析类 - Network Topology Analyzer

    This class manages the topological structure of a pipe network, including:
    - Node-pipe connectivity
    - Loop identification
    - Tree structure analysis
    - Path finding
    - Incidence matrix construction

    功能特性:
    - 添加/删除节点和管道
    - 自动维护连接关系
    - 识别独立回路（基本回路）
    - 构造关联矩阵
    - 拓扑有效性检查
    - 最短路径搜索

    Typical usage:
        >>> topology = NetworkTopology()
        >>> topology.add_node(Junction("J1", elevation=10.0))
        >>> topology.add_pipe(pipe, "J1", "J2")
        >>> loops = topology.find_loops()
    """

    def __init__(self, name: str = "Network"):
        """
        初始化管网拓扑

        Args:
            name: 管网名称
        """
        self.name = name

        # 节点和管道存储
        self.nodes: Dict[str, NetworkNode] = {}  # {node_id: NetworkNode}
        self.pipes: Dict[str, PressurePipe] = {}  # {pipe_id: PressurePipe}

        # 拓扑连接关系
        self.pipe_connections: Dict[str, Tuple[str, str]] = {}  # {pipe_id: (from_node, to_node)}
        self.node_connections: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # {node_id: [(pipe_id, direction), ...]}
        # direction: 'in' 表示流入节点, 'out' 表示流出节点

        # 邻接表（用于图算法）
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # {node_id: [neighbor_ids]}

        # 回路缓存
        self._loops_cache: Optional[List[List[str]]] = None
        self._loops_dirty = True  # 标记回路缓存是否过期

        # 统计信息
        self.num_loops: int = 0
        self.num_branches: int = 0

    def add_node(self, node: NetworkNode):
        """
        添加节点到管网

        Args:
            node: NetworkNode实例

        Raises:
            ValueError: 如果节点ID已存在
        """
        if node.node_id in self.nodes:
            raise ValueError(f"节点 {node.node_id} 已存在于管网中")

        self.nodes[node.node_id] = node
        self._loops_dirty = True

    def add_pipe(self, pipe: PressurePipe, from_node_id: str, to_node_id: str):
        """
        添加管道到管网并建立连接

        Args:
            pipe: PressurePipe实例
            from_node_id: 起始节点ID
            to_node_id: 终止节点ID

        Raises:
            ValueError: 如果管道ID已存在或节点不存在
        """
        # 验证
        if pipe.pipe_id in self.pipes:
            raise ValueError(f"管道 {pipe.pipe_id} 已存在于管网中")

        if from_node_id not in self.nodes:
            raise ValueError(f"起始节点 {from_node_id} 不存在")

        if to_node_id not in self.nodes:
            raise ValueError(f"终止节点 {to_node_id} 不存在")

        if from_node_id == to_node_id:
            raise ValueError(f"管道不能连接到自身: {from_node_id}")

        # 添加管道
        self.pipes[pipe.pipe_id] = pipe

        # 建立连接关系
        self.pipe_connections[pipe.pipe_id] = (from_node_id, to_node_id)

        # 更新节点连接
        self.node_connections[from_node_id].append((pipe.pipe_id, 'out'))
        self.node_connections[to_node_id].append((pipe.pipe_id, 'in'))

        # 更新邻接表
        self.adjacency[from_node_id].append(to_node_id)
        self.adjacency[to_node_id].append(from_node_id)  # 无向图

        # 更新节点的连接管道列表
        self.nodes[from_node_id].add_connected_pipe(pipe.pipe_id)
        self.nodes[to_node_id].add_connected_pipe(pipe.pipe_id)

        # 标记回路缓存过期
        self._loops_dirty = True

    def remove_pipe(self, pipe_id: str):
        """
        从管网中移除管道

        Args:
            pipe_id: 管道ID

        Raises:
            ValueError: 如果管道不存在
        """
        if pipe_id not in self.pipes:
            raise ValueError(f"管道 {pipe_id} 不存在")

        # 获取连接关系
        from_node, to_node = self.pipe_connections[pipe_id]

        # 移除管道
        del self.pipes[pipe_id]
        del self.pipe_connections[pipe_id]

        # 更新节点连接
        self.node_connections[from_node] = [
            (p, d) for p, d in self.node_connections[from_node] if p != pipe_id
        ]
        self.node_connections[to_node] = [
            (p, d) for p, d in self.node_connections[to_node] if p != pipe_id
        ]

        # 更新邻接表（需要检查是否有其他管道连接这两个节点）
        self._rebuild_adjacency()

        # 更新节点的连接管道列表
        self.nodes[from_node].remove_connected_pipe(pipe_id)
        self.nodes[to_node].remove_connected_pipe(pipe_id)

        # 标记回路缓存过期
        self._loops_dirty = True

    def remove_node(self, node_id: str):
        """
        从管网中移除节点（会移除所有连接的管道）

        Args:
            node_id: 节点ID

        Raises:
            ValueError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise ValueError(f"节点 {node_id} 不存在")

        # 获取连接的管道
        connected_pipes = list(self.nodes[node_id].connected_pipes)

        # 移除所有连接的管道
        for pipe_id in connected_pipes:
            if pipe_id in self.pipes:
                self.remove_pipe(pipe_id)

        # 移除节点
        del self.nodes[node_id]
        if node_id in self.node_connections:
            del self.node_connections[node_id]
        if node_id in self.adjacency:
            del self.adjacency[node_id]

        self._loops_dirty = True

    def _rebuild_adjacency(self):
        """重建邻接表"""
        self.adjacency = defaultdict(list)

        for pipe_id, (from_node, to_node) in self.pipe_connections.items():
            if to_node not in self.adjacency[from_node]:
                self.adjacency[from_node].append(to_node)
            if from_node not in self.adjacency[to_node]:
                self.adjacency[to_node].append(from_node)

    def get_pipe_endpoints(self, pipe_id: str) -> Tuple[str, str]:
        """
        获取管道的起止节点

        Args:
            pipe_id: 管道ID

        Returns:
            (起始节点ID, 终止节点ID)

        Raises:
            ValueError: 如果管道不存在
        """
        if pipe_id not in self.pipe_connections:
            raise ValueError(f"管道 {pipe_id} 不存在")

        return self.pipe_connections[pipe_id]

    def get_node_pipes(self, node_id: str) -> List[Tuple[str, str]]:
        """
        获取节点连接的所有管道

        Args:
            node_id: 节点ID

        Returns:
            [(pipe_id, direction), ...] 列表
            direction: 'in' (流入) 或 'out' (流出)

        Raises:
            ValueError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise ValueError(f"节点 {node_id} 不存在")

        return self.node_connections.get(node_id, [])

    def find_loops(self, max_loops: Optional[int] = None) -> List[List[str]]:
        """
        识别管网中的所有独立回路 - Find all independent loops

        使用深度优先搜索(DFS)识别基本回路。

        算法原理:
        1. 选择一棵生成树
        2. 每条非树边对应一个基本回路
        3. 基本回路数 = 管道数 - 节点数 + 1 (对于连通图)

        Args:
            max_loops: 最大回路数限制（可选）

        Returns:
            回路列表，每个回路是节点ID的列表
            例如: [['J1', 'J2', 'J3', 'J1'], ['J2', 'J4', 'J5', 'J2']]
        """
        if not self._loops_dirty and self._loops_cache is not None:
            return self._loops_cache

        loops = []

        # 检查是否有节点和管道
        if not self.nodes or not self.pipes:
            self._loops_cache = loops
            self._loops_dirty = False
            return loops

        # 找出所有连通分量
        visited_global = set()
        for start_node in self.nodes:
            if start_node in visited_global:
                continue

            # 对每个连通分量使用DFS找回路
            component_loops = self._find_loops_dfs(start_node, visited_global)
            loops.extend(component_loops)

            if max_loops is not None and len(loops) >= max_loops:
                loops = loops[:max_loops]
                break

        # 缓存结果
        self._loops_cache = loops
        self._loops_dirty = False
        self.num_loops = len(loops)

        return loops

    def _find_loops_dfs(self, start_node: str, visited_global: Set[str]) -> List[List[str]]:
        """
        使用DFS在一个连通分量中查找所有基本回路

        Args:
            start_node: 起始节点
            visited_global: 全局访问标记

        Returns:
            该连通分量中的所有回路
        """
        loops = []

        # 构建生成树
        parent = {}  # {node: parent_node}
        visited = set()
        stack = [start_node]
        parent[start_node] = None

        # DFS构建生成树
        while stack:
            node = stack.pop()

            if node in visited:
                continue

            visited.add(node)
            visited_global.add(node)

            for neighbor in self.adjacency[node]:
                if neighbor not in visited:
                    parent[neighbor] = node
                    stack.append(neighbor)

        # 找出所有非树边（这些边会形成回路）
        for pipe_id, (from_node, to_node) in self.pipe_connections.items():
            # 检查该边是否在生成树中
            is_tree_edge = (
                parent.get(to_node) == from_node or
                parent.get(from_node) == to_node
            )

            if not is_tree_edge and from_node in visited and to_node in visited:
                # 这是一条非树边，形成一个回路
                loop = self._construct_loop(from_node, to_node, parent)
                if loop and len(loop) >= 3:  # 至少3个节点才能形成回路
                    loops.append(loop)

        return loops

    def _construct_loop(
        self,
        node1: str,
        node2: str,
        parent: Dict[str, Optional[str]]
    ) -> List[str]:
        """
        根据非树边构造回路

        Args:
            node1: 非树边的一个端点
            node2: 非树边的另一个端点
            parent: 生成树的父节点字典

        Returns:
            回路节点列表
        """
        # 找到node1和node2的最近公共祖先
        path1 = []
        node = node1
        while node is not None:
            path1.append(node)
            node = parent.get(node)

        path2 = []
        node = node2
        while node is not None:
            path2.append(node)
            node = parent.get(node)

        # 找到公共祖先
        path1_set = set(path1)
        common_ancestor = None
        for node in path2:
            if node in path1_set:
                common_ancestor = node
                break

        if common_ancestor is None:
            return []

        # 构造回路：node1 -> ancestor -> node2 -> node1
        loop = []

        # node1到公共祖先
        node = node1
        while node != common_ancestor:
            loop.append(node)
            node = parent.get(node)
            if node is None:
                break

        loop.append(common_ancestor)

        # 公共祖先到node2（逆序）
        path_to_node2 = []
        node = node2
        while node != common_ancestor:
            path_to_node2.append(node)
            node = parent.get(node)
            if node is None:
                break

        # 反向添加
        loop.extend(reversed(path_to_node2))

        return loop

    def incidence_matrix(self) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        构造关联矩阵 - Construct Incidence Matrix

        关联矩阵 A[i,j] 定义为:
        - A[i,j] = +1  如果管道j流出节点i
        - A[i,j] = -1  如果管道j流入节点i
        - A[i,j] = 0   其他情况

        用于管网方程:
        A * Q = D  (连续性方程)
        其中 Q = 流量向量, D = 需水量向量

        Returns:
            (矩阵, 节点ID列表, 管道ID列表)
        """
        # 节点和管道排序（确保稳定性）
        node_ids = sorted(self.nodes.keys())
        pipe_ids = sorted(self.pipes.keys())

        n_nodes = len(node_ids)
        n_pipes = len(pipe_ids)

        # 初始化矩阵
        A = np.zeros((n_nodes, n_pipes), dtype=np.float64)

        # 创建索引映射
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        pipe_idx = {pid: j for j, pid in enumerate(pipe_ids)}

        # 填充矩阵
        for pipe_id, (from_node, to_node) in self.pipe_connections.items():
            j = pipe_idx[pipe_id]
            i_from = node_idx[from_node]
            i_to = node_idx[to_node]

            # 管道从from_node流出，流入to_node
            A[i_from, j] = +1.0  # 流出
            A[i_to, j] = -1.0    # 流入

        return A, node_ids, pipe_ids

    def loop_matrix(self) -> Tuple[np.ndarray, List[List[str]], List[str]]:
        """
        构造回路矩阵 - Construct Loop Matrix

        回路矩阵 B[i,j] 定义为:
        - B[i,j] = +1  如果管道j在回路i中，且方向一致
        - B[i,j] = -1  如果管道j在回路i中，但方向相反
        - B[i,j] = 0   如果管道j不在回路i中

        用于Hardy Cross法:
        Σ B[i,j] * h_j = 0  (每个回路的能量守恒)

        Returns:
            (矩阵, 回路节点列表, 管道ID列表)
        """
        loops = self.find_loops()
        pipe_ids = sorted(self.pipes.keys())

        n_loops = len(loops)
        n_pipes = len(pipe_ids)

        if n_loops == 0:
            return np.zeros((0, n_pipes)), [], pipe_ids

        # 初始化矩阵
        B = np.zeros((n_loops, n_pipes), dtype=np.float64)

        # 创建管道索引映射
        pipe_idx = {pid: j for j, pid in enumerate(pipe_ids)}

        # 填充矩阵
        for i, loop in enumerate(loops):
            # 找出回路中的所有管道
            for k in range(len(loop)):
                node1 = loop[k]
                node2 = loop[(k + 1) % len(loop)]

                # 查找连接这两个节点的管道
                pipe_id = self._find_pipe_between(node1, node2)

                if pipe_id is not None:
                    j = pipe_idx[pipe_id]

                    # 确定方向
                    from_node, to_node = self.pipe_connections[pipe_id]
                    if from_node == node1 and to_node == node2:
                        B[i, j] = +1.0
                    elif from_node == node2 and to_node == node1:
                        B[i, j] = -1.0

        return B, loops, pipe_ids

    def _find_pipe_between(self, node1: str, node2: str) -> Optional[str]:
        """
        查找连接两个节点的管道

        Args:
            node1: 节点1 ID
            node2: 节点2 ID

        Returns:
            管道ID，如果不存在则返回None
        """
        for pipe_id, (from_node, to_node) in self.pipe_connections.items():
            if (from_node == node1 and to_node == node2) or \
               (from_node == node2 and to_node == node1):
                return pipe_id

        return None

    def shortest_path(self, start_node: str, end_node: str) -> Optional[List[str]]:
        """
        使用BFS查找两个节点间的最短路径

        Args:
            start_node: 起始节点ID
            end_node: 终止节点ID

        Returns:
            最短路径节点列表，如果不存在则返回None
        """
        if start_node not in self.nodes or end_node not in self.nodes:
            raise ValueError("起始或终止节点不存在")

        if start_node == end_node:
            return [start_node]

        # BFS
        queue = deque([(start_node, [start_node])])
        visited = {start_node}

        while queue:
            node, path = queue.popleft()

            for neighbor in self.adjacency[node]:
                if neighbor in visited:
                    continue

                new_path = path + [neighbor]

                if neighbor == end_node:
                    return new_path

                visited.add(neighbor)
                queue.append((neighbor, new_path))

        return None  # 没有路径

    def is_connected(self) -> bool:
        """
        检查管网是否连通

        Returns:
            如果所有节点都连通返回True，否则False
        """
        if not self.nodes:
            return True

        # 从任意节点开始BFS
        start_node = next(iter(self.nodes))
        visited = set()
        queue = deque([start_node])

        while queue:
            node = queue.popleft()

            if node in visited:
                continue

            visited.add(node)

            for neighbor in self.adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

        return len(visited) == len(self.nodes)

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证管网拓扑有效性

        Returns:
            (是否有效, 错误/警告信息列表)
        """
        issues = []

        # 检查节点数
        if len(self.nodes) == 0:
            issues.append("警告: 管网中没有节点")

        # 检查管道数
        if len(self.pipes) == 0:
            issues.append("警告: 管网中没有管道")

        # 检查水源
        has_source = False
        for node in self.nodes.values():
            if isinstance(node, Reservoir):
                has_source = True
                break

        if not has_source:
            issues.append("警告: 管网中没有水源(Reservoir)")

        # 检查连通性
        if not self.is_connected():
            issues.append("错误: 管网不连通，存在孤立节点")

        # 检查孤立节点
        for node_id, node in self.nodes.items():
            if len(node.connected_pipes) == 0:
                issues.append(f"警告: 节点 {node_id} 没有连接任何管道")

        # 检查悬挂管道
        for pipe_id in self.pipes:
            from_node, to_node = self.pipe_connections[pipe_id]
            if from_node not in self.nodes or to_node not in self.nodes:
                issues.append(f"错误: 管道 {pipe_id} 连接到不存在的节点")

        is_valid = not any("错误" in issue for issue in issues)

        return is_valid, issues

    def summary(self) -> Dict:
        """
        生成管网拓扑摘要统计

        Returns:
            统计信息字典
        """
        # 节点统计
        num_junctions = sum(1 for n in self.nodes.values() if isinstance(n, Junction))
        num_reservoirs = sum(1 for n in self.nodes.values() if isinstance(n, Reservoir))
        num_tanks = sum(1 for n in self.nodes.values() if isinstance(n, Tank))

        # 回路和分支数
        loops = self.find_loops()
        n_loops = len(loops)
        n_pipes = len(self.pipes)
        n_nodes = len(self.nodes)

        # 基本回路数理论值 = n_pipes - n_nodes + 1 (对于连通图)
        expected_loops = max(0, n_pipes - n_nodes + 1) if self.is_connected() else 0

        return {
            'name': self.name,
            'num_nodes': n_nodes,
            'num_junctions': num_junctions,
            'num_reservoirs': num_reservoirs,
            'num_tanks': num_tanks,
            'num_pipes': n_pipes,
            'num_loops': n_loops,
            'expected_loops': expected_loops,
            'is_connected': self.is_connected(),
            'average_degree': 2 * n_pipes / n_nodes if n_nodes > 0 else 0
        }

    def __repr__(self) -> str:
        return (f"NetworkTopology(name='{self.name}', nodes={len(self.nodes)}, "
                f"pipes={len(self.pipes)}, loops={self.num_loops})")
