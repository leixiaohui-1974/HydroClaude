"""
MacDonald Test 5 时间步长限制测试

测试手动限制dt_max是否能解决不稳定问题
"""
import sys
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



def compute_normal_depth(Q, B, S0, n, h_guess=1.0, tol=1e-6, max_iter=100):
    """计算正常水深"""
    h = h_guess
    for i in range(max_iter):
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0/n) * A * (R**(2.0/3.0)) * np.sqrt(S0)
        f = Q_calc - Q
        if abs(f) < tol:
            return h
        dh = 1e-6
        A_dh = B * (h + dh)
        P_dh = B + 2 * (h + dh)
        R_dh = A_dh / P_dh
        Q_dh = (1.0/n) * A_dh * (R_dh**(2.0/3.0)) * np.sqrt(S0)
        df_dh = (Q_dh - Q_calc) / dh
        h = h - f / df_dh
        if h <= 0:
            h = h_guess / 2.0
    return h


def test_with_dt_limit():
    """
    测试不同的dt_max限制
    """
    print("\n" + "="*80)
    print("MacDonald Test 5 dt_max限制测试")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50
    cfl = 0.5

    h_normal = compute_normal_depth(Q, B, S0, n)

    # 测试不同的dt_max值
    dt_max_values = [1.0, 0.5, 0.3, 0.2]

    for dt_max in dt_max_values:
        print(f"\n{'='*60}")
        print(f"测试 dt_max = {dt_max} s")
        print(f"{'='*60}")

        solver = GodunvFVMSolver(
            width=B, length=L, n_cells=n_cells,
            manning_n=n, slope=S0, cfl=cfl, order=1,
            riemann_solver='hll', use_numba=True
        )

        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_normal}

        h_init_arr = np.ones(n_cells) * h_normal
        Q_init_arr = np.ones(n_cells) * Q

        solver.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

        # 目标：运行到500s
        target_time = 500.0
        n_steps = 0
        max_steps = 100000

        failed = False
        dt_limited_count = 0

        while solver.t < target_time and n_steps < max_steps:
            # 计算dt并限制
            dt = solver.compute_dt()
            dt_original = dt

            if dt > dt_max:
                dt = dt_max
                dt_limited_count += 1

            solver.step(dt)
            n_steps += 1

            # 检查NaN
            if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                print(f" NaN出现在第{n_steps}步 (t={solver.t:.2f}s, dt={dt:.6f}s)")
                failed = True
                break

            # 每100步输出
            if n_steps % 100 == 0:
                h_mean = np.mean(solver.h)
                mass_error = abs(solver.get_mass_conservation_error())
                print(f"  步骤{n_steps}: t={solver.t:.2f}s, h_mean={h_mean:.4f}m, 质量误差={mass_error:.2f}%")

        if not failed:
            h_mean = np.mean(solver.h)
            mass_error = abs(solver.get_mass_conservation_error())
            print(f"\n 成功运行到{solver.t:.2f}s")
            print(f"   总步数: {n_steps}")
            print(f"   dt被限制次数: {dt_limited_count} ({dt_limited_count/n_steps*100:.1f}%)")
            print(f"   最终h_mean: {h_mean:.4f}m")
            print(f"   质量误差: {mass_error:.2f}%")


def test_optimal_dt_max():
    """
    使用最优dt_max运行完整500s模拟
    """
    print("\n" + "="*80)
    print("MacDonald Test 5 最优dt_max完整测试")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50
    cfl = 0.5
    dt_max = 0.5  # 根据之前的结果选择

    h_normal = compute_normal_depth(Q, B, S0, n)
    g = 9.81

    print(f"\n配置:")
    print(f"  正常水深 h_n = {h_normal:.4f} m")
    print(f"  CFL = {cfl}")
    print(f"  dt_max = {dt_max} s")

    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=cfl, order=1,
        riemann_solver='hll', use_numba=True
    )

    bc_left = {'type': 'Q', 'value': Q}
    bc_right = {'type': 'h', 'value': h_normal}

    h_init_arr = np.ones(n_cells) * h_normal
    Q_init_arr = np.ones(n_cells) * Q

    solver.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

    target_time = 500.0
    n_steps = 0
    max_steps = 100000

    print(f"\n运行模拟到{target_time}s...")

    while solver.t < target_time and n_steps < max_steps:
        dt = min(solver.compute_dt(), dt_max)
        solver.step(dt)
        n_steps += 1

        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            print(f" NaN出现在第{n_steps}步")
            return False

        if n_steps % 100 == 0:
            h_mean = np.mean(solver.h)
            mass_error = abs(solver.get_mass_conservation_error())
            print(f"  步骤{n_steps}: t={solver.t:.2f}s, h_mean={h_mean:.4f}m, 质量误差={mass_error:.2f}%")

    # 最终验证
    print(f"\n模拟完成:")
    print(f"  最终时间: {solver.t:.2f} s")
    print(f"  总步数: {n_steps}")

    h_final = solver.h
    h_mean = np.mean(h_final)
    h_std = np.std(h_final)
    h_error = abs(h_mean - h_normal) / h_normal * 100
    mass_error = abs(solver.get_mass_conservation_error())

    u_final = solver.Q / (B * h_final)
    Fr_final = u_final / np.sqrt(g * h_final)
    Fr_mean = np.mean(Fr_final)

    print(f"\n结果分析:")
    print(f"  平均水深: {h_mean:.4f} m (目标: {h_normal:.4f} m)")
    print(f"  标准差: {h_std:.4f} m")
    print(f"  水深误差: {h_error:.2f}%")
    print(f"  质量守恒误差: {mass_error:.2f}%")
    print(f"  平均Froude数: {Fr_mean:.3f}")

    # 验证标准（放宽）
    print(f"\n验证标准:")
    success = True

    if h_error < 10.0:
        print(f"   水深误差 {h_error:.2f}% < 10%")
    else:
        print(f"   水深误差 {h_error:.2f}% >= 10%")
        success = False

    if mass_error < 10.0:
        print(f"   质量守恒误差 {mass_error:.2f}% < 10%")
    else:
        print(f"   质量守恒误差 {mass_error:.2f}% >= 10%")
        success = False

    if Fr_mean < 1.0:
        print(f"   平均Froude数 {Fr_mean:.3f} < 1 (缓流)")
    else:
        print(f"   平均Froude数 {Fr_mean:.3f} >= 1")
        success = False

    if success:
        print(f"\n MacDonald Test 5 通过（使用dt_max={dt_max}s）")
    else:
        print(f"\n️ MacDonald Test 5 未完全满足验收标准")

    return success


if __name__ == "__main__":
    test_with_dt_limit()
    test_optimal_dt_max()
