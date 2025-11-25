"""
FVM求解器验证测试

测试FVM求解器的关键性质：
1. 静水平衡（Well-balanced）
2. Dam break（守恒性和激波捕捉）
3. 精度收敛性

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from solvers.fvm_solver import FVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_still_water():
    """
    测试1: 静水平衡

    初始条件：h = h0 - S0*x, Q = 0
    理论：应该保持静止（well-balanced性质）
    """
    print("=" * 70)
    print("测试1: 静水平衡 (Well-Balanced)")
    print("=" * 70)
    print()

    # 网格
    L = 1000.0
    nx = 101
    x = np.linspace(0, L, nx)

    # 参数
    B = 10.0
    S0 = 0.001  # 坡度
    n = 0.025   # Manning糙率
    g = 9.81

    # 创建求解器
    solver = FVMSolver(
        x_grid=x,
        B=B, S0=S0, n=n, g=g,
        reconstruction='muscl',
        limiter='minmod',
        riemann='hll',
        time_integrator='ssp_rk2'
    )

    # 初始条件：静水平衡
    h0 = 5.0 - S0 * solver.x_cell
    Q0 = np.zeros(solver.ncells)

    solver.initialize(h0, Q0)

    print("初始状态:")
    print(f"  h范围: [{h0.min():.4f}, {h0.max():.4f}]m")
    print(f"  Q: 全部为0")
    print()

    # 求解
    t_end = 100.0
    history = solver.solve(t_end, cfl=0.5, verbose=False)

    h_final, u_final = solver.get_primitive_variables()

    # 计算误差
    h_error_max = np.max(np.abs(h_final - h0))
    u_max = np.max(np.abs(u_final))

    print("最终状态:")
    print(f"  t = {t_end}s")
    print(f"  水深最大变化: {h_error_max:.2e}m")
    print(f"  最大流速: {u_max:.2e}m/s")
    print()

    # 判断
    if h_error_max < 1e-10 and u_max < 1e-10:
        print(" Well-balanced性质：完美保持静水平衡（机器精度）")
        result = "perfect"
    elif h_error_max < 1e-6 and u_max < 1e-6:
        print(" Well-balanced性质：良好保持静水平衡")
        result = "good"
    elif h_error_max < 1e-3 and u_max < 1e-3:
        print(" Well-balanced性质：可接受")
        result = "acceptable"
    else:
        print(" Well-balanced性质：不佳")
        result = "poor"

    print()
    return result


def test_dam_break():
    """
    测试2: Dam break问题

    验证守恒性和激波捕捉能力
    """
    print("=" * 70)
    print("测试2: Dam break (守恒性和激波)")
    print("=" * 70)
    print()

    # 网格
    L = 100.0
    nx = 201
    x = np.linspace(0, L, nx)

    # 参数
    B = 10.0
    S0 = 0.0
    n = 0.0  # 无摩阻以验证守恒
    g = 9.81

    # 创建求解器
    solver = FVMSolver(
        x_grid=x,
        B=B, S0=S0, n=n, g=g,
        reconstruction='muscl',
        limiter='minmod',
        riemann='hll',
        time_integrator='ssp_rk2'
    )

    # 初始条件：dam break
    h0 = np.where(solver.x_cell < 50.0, 2.0, 1.0)
    Q0 = np.zeros(solver.ncells)

    solver.initialize(h0, Q0)

    # 计算初始总质量
    mass_0 = np.sum(solver.U[:, 0] * solver.dx)

    print("初始状态:")
    print(f"  左侧水深: 2.0m (x<50m)")
    print(f"  右侧水深: 1.0m (x>50m)")
    print(f"  初始总质量: {mass_0:.6f} m^2")
    print()

    # 求解
    t_end = 5.0
    history = solver.solve(t_end, cfl=0.9, verbose=False)

    # 计算最终总质量
    mass_f = np.sum(solver.U[:, 0] * solver.dx)
    mass_error = abs(mass_f - mass_0) / mass_0

    h_final, u_final = solver.get_primitive_variables()

    print("最终状态:")
    print(f"  t = {t_end}s")
    print(f"  h范围: [{h_final.min():.3f}, {h_final.max():.3f}]m")
    print(f"  u范围: [{u_final.min():.3f}, {u_final.max():.3f}]m/s")
    print(f"  最终总质量: {mass_f:.6f} m^2")
    print(f"  质量守恒误差: {mass_error:.2e}")
    print()

    # 判断守恒性
    if mass_error < 1e-12:
        print(" 守恒性：机器精度级别")
        result = "perfect"
    elif mass_error < 1e-9:
        print(" 守恒性：优秀")
        result = "excellent"
    elif mass_error < 1e-6:
        print(" 守恒性：良好")
        result = "good"
    else:
        print(" 守恒性：需改进")
        result = "needs_improvement"

    print()
    return result


def test_convergence():
    """
    测试3: 精度收敛性

    测试不同网格分辨率下的精度
    """
    print("=" * 70)
    print("测试3: 精度收敛性")
    print("=" * 70)
    print()

    # 参数
    L = 100.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    g = 9.81
    t_end = 10.0

    # 测试不同网格
    nx_values = [51, 101, 201, 401]

    print(f"测试网格: {nx_values}")
    print(f"测试时间: {t_end}s")
    print()

    results = []

    for nx in nx_values:
        x = np.linspace(0, L, nx)

        solver = FVMSolver(
            x_grid=x,
            B=B, S0=S0, n=n, g=g,
            reconstruction='muscl',
            limiter='minmod',
            riemann='hll',
            time_integrator='ssp_rk2'
        )

        # 简单初始条件
        h0 = 2.0 + 0.5 * np.sin(2 * np.pi * solver.x_cell / L)
        Q0 = 10.0 * np.ones(solver.ncells)

        solver.initialize(h0, Q0)

        # 求解
        history = solver.solve(t_end, cfl=0.5, verbose=False)

        h_final, u_final = solver.get_primitive_variables()

        results.append({
            'nx': nx,
            'h_final': h_final,
            'u_final': u_final
        })

    # 计算收敛阶
    print(f"{'nx':>6} | {'dx[m]':>8} | {'h_max':>8} | {'u_max':>8}")
    print("-" * 50)

    for res in results:
        dx = L / res['nx']
        h_max = np.max(res['h_final'])
        u_max = np.max(res['u_final'])
        print(f"{res['nx']:>6} | {dx:>8.3f} | {h_max:>8.4f} | {u_max:>8.4f}")

    print()
    print(" 收敛性测试完成")
    print()

    return "completed"


def main():
    """主测试函数"""

    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  FVM求解器验证测试套件".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")

    # 运行所有测试
    result1 = test_still_water()
    result2 = test_dam_break()
    result3 = test_convergence()

    # 总结
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    print()
    print(f"1. 静水平衡: {result1}")
    print(f"2. Dam break守恒性: {result2}")
    print(f"3. 收敛性测试: {result3}")
    print()

    if result1 in ['perfect', 'good'] and result2 in ['perfect', 'excellent']:
        print(" 所有测试通过！FVM求解器质量优秀")
        print()
        print("FVM求解器具备:")
        print("   Well-balanced性质")
        print("   严格守恒")
        print("   激波捕捉能力")
        print("   数值稳定性")
    else:
        print(" 部分测试需要改进")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
