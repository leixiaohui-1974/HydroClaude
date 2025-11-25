#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
所有水工结构类型的综合测试

测试内容：
1. 宽顶堰 (BroadCrestedWeir)
2. 薄壁堰/溢洪道 (Spillway)
3. 跌水 (Drop)
4. 渐变段 (Transition)
5. 孔口 (Orifice)

所有测试使用静水重构求解器验证精度

作者: Claude
日期: 2025-10-23
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import numpy as np
import matplotlib.pyplot as plt
try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import (
    SluiceGate, BroadCrestedWeir, Orifice,
    Spillway, Transition, Drop
)


def test_broad_crested_weir():
    """测试1: 宽顶堰"""
    print("=" * 80)
    print("测试1: 宽顶堰 (Broad-Crested Weir)")
    print("=" * 80)

    # 渠道参数
    L = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.0005
    n = 0.025

    # 创建宽顶堰（位于渠道中点）
    weir = BroadCrestedWeir(
        position=500.0,
        width=B,
        crest_height=0.5,  # 堰顶高程0.5m
        Cd=0.848
    )

    print(f"\n宽顶堰配置：")
    print(f"  位置: {weir.position} m")
    print(f"  堰顶高程: {weir.crest_height} m")
    print(f"  流量系数: {weir.Cd}")

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(500.0, weir)]
    )

    # 目标流量
    Q_target = 8.0  # m^3/s

    # 下游边界（均匀流水深）
    def compute_uniform_h(Q, B, S0, n):
        from scipy.optimize import fsolve
        def residual(h):
            if h <= 0: return 1e10
            A = B * h
            R = A / (B + 2*h)
            Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
            return Q - Q_calc
        return fsolve(residual, 1.0)[0]

    h_downstream = compute_uniform_h(Q_target, B, S0, n)
    print(f"\n边界条件：")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    # 求解稳态
    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        verbose=True
    )

    # 分析结果
    print(f"\n堰流分析：")
    weir_idx = np.argmin(np.abs(solver.x - weir.position))
    h_up = solver.h[weir_idx - 1]
    h_down = solver.h[weir_idx + 1]
    Q_weir, flow_type = weir.calculate_discharge(h_up, h_down)
    H_weir = h_up - weir.crest_height

    print(f"  上游水深: {h_up:.3f} m")
    print(f"  下游水深: {h_down:.3f} m")
    print(f"  堰顶水头: {H_weir:.3f} m")
    print(f"  堰流量: {Q_weir:.3f} m^3/s")
    print(f"  流态: {flow_type}")
    print(f"  流量误差: {abs(Q_weir - Q_target)/Q_target*100:.2f}%")

    # 绘图
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 水深剖面
    ax = axes[0]
    ax.plot(solver.x, solver.h, 'b-', linewidth=2, label='Water depth')
    ax.axhline(weir.crest_height, color='gray', linestyle='--',
               alpha=0.5, label='Weir crest')
    ax.axvline(weir.position, color='red', linestyle='--',
               alpha=0.5, label='Weir position')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Broad-Crested Weir: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 流量分布
    ax = axes[1]
    Q_array = solver.get_Q()
    ax.plot(solver.x, Q_array, 'g-', linewidth=2, label='Discharge')
    ax.axhline(Q_target, color='red', linestyle='--', alpha=0.5, label='Target')
    ax.axvline(weir.position, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_broad_crested_weir.png', dpi=150)
    print(f"\n  图表保存: test_broad_crested_weir.png")

    return result


def test_spillway():
    """测试2: 溢洪道 (WES标准)"""
    print("\n" + "=" * 80)
    print("测试2: 溢洪道 (Spillway - WES Standard)")
    print("=" * 80)

    L = 1000.0
    nx = 101
    B = 15.0  # 更宽的溢洪道
    S0 = 0.001
    n = 0.025

    # WES标准溢洪道
    spillway = Spillway(
        position=500.0,
        width=B,
        crest_elevation=1.0,  # 堰顶高程1.0m
        spillway_type='wes',
        Cd=2.1
    )

    print(f"\n溢洪道配置：")
    print(f"  类型: WES Standard")
    print(f"  堰顶高程: {spillway.crest_elevation} m")
    print(f"  流量系数: {spillway.Cd}")

    solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(500.0, spillway)]
    )

    Q_target = 15.0

    # 下游水深
    from scipy.optimize import fsolve
    def compute_uniform_h(Q, B, S0, n):
        def residual(h):
            if h <= 0: return 1e10
            A = B * h
            R = A / (B + 2*h)
            Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
            return Q - Q_calc
        return fsolve(residual, 1.0)[0]

    h_downstream = compute_uniform_h(Q_target, B, S0, n)

    print(f"\n边界条件：")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        verbose=True
    )

    # 分析
    spillway_idx = np.argmin(np.abs(solver.x - spillway.position))
    h_up = solver.h[spillway_idx - 1]
    h_down = solver.h[spillway_idx + 1]
    Q_spillway, flow_type = spillway.calculate_discharge(h_up, h_down)
    H = h_up - spillway.crest_elevation

    print(f"\n溢洪道流态：")
    print(f"  上游水深: {h_up:.3f} m")
    print(f"  堰顶水头: {H:.3f} m")
    print(f"  溢流量: {Q_spillway:.3f} m^3/s")
    print(f"  流态: {flow_type}")
    print(f"  误差: {abs(Q_spillway - Q_target)/Q_target*100:.2f}%")

    # 绘图
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    ax = axes[0]
    ax.plot(solver.x, solver.h, 'b-', linewidth=2, label='Water depth')
    ax.axhline(spillway.crest_elevation, color='gray', linestyle='--',
               alpha=0.5, label='Spillway crest')
    ax.axvline(spillway.position, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('WES Spillway: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    Q_array = solver.get_Q()
    ax.plot(solver.x, Q_array, 'g-', linewidth=2)
    ax.axhline(Q_target, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_spillway.png', dpi=150)
    print(f"  图表保存: test_spillway.png")

    return result


def test_drop():
    """测试3: 跌水"""
    print("\n" + "=" * 80)
    print("测试3: 跌水 (Drop)")
    print("=" * 80)

    L = 800.0
    nx = 101
    B = 10.0
    S0 = 0.002
    n = 0.025

    # 跌水结构
    drop = Drop(
        position=400.0,
        width=B,
        drop_height=0.5,  # 跌水高度0.5m
        Cd=0.6
    )

    print(f"\n跌水配置：")
    print(f"  位置: {drop.position} m")
    print(f"  跌水高度: {drop.drop_height} m")
    print(f"  流量系数: {drop.Cd}")

    solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(400.0, drop)]
    )

    Q_target = 6.0

    from scipy.optimize import fsolve
    def compute_uniform_h(Q, B, S0, n):
        def residual(h):
            if h <= 0: return 1e10
            A = B * h
            R = A / (B + 2*h)
            Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
            return Q - Q_calc
        return fsolve(residual, 1.0)[0]

    h_downstream = compute_uniform_h(Q_target, B, S0, n)

    print(f"\n边界条件：")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        verbose=True
    )

    # 分析
    drop_idx = np.argmin(np.abs(solver.x - drop.position))
    h_up = solver.h[drop_idx - 1]
    h_down = solver.h[drop_idx + 1]
    Q_drop, flow_type = drop.calculate_discharge(h_up, h_down)

    print(f"\n跌水流态：")
    print(f"  上游水深: {h_up:.3f} m")
    print(f"  下游水深: {h_down:.3f} m")
    print(f"  跌水流量: {Q_drop:.3f} m^3/s")
    print(f"  误差: {abs(Q_drop - Q_target)/Q_target*100:.2f}%")

    # 绘图
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    ax = axes[0]
    ax.plot(solver.x, solver.h, 'b-', linewidth=2, label='Water depth')
    ax.axvline(drop.position, color='red', linestyle='--',
               alpha=0.5, label='Drop position')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Drop Structure: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    Q_array = solver.get_Q()
    ax.plot(solver.x, Q_array, 'g-', linewidth=2)
    ax.axhline(Q_target, color='red', linestyle='--', alpha=0.5)
    ax.axvline(drop.position, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_drop.png', dpi=150)
    print(f"  图表保存: test_drop.png")

    return result


def test_orifice():
    """测试4: 孔口"""
    print("\n" + "=" * 80)
    print("测试4: 孔口 (Orifice)")
    print("=" * 80)

    L = 600.0
    nx = 101
    B = 8.0
    S0 = 0.001
    n = 0.025

    # 孔口
    orifice = Orifice(
        position=300.0,
        width=B,
        height=0.6,  # 孔口高度0.6m
        bottom_elevation=0.2,  # 孔口底部高程0.2m
        Cd=0.61
    )

    print(f"\n孔口配置：")
    print(f"  位置: {orifice.position} m")
    print(f"  孔口尺寸: {orifice.width}m x {orifice.height}m")
    print(f"  底部高程: {orifice.bottom_elevation} m")
    print(f"  流量系数: {orifice.Cd}")

    solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(300.0, orifice)]
    )

    Q_target = 4.0

    from scipy.optimize import fsolve
    def compute_uniform_h(Q, B, S0, n):
        def residual(h):
            if h <= 0: return 1e10
            A = B * h
            R = A / (B + 2*h)
            Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
            return Q - Q_calc
        return fsolve(residual, 1.0)[0]

    h_downstream = compute_uniform_h(Q_target, B, S0, n)

    print(f"\n边界条件：")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        verbose=True
    )

    # 分析
    orifice_idx = np.argmin(np.abs(solver.x - orifice.position))
    h_up = solver.h[orifice_idx - 1]
    h_down = solver.h[orifice_idx + 1]
    Q_orifice, flow_type = orifice.calculate_discharge(h_up, h_down)

    print(f"\n孔口流态：")
    print(f"  上游水深: {h_up:.3f} m")
    print(f"  下游水深: {h_down:.3f} m")
    print(f"  孔口流量: {Q_orifice:.3f} m^3/s")
    print(f"  流态: {flow_type}")
    print(f"  误差: {abs(Q_orifice - Q_target)/Q_target*100:.2f}%")

    # 绘图
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    ax = axes[0]
    ax.plot(solver.x, solver.h, 'b-', linewidth=2, label='Water depth')
    ax.axhline(orifice.bottom_elevation, color='gray', linestyle=':',
               alpha=0.5, label='Orifice bottom')
    ax.axhline(orifice.bottom_elevation + orifice.height, color='gray',
               linestyle=':', alpha=0.5, label='Orifice top')
    ax.axvline(orifice.position, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Orifice: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    Q_array = solver.get_Q()
    ax.plot(solver.x, Q_array, 'g-', linewidth=2)
    ax.axhline(Q_target, color='red', linestyle='--', alpha=0.5)
    ax.axvline(orifice.position, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_orifice.png', dpi=150)
    print(f"  图表保存: test_orifice.png")

    return result


def test_multiple_structures():
    """测试5: 多种结构组合"""
    print("\n" + "=" * 80)
    print("测试5: 多种结构组合")
    print("=" * 80)

    L = 2000.0
    nx = 201
    B = 12.0
    S0 = 0.0008
    n = 0.025

    # 创建多个不同类型的结构
    gate = SluiceGate(position=400.0, width=B, opening=0.8, Cd=0.6)
    weir = BroadCrestedWeir(position=800.0, width=B, crest_height=0.4, Cd=0.848)
    drop = Drop(position=1200.0, width=B, drop_height=0.3, Cd=0.6)
    spillway = Spillway(position=1600.0, width=B, crest_elevation=0.5,
                       spillway_type='wes', Cd=2.1)

    print(f"\n结构配置：")
    print(f"  1. 闸门 @ {gate.position}m, 开度={gate.get_opening():.2f}m")
    print(f"  2. 宽顶堰 @ {weir.position}m, 堰顶={weir.crest_height}m")
    print(f"  3. 跌水 @ {drop.position}m, 高度={drop.drop_height}m")
    print(f"  4. 溢洪道 @ {spillway.position}m, 堰顶={spillway.crest_elevation}m")

    solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[
            (400.0, gate),
            (800.0, weir),
            (1200.0, drop),
            (1600.0, spillway)
        ]
    )

    Q_target = 10.0

    from scipy.optimize import fsolve
    def compute_uniform_h(Q, B, S0, n):
        def residual(h):
            if h <= 0: return 1e10
            A = B * h
            R = A / (B + 2*h)
            Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
            return Q - Q_calc
        return fsolve(residual, 1.5)[0]

    h_downstream = compute_uniform_h(Q_target, B, S0, n)

    print(f"\n边界条件：")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        max_iterations=8000,
        verbose=True
    )

    # 分析每个结构
    print(f"\n各结构流态分析：")

    structures = [(gate, "闸门"), (weir, "宽顶堰"), (drop, "跌水"), (spillway, "溢洪道")]
    for struct, name in structures:
        idx = np.argmin(np.abs(solver.x - struct.position))
        h_up = solver.h[idx - 1]
        h_down = solver.h[idx + 1]
        Q_struct, flow_type = struct.calculate_discharge(h_up, h_down)
        error = abs(Q_struct - Q_target) / Q_target * 100
        print(f"  {name} @ {struct.position}m:")
        print(f"    上游水深: {h_up:.3f}m, 下游水深: {h_down:.3f}m")
        print(f"    流量: {Q_struct:.3f} m^3/s, 误差: {error:.2f}%")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # 水深剖面
    ax = axes[0]
    ax.plot(solver.x, solver.h, 'b-', linewidth=2, label='Water depth')
    for struct, name in structures:
        ax.axvline(struct.position, color='red', linestyle='--', alpha=0.3)
        ax.text(struct.position, ax.get_ylim()[1]*0.9, name,
                ha='center', fontsize=9)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Multiple Structures: Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 流量分布
    ax = axes[1]
    Q_array = solver.get_Q()
    ax.plot(solver.x, Q_array, 'g-', linewidth=2)
    ax.axhline(Q_target, color='red', linestyle='--', alpha=0.5, label='Target')
    for struct, _ in structures:
        ax.axvline(struct.position, color='red', linestyle='--', alpha=0.3)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Discharge Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 比能
    ax = axes[2]
    u = Q_array / (B * solver.h)
    E = solver.h + u**2 / (2 * 9.81)
    ax.plot(solver.x, E, 'purple', linewidth=2, label='Specific energy')
    for struct, _ in structures:
        ax.axvline(struct.position, color='red', linestyle='--', alpha=0.3)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Specific energy (m)')
    ax.set_title('Specific Energy Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_multiple_structures.png', dpi=150)
    print(f"\n  图表保存: test_multiple_structures.png")

    return result


def main():
    """运行所有测试"""
    print("\n" + "" * 40)
    print("水工结构综合测试 - 静水重构求解器")
    print("" * 40 + "\n")

    results = {}

    try:
        results['weir'] = test_broad_crested_weir()
    except Exception as e:
        print(f" 宽顶堰测试失败: {e}")

    try:
        results['spillway'] = test_spillway()
    except Exception as e:
        print(f" 溢洪道测试失败: {e}")

    try:
        results['drop'] = test_drop()
    except Exception as e:
        print(f" 跌水测试失败: {e}")

    try:
        results['orifice'] = test_orifice()
    except Exception as e:
        print(f" 孔口测试失败: {e}")

    try:
        results['multiple'] = test_multiple_structures()
    except Exception as e:
        print(f" 多结构测试失败: {e}")

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    test_names = {
        'weir': '宽顶堰',
        'spillway': '溢洪道',
        'drop': '跌水',
        'orifice': '孔口',
        'multiple': '多结构组合'
    }

    for key, name in test_names.items():
        if key in results:
            res = results[key]
            status = " PASS" if res['converged'] else " 部分收敛"
            print(f"  {name}: {status}, 流量误差={res['Q_error_percent']:.2f}%")
        else:
            print(f"  {name}:  FAIL")

    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
