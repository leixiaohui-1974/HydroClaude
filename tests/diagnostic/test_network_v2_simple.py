#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试网络求解器V2 - Y-split简单测试

测试目标：验证守恒改进效果
- Phase 1问题：质量误差9-22%
- 目标：质量误差<1%

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from solvers.godunov_fvm_network_v2 import GodunvFVMNetworkV2, NodeType
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

import numpy as np

print("=" * 80)
print("网络求解器V2测试 - Y-split场景")
print("=" * 80)

# 创建网络
network = GodunvFVMNetworkV2(relaxation=0.5)

# 节点
n1 = network.add_node('N1', NodeType.SOURCE, x=0, y=0, bc_value=50.0)
n2 = network.add_node('N2', NodeType.BIFURCATION, x=1000, y=0)
n3 = network.add_node('N3', NodeType.SINK, x=2000, y=500, bc_value=1.0)
n4 = network.add_node('N4', NodeType.SINK, x=2000, y=-500, bc_value=1.0)

# 边（渠道）
e1 = network.add_edge('E1', 'N1', 'N2', width=10.0, length=1000.0, n_cells=50,
                      manning_n=0.025, slope=0.001)
e2 = network.add_edge('E2', 'N2', 'N3', width=10.0, length=1000.0, n_cells=50,
                      manning_n=0.025, slope=0.001)
e3 = network.add_edge('E3', 'N2', 'N4', width=10.0, length=1000.0, n_cells=50,
                      manning_n=0.025, slope=0.001)

# 初始化
network.initialize_network(h_default=2.0, Q_default=50.0)

print("\n网络拓扑：")
print("  N1(SOURCE) --E1--> N2(BIFURCATION) --E2--> N3(SINK)")
print("                                      \\--E3--> N4(SINK)")
print(f"\n初始总质量: {network.initial_mass:.2f} m^3")

# 运行
print("\n推进500步...")
for i in range(500):
    network.step()
    
    if (i + 1) % 100 == 0:
        state = network.get_network_state()
        mass_error = state['network_mass_error']
        print(f"  步数 {i+1:4d}, t={network.t:6.1f}s, 质量误差={mass_error:+.4f}%")

# 最终结果
print("\n" + "=" * 80)
print("最终结果")
print("=" * 80)

state = network.get_network_state()
mass_error = state['network_mass_error']

print(f"\n网络质量守恒：")
print(f"  质量误差: {mass_error:.4f}%")
print(f"  状态: {' 优秀' if abs(mass_error) < 1.0 else '️ 需改进'}")

print(f"\n节点流量平衡：")
for node_id in ['N1', 'N2', 'N3', 'N4']:
    balance = network.get_node_mass_balance(node_id)
    print(f"  {node_id}: Q_in={balance['Q_in']:6.2f}, Q_out={balance['Q_out']:6.2f}, "
          f"误差={balance['relative_error']:.2f}%")

print(f"\n边质量守恒：")
for edge_id in ['E1', 'E2', 'E3']:
    edge_error = state['edges'][edge_id]['mass_error']
    print(f"  {edge_id}: {edge_error:.4f}%")

# 综合评价
print("\n" + "=" * 80)
print("综合评价")
print("=" * 80)

if abs(mass_error) < 1.0:
    print("\n 测试通过！")
    print(f"   质量误差 {abs(mass_error):.4f}% < 1%目标")
    print("   V2改进成功！")
else:
    print(f"\n️ 测试未达标")
    print(f"   质量误差 {abs(mass_error):.4f}% > 1%目标")
    print("   需要进一步调试")

print("\n" + "=" * 80)
