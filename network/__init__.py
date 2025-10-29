"""
HydroClaude Network Module

河网模拟模块 - Stage 3

提供河网拓扑结构、多河段耦合、内部边界条件等功能。

主要组件:
- topology: 网络拓扑数据结构（Node, Reach, RiverNetwork）
- nodes: 各类节点实现（Junction, Bifurcation, Reservoir）
- coupling: 河段耦合器
- solver: 网络求解器

作者: HydroClaude Team
日期: 2025-10-29
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "HydroClaude Team"

# 核心类导入
from .topology import Node, Reach, RiverNetwork
# from .nodes import JunctionNode, BifurcationNode, ReservoirNode  # Coming in Task 3.1.2
# from .coupling import ReachCoupler  # Coming in Task 3.2.1
# from .solver import NetworkSolver  # Coming in Task 3.2.3

__all__ = [
    'Node',
    'Reach',
    'RiverNetwork',
    # 'JunctionNode',  # Task 3.1.2
    # 'BifurcationNode',  # Task 3.1.2
    # 'ReservoirNode',  # Task 3.1.2
    # 'ReachCoupler',  # Task 3.2.1
    # 'NetworkSolver',  # Task 3.2.3
]
