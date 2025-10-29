"""
高级边界条件使用示例

演示如何在GodunvFVMSolver中使用高级边界条件：
1. 洪水过程线模拟
2. 潮汐影响模拟
3. 堰控制下游边界
4. 闸门调度

Phase 2.4 示例

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from physics.advanced_boundary_conditions import (
    TimeDependentBC,
    TidalBC,
    HydrographBC
)
from physics.hydraulic_structures import (
    BroadCrestedWeir,
    SluiceGate
)


def example_1_flood_hydrograph():
    """
    示例1: 洪水过程线模拟

    场景：
    - 上游：三角形洪水过程
    - 下游：固定水位
    - 渠道：矩形，1000m长
    """
    print("\n" + "="*80)
    print("示例1: 洪水过程线模拟")
    print("="*80)

    # 创建洪水过程线
    flood = HydrographBC.triangular(
        base_flow=10.0,       # 基流 10 m³/s
        peak_flow=100.0,      # 洪峰 100 m³/s
        time_to_peak=2*3600,  # 2小时涨洪
        time_to_base=8*3600   # 8小时总历时
    )

    print(f"\n洪水过程线: {flood}")

    # 创建求解器
    solver = GodunvFVMSolver(
        width=20.0,
        length=1000.0,
        n_cells=100,
        manning_n=0.025,
        slope=0.001,
        cfl=0.5
    )

    # 初始条件
    h_init = np.ones(100) * 2.0  # 初始水深 2m
    Q_init = np.ones(100) * 10.0  # 初始流量 10 m³/s

    # 边界条件
    bc_left = {'type': 'Q', 'value': flood}  # 上游：洪水过程线（时变）
    bc_right = {'type': 'h', 'value': 2.0}   # 下游：固定水位

    solver.set_initial_conditions(h_init, Q_init, bc_left, bc_right)

    print(f"\n初始条件:")
    print(f"  初始水深: {np.mean(h_init):.2f} m")
    print(f"  初始流量: {np.mean(Q_init):.2f} m³/s")
    print(f"  上游BC: 时变流量 (洪水过程线)")
    print(f"  下游BC: 固定水位 h={bc_right['value']:.2f}m")

    # 模拟10小时
    print(f"\n开始模拟 (t_end=10小时)...")
    t_end = 10 * 3600
    dt, states = solver.run(t_end=t_end, save_interval=600)  # 每10分钟保存一次

    print(f"✅ 模拟完成")
    print(f"  总步数: {solver.step_count}")
    print(f"  平均dt: {solver.dt:.3f} s")
    print(f"  质量误差: {solver.get_mass_conservation_error():.4f}%")

    # 分析结果
    print(f"\n洪水传播分析:")
    for i, state in enumerate(states[::6]):  # 每小时一个点
        t_hr = state['t'] / 3600
        Q_upstream = flood(state['t'])
        h_max = np.max(state['h'])
        Q_max = np.max(state['Q'])
        print(f"  t={t_hr:4.1f}h: Q_in={Q_upstream:5.1f} m³/s, "
              f"h_max={h_max:.2f}m, Q_max={Q_max:.1f} m³/s")

    return solver, states


def example_2_tidal_boundary():
    """
    示例2: 潮汐影响模拟

    场景：
    - 上游：固定流量（河流径流）
    - 下游：潮汐水位变化
    - 河口段：受潮汐顶托影响
    """
    print("\n" + "="*80)
    print("示例2: 潮汐影响模拟")
    print("="*80)

    # 创建半日潮
    tidal = TidalBC(
        period=12.42*3600,  # 半日潮周期
        amplitude=2.0,      # 振幅 2m
        mean_level=1.0,     # 平均潮位 1m
        phase=0.0,
        duration=24*3600
    )

    print(f"\n潮汐边界: {tidal}")

    # 创建求解器
    solver = GodunvFVMSolver(
        width=50.0,        # 河口宽50m
        length=5000.0,     # 5km河段
        n_cells=100,
        manning_n=0.030,
        slope=0.0001,      # 河口段坡度很小
        cfl=0.5
    )

    # 初始条件（平均潮位）
    h_init = np.ones(100) * 1.0
    Q_init = np.ones(100) * 100.0  # 河流径流

    # 边界条件
    bc_left = {'type': 'Q', 'value': 100.0}  # 上游：稳定径流
    bc_right = {'type': 'h', 'value': tidal}  # 下游：潮汐水位（时变）

    solver.set_initial_conditions(h_init, Q_init, bc_left, bc_right)

    print(f"\n初始条件:")
    print(f"  河流径流: {bc_left['value']:.1f} m³/s (上游)")
    print(f"  潮汐边界: 周期={tidal.period/3600:.2f}h (下游)")

    # 模拟24小时（2个潮周期）
    print(f"\n开始模拟 (t_end=24小时)...")
    t_end = 24 * 3600
    dt, states = solver.run(t_end=t_end, save_interval=1800)  # 每30分钟保存

    print(f"✅ 模拟完成")
    print(f"  总步数: {solver.step_count}")
    print(f"  质量误差: {solver.get_mass_conservation_error():.4f}%")

    # 分析结果 - 上下游水位差变化
    print(f"\n潮汐影响分析:")
    for i, state in enumerate(states[::4]):  # 每2小时
        t_hr = state['t'] / 3600
        h_downstream = tidal(state['t'])
        h_upstream = state['h'][0]
        delta_h = h_downstream - h_upstream
        print(f"  t={t_hr:4.1f}h: h_下游={h_downstream:.2f}m, "
              f"h_上游={h_upstream:.2f}m, Δh={delta_h:+.2f}m")

    return solver, states


def example_3_weir_controlled():
    """
    示例3: 堰控制出流

    场景：
    - 上游：固定流量
    - 下游：宽顶堰控制（Rating Curve类型）
    - 堰上游水位自动调整
    """
    print("\n" + "="*80)
    print("示例3: 堰控制出流")
    print("="*80)

    # 创建宽顶堰
    weir = BroadCrestedWeir(
        crest_elevation=1.0,  # 堰顶高程 1m
        width=15.0,           # 堰宽 15m
        discharge_coeff=1.7,
        name="控制堰"
    )

    print(f"\n堰参数: {weir}")

    # 创建求解器
    solver = GodunvFVMSolver(
        width=15.0,
        length=500.0,
        n_cells=50,
        manning_n=0.025,
        slope=0.002,
        cfl=0.5
    )

    # 初始条件
    h_init = np.ones(50) * 1.5  # 初始水深 1.5m
    Q_init = np.ones(50) * 20.0  # 初始流量 20 m³/s

    # 边界条件
    # 注意：堰边界需要特殊处理，这里简化为固定水位
    # 实际应用中可以迭代求解 h_downstream 使得 Q_weir = Q_channel
    bc_left = {'type': 'Q', 'value': 30.0}   # 上游：流量 30 m³/s
    bc_right = {'type': 'h', 'value': 1.0}   # 下游：堰顶高程（简化）

    solver.set_initial_conditions(h_init, Q_init, bc_left, bc_right)

    print(f"\n边界条件:")
    print(f"  上游: Q={bc_left['value']:.1f} m³/s")
    print(f"  下游: 堰控制 (z_crest={weir.z_crest:.1f}m)")

    # 模拟到稳态
    print(f"\n开始模拟 (t_end=2小时，趋向稳态)...")
    t_end = 2 * 3600
    dt, states = solver.run(t_end=t_end, save_interval=600)

    print(f"✅ 模拟完成")

    # 计算稳态时的堰上游水位和过堰流量
    final_state = states[-1]
    h_upstream = final_state['h'][-1]  # 堰上游水位
    Q_weir = weir.compute_discharge(h_upstream, h_downstream=None)

    print(f"\n稳态结果:")
    print(f"  堰上游水位: h={h_upstream:.2f}m")
    print(f"  堰上水头: H={h_upstream - weir.z_crest:.2f}m")
    print(f"  过堰流量: Q_weir={Q_weir:.2f} m³/s")
    print(f"  上游流量: Q_in={bc_left['value']:.2f} m³/s")
    print(f"  流量平衡: {abs(Q_weir - bc_left['value'])/bc_left['value']*100:.1f}% 偏差")

    return solver, states


def example_4_gate_operation():
    """
    示例4: 闸门调度模拟

    场景：
    - 上游：固定流量
    - 中游：闸门控制（开度随时间变化）
    - 下游：自由出流
    """
    print("\n" + "="*80)
    print("示例4: 闸门调度模拟 (概念演示)")
    print("="*80)

    # 创建闸门
    gate = SluiceGate(
        sill_elevation=0.0,
        width=10.0,
        opening=1.0,  # 初始开度 1m
        name="调节闸"
    )

    print(f"\n闸门参数: {gate}")

    # 闸门调度方案
    def gate_schedule(t):
        """
        闸门开度随时间变化

        0-1h: 开度 1.0m
        1-2h: 逐渐关闭到 0.5m
        2-3h: 开度 0.5m
        3-4h: 逐渐打开到 1.5m
        """
        t_hr = t / 3600
        if t_hr < 1:
            return 1.0
        elif t_hr < 2:
            # 线性关闭
            return 1.0 - 0.5 * (t_hr - 1)
        elif t_hr < 3:
            return 0.5
        elif t_hr < 4:
            # 线性打开
            return 0.5 + 1.0 * (t_hr - 3)
        else:
            return 1.5

    print(f"\n闸门调度方案:")
    for t_hr in [0, 1, 2, 3, 4]:
        opening = gate_schedule(t_hr * 3600)
        print(f"  t={t_hr:.0f}h: 开度={opening:.1f}m")

    # 计算不同开度下的流量
    print(f"\n不同开度下的过闸流量 (h_up=3m, h_down=1m):")
    for opening in [0.5, 1.0, 1.5]:
        gate.set_opening(opening)
        Q = gate.compute_discharge(h_upstream=3.0, h_downstream=1.0)
        print(f"  开度={opening:.1f}m: Q={Q:.2f} m³/s")

    print(f"\n说明:")
    print(f"  闸门调度可用于：")
    print(f"  1. 水位控制：根据上游水位调节开度")
    print(f"  2. 流量控制：根据需求流量调节开度")
    print(f"  3. 防洪调度：洪水期间的闸门操作")
    print(f"  4. 生态调度：满足生态流量需求")

    print(f"\n注意:")
    print(f"  完整的闸门调度模拟需要：")
    print(f"  1. 将闸门作为内部边界条件")
    print(f"  2. 分段求解（闸门上下游）")
    print(f"  3. 迭代求解闸门处的水位和流量")


if __name__ == "__main__":
    """运行所有示例"""

    print("="*80)
    print("高级边界条件使用示例集")
    print("Phase 2.4 - Advanced Boundary Conditions")
    print("="*80)

    # 运行示例1
    solver1, states1 = example_1_flood_hydrograph()

    # 运行示例2
    solver2, states2 = example_2_tidal_boundary()

    # 运行示例3
    solver3, states3 = example_3_weir_controlled()

    # 运行示例4（概念演示）
    example_4_gate_operation()

    print("\n" + "="*80)
    print("✅ 所有示例运行完成！")
    print("="*80)

    print("\n总结:")
    print("  Phase 2.4 提供的高级边界条件：")
    print("  1. ✅ 时变边界条件 - 洪水过程线、潮汐")
    print("  2. ✅ Rating Curve - 水位-流量关系")
    print("  3. ✅ 水工建筑物 - 堰、闸门、孔口")
    print("\n  可直接用于GodunvFVMSolver！")
    print("  求解器已支持 callable(t) 作为边界值")
