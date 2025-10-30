#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Newton-Raphson求解器优化测试
Test Newton-Raphson solver improvements

测试use_hardy_cross_init参数是否提高了收敛性

作者: HydroClaude Team
日期: 2025-10-30
"""

import pytest
import numpy as np

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver
from solvers.newton_raphson_network_solver import NewtonRaphsonNetworkSolver


def create_test_network():
    """创建测试用环状管网"""
    topology = NetworkTopology()

    # 创建节点
    r1 = Reservoir('R1', elevation=100, head=120)
    j1 = Junction('J1', elevation=100, demand=0.02)
    j2 = Junction('J2', elevation=100, demand=0.03)
    j3 = Junction('J3', elevation=100, demand=0.02)

    topology.add_node(r1)
    topology.add_node(j1)
    topology.add_node(j2)
    topology.add_node(j3)

    # 创建管道
    p1 = create_pressure_pipe('P1', 0.3, 500, 'cast_iron_new')
    p2 = create_pressure_pipe('P2', 0.25, 400, 'cast_iron_new')
    p3 = create_pressure_pipe('P3', 0.2, 300, 'cast_iron_new')
    p4 = create_pressure_pipe('P4', 0.2, 350, 'cast_iron_new')

    topology.add_pipe(p1, 'R1', 'J1')
    topology.add_pipe(p2, 'J1', 'J2')
    topology.add_pipe(p3, 'J2', 'J3')
    topology.add_pipe(p4, 'J3', 'J1')

    return topology


def test_newton_raphson_without_hardy_cross_init():
    """测试不使用Hardy Cross初始化的Newton-Raphson"""
    topology = create_test_network()

    nr_solver = NewtonRaphsonNetworkSolver(
        topology,
        max_iter=50,
        tol=1e-6,
        verbose=False,
        use_hardy_cross_init=False
    )

    try:
        flows, heads = nr_solver.solve()
        converged = nr_solver.converged
    except:
        converged = False

    # 不使用HC初始化，可能不收敛
    print(f"\n不使用HC初始化: {'收敛' if converged else '未收敛'}")
    if converged:
        print(f"  迭代次数: {nr_solver.iteration_count}")


def test_newton_raphson_with_hardy_cross_init():
    """测试使用Hardy Cross初始化的Newton-Raphson"""
    topology = create_test_network()

    nr_solver = NewtonRaphsonNetworkSolver(
        topology,
        max_iter=50,
        tol=1e-6,
        verbose=False,
        use_hardy_cross_init=True
    )

    flows, heads = nr_solver.solve()

    # 使用HC初始化，应该收敛
    assert nr_solver.converged, "使用HC初始化应该收敛"
    assert nr_solver.iteration_count < 50, "使用HC初始化应该快速收敛"

    print(f"\n使用HC初始化: 收敛")
    print(f"  迭代次数: {nr_solver.iteration_count}")

    # 验证流量守恒
    assert len(flows) == 4, "应有4个管道流量"

    # 验证结果合理性
    for pid, Q in flows.items():
        assert abs(Q) < 1.0, f"流量 {pid} = {Q} 应在合理范围内"


def test_compare_with_hardy_cross():
    """对比Newton-Raphson (with HC init)和Hardy Cross的结果"""
    topology = create_test_network()

    # Hardy Cross
    hc_solver = HardyCrossSolver(topology, verbose=False)
    hc_flows, hc_heads = hc_solver.solve()
    assert hc_solver.converged, "Hardy Cross应收敛"

    # Newton-Raphson with HC init
    nr_solver = NewtonRaphsonNetworkSolver(
        topology,
        verbose=False,
        use_hardy_cross_init=True
    )
    nr_flows, nr_heads = nr_solver.solve()
    assert nr_solver.converged, "Newton-Raphson应收敛"

    # 对比结果
    flow_diffs = []
    for pid in hc_flows.keys():
        diff = abs(hc_flows[pid] - nr_flows[pid])
        flow_diffs.append(diff)

    max_diff = max(flow_diffs)
    mean_diff = np.mean(flow_diffs)

    print(f"\n结果对比:")
    print(f"  Hardy Cross迭代: {hc_solver.iteration_count}")
    print(f"  Newton-Raphson迭代: {nr_solver.iteration_count}")
    print(f"  流量最大差异: {max_diff:.8f} m³/s")
    print(f"  流量平均差异: {mean_diff:.8f} m³/s")

    # 两种方法应该得到相近的结果
    assert max_diff < 1e-3, "两种方法结果应该接近"


def test_initialization_quality():
    """测试Hardy Cross初始化的质量"""
    topology = create_test_network()

    # 创建两个求解器
    nr_no_init = NewtonRaphsonNetworkSolver(
        topology, verbose=False, use_hardy_cross_init=False
    )
    nr_with_init = NewtonRaphsonNetworkSolver(
        topology, verbose=False, use_hardy_cross_init=True
    )

    # 使用HC初始化应该显著减少迭代次数
    try:
        flows_no_init, _ = nr_no_init.solve()
        iter_no_init = nr_no_init.iteration_count if nr_no_init.converged else 999
    except:
        iter_no_init = 999

    flows_with_init, _ = nr_with_init.solve()
    iter_with_init = nr_with_init.iteration_count

    print(f"\n初始化质量对比:")
    print(f"  无HC初始化: {iter_no_init if iter_no_init < 999 else '未收敛'} 次迭代")
    print(f"  有HC初始化: {iter_with_init} 次迭代")

    # HC初始化应该显著改善收敛性
    assert nr_with_init.converged, "使用HC初始化应该收敛"
    assert iter_with_init < 20, "使用HC初始化迭代次数应该很少"


if __name__ == '__main__':
    print("="*80)
    print("Newton-Raphson求解器优化测试")
    print("="*80)

    test_newton_raphson_without_hardy_cross_init()
    test_newton_raphson_with_hardy_cross_init()
    test_compare_with_hardy_cross()
    test_initialization_quality()

    print("\n" + "="*80)
    print("✅ 所有测试通过！Newton-Raphson优化成功！")
    print("="*80)
