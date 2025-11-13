#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
渐变流水面线解析解验证 (Gradually Varied Flow)

理论基础
    dy/dx = (S0 - Sf) / (1 - Fr^2)

水面线分类根据水深与正常水深yn临界水深yc的关系
- M1曲线: 壅水曲线 (y > yn > yc) - 堰前壅水
- M2曲线: 降水曲线 (yn > y > yc) - 堰后降水
- M3曲线: 降水曲线 (yn > yc > y) - 陡坡后

验证方法
1. 用标准步长法计算解析解Runge-Kutta积分
2. 用HydroClaude数值求解器计算
3. 对比水位剖面

验收标准
- 水位RMSE < 0.02m
- 最大误差 < 0.05m
- 水面线形态正确

参考
- Chow (1959) "Open-Channel Hydraulics", Chapter 10
- Henderson (1966) "Open Channel Flow"
- HEC-RAS Hydraulic Reference Manual

作者HydroClaude Team
日期2025-10-28
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def compute_normal_depth(Q: float, b: float, S0: float, n: float, g: float = 9.81) -> float:
    """
    计算正常水深 (Normal Depth)

    Manning公式: Q = (1/n) * A * R^(2/3) * sqrt(S0)
    矩形断面: A = b*y, R = b*y/(b+2*y)

    Args:
        Q: 流量 (m^3/s)
        b: 渠宽 (m)
        S0: 底坡
        n: 曼宁系数
        g: 重力加速度

    Returns:
        正常水深 yn (m)
    """
    def manning_residual(y):
        """Manning公式残差"""
        A = b * y
        P = b + 2 * y
        R = A / P
        Q_calc = (1/n) * A * (R ** (2.0/3.0)) * np.sqrt(S0)
        return Q_calc - Q

    # 用二分法求解
    y_min, y_max = 0.01, 20.0
    for _ in range(100):
        y_mid = (y_min + y_max) / 2
        res = manning_residual(y_mid)

        if abs(res) < 1e-6:
            return y_mid

        if res > 0:
            y_max = y_mid
        else:
            y_min = y_mid

    return y_mid


def compute_critical_depth(Q: float, b: float, g: float = 9.81) -> float:
    """
    计算临界水深 (Critical Depth)

    临界流条件: Fr = 1
    矩形断面: yc = (Q^2/(g*b^2))^(1/3)

    Args:
        Q: 流量 (m^3/s)
        b: 渠宽 (m)
        g: 重力加速度

    Returns:
        临界水深 yc (m)
    """
    yc = (Q**2 / (g * b**2)) ** (1.0/3.0)
    return yc


def analytical_solution_M1(Q: float, b: float, S0: float, n: float,
                           h_downstream: float, L: float,
                           n_points: int = 500, g: float = 9.81):
    """
    M1壅水曲线解析解

    场景缓坡渠道末端有堰形成壅水

    Args:
        Q: 流量 (m^3/s)
        b: 渠宽 (m)
        S0: 底坡
        n: 曼宁系数
        h_downstream: 下游边界水深 (堰顶水深> yn)
        L: 渠道长度 (m)
        n_points: 计算点数
        g: 重力加速度

    Returns:
        x, y: 距离和水深数组
    """
    # 计算正常水深和临界水深
    yn = compute_normal_depth(Q, b, S0, n, g)
    yc = compute_critical_depth(Q, b, g)

    print(f"正常水深 yn = {yn:.3f} m")
    print(f"临界水深 yc = {yc:.3f} m")
    print(f"下游水深 h_down = {h_downstream:.3f} m")

    # 验证是M1曲线
    assert h_downstream > yn > yc, "不是M1曲线条件"

    # 水面线微分方程: dy/dx = (S0 - Sf) / (1 - Fr^2)
    def water_surface_ode(x, y):
        """水面线微分方程"""
        if y <= 0:
            return 0

        # 几何参数
        A = b * y
        P = b + 2 * y
        R = A / P

        # 流速
        V = Q / A

        # 摩阻坡度Manning公式
        Sf = (n * V / (R ** (2.0/3.0))) ** 2

        # 弗劳德数
        Fr = V / np.sqrt(g * y)

        # 水面线方程
        dy_dx = (S0 - Sf) / (1 - Fr**2)

        return dy_dx

    # 从下游向上游积分
    x_span = [L, 0]
    x_eval = np.linspace(L, 0, n_points)

    # 使用solve_ivp求解ODE
    sol = solve_ivp(water_surface_ode, x_span, [h_downstream],
                    t_eval=x_eval, method='RK45', rtol=1e-6)

    # 反转数组从上游到下游
    x = sol.t[::-1]
    y = sol.y[0][::-1]

    return x, y, yn, yc


def validate_M1_curve():
    """验证M1壅水曲线"""

    print("=" * 80)
    print("M1壅水曲线验证 (Backwater Curve)")
    print("=" * 80)

    # 参数设置
    b = 10.0      # 渠宽 (m)
    Q = 20.0      # 流量 (m^3/s)
    S0 = 0.0001   # 底坡缓坡
    n = 0.025     # 曼宁系数
    L = 5000.0    # 渠长 (m)
    g = 9.81      # 重力加速度

    # 先计算正常水深以确定合适的下游边界
    yn_temp = compute_normal_depth(Q, b, S0, n, g)

    # 下游边界堰顶水深壅水必须大于正常水深
    h_downstream = yn_temp * 1.2  # 比正常水深高20%

    print(f"\n参数设置:")
    print(f"  渠宽 b = {b} m")
    print(f"  流量 Q = {Q} m^3/s")
    print(f"  底坡 S0 = {S0}")
    print(f"  曼宁系数 n = {n}")
    print(f"  渠长 L = {L} m")
    print(f"  下游水深 = {h_downstream} m\n")

    # 1. 计算解析解
    print("[1] 计算解析解 (标准步长法)...")
    x_analytical, y_analytical, yn, yc = analytical_solution_M1(
        Q, b, S0, n, h_downstream, L
    )
    print(f" 解析解计算完成\n")

    # 2. 用HydroClaude求解
    print("[2] HydroClaude数值求解...")

    n_cells = 500
    solver = GodunvFVMSolver(
        width=b,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        g=g,
        cfl = 0.3
    )

    # 初始条件线性插值从下游水深到上游接近正常水深
    h_upstream_init = yn + (h_downstream - yn) * 0.1
    solver.h = np.linspace(h_upstream_init, h_downstream, n_cells)
    solver.Q = Q * np.ones(n_cells)

    # 边界条件
    # 上游固定流量
    # 下游固定水深堰顶
    solver.bc_left = {'type': 'Q', 'value': Q}
    solver.bc_right = {'type': 'h', 'value': h_downstream}

    # 时间推进到稳态
    print("  时间推进到稳态...")
    t_max = 50000.0  # s
    dt = 10.0
    t = 0

    # 记录初始质量
    solver.initial_mass = np.sum(solver.h * solver.dx * b)

    convergence_threshold = 1e-5
    prev_h = solver.h.copy()

    n_steps = 0
    while t < t_max:
        # 时间步进
        solver.step()
        t += solver.dt
        n_steps += 1

        # 检查收敛
        if n_steps % 100 == 0:
            delta = np.max(np.abs(solver.h - prev_h))
            if delta < convergence_threshold:
                print(f"  收敛! t = {t:.1f}s, Deltah_max = {delta:.2e}m")
                break
            prev_h = solver.h.copy()

            if n_steps % 1000 == 0:
                print(f"  t = {t:.1f}s, Deltah_max = {delta:.2e}m")

    print(f" 数值求解完成 ({n_steps}步)\n")

    # 3. 对比分析
    print("[3] 结果对比...")

    # 插值到相同的x坐标
    y_numerical = np.interp(x_analytical, solver.x, solver.h)

    # 误差分析
    errors = np.abs(y_analytical - y_numerical)
    rmse = np.sqrt(np.mean(errors**2))
    max_error = np.max(errors)
    mean_error = np.mean(errors)

    print(f"  RMSE = {rmse:.4f} m")
    print(f"  最大误差 = {max_error:.4f} m")
    print(f"  平均误差 = {mean_error:.4f} m")

    # 4. 绘图
    print("\n[4] 生成对比图...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # 子图1水面线对比
    ax1.plot(x_analytical, y_analytical, 'k-', linewidth=2, label='解析解')
    ax1.plot(solver.x, solver.h, 'r--', linewidth=1.5, label='HydroClaude')
    ax1.axhline(yn, color='b', linestyle=':', label=f'正常水深 yn={yn:.3f}m')
    ax1.axhline(yc, color='g', linestyle=':', label=f'临界水深 yc={yc:.3f}m')

    ax1.set_xlabel('距离 x (m)', fontsize=12)
    ax1.set_ylabel('水深 y (m)', fontsize=12)
    ax1.set_title('M1壅水曲线对比', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    # 子图2误差分布
    ax2.plot(x_analytical, errors * 1000, 'r-', linewidth=1.5)
    ax2.axhline(rmse * 1000, color='b', linestyle='--', label=f'RMSE={rmse*1000:.2f}mm')
    ax2.set_xlabel('距离 x (m)', fontsize=12)
    ax2.set_ylabel('误差 (mm)', fontsize=12)
    ax2.set_title('水位误差分布', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('validation_M1_curve.png', dpi=300, bbox_inches='tight')
    print(f" 图表已保存: validation_M1_curve.png\n")

    # 5. 验证判断
    print("=" * 80)
    print("验证结果")
    print("=" * 80)

    tolerance_rmse = 0.02  # m
    tolerance_max = 0.05   # m

    passed = True

    if rmse < tolerance_rmse:
        print(f" RMSE测试通过: {rmse:.4f}m < {tolerance_rmse}m")
    else:
        print(f" RMSE测试失败: {rmse:.4f}m >= {tolerance_rmse}m")
        passed = False

    if max_error < tolerance_max:
        print(f" 最大误差测试通过: {max_error:.4f}m < {tolerance_max}m")
    else:
        print(f" 最大误差测试失败: {max_error:.4f}m >= {tolerance_max}m")
        passed = False

    print("=" * 80)

    if passed:
        print(" M1壅水曲线验证通过!")
    else:
        print(" M1壅水曲线验证失败!")

    print("=" * 80 + "\n")

    return {
        'test_name': 'M1_backwater_curve',
        'passed': passed,
        'rmse': rmse,
        'max_error': max_error,
        'mean_error': mean_error,
        'tolerance_rmse': tolerance_rmse,
        'tolerance_max': tolerance_max
    }


if __name__ == '__main__':
    result = validate_M1_curve()

    # 返回测试状态
    import sys
    sys.exit(0 if result['passed'] else 1)
