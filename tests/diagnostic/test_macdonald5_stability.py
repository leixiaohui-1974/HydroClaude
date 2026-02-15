"""
MacDonald Test 5 稳定性诊断

目的：找出NaN出现的临界时间点
策略：逐步增加模拟时间，定位失败点
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
import pytest
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



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


def test_stability_progressive():
    """
    渐进式稳定性测试：逐步增加模拟时间
    """
    print("\n" + "="*80)
    print("MacDonald Test 5 渐进式稳定性测试")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50

    h_normal = compute_normal_depth(Q, B, S0, n)

    print(f"\n配置:")
    print(f"  正常水深 h_n = {h_normal:.4f} m")
    print(f"  Manning系数 n = {n}")
    print(f"  底坡 S0 = {S0}")

    # 测试不同的模拟时长
    test_times = [100, 200, 300, 400, 500, 600, 800, 1000]

    print(f"\n测试策略：逐步增加模拟时间")
    print(f"时间点: {test_times}")

    for end_time in test_times:
        print(f"\n{'='*80}")
        print(f"测试时长: {end_time} s")
        print(f"{'='*80}")

        solver = GodunvFVMSolver(
            width=B, length=L, n_cells=n_cells,
            manning_n=n, slope=S0, cfl=0.5, order=1,
            riemann_solver='hll', use_numba=True
        )

        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_normal}

        h_init_arr = np.ones(n_cells) * h_normal
        Q_init_arr = np.ones(n_cells) * Q

        solver.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

        # 固定时间步长
        dt = 0.5
        n_steps = int(end_time / dt)

        failed = False
        fail_step = 0

        for step in range(n_steps):
            solver.step(dt)

            if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                failed = True
                fail_step = step + 1
                fail_time = solver.t
                print(f" NaN出现在第{fail_step}步 (t={fail_time:.2f}s)")
                break

            # 每100步检查一次
            if (step + 1) % 100 == 0:
                h_mean = np.mean(solver.h)
                h_std = np.std(solver.h)
                mass_error = abs(solver.get_mass_conservation_error())
                print(f"  步骤{step+1}/{n_steps}: h={h_mean:.4f}+/-{h_std:.4f}m, 质量误差={mass_error:.2f}%")

        if not failed:
            h_mean = np.mean(solver.h)
            mass_error = abs(solver.get_mass_conservation_error())
            print(f" 成功完成{n_steps}步 (t={end_time:.0f}s)")
            print(f"   最终: h_mean={h_mean:.4f}m, 质量误差={mass_error:.2f}%")
        else:
            print(f" 失败于 t={fail_time:.2f}s")
            print(f"\n临界时间在 {test_times[test_times.index(end_time)-1] if test_times.index(end_time) > 0 else 0}s ~ {end_time}s 之间")
            break

    print(f"\n{'='*80}")
    print("稳定性测试完成")
    print(f"{'='*80}")


def test_stability_smaller_cfl():
    """
    测试更小的CFL数是否能提高稳定性
    """
    print("\n" + "="*80)
    print("MacDonald Test 5 CFL敏感性测试")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50

    h_normal = compute_normal_depth(Q, B, S0, n)

    # 测试不同的CFL数
    cfl_values = [0.5, 0.4, 0.3, 0.2, 0.1]
    end_time = 500.0

    for cfl in cfl_values:
        print(f"\n{'='*60}")
        print(f"CFL = {cfl}")
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

        # 运行固定步数
        n_steps = 1000

        failed = False

        for step in range(n_steps):
            dt = solver.compute_dt()
            solver.step(dt)

            if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                failed = True
                print(f" NaN出现在第{step+1}步 (t={solver.t:.2f}s, dt={dt:.4f}s)")
                break

        if not failed:
            h_mean = np.mean(solver.h)
            mass_error = abs(solver.get_mass_conservation_error())
            print(f" 成功完成{n_steps}步 (t={solver.t:.2f}s)")
            print(f"   最终: h_mean={h_mean:.4f}m, 质量误差={mass_error:.2f}%")


if __name__ == "__main__":
    test_stability_progressive()
    test_stability_smaller_cfl()
