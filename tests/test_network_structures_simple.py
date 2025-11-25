"""
简单测试内部水工建筑物（不使用pytest）

验证堰、闸等内部建筑物的耦合功能。

Stage 3 - Task 3.3.2 测试

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network.topology import RiverNetwork, Node, Reach
from network.nodes import create_inflow_boundary, create_outflow_boundary
from network.structures import InternalWeir, InternalGate, InternalOrifice
from network.coupling import StructureCoupler
from network.solver import NetworkSolver
from physics.hydraulic_structures import BroadCrestedWeir, SluiceGate, Orifice
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def create_test_solver(length=100.0, width=10.0, h_init=2.0, Q_init=20.0, slope=0.001):
    """创建测试求解器"""
    n_cells = max(10, int(length / 10))
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.025,
        slope=slope
    )

    h = np.ones(n_cells) * h_init
    Q = np.ones(n_cells) * Q_init

    solver.initialize(
        h, Q,
        {'type': 'Q', 'value': Q_init},
        {'type': 'h', 'value': h_init}
    )

    return solver


def test_internal_weir():
    """测试内部堰"""
    print("\n[测试1] 内部堰基本功能")
    print("-" * 70)

    # 创建堰
    weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0, discharge_coeff=1.7)

    # 创建河段和节点
    solver1 = create_test_solver(h_init=3.0, Q_init=30.0)
    solver2 = create_test_solver(h_init=2.5, Q_init=30.0)
    reach1 = Reach("R1", "N1", "N2", solver1)
    reach2 = Reach("R2", "N2", "N3", solver2)
    node = Node("N2", "junction", elevation=100.0)

    # 创建内部堰
    internal_weir = InternalWeir(weir, reach1, reach2, node)

    print(f"  创建内部堰: {internal_weir.name}")
    print(f"  上游河段: {internal_weir.upstream.id}")
    print(f"  下游河段: {internal_weir.downstream.id}")

    # 求解流量
    Q = internal_weir.solve()

    print(f"  计算流量: {Q:.3f} m^3/s")
    print(f"  上游水位: {internal_weir.h_upstream:.3f} m")
    print(f"  下游水位: {internal_weir.h_downstream:.3f} m")
    print(f"  水位差: {internal_weir.delta_h:.3f} m")

    # 验证BC已设置
    assert solver1.bc_right['type'] == 'Q', "上游河段BC类型错误"
    assert solver2.bc_left['type'] == 'Q', "下游河段BC类型错误"
    assert abs(solver1.bc_right['value'] - Q) < 1e-6, "上游河段BC值错误"
    assert abs(solver2.bc_left['value'] - Q) < 1e-6, "下游河段BC值错误"

    # 检查质量守恒
    is_balanced, error = internal_weir.check_mass_balance(tol=1.0)
    print(f"  质量守恒: {'' if is_balanced else ''} (误差={error:.4f} m^3/s)")

    print(" 测试通过")


def test_internal_gate():
    """测试内部闸门"""
    print("\n[测试2] 内部闸门及开度控制")
    print("-" * 70)

    # 创建闸门
    gate = SluiceGate(sill_elevation=0.0, width=8.0, opening=0.5)

    # 创建河段和节点
    solver1 = create_test_solver(h_init=3.0, Q_init=25.0)
    solver2 = create_test_solver(h_init=2.0, Q_init=25.0)
    reach1 = Reach("R1", "N1", "N2", solver1)
    reach2 = Reach("R2", "N2", "N3", solver2)
    node = Node("N2", "junction", elevation=100.0)

    # 创建内部闸门
    internal_gate = InternalGate(gate, reach1, reach2, node)

    print(f"  创建内部闸门: {internal_gate.name}")
    print(f"  初始开度: {internal_gate.get_opening():.2f} m")

    # 求解流量（初始开度）
    Q1 = internal_gate.solve()
    print(f"  初始流量: {Q1:.3f} m^3/s")

    # 增大开度
    internal_gate.set_opening(0.8)
    print(f"  调整开度: {internal_gate.get_opening():.2f} m")

    Q2 = internal_gate.solve()
    print(f"  新流量: {Q2:.3f} m^3/s")

    assert Q2 > Q1, "开度增大后流量应增大"
    print(f"  流量变化: +{((Q2-Q1)/Q1*100):.1f}%")

    print(" 测试通过")


def test_internal_orifice():
    """测试内部孔口"""
    print("\n[测试3] 内部孔口")
    print("-" * 70)

    # 创建孔口
    orifice = Orifice(center_elevation=1.0, diameter=1.5, discharge_coeff=0.62)

    # 创建河段和节点
    solver1 = create_test_solver(h_init=3.0, Q_init=15.0)
    solver2 = create_test_solver(h_init=2.0, Q_init=15.0)
    reach1 = Reach("R1", "N1", "N2", solver1)
    reach2 = Reach("R2", "N2", "N3", solver2)
    node = Node("N2", "junction", elevation=100.0)

    # 创建内部孔口
    internal_orifice = InternalOrifice(orifice, reach1, reach2, node)

    print(f"  创建内部孔口: {internal_orifice.name}")
    print(f"  孔口直径: {orifice.D:.2f} m")
    print(f"  孔口面积: {orifice.A:.3f} m^2")

    # 求解流量
    Q = internal_orifice.solve()
    print(f"  过流流量: {Q:.3f} m^3/s")

    assert Q > 0, "流量应为正值"

    print(" 测试通过")


def test_structure_coupler():
    """测试建筑物耦合器"""
    print("\n[测试4] 建筑物耦合器")
    print("-" * 70)

    # 创建堰
    weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)

    # 创建河段和节点
    solver1 = create_test_solver(h_init=3.0, Q_init=30.0)
    solver2 = create_test_solver(h_init=2.5, Q_init=30.0)
    reach1 = Reach("R1", "N1", "N2", solver1)
    reach2 = Reach("R2", "N2", "N3", solver2)
    node = Node("N2", "junction", elevation=100.0)

    # 创建内部堰和耦合器
    internal_weir = InternalWeir(weir, reach1, reach2, node)
    coupler = StructureCoupler(internal_weir)

    print(f"  创建耦合器: StructureCoupler")
    print(f"  建筑物类型: {type(internal_weir.structure).__name__}")

    # 执行耦合
    Q = coupler.couple()
    print(f"  耦合流量: {Q:.3f} m^3/s")

    # 检查质量守恒
    is_balanced, error = coupler.check_mass_balance(tol=1.0)
    print(f"  质量守恒: {'' if is_balanced else ''} (误差={error:.4f} m^3/s)")

    assert is_balanced, "质量应守恒"

    print(" 测试通过")


def test_network_integration():
    """测试网络集成"""
    print("\n[测试5] 网络集成 - 向网络添加内部建筑物")
    print("-" * 70)

    # 创建网络
    network = RiverNetwork("串联闸门系统")

    # 添加节点
    n1 = create_inflow_boundary("上游", Q=30.0, elevation=110.0)
    n2 = Node("闸门", "junction", elevation=105.0)
    n3 = create_outflow_boundary("下游", h=2.0, elevation=100.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 添加河段
    s1 = create_test_solver(length=500.0, width=15.0, h_init=3.0, Q_init=30.0)
    s2 = create_test_solver(length=500.0, width=15.0, h_init=2.5, Q_init=30.0)

    r1 = Reach("R1", "上游", "闸门", s1)
    r2 = Reach("R2", "闸门", "下游", s2)

    network.add_reach(r1)
    network.add_reach(r2)

    print(f"  网络: {network.name}")
    print(f"  节点数: {len(network.nodes)}")
    print(f"  河段数: {len(network.reaches)}")

    # 创建并添加内部闸门
    gate = SluiceGate(sill_elevation=105.0, width=10.0, opening=0.5)
    internal_gate = InternalGate(gate, r1, r2, n2)

    network.add_internal_structure("闸门", internal_gate)

    assert network.nodes["闸门"].internal_structure == internal_gate, "内部建筑物未正确附加"
    print(f"  添加内部闸门: ")

    # 创建求解器
    solver = NetworkSolver(network)

    # 验证StructureCoupler已创建
    assert "闸门" in solver.couplers, "耦合器未创建"
    assert isinstance(solver.couplers["闸门"], StructureCoupler), "耦合器类型错误"
    print(f"  自动创建StructureCoupler: ")

    print(" 测试通过")


def test_network_simulation():
    """测试带内部建筑物的网络模拟"""
    print("\n[测试6] 网络模拟 - 带内部堰的完整模拟")
    print("-" * 70)

    # 创建网络
    network = RiverNetwork("堰控河道")

    # 节点
    n1 = create_inflow_boundary("入口", Q=40.0, elevation=110.0)
    n2 = Node("堰", "junction", elevation=105.0)
    n3 = create_outflow_boundary("出口", h=2.0, elevation=100.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 河段
    s1 = create_test_solver(length=800.0, width=15.0, h_init=3.0, Q_init=40.0)
    s2 = create_test_solver(length=800.0, width=15.0, h_init=2.5, Q_init=40.0)

    r1 = Reach("上游段", "入口", "堰", s1)
    r2 = Reach("下游段", "堰", "出口", s2)

    network.add_reach(r1)
    network.add_reach(r2)

    # 添加宽顶堰
    weir = BroadCrestedWeir(crest_elevation=105.0, width=12.0, discharge_coeff=1.7)
    internal_weir = InternalWeir(weir, r1, r2, n2)

    network.add_internal_structure("堰", internal_weir)

    print(f"  网络: {network.name}")
    print(f"  内部建筑物: 宽顶堰 (堰顶高程={weir.z_crest:.1f}m, 宽度={weir.B:.1f}m)")

    # 创建求解器
    solver = NetworkSolver(network, solve_method='sequential')

    print(f"  求解方法: {solver.solve_method}")

    # 运行短时间模拟
    print(f"\n  运行模拟 (t=0 -> 100s)...")
    results = solver.run(t_end=50.0, dt=1.0, verbose=False)

    print(f"  总步数: {results['n_steps']}")
    print(f"  计算时间: {results['total_time']:.3f} s")

    # 质量守恒
    max_error = max(results['mass_error_history'])
    avg_error = np.mean(results['mass_error_history'])

    print(f"  质量守恒:")
    print(f"    最大误差: {max_error:.4f}%")
    print(f"    平均误差: {avg_error:.4f}%")

    assert max_error < 10.0, "质量守恒误差过大"

    if max_error < 1.0:
        print(f"    评价:  优秀 (< 1%)")
    elif max_error < 5.0:
        print(f"    评价:   良好 (< 5%)")
    else:
        print(f"    评价:   需改进 (< 10%)")

    print(" 测试通过")


if __name__ == "__main__":
    print("=" * 80)
    print("内部水工建筑物测试套件")
    print("Stage 3 - Task 3.3.2")
    print("=" * 80)

    try:
        test_internal_weir()
        test_internal_gate()
        test_internal_orifice()
        test_structure_coupler()
        test_network_integration()
        test_network_simulation()

        print("\n" + "=" * 80)
        print(" 所有测试通过！")
        print("=" * 80)

        print("\n总结:")
        print("  1.  InternalWeir - 内部堰")
        print("  2.  InternalGate - 内部闸门（可调开度）")
        print("  3.  InternalOrifice - 内部孔口")
        print("  4.  StructureCoupler - 建筑物耦合器")
        print("  5.  Network集成 - 自动构建StructureCoupler")
        print("  6.  Network模拟 - 完整模拟流程")

    except AssertionError as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n 错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
