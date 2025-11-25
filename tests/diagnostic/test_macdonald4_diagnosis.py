"""
MacDonald Test 4 (水跃) 诊断测试

目的：
1. 实际运行Test 4配置，观察失败模式
2. 验证supercritical BC是否被正确应用
3. 分析为什么上游急流无法维持
4. 探索可能的解决方案
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
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_hydraulic_jump_basic():
    """
    基础水跃测试：使用Test 4的配置
    """
    print("\n" + "="*80)
    print("MacDonald Test 4 诊断：基础水跃配置")
    print("="*80)

    # Test 4参数
    L = 1000.0
    B = 10.0
    S0 = 0.0
    n = 0.0
    Q = 20.0

    h_upstream = 0.7   # 上游急流水深
    h_downstream = 2.8  # 下游缓流水深

    n_cells = 200
    g = 9.81

    # 计算上游Froude数
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)

    # 理论水跃后水深（Belanger方程）
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream**2))

    print(f"\n理论分析:")
    print(f"  上游：h1 = {h_upstream:.2f}m, u1 = {u_upstream:.2f}m/s, Fr1 = {Fr_upstream:.3f} (急流)")
    print(f"  下游目标：h = {h_downstream:.2f}m")
    print(f"  理论水跃后水深：h2 = {h2_theory:.2f}m (Belanger方程)")
    print(f"  配置差异：{h_downstream:.2f}m vs {h2_theory:.2f}m (差{abs(h_downstream-h2_theory):.2f}m)")

    # 创建solver
    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=0.5, order=1,
        riemann_solver='hll', use_numba=True
    )

    # 边界条件
    bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q}
    bc_right = {'type': 'h', 'value': h_downstream}

    # 初始条件：线性插值（Test 4的方式）
    x = np.linspace(L/(2*n_cells), L - L/(2*n_cells), n_cells)
    h_init = np.linspace(h_upstream, h_downstream, n_cells)
    Q_init = np.ones(n_cells) * Q

    print(f"\n初始条件:")
    print(f"  h范围: [{h_init[0]:.3f}, {h_init[-1]:.3f}] m")
    print(f"  Q: {Q:.1f} m^3/s (均匀)")

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行模拟
    dt = 0.5  # 固定时间步长
    n_steps = 200
    check_interval = 20

    print(f"\n运行模拟（{n_steps}步，dt={dt}s）...")
    print(f"{'步骤':<8} {'时间(s)':<10} {'h[0]':<10} {'Fr[0]':<10} {'h[-1]':<10} {'质量误差%':<12} {'状态':<10}")
    print("="*80)

    for step in range(n_steps):
        solver.step(dt)

        if (step + 1) % check_interval == 0 or step < 5:
            h_left = solver.h[0]
            h_right = solver.h[-1]
            u_left = solver.Q[0] / (B * h_left)
            Fr_left = u_left / np.sqrt(g * h_left)
            mass_error = abs(solver.get_mass_conservation_error())

            status = ""
            if Fr_left < 1.0:
                status = "️ Fr<1"
            if mass_error > 10.0:
                status = "️ 质量"
            if np.any(np.isnan(solver.h)):
                status = " NaN"
                print(f"{step+1:<8} {solver.t:<10.2f} {'NaN':<10} {'NaN':<10} {'NaN':<10} {'NaN':<12} {status:<10}")
                break

            print(f"{step+1:<8} {solver.t:<10.2f} {h_left:<10.4f} {Fr_left:<10.4f} {h_right:<10.4f} {mass_error:<12.2f} {status:<10}")

    # 最终分析
    print("\n" + "="*80)
    print("最终状态分析")
    print("="*80)

    if not np.any(np.isnan(solver.h)):
        h_final = solver.h
        Q_final = solver.Q
        u_final = Q_final / (B * h_final)
        Fr_final = u_final / np.sqrt(g * h_final)

        print(f"\n水深分布:")
        print(f"  上游 h[0] = {h_final[0]:.4f}m (目标: {h_upstream:.2f}m)")
        print(f"  下游 h[-1] = {h_final[-1]:.4f}m (目标: {h_downstream:.2f}m)")
        print(f"  平均 h_mean = {np.mean(h_final):.4f}m")
        print(f"  范围 [{np.min(h_final):.4f}, {np.max(h_final):.4f}]m")

        print(f"\nFroude数分布:")
        print(f"  上游 Fr[0] = {Fr_final[0]:.4f} (目标: >1, 实际: {'急流' if Fr_final[0] > 1 else '缓流'})")
        print(f"  下游 Fr[-1] = {Fr_final[-1]:.4f}")
        print(f"  平均 Fr_mean = {np.mean(Fr_final):.4f}")
        print(f"  急流区域: {np.sum(Fr_final > 1)} / {n_cells} 单元")

        print(f"\n质量守恒:")
        mass_error = abs(solver.get_mass_conservation_error())
        print(f"  质量误差: {mass_error:.2f}%")

        # 诊断结论
        print("\n" + "="*80)
        print("诊断结论")
        print("="*80)

        if Fr_final[0] < 1.0:
            print(" 问题确认：上游失去急流状态")
            print(f"   期望：Fr[0] > 1.0")
            print(f"   实际：Fr[0] = {Fr_final[0]:.4f} < 1.0")
            print(f"   原因：下游高水位({h_downstream}m)回传，'淹没'上游")
        else:
            print(" 上游保持急流状态")

        if mass_error > 10.0:
            print(f" 质量守恒较差：{mass_error:.2f}%")
        else:
            print(f" 质量守恒可接受：{mass_error:.2f}%")

        return Fr_final[0] > 1.0 and mass_error < 10.0
    else:
        print(" 模拟出现NaN")
        return False


def test_hydraulic_jump_with_preformed_jump():
    """
    测试：使用预形成的水跃初始条件
    """
    print("\n" + "="*80)
    print("MacDonald Test 4 诊断：预形成水跃初始条件")
    print("="*80)

    L = 1000.0
    B = 10.0
    S0 = 0.0
    n = 0.0
    Q = 20.0

    h_upstream = 0.7
    h_downstream = 2.8

    n_cells = 200
    g = 9.81

    # 计算理论水跃位置和后水深
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream**2))

    print(f"\n理论分析:")
    print(f"  上游：h1 = {h_upstream:.2f}m, Fr1 = {Fr_upstream:.3f}")
    print(f"  理论水跃后：h2 = {h2_theory:.2f}m")
    print(f"  实际下游：h = {h_downstream:.2f}m")

    # 创建预形成水跃的初始条件
    # 策略：前半段急流，后半段缓流，中间快速过渡
    x = np.linspace(L/(2*n_cells), L - L/(2*n_cells), n_cells)
    jump_location = L / 2.0  # 水跃位置在中间

    h_init = np.zeros(n_cells)
    for i in range(n_cells):
        if x[i] < jump_location:
            # 上游：保持急流水深
            h_init[i] = h_upstream
        else:
            # 下游：使用理论水跃后水深
            # 逐渐过渡到下游边界值
            alpha = (x[i] - jump_location) / (L - jump_location)
            h_init[i] = h2_theory * (1 - alpha) + h_downstream * alpha

    Q_init = np.ones(n_cells) * Q

    print(f"\n初始条件（预形成水跃）:")
    print(f"  水跃位置: x = {jump_location:.1f}m")
    print(f"  上游段 (x<{jump_location:.0f}m): h = {h_upstream:.2f}m (急流)")
    print(f"  下游段 (x>{jump_location:.0f}m): h从{h2_theory:.2f}m过渡到{h_downstream:.2f}m (缓流)")

    # 创建solver
    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=0.5, order=1,
        riemann_solver='hll', use_numba=True
    )

    bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q}
    bc_right = {'type': 'h', 'value': h_downstream}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行模拟
    dt = 0.5
    n_steps = 200
    check_interval = 20

    print(f"\n运行模拟...")
    print(f"{'步骤':<8} {'时间(s)':<10} {'Fr[0]':<10} {'质量误差%':<12} {'急流区':<10} {'状态':<10}")
    print("="*80)

    for step in range(n_steps):
        solver.step(dt)

        if (step + 1) % check_interval == 0:
            u = solver.Q / (B * solver.h)
            Fr = u / np.sqrt(g * solver.h)
            Fr_left = Fr[0]
            mass_error = abs(solver.get_mass_conservation_error())
            supercritical_cells = np.sum(Fr > 1)

            status = ""
            if Fr_left < 1.0:
                status = "️ Fr<1"
            if mass_error > 10.0:
                status = "️ 质量"

            print(f"{step+1:<8} {solver.t:<10.2f} {Fr_left:<10.4f} {mass_error:<12.2f} {supercritical_cells:<10} {status:<10}")

            if np.any(np.isnan(solver.h)):
                print(" 出现NaN")
                break

    # 最终分析
    if not np.any(np.isnan(solver.h)):
        h_final = solver.h
        u_final = solver.Q / (B * h_final)
        Fr_final = u_final / np.sqrt(g * h_final)

        print(f"\n最终状态:")
        print(f"  上游Fr[0] = {Fr_final[0]:.4f} ({'急流' if Fr_final[0] > 1 else '缓流'})")
        print(f"  质量误差: {abs(solver.get_mass_conservation_error()):.2f}%")
        print(f"  急流区域: {np.sum(Fr_final > 1)}/{n_cells}单元")

        return Fr_final[0] > 1.0
    else:
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MacDonald Test 4 诊断测试套件")
    print("="*80)

    # 测试1：基础配置
    result1 = test_hydraulic_jump_basic()

    # 测试2：预形成水跃
    result2 = test_hydraulic_jump_with_preformed_jump()

    print("\n" + "="*80)
    print("诊断总结")
    print("="*80)
    print(f"测试1（线性初始条件）: {' 通过' if result1 else ' 失败'}")
    print(f"测试2（预形成水跃）: {' 通过' if result2 else ' 失败'}")

    if not result1 and not result2:
        print("\n️ 两种方法都失败，水跃问题需要更深入研究")
    elif not result1 and result2:
        print("\n 预形成水跃可行！建议Test 4使用此初始条件")
    elif result1:
        print("\n 基础配置可行！")
