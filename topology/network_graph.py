from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

class NodeType(Enum):
    """节点类型"""
    SOURCE = "source"
    SINK = "sink"
    JUNCTION = "junction"
    BRANCH = "branch"
    MERGE = "merge"
    COMPLEX = "complex"

@dataclass
class Node:
    """网络节点"""
    id: str
    node_type: NodeType
    elevation: float = 0.0
    demand: float = 0.0
    supply: float = 0.0

    incoming_edges: List[str] = field(default_factory=list)
    outgoing_edges: List[str] = field(default_factory=list)

    head: float = 0.0
    pressure: float = 0.0

    def degree(self) -> Tuple[int, int]:
        return len(self.incoming_edges), len(self.outgoing_edges)

@dataclass
class Edge:
    """网络边（管段/渠段）"""
    id: str
    start_node: str
    end_node: str
    component: any
    length: float

    flow: float = 0.0
    head_loss: float = 0.0

class NetworkTopology:
    """网络拓扑管理器"""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)

        self.is_tree = False
        self.is_loop = False
        self.loops: List[List[str]] = []

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        self.edges[edge.id] = edge

        if edge.start_node in self.nodes:
            self.nodes[edge.start_node].outgoing_edges.append(edge.id)
        if edge.end_node in self.nodes:
            self.nodes[edge.end_node].incoming_edges.append(edge.id)

        self.adjacency[edge.start_node].add(edge.end_node)

    def analyze_topology(self):
        print("\n" + "="*60)
        print("拓扑分析")
        print("="*60)

        sources = [n for n in self.nodes.values()
                  if n.node_type == NodeType.SOURCE or len(n.incoming_edges) == 0]
        sinks = [n for n in self.nodes.values()
                if n.node_type == NodeType.SINK or len(n.outgoing_edges) == 0]

        print(f"源节点数: {len(sources)}")
        print(f"汇节点数: {len(sinks)}")
        print(f"总节点数: {len(self.nodes)}")
        print(f"总管段数: {len(self.edges)}")

        self.loops = self._detect_loops()
        self.is_loop = len(self.loops) > 0

        if self.is_loop:
            print(f"✓ 环状网络: 检测到 {len(self.loops)} 个环路")
            for i, loop in enumerate(self.loops):
                print(f"  环路{i+1}: {' -> '.join(loop)}")
        else:
            print("✓ 树状网络: 无环路")
            self.is_tree = True

        node_stats = defaultdict(int)
        for node in self.nodes.values():
            in_deg, out_deg = node.degree()
            if in_deg == 0:
                node.node_type = NodeType.SOURCE
            elif out_deg == 0:
                node.node_type = NodeType.SINK
            elif in_deg == 1 and out_deg == 1:
                node.node_type = NodeType.JUNCTION
            elif in_deg == 1 and out_deg > 1:
                node.node_type = NodeType.BRANCH
            elif in_deg > 1 and out_deg == 1:
                node.node_type = NodeType.MERGE
            else:
                node.node_type = NodeType.COMPLEX

            node_stats[node.node_type.value] += 1

        print("\n节点分类:")
        for ntype, count in node_stats.items():
            print(f"  {ntype}: {count}")

        print("="*60 + "\n")

        return {
            'is_tree': self.is_tree,
            'is_loop': self.is_loop,
            'loops': self.loops,
            'sources': sources,
            'sinks': sinks
        }

    def _detect_loops(self) -> List[List[str]]:
        loops = []
        visited = set()
        path = []
        path_set = set()

        def dfs(node_id: str):
            if node_id in path_set:
                cycle_start = path.index(node_id)
                loop = path[cycle_start:] + [node_id]
                loops.append(loop)
                return

            if node_id in visited:
                return

            visited.add(node_id)
            path.append(node_id)
            path_set.add(node_id)

            for neighbor in self.adjacency.get(node_id, []):
                dfs(neighbor)

            path.pop()
            path_set.remove(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return loops

    def get_path(self, start: str, end: str) -> Optional[List[str]]:
        if start not in self.nodes or end not in self.nodes:
            return None

        queue = deque([(start, [start])])
        visited = {start}

        while queue:
            node, path = queue.popleft()

            if node == end:
                return path

            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None
