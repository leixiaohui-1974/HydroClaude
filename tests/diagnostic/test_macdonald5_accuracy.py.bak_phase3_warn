"""
MacDonald Test 5 精度改进诊断

目的：探索提升Test 5精度的方法
当前状态：平均偏差17.6%，目标：<10%

策略：
1. 增加模拟时间（更充分收敛）
2. 细化网格
3. 使用二阶格式
4. 优化dt_max
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


def run_test5_config(end_time, n_cells, order, dt_max, description):
    """
    运行Test 5配置并返回精度指标
    """
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")

    L = 1000.0
    B = 50.0
    S0 = 0.001
    n = 0.025
    Q = 20.0
    g = 9.81

    h_normal = compute_normal_depth(Q, B, S0, n)

    print(f"配置:")
    print(f"  模拟时间: {end_time}s")
    print(f"  网格单元: {n_cells}")
    print(f"  空间精度: {order}阶")
    print(f"  dt_max: {dt_max}s")
    print(f"  目标h_n: {h_normal:.4f}m")

    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0, cfl=0.5, order=order,
        riemann_solver='hll', use_numba=True,
        dt_max=dt_max
    )

    bc_left = {'type': 'Q', 'value': Q}
    bc_right = {'type': 'h', 'value': h_normal}

    h_init_arr = np.ones(n_cells) * h_normal
    Q_init_arr = np.ones(n_cells) * Q

    solver.initialize(h_init_arr, Q_init_arr, bc_left, bc_right)

    # 运行模拟
    target_time = end_time
    n_steps = 0
    max_steps = 100000

    while solver.t < target_time and n_steps < max_steps:
        dt = min(solver.compute_dt(), dt_max)
        solver.step(dt)
        n_steps += 1

        if np.any(np.isnan(solver.h)):
            print(f" NaN出现在第{n_steps}步")
            return None

    # 分析结果
    h_final = solver.h
    h_deviation = np.abs(h_final - h_normal) / h_normal * 100
    mass_error = abs(solver.get_mass_conservation_error())

    u_final = solver.Q / (B * h_final)
    Fr_final = u_final / np.sqrt(g * h_final)

    print(f"\n结果:")
    print(f"  总步数: {n_steps}")
    print(f"  最终时间: {solver.t:.1f}s")
    print(f"  h_mean: {np.mean(h_final):.4f}m (目标: {h_normal:.4f}m)")
    print(f"  h_std: {np.std(h_final):.4f}m")
    print(f"  平均偏差: {np.mean(h_deviation):.2f}%")
    print(f"  最大偏差: {np.max(h_deviation):.2f}%")
    print(f"  RMS偏差: {np.sqrt(np.mean(h_deviation**2)):.2f}%")
    print(f"  质量误差: {mass_error:.2f}%")
    print(f"  平均Fr: {np.mean(Fr_final):.4f}")

    return {
        'n_steps': n_steps,
        'h_mean': np.mean(h_final),
        'h_std': np.std(h_final),
        'mean_deviation': np.mean(h_deviation),
        'max_deviation': np.max(h_deviation),
        'rms_deviation': np.sqrt(np.mean(h_deviation**2)),
        'mass_error': mass_error,
        'Fr_mean': np.mean(Fr_final)
    }


def test_longer_simulation():
    """
    测试1：更长的模拟时间（收敛性）
    """
    print("\n" + "="*80)
    print("测试1：模拟时间的影响")
    print("="*80)

    times = [500, 1000, 1500, 2000]
    results = []

    for end_time in times:
        result = run_test5_config(
            end_time=end_time,
            n_cells=50,
            order=1,
            dt_max=0.5,
            description=f"模拟时间 = {end_time}s"
        )
        if result:
            results.append(result)

    # 分析趋势
    print("\n" + "="*80)
    print("收敛性分析")
    print("="*80)
    print(f"{'时间(s)':<12} {'平均偏差%':<12} {'质量误差%':<12} {'h_std':<12}")
    print("-"*80)
    for i, end_time in enumerate(times[:len(results)]):
        r = results[i]
        print(f"{end_time:<12} {r['mean_deviation']:<12.2f} {r['mass_error']:<12.2f} {r['h_std']:<12.4f}")

    if len(results) >= 2:
        improvement = results[0]['mean_deviation'] - results[-1]['mean_deviation']
        if improvement > 0:
            print(f"\n 偏差改善: {improvement:.2f}%")
        else:
            print(f"\n 偏差未改善（可能已收敛）")


def test_finer_grid():
    """
    测试2：更细的网格
    """
    print("\n" + "="*80)
    print("测试2：网格细化的影响")
    print("="*80)

    grid_sizes = [50, 100, 200, 400]
    results = []

    for n_cells in grid_sizes:
        result = run_test5_config(
            end_time=500,
            n_cells=n_cells,
            order=1,
            dt_max=0.5,
            description=f"网格单元 = {n_cells}"
        )
        if result:
            results.append(result)

    # 分析网格收敛性
    print("\n" + "="*80)
    print("网格收敛性分析")
    print("="*80)
    print(f"{'单元数':<12} {'dx(m)':<12} {'平均偏差%':<12} {'h_std':<12} {'步数':<12}")
    print("-"*80)
    for i, n_cells in enumerate(grid_sizes[:len(results)]):
        r = results[i]
        dx = 1000.0 / n_cells
        print(f"{n_cells:<12} {dx:<12.2f} {r['mean_deviation']:<12.2f} {r['h_std']:<12.4f} {r['n_steps']:<12}")

    if len(results) >= 2:
        improvement = results[0]['mean_deviation'] - results[-1]['mean_deviation']
        print(f"\n精度变化: {improvement:+.2f}%")


def test_higher_order():
    """
    测试3：二阶格式
    """
    print("\n" + "="*80)
    print("测试3：空间精度的影响")
    print("="*80)

    # 一阶
    result1 = run_test5_config(
        end_time=500,
        n_cells=50,
        order=1,
        dt_max=0.5,
        description="一阶格式"
    )

    # 二阶
    result2 = run_test5_config(
        end_time=500,
        n_cells=50,
        order=2,
        dt_max=0.5,
        description="二阶格式"
    )

    if result1 and result2:
        print("\n" + "="*80)
        print("对比分析")
        print("="*80)
        print(f"{'格式':<12} {'平均偏差%':<12} {'质量误差%':<12} {'h_std':<12}")
        print("-"*80)
        print(f"{'一阶':<12} {result1['mean_deviation']:<12.2f} {result1['mass_error']:<12.2f} {result1['h_std']:<12.4f}")
        print(f"{'二阶':<12} {result2['mean_deviation']:<12.2f} {result2['mass_error']:<12.2f} {result2['h_std']:<12.4f}")

        improvement = result1['mean_deviation'] - result2['mean_deviation']
        print(f"\n二阶改善: {improvement:+.2f}%")


def test_optimal_config():
    """
    测试4：最优配置组合
    """
    print("\n" + "="*80)
    print("测试4：最优配置探索")
    print("="*80)

    configs = [
        (500, 50, 1, 0.5, "当前配置（基准）"),
        (1000, 50, 2, 0.5, "二阶+长时间"),
        (500, 100, 2, 0.5, "二阶+细网格"),
        (1000, 100, 2, 0.5, "二阶+长时间+细网格"),
    ]

    results = []
    for end_time, n_cells, order, dt_max, desc in configs:
        result = run_test5_config(end_time, n_cells, order, dt_max, desc)
        if result:
            results.append((desc, result))

    # 找出最佳配置
    print("\n" + "="*80)
    print("最优配置对比")
    print("="*80)
    print(f"{'配置':<30} {'平均偏差%':<12} {'质量误差%':<12}")
    print("-"*80)

    best_deviation = float('inf')
    best_config = None

    for desc, r in results:
        print(f"{desc:<30} {r['mean_deviation']:<12.2f} {r['mass_error']:<12.2f}")
        if r['mean_deviation'] < best_deviation:
            best_deviation = r['mean_deviation']
            best_config = desc

    print("\n" + "="*80)
    print(f" 最佳配置: {best_config}")
    print(f"   平均偏差: {best_deviation:.2f}%")
    print("="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MacDonald Test 5 精度改进诊断")
    print("="*80)

    # 运行各项测试
    test_longer_simulation()
    test_finer_grid()
    test_higher_order()
    test_optimal_config()

    print("\n" + "="*80)
    print("诊断完成")
    print("="*80)
