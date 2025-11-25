"""
MacDonald Test 5 时间步长演化追踪

目的：跟踪自适应dt的演化，找出失败原因
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


def test_dt_evolution_trace():
    """
    追踪自适应dt的演化过程
    """
    print("\n" + "="*80)
    print("MacDonald Test 5 时间步长演化追踪")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50
    cfl = 0.5

    h_normal = compute_normal_depth(Q, B, S0, n)

    print(f"\n配置:")
    print(f"  正常水深 h_n = {h_normal:.4f} m")
    print(f"  CFL = {cfl}")

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

    print(f"\n开始追踪dt演化...")
    print(f"{'步骤':<6} {'时间(s)':<10} {'dt(s)':<10} {'h_min':<10} {'h_max':<10} {'h_mean':<10} {'|u|_max':<10} {'状态':<10}")
    print("=" * 80)

    max_steps = 200
    dt_history = []
    t_history = []

    for step in range(max_steps):
        # 计算时间步长
        dt = solver.compute_dt()
        dt_history.append(dt)
        t_history.append(solver.t)

        # 检查dt
        if dt <= 0 or np.isnan(dt) or np.isinf(dt):
            print(f"{step+1:<6} {solver.t:<10.2f} {dt:<10.6f} {'---':<10} {'---':<10} {'---':<10} {'---':<10}  dt异常")
            break

        # 执行时间步
        solver.step(dt)

        # 检查状态
        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            h_min = np.nanmin(solver.h)
            h_max = np.nanmax(solver.h)
            h_mean = np.nanmean(solver.h)
            u = solver.Q / (B * solver.h)
            u_max = np.nanmax(np.abs(u))
            print(f"{step+1:<6} {solver.t:<10.2f} {dt:<10.6f} {h_min:<10.4f} {h_max:<10.4f} {h_mean:<10.4f} {u_max:<10.4f}  NaN")
            break

        # 正常输出
        h_min = np.min(solver.h)
        h_max = np.max(solver.h)
        h_mean = np.mean(solver.h)
        u = solver.Q / (B * solver.h)
        u_max = np.max(np.abs(u))

        status = ""

        # 检查异常迹象
        if dt < 0.1:
            status = " dt小"
        if h_min < 0.1:
            status = " h小"
        if h_max > 10.0:
            status = " h大"
        if u_max > 10.0:
            status = " u大"

        # 每步输出
        if step < 50 or step % 10 == 0 or status != "":
            print(f"{step+1:<6} {solver.t:<10.2f} {dt:<10.6f} {h_min:<10.4f} {h_max:<10.4f} {h_mean:<10.4f} {u_max:<10.4f} {status:<10}")

    print("\n" + "="*80)
    print("dt统计:")
    if len(dt_history) > 0:
        print(f"  dt范围: [{np.min(dt_history):.6f}, {np.max(dt_history):.6f}] s")
        print(f"  dt平均: {np.mean(dt_history):.6f} s")
        print(f"  dt标准差: {np.std(dt_history):.6f} s")

        # 找出dt突变点
        if len(dt_history) > 1:
            dt_changes = np.abs(np.diff(dt_history))
            max_change_idx = np.argmax(dt_changes)
            max_change = dt_changes[max_change_idx]
            if max_change > 0.5:
                print(f"\n️  dt最大突变:")
                print(f"  位置: 步骤{max_change_idx+1} -> {max_change_idx+2}")
                print(f"  dt变化: {dt_history[max_change_idx]:.6f} -> {dt_history[max_change_idx+1]:.6f}")
                print(f"  变化量: {max_change:.6f} s")

    print("="*80)


def test_fixed_vs_adaptive():
    """
    对比固定dt和自适应dt的差异
    """
    print("\n" + "="*80)
    print("固定dt vs 自适应dt 对比测试")
    print("="*80)

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    n_cells = 50

    h_normal = compute_normal_depth(Q, B, S0, n)

    # 测试1：固定dt=0.5
    print(f"\n--- 测试1：固定dt=0.5 ---")
    solver1 = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=0.5, order=1,
        riemann_solver='hll', use_numba=True
    )
    bc_left = {'type': 'Q', 'value': Q}
    bc_right = {'type': 'h', 'value': h_normal}
    h_init_arr = np.ones(n_cells) * h_normal
    Q_init_arr = np.ones(n_cells) * Q
    solver1.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

    dt_fixed = 0.5
    n_steps = 200
    failed1 = False

    for step in range(n_steps):
        solver1.step(dt_fixed)
        if np.any(np.isnan(solver1.h)):
            print(f" 固定dt失败于第{step+1}步 (t={solver1.t:.2f}s)")
            failed1 = True
            break

    if not failed1:
        print(f" 固定dt成功：{n_steps}步 (t={solver1.t:.2f}s)")
        print(f"   h_mean={np.mean(solver1.h):.4f}m, 质量误差={abs(solver1.get_mass_conservation_error()):.2f}%")

    # 测试2：自适应dt, CFL=0.5
    print(f"\n--- 测试2：自适应dt, CFL=0.5 ---")
    solver2 = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=0.5, order=1,
        riemann_solver='hll', use_numba=True
    )
    solver2.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

    failed2 = False

    for step in range(n_steps):
        dt = solver2.compute_dt()
        solver2.step(dt)
        if np.any(np.isnan(solver2.h)):
            print(f" 自适应dt失败于第{step+1}步 (t={solver2.t:.2f}s, dt={dt:.6f}s)")
            failed2 = True
            break

    if not failed2:
        print(f" 自适应dt成功：{n_steps}步 (t={solver2.t:.2f}s)")
        print(f"   h_mean={np.mean(solver2.h):.4f}m, 质量误差={abs(solver2.get_mass_conservation_error()):.2f}%")


if __name__ == "__main__":
    test_dt_evolution_trace()
    test_fixed_vs_adaptive()
