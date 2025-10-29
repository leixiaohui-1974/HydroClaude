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
from .nodes import (
    JunctionNode, BifurcationNode, ReservoirNode, BoundaryNode,
    create_junction, create_bifurcation, create_reservoir,
    create_inflow_boundary, create_outflow_boundary
)
from .validation import (
    NetworkValidator, NetworkVisualizer,
    validate_network, visualize_network
)
from .coupling import (
    ReachCoupler, JunctionCoupler, BifurcationCoupler, StructureCoupler,
    create_reach_coupler, create_junction_coupler, create_bifurcation_coupler,
    create_structure_coupler
)
from .structures import (
    InternalStructure, InternalWeir, InternalGate, InternalOrifice,
    create_internal_weir, create_internal_gate, create_internal_orifice
)
from .solver import NetworkSolver, create_network_solver, solve_network

__all__ = [
    # 基础类
    'Node',
    'Reach',
    'RiverNetwork',
    # 节点类型
    'JunctionNode',
    'BifurcationNode',
    'ReservoirNode',
    'BoundaryNode',
    # 便捷函数
    'create_junction',
    'create_bifurcation',
    'create_reservoir',
    'create_inflow_boundary',
    'create_outflow_boundary',
    # 验证和可视化
    'NetworkValidator',
    'NetworkVisualizer',
    'validate_network',
    'visualize_network',
    # 耦合器
    'ReachCoupler',
    'JunctionCoupler',
    'BifurcationCoupler',
    'StructureCoupler',
    'create_reach_coupler',
    'create_junction_coupler',
    'create_bifurcation_coupler',
    'create_structure_coupler',
    # 内部建筑物
    'InternalStructure',
    'InternalWeir',
    'InternalGate',
    'InternalOrifice',
    'create_internal_weir',
    'create_internal_gate',
    'create_internal_orifice',
    # 求解器
    'NetworkSolver',
    'create_network_solver',
    'solve_network',
]
