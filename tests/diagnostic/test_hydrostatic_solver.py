"""
测试HydrostaticCanalSolver稳态求解

测试案例：
1. 简单渠道稳态流（无闸门）
2. 与理论解对比
3. 流量守恒验证
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append('.')

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from utils.canal_utils import compute_steady_uniform_flow


def test_simple_steady_flow():
    """测试简单渠道的稳态流"""
    print("=" * 70)
    print("HydrostaticCanalSolver 稳态流测试")
    print("=" * 70)

    # 参数
    L = 1000.0  # 渠道长度 (m)
    nx = 101     # 网格点数
    B = 10.0     # 渠道宽度 (m)
    S0 = 0.001   # 底坡
    n = 0.025    # Manning糙率
    g = 9.81

    Q_target = 10.0  # 目标流量 (m^3/s)

    print(f"\n渠道参数：")
    print(f"  长度：{L} m")
    print(f"  宽度：{B} m")
    print(f"  底坡：{S0}")
    print(f"  Manning糙率：{n}")
    print(f"  目标流量：{Q_target} m^3/s")

    # 计算理论均匀流水深
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n, g)
    print(f"\n理论均匀流水深：{h_uniform:.4f} m")

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=B,
        S0=S0,
        n=n,
        g=g
    )

    print(f"\n求解器设置：")
    print(f"  网格点数：{nx}")
    print(f"  网格间距：{solver.dx:.2f} m")
    print(f"  Preissmann参数：theta={solver.theta}, omega={solver.omega}")

    # 求解稳态
    print(f"\n开始稳态求解...")
    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_uniform,  # 使用理论均匀流水深作为下游边界
        max_iterations=3000,
        convergence_tol=0.001,
        dt=0.5,
        verbose=True
    )

    # 分析结果
    print(f"\n结果分析：")
    print(f"  收敛状态：{' 收敛' if result['converged'] else ' 未收敛'}")
    print(f"  迭代次数：{result['iterations']}")
    print(f"  流量守恒：")
    print(f"    目标流量：{Q_target:.3f} m^3/s")
    print(f"    实际流量：{result['Q_mean']:.3f} m^3/s")
    print(f"    误差：{result['Q_error_percent']:.2f}%")

    # 与理论解对比
    h_mean = np.mean(result['h'])
    h_error = abs(h_mean - h_uniform) / h_uniform * 100

    print(f"  水深对比：")
    print(f"    理论均匀流：{h_uniform:.4f} m")
    print(f"    数值解平均：{h_mean:.4f} m")
    print(f"    误差：{h_error:.2f}%")
    print(f"    数值解范围：[{result['h'].min():.4f}, {result['h'].max():.4f}] m")

    # 绘图
    print(f"\n生成图表...")

    fig, axes = plt.subplots(3, 1, figsize=(10, 9))

    x = solver.x

    # 图1：水深分布
    ax = axes[0]
    ax.plot(x, result['h'], 'b-', linewidth=2, label='Hydrostatic reconstruction')
    ax.axhline(h_uniform, color='r', linestyle='--', linewidth=1.5, label=f'Uniform flow theory ({h_uniform:.3f}m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title(f'Steady State Solution (Q={Q_target} m^3/s)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图2：流量分布
    ax = axes[1]
    ax.plot(x, result['Q'], 'g-', linewidth=2, label='Discharge')
    ax.axhline(Q_target, color='k', linestyle='--', linewidth=1.5, label=f'Target ({Q_target} m^3/s)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title(f'Mass Conservation (error={result["Q_error_percent"]:.2f}%)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图3：水位分布
    ax = axes[2]
    eta = result['h'] + solver.z
    ax.plot(x, eta, 'r-', linewidth=2, label='Water surface')
    ax.fill_between(x, solver.z, alpha=0.3, color='brown', label='Bed')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Elevation (m)')
    ax.set_title('Water Surface Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('hydrostatic_solver_test.png', dpi=150)
    print(f"  图表保存至：hydrostatic_solver_test.png")

    # 判断测试是否通过
    mass_ok = result['Q_error_percent'] < 5.0  # 5%容差
    depth_ok = h_error < 10.0  # 10%容差（考虑边界效应）
    converged_ok = result['converged']

    print(f"\n测试结果：")
    print(f"  流量守恒：{' PASS' if mass_ok else ' FAIL'} ({result['Q_error_percent']:.2f}% < 5%)")
    print(f"  水深精度：{' PASS' if depth_ok else ' FAIL'} ({h_error:.2f}% < 10%)")
    print(f"  收敛性：{' PASS' if converged_ok else ' FAIL'}")

    overall_pass = mass_ok and depth_ok and converged_ok

    print(f"\n总体结论：{' 测试通过' if overall_pass else ' 测试失败'}")
    print("=" * 70)

    return overall_pass, result


if __name__ == "__main__":
    success, result = test_simple_steady_flow()
    sys.exit(0 if success else 1)
