#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
渠系网络测试案例

测试复杂拓扑结构：
1. 串联网络
2. 并联网络（分流-汇合）
3. 树状网络

作者: Claude
日期: 2025-10-23
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import numpy as np
import matplotlib.pyplot as plt
try:
    from solvers.canal_network_solver import CanalNetworkSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate


def test_series_network():
    """测试1: 串联网络（3段渠道）"""
    print("=" * 80)
    print("测试1: 串联网络")
    print("=" * 80)

    network = CanalNetworkSolver()

    # 节点
    network.add_node('Source', 'source', {'Q': 12.0})
    network.add_node('J1', 'internal')
    network.add_node('J2', 'internal')
    network.add_node('Sink', 'sink', {'h': 0.95})

    # 渠段
    network.add_canal_segment('C1', 'Source', 'J1',
                             length=600.0, nx=61, B=12.0, S0=0.0008, n=0.025)
    network.add_canal_segment('C2', 'J1', 'J2',
                             length=600.0, nx=61, B=12.0, S0=0.0008, n=0.025)
    network.add_canal_segment('C3', 'J2', 'Sink',
                             length=600.0, nx=61, B=12.0, S0=0.0008, n=0.025)

    # 求解
    network.initialize_network(h_initial=1.0, Q_initial=12.0)
    converged = network.solve_network_steady(max_iterations=30, verbose=True)
    network.print_network_summary()

    # 绘图
    state = network.get_network_state()
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 水深剖面
    ax = axes[0]
    x_offset = 0
    for seg_id in ['C1', 'C2', 'C3']:
        seg = state['segments'][seg_id]
        x_plot = seg['x'] + x_offset
        ax.plot(x_plot, seg['h'], linewidth=2, label=seg_id)
        x_offset += seg['x'][-1]

    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Series Network: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 流量剖面
    ax = axes[1]
    x_offset = 0
    for seg_id in ['C1', 'C2', 'C3']:
        seg = state['segments'][seg_id]
        x_plot = seg['x'] + x_offset
        ax.plot(x_plot, seg['Q'], linewidth=2, label=seg_id)
        x_offset += seg['x'][-1]

    ax.axhline(12.0, color='red', linestyle='--', alpha=0.5, label='Target')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_network_series.png', dpi=150)
    print(f"\n图表保存: test_network_series.png")

    return converged


def test_parallel_network():
    """测试2: 并联网络（分流-汇合）"""
    print("\n" + "=" * 80)
    print("测试2: 并联网络（分流-汇合）")
    print("=" * 80)
    print("""
    网络拓扑:
                  ┌─ C2 (B=8m) ─┐
    Source -> C1 ─┤              ├─ C4 -> Sink
                  └─ C3 (B=6m) ─┘
    """)

    network = CanalNetworkSolver()

    # 节点
    network.add_node('Source', 'source', {'Q': 15.0})
    network.add_node('Bifurcation', 'bifurcation')  # 分流点
    network.add_node('Junction', 'junction')  # 汇合点
    network.add_node('Sink', 'sink', {'h': 0.90})

    # 渠段
    network.add_canal_segment('C1', 'Source', 'Bifurcation',
                             length=400.0, nx=41, B=14.0, S0=0.001, n=0.025)
    network.add_canal_segment('C2', 'Bifurcation', 'Junction',
                             length=500.0, nx=51, B=10.0, S0=0.001, n=0.025)
    network.add_canal_segment('C3', 'Bifurcation', 'Junction',
                             length=500.0, nx=51, B=8.0, S0=0.001, n=0.025)
    network.add_canal_segment('C4', 'Junction', 'Sink',
                             length=400.0, nx=41, B=14.0, S0=0.001, n=0.025)

    # 求解
    network.initialize_network(h_initial=0.95, Q_initial=15.0)
    converged = network.solve_network_steady(max_iterations=50, verbose=True)
    network.print_network_summary()

    # 分析分流比
    state = network.get_network_state()
    Q_C2 = np.mean(state['segments']['C2']['Q'])
    Q_C3 = np.mean(state['segments']['C3']['Q'])
    Q_total = Q_C2 + Q_C3
    print(f"\n分流分析：")
    print(f"  C2 (B=10m): {Q_C2:.3f} m^3/s ({Q_C2/Q_total*100:.1f}%)")
    print(f"  C3 (B=8m):  {Q_C3:.3f} m^3/s ({Q_C3/Q_total*100:.1f}%)")
    print(f"  总流量:     {Q_total:.3f} m^3/s")

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # C1水深
    ax = axes[0, 0]
    seg = state['segments']['C1']
    ax.plot(seg['x'], seg['h'], 'b-', linewidth=2)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('C1 (Inlet Canal)')
    ax.grid(True, alpha=0.3)

    # C2和C3对比
    ax = axes[0, 1]
    seg2 = state['segments']['C2']
    seg3 = state['segments']['C3']
    ax.plot(seg2['x'], seg2['h'], 'g-', linewidth=2, label='C2 (B=10m)')
    ax.plot(seg3['x'], seg3['h'], 'r-', linewidth=2, label='C3 (B=8m)')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Parallel Canals')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # C4水深
    ax = axes[1, 0]
    seg = state['segments']['C4']
    ax.plot(seg['x'], seg['h'], 'purple', linewidth=2)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('C4 (Outlet Canal)')
    ax.grid(True, alpha=0.3)

    # 流量分布
    ax = axes[1, 1]
    canals = ['C1', 'C2', 'C3', 'C4']
    Q_means = [np.mean(state['segments'][c]['Q']) for c in canals]
    colors = ['blue', 'green', 'red', 'purple']
    bars = ax.bar(canals, Q_means, color=colors, alpha=0.7)
    ax.axhline(15.0, color='black', linestyle='--', alpha=0.5, label='Total')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Flow Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar, q in zip(bars, Q_means):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{q:.2f}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('test_network_parallel.png', dpi=150)
    print(f"图表保存: test_network_parallel.png")

    return converged


def test_tree_network():
    """测试3: 树状网络（多级分流）"""
    print("\n" + "=" * 80)
    print("测试3: 树状网络（多级分流）")
    print("=" * 80)
    print("""
    网络拓扑:
                    ┌─ C2 -> Sink1
    Source -> C1 -> J1┤
                    └─ C3 -> J2 ┬─ C4 -> Sink2
                                └─ C5 -> Sink3
    """)

    network = CanalNetworkSolver()

    # 节点
    network.add_node('Source', 'source', {'Q': 20.0})
    network.add_node('J1', 'bifurcation')
    network.add_node('J2', 'bifurcation')
    network.add_node('Sink1', 'sink', {'h': 0.85})
    network.add_node('Sink2', 'sink', {'h': 0.85})
    network.add_node('Sink3', 'sink', {'h': 0.85})

    # 渠段
    network.add_canal_segment('C1', 'Source', 'J1',
                             length=500.0, nx=51, B=15.0, S0=0.001, n=0.025)
    network.add_canal_segment('C2', 'J1', 'Sink1',
                             length=400.0, nx=41, B=8.0, S0=0.001, n=0.025)
    network.add_canal_segment('C3', 'J1', 'J2',
                             length=500.0, nx=51, B=12.0, S0=0.001, n=0.025)
    network.add_canal_segment('C4', 'J2', 'Sink2',
                             length=400.0, nx=41, B=7.0, S0=0.001, n=0.025)
    network.add_canal_segment('C5', 'J2', 'Sink3',
                             length=400.0, nx=41, B=6.0, S0=0.001, n=0.025)

    # 求解
    network.initialize_network(h_initial=0.90, Q_initial=20.0)
    converged = network.solve_network_steady(max_iterations=50, verbose=True)
    network.print_network_summary()

    # 流量分配分析
    state = network.get_network_state()
    print(f"\n流量分配分析：")
    print(f"  总入流 (C1): {np.mean(state['segments']['C1']['Q']):.3f} m^3/s")
    print(f"  第一级分流:")
    Q_C2 = np.mean(state['segments']['C2']['Q'])
    Q_C3 = np.mean(state['segments']['C3']['Q'])
    print(f"    -> C2 (B=8m):  {Q_C2:.3f} m^3/s -> Sink1")
    print(f"    -> C3 (B=12m): {Q_C3:.3f} m^3/s -> J2")
    print(f"  第二级分流:")
    Q_C4 = np.mean(state['segments']['C4']['Q'])
    Q_C5 = np.mean(state['segments']['C5']['Q'])
    print(f"    -> C4 (B=7m):  {Q_C4:.3f} m^3/s -> Sink2")
    print(f"    -> C5 (B=6m):  {Q_C5:.3f} m^3/s -> Sink3")
    print(f"  质量守恒检验: {Q_C2 + Q_C4 + Q_C5:.3f} m^3/s")

    # 绘图
    fig = plt.figure(figsize=(14, 10))

    # 使用GridSpec自定义布局
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # C1 (主干)
    ax1 = fig.add_subplot(gs[0, :])
    seg = state['segments']['C1']
    ax1.plot(seg['x'], seg['h'], 'b-', linewidth=3, label='C1 (Main)')
    ax1.set_ylabel('Water depth (m)')
    ax1.set_title('Main Canal (C1)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # C2 (第一分支)
    ax2 = fig.add_subplot(gs[1, 0])
    seg = state['segments']['C2']
    ax2.plot(seg['x'], seg['h'], 'g-', linewidth=2)
    ax2.set_ylabel('h (m)')
    ax2.set_title('C2 -> Sink1')
    ax2.grid(True, alpha=0.3)

    # C3 (第二主干)
    ax3 = fig.add_subplot(gs[1, 1:])
    seg = state['segments']['C3']
    ax3.plot(seg['x'], seg['h'], 'orange', linewidth=2.5, label='C3')
    ax3.set_ylabel('Water depth (m)')
    ax3.set_title('Secondary Main (C3)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # C4 (第二级分支1)
    ax4 = fig.add_subplot(gs[2, 0])
    seg = state['segments']['C4']
    ax4.plot(seg['x'], seg['h'], 'r-', linewidth=2)
    ax4.set_xlabel('Position (m)')
    ax4.set_ylabel('h (m)')
    ax4.set_title('C4 -> Sink2')
    ax4.grid(True, alpha=0.3)

    # C5 (第二级分支2)
    ax5 = fig.add_subplot(gs[2, 1])
    seg = state['segments']['C5']
    ax5.plot(seg['x'], seg['h'], 'purple', linewidth=2)
    ax5.set_xlabel('Position (m)')
    ax5.set_ylabel('h (m)')
    ax5.set_title('C5 -> Sink3')
    ax5.grid(True, alpha=0.3)

    # 流量分布柱状图
    ax6 = fig.add_subplot(gs[2, 2])
    canals = ['C1', 'C2', 'C3', 'C4', 'C5']
    Q_values = [np.mean(state['segments'][c]['Q']) for c in canals]
    colors = ['blue', 'green', 'orange', 'red', 'purple']
    ax6.barh(canals, Q_values, color=colors, alpha=0.7)
    ax6.set_xlabel('Q (m^3/s)')
    ax6.set_title('Flow Distribution')
    ax6.grid(True, alpha=0.3, axis='x')

    plt.savefig('test_network_tree.png', dpi=150)
    print(f"图表保存: test_network_tree.png")

    return converged


def main():
    """运行所有测试"""
    print("\n" + "" * 40)
    print("渠系网络综合测试")
    print("" * 40 + "\n")

    results = {}

    # 测试1
    try:
        results['series'] = test_series_network()
    except Exception as e:
        print(f" 串联网络测试失败: {e}")
        results['series'] = False

    # 测试2
    try:
        results['parallel'] = test_parallel_network()
    except Exception as e:
        print(f" 并联网络测试失败: {e}")
        results['parallel'] = False

    # 测试3
    try:
        results['tree'] = test_tree_network()
    except Exception as e:
        print(f" 树状网络测试失败: {e}")
        results['tree'] = False

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    test_names = {
        'series': '串联网络',
        'parallel': '并联网络',
        'tree': '树状网络'
    }

    for key, name in test_names.items():
        status = " PASS" if results.get(key, False) else " FAIL"
        print(f"  {name}: {status}")

    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
