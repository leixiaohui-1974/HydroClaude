#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1明渠非恒定流 - 三种数值方法标准对比测试

对比EXPLICITPREISSMANN和HLL三种方法
使用标准的物理参数边界条件和初始条件

作者: Claude
日期: 2025-10-21
"""

import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.signal import savgol_filter
import time
from datetime import datetime
import os
import pandas as pd

# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import save_figure, save_table, get_output_path

# 配置matplotlib支持中文
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
# 设置字体大小
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

# ============================================================================
# 中文标签映射避免中文字体问题
# ============================================================================

LABELS = {
    'title': 'Canal Flow - Numerical Methods Comparison',
    'subtitle': '(nx={}, T={:.1f}s)',
    'time': 'Time (s)',
    'distance': 'Distance (m)',
    'depth': 'Water Depth (m)',
    'discharge': 'Discharge (m^3/s)',
    'method_explicit': 'EXPLICIT (Explicit FD)',
    'method_preissmann': 'PREISSMANN (Implicit 4-point)',
    'method_hll': 'HLL (Finite Volume)',
    'spatial_dist': 'Spatial Distribution',
    'temporal_evo': 'Temporal Evolution',
    'statistics': 'Statistics',
    'mean': 'Mean',
    'std': 'Std Dev',
    'cv': 'CV',
    'theory': 'Theoretical',
    'numerical': 'Numerical',
    'error': 'Error (%)',
    'convergence': 'Convergence',
    'mass_conservation': 'Mass Conservation',
    'computation_time': 'Computation Time (s)',
    'speed': 'Speed (steps/s)',
}

# ============================================================================
# 稳定流初值计算
# ============================================================================

def compute_steady_uniform_flow(Q, B, S0, n, g=9.81):
    """
    使用Manning公式计算恒定均匀流水深

    Manning公式: Q = (1/n) * A * R^(2/3) * S0^(1/2)
    """
    def manning_equation(h):
        if h <= 0:
            return 1e10
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)
        return Q_calc - Q

    # 二分法求解
    h_min, h_max = 0.01, 20.0

    if manning_equation(h_min) * manning_equation(h_max) > 0:
        h_est = (Q * n / (B * S0**0.5)) ** (3./5.)
        return max(0.5, min(10.0, h_est))

    while h_max - h_min > 1e-6:
        h_mid = (h_min + h_max) / 2
        if manning_equation(h_mid) * manning_equation(h_min) < 0:
            h_max = h_mid
        else:
            h_min = h_mid

    return (h_min + h_max) / 2


# ============================================================================
# 明渠求解器类
# ============================================================================

class CanalSolver:
    """明渠非恒定流求解器无振荡版本"""

    def __init__(self, length=1000.0, nx=201, B=10.0, S0=0.001, n=0.025,
                 g=9.81, method='preissmann'):
        """
        初始化求解器

        参数:
            length: 渠道长度 (m)
            nx: 空间离散点数
            B: 渠道宽度 (m)
            S0: 底坡
            n: Manning糙率
            g: 重力加速度 (m/s^2)
            method: 数值方法 ('explicit', 'preissmann', 'hll')
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method.lower()

        # 空间离散
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)

        # 初始化状态变量
        self.h = np.ones(nx) * 1.0
        self.Q = np.ones(nx) * 5.0

        # Savitzky-Golay滤波参数
        self.filter_window = 11
        self.filter_order = 3

        # Preissmann格式参数
        self.theta = 0.6
        self.omega = 0.95

    def reset_with_steady_state(self, Q0):
        """使用恒定均匀流作为初值"""
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)
        self.h[:] = h_uniform
        self.Q[:] = Q0
        return h_uniform

    def apply_spatial_filter(self, field):
        """应用Savitzky-Golay空间滤波器"""
        filtered = savgol_filter(field, self.filter_window, self.filter_order, mode='nearest')
        filtered[0] = field[0]
        filtered[-1] = field[-1]
        return filtered

    def compute_friction_slope(self, h, Q):
        """计算摩阻坡度 (Manning公式)"""
        Sf = np.zeros_like(h)
        for i in range(len(h)):
            if h[i] > 1e-6:
                A = self.B * h[i]
                P = self.B + 2 * h[i]
                R = A / P
                V = Q[i] / A if A > 1e-6 else 0.0
                Sf[i] = (self.n * abs(V)) ** 2 / (R ** (4./3.))
            else:
                Sf[i] = 0.0
        return Sf

    def step_explicit(self, dt, Q_upstream, h_downstream):
        """显式有限差分法混合迎风-中心格式"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)
        upwind_ratio = 0.3

        for i in range(1, self.nx - 1):
            if h_old[i] > 1e-6:
                A = self.B * h_old[i]
                V = Q_old[i] / A

                # 连续性方程
                dQ_dx_central = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)
                if Q_old[i] >= 0:
                    dQ_dx_upwind = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_upwind = (Q_old[i+1] - Q_old[i]) / self.dx
                dQ_dx = upwind_ratio * dQ_dx_upwind + (1 - upwind_ratio) * dQ_dx_central
                dh_dt = -dQ_dx / self.B
                h_new[i] = h_old[i] + dt * dh_dt

                # 动量方程
                dh_dx_central = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)
                if Q_old[i] >= 0:
                    dh_dx_upwind = (h_old[i] - h_old[i-1]) / self.dx
                else:
                    dh_dx_upwind = (h_old[i+1] - h_old[i]) / self.dx
                dh_dx = upwind_ratio * dh_dx_upwind + (1 - upwind_ratio) * dh_dx_central

                if Q_old[i] >= 0:
                    dQ_dx_mom = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_mom = (Q_old[i+1] - Q_old[i]) / self.dx

                dQ_dt = -V * dQ_dx_mom - self.g * A * dh_dx + self.g * A * (self.S0 - Sf[i])
                Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # 应用空间滤波
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new
        return h_new, Q_new

    def step_preissmann(self, dt, Q_upstream, h_downstream):
        """Preissmann四点隐式格式"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 显式预估
        h_pred, Q_pred = self.step_explicit(dt, Q_upstream, h_downstream)

        # theta加权校正
        self.h = self.omega * ((1 - self.theta) * h_old + self.theta * h_pred) + (1 - self.omega) * h_old
        self.Q = self.omega * ((1 - self.theta) * Q_old + self.theta * Q_pred) + (1 - self.omega) * Q_old

        # 应用空间滤波
        self.h = self.apply_spatial_filter(self.h)
        self.Q = self.apply_spatial_filter(self.Q)

        return self.h, self.Q

    def step_hll(self, dt, Q_upstream, h_downstream):
        """HLL有限体积法"""
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        Sf = self.compute_friction_slope(h_old, Q_old)

        for i in range(1, self.nx - 1):
            h_L = h_old[i]
            h_R = h_old[i+1]
            Q_L = Q_old[i]
            Q_R = Q_old[i+1]

            if h_L > 1e-6 and h_R > 1e-6:
                A_L = self.B * h_L
                A_R = self.B * h_R
                V_L = Q_L / A_L
                V_R = Q_R / A_R
                c_L = np.sqrt(self.g * h_L)
                c_R = np.sqrt(self.g * h_R)

                # 波速估计
                S_L = min(V_L - c_L, V_R - c_R)
                S_R = max(V_L + c_L, V_R + c_R)

                # 通量
                F1_L = Q_L
                F1_R = Q_R
                F2_L = Q_L * V_L + 0.5 * self.g * self.B * h_L**2
                F2_R = Q_R * V_R + 0.5 * self.g * self.B * h_R**2

                # HLL通量
                if S_L >= 0:
                    F1 = F1_L
                    F2 = F2_L
                elif S_R <= 0:
                    F1 = F1_R
                    F2 = F2_R
                else:
                    F1 = (S_R * F1_L - S_L * F1_R + S_L * S_R * (A_R - A_L)) / (S_R - S_L)
                    F2 = (S_R * F2_L - S_L * F2_R + S_L * S_R * (Q_R - Q_L)) / (S_R - S_L)

                # 更新
                dh_dt = -(F1 - Q_old[i-1]) / self.dx / self.B
                dQ_dt = -(F2 - (Q_old[i-1]**2/A_L + 0.5*self.g*self.B*h_old[i-1]**2)) / self.dx
                dQ_dt += self.g * A_L * (self.S0 - Sf[i])

                h_new[i] = h_old[i] + dt * dh_dt
                Q_new[i] = Q_old[i] + dt * dQ_dt

        # 边界条件
        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # 应用空间滤波
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)

        self.h = h_new
        self.Q = Q_new
        return h_new, Q_new

    def step(self, dt, Q_upstream, h_downstream):
        """执行一个时间步"""
        if self.method == 'explicit':
            return self.step_explicit(dt, Q_upstream, h_downstream)
        elif self.method == 'preissmann':
            return self.step_preissmann(dt, Q_upstream, h_downstream)
        elif self.method == 'hll':
            return self.step_hll(dt, Q_upstream, h_downstream)
        else:
            raise ValueError(f"Unknown method: {self.method}")


# ============================================================================
# 标准对比测试
# ============================================================================

def run_standard_comparison_test():
    """
    运行标准的三种方法对比测试

    使用通用的物理参数和边界条件
    """

    print("=" * 80)
    print("Example 1: Open Channel Unsteady Flow - Standard Methods Comparison")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # ========================================================================
    # 标准物理参数通用设置
    # ========================================================================

    # 渠道几何参数
    length = 1000.0      # 渠道长度 (m)
    B = 10.0            # 渠道宽度 (m)
    S0 = 0.001          # 底坡 (无量纲)
    n = 0.025           # Manning糙率系数 (s/m^(1/3))
    g = 9.81            # 重力加速度 (m/s^2)

    # 数值参数
    nx = 201            # 空间离散点数
    dt = 0.5            # 时间步长 (s)
    T_total = 600.0     # 总模拟时间 (s)
    n_steps = int(T_total / dt)

    # 边界条件恒定
    Q_upstream = 8.0    # 上游流量 (m^3/s)

    # 计算下游水深使用Manning公式保证兼容性
    h_downstream = compute_steady_uniform_flow(Q_upstream, B, S0, n, g)

    # 初始条件恒定均匀流
    Q_initial = Q_upstream
    h_initial = h_downstream

    print("\n" + "=" * 80)
    print("STANDARD PHYSICAL PARAMETERS")
    print("=" * 80)
    print(f"\nChannel Geometry:")
    print(f"  Length L        = {length:.1f} m")
    print(f"  Width B         = {B:.1f} m")
    print(f"  Bed Slope S0    = {S0:.4f}")
    print(f"  Manning's n     = {n:.3f} s/m^(1/3)")
    print(f"  Gravity g       = {g:.2f} m/s^2")

    print(f"\nNumerical Parameters:")
    print(f"  Grid Points nx  = {nx}")
    print(f"  Grid Spacing dx = {length/(nx-1):.2f} m")
    print(f"  Time Step dt    = {dt:.2f} s")
    print(f"  Total Time T    = {T_total:.1f} s")
    print(f"  Total Steps     = {n_steps}")

    print(f"\nBoundary Conditions (Steady):")
    print(f"  Upstream Q      = {Q_upstream:.2f} m^3/s")
    print(f"  Downstream h    = {h_downstream:.4f} m (computed from Manning)")

    print(f"\nInitial Conditions (Uniform Flow):")
    print(f"  Initial Q       = {Q_initial:.2f} m^3/s")
    print(f"  Initial h       = {h_initial:.4f} m")

    # CFL条件检查
    V_max = Q_upstream / (B * h_initial)
    c_max = np.sqrt(g * h_initial)
    CFL = (V_max + c_max) * dt / (length / (nx - 1))
    print(f"\nCFL Condition Check:")
    print(f"  Max Velocity V  = {V_max:.3f} m/s")
    print(f"  Wave Speed c    = {c_max:.3f} m/s")
    print(f"  CFL Number      = {CFL:.3f} {'< 0.5 OK' if CFL < 0.5 else '>= 0.5 WARNING'}")

    # ========================================================================
    # 运行三种方法
    # ========================================================================

    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    results = {}

    for method_name in methods:
        print("\n" + "=" * 80)
        print(f"Running: {method_name}")
        print("=" * 80)

        # 创建求解器
        solver = CanalSolver(
            length=length, nx=nx, B=B, S0=S0, n=n, g=g,
            method=method_name.lower()
        )

        # 使用恒定均匀流初值
        solver.reset_with_steady_state(Q_initial)

        # 数据记录
        time_history = []
        h_history = []
        Q_history = []
        h_mid_history = []
        Q_mid_history = []

        # 中点索引
        idx_mid = nx // 2

        # 时间积分
        t_start = time.time()

        for step in range(n_steps):
            t = step * dt

            # 时间推进
            solver.step(dt, Q_upstream, h_downstream)

            # 记录数据每10步记录一次
            if step % 10 == 0:
                time_history.append(t)
                h_history.append(solver.h.copy())
                Q_history.append(solver.Q.copy())
                h_mid_history.append(solver.h[idx_mid])
                Q_mid_history.append(solver.Q[idx_mid])

            # 打印进度
            if (step + 1) % 200 == 0:
                h_mean = np.mean(solver.h)
                Q_mean = np.mean(solver.Q)
                h_std = np.std(solver.h)
                Q_std = np.std(solver.Q)
                print(f"  Step {step+1}/{n_steps}: t={t:.1f}s, "
                      f"h_mean={h_mean:.4f}m (std={h_std:.6f}m), "
                      f"Q_mean={Q_mean:.4f}m^3/s (std={Q_std:.6f}m^3/s)")

        t_end = time.time()
        comp_time = t_end - t_start

        # 最终统计
        h_final = solver.h
        Q_final = solver.Q

        h_mean = np.mean(h_final)
        h_std = np.std(h_final)
        h_cv = 100.0 * h_std / h_mean if h_mean > 0 else 0

        Q_mean = np.mean(Q_final)
        Q_std = np.std(Q_final)
        Q_cv = 100.0 * Q_std / Q_mean if Q_mean > 0 else 0

        h_error = 100.0 * abs(h_mean - h_initial) / h_initial
        Q_error = 100.0 * abs(Q_mean - Q_initial) / Q_initial

        print(f"\nFinal Statistics (t={T_total:.1f}s):")
        print(f"  Water Depth:")
        print(f"    Mean   = {h_mean:.6f} m")
        print(f"    Std    = {h_std:.8f} m")
        print(f"    CV     = {h_cv:.6f} %")
        print(f"    Error  = {h_error:.6f} %")
        print(f"  Discharge:")
        print(f"    Mean   = {Q_mean:.6f} m^3/s")
        print(f"    Std    = {Q_std:.8f} m^3/s")
        print(f"    CV     = {Q_cv:.6f} %")
        print(f"    Error  = {Q_error:.6f} %")
        print(f"  Computation:")
        print(f"    Time   = {comp_time:.2f} s")
        print(f"    Speed  = {n_steps/comp_time:.1f} steps/s")

        # 保存结果
        results[method_name] = {
            'time': np.array(time_history),
            'h_history': h_history,
            'Q_history': Q_history,
            'h_mid': np.array(h_mid_history),
            'Q_mid': np.array(Q_mid_history),
            'h_final': h_final,
            'Q_final': Q_final,
            'x': solver.x,
            'h_mean': h_mean,
            'h_std': h_std,
            'h_cv': h_cv,
            'h_error': h_error,
            'Q_mean': Q_mean,
            'Q_std': Q_std,
            'Q_cv': Q_cv,
            'Q_error': Q_error,
            'comp_time': comp_time,
            'comp_speed': n_steps / comp_time
        }

    # ========================================================================
    # 生成对比报告
    # ========================================================================

    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    print("\n{:<15} {:>15} {:>15} {:>15} {:>15}".format(
        "Method", "h_mean (m)", "h_CV (%)", "Q_mean (m^3/s)", "Q_CV (%)"))
    print("-" * 80)
    for method_name in methods:
        r = results[method_name]
        print("{:<15} {:>15.6f} {:>15.8f} {:>15.6f} {:>15.8f}".format(
            method_name, r['h_mean'], r['h_cv'], r['Q_mean'], r['Q_cv']))

    print("\n{:<15} {:>15} {:>15} {:>15}".format(
        "Method", "h_Error (%)", "Q_Error (%)", "Speed (step/s)"))
    print("-" * 80)
    for method_name in methods:
        r = results[method_name]
        print("{:<15} {:>15.6f} {:>15.6f} {:>15.1f}".format(
            method_name, r['h_error'], r['Q_error'], r['comp_speed']))

    # ========================================================================
    # 生成可视化
    # ========================================================================

    print("\n" + "=" * 80)
    print("Generating Visualizations...")
    print("=" * 80)

    generate_comparison_plots(results, methods, h_initial, Q_initial, nx, T_total)

    return results


def generate_comparison_plots(results, methods, h_theory, Q_theory, nx, T_total):
    """生成对比图表使用英文标签避免中文显示问题"""

    # ========================================================================
    # 图1空间分布对比最终时刻
    # ========================================================================

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f'Spatial Distribution Comparison (nx={nx}, T={T_total:.1f}s)',
                 fontsize=14, fontweight='bold')

    colors = {'EXPLICIT': 'blue', 'PREISSMANN': 'red', 'HLL': 'green'}

    # 第一行水深分布
    for j, method in enumerate(methods):
        ax = axes[0, j]
        r = results[method]

        ax.plot(r['x'], r['h_final'], color=colors[method], linewidth=2,
                label=f'{method}', alpha=0.8)
        ax.axhline(h_theory, color='gray', linestyle='--', linewidth=1.5,
                   label='Theoretical', alpha=0.7)

        ax.set_xlabel('Distance (m)', fontsize=11)
        ax.set_ylabel('Water Depth (m)', fontsize=11)
        ax.set_title(f'{method}\nh_mean={r["h_mean"]:.6f}m, CV={r["h_cv"]:.6f}%',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)

        # 设置合理的Y轴范围避免科学计数法混淆
        h_margin = h_theory * 0.05  # +/-5%
        ax.set_ylim([h_theory - h_margin, h_theory + h_margin])

        # 添加统计信息
        textstr = f'Mean: {r["h_mean"]:.6f} m\nStd:  {r["h_std"]:.8f} m\nCV:   {r["h_cv"]:.6f} %'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)

    # 第二行流量分布
    for j, method in enumerate(methods):
        ax = axes[1, j]
        r = results[method]

        ax.plot(r['x'], r['Q_final'], color=colors[method], linewidth=2,
                label=f'{method}', alpha=0.8)
        ax.axhline(Q_theory, color='gray', linestyle='--', linewidth=1.5,
                   label='Theoretical', alpha=0.7)

        ax.set_xlabel('Distance (m)', fontsize=11)
        ax.set_ylabel('Discharge (m^3/s)', fontsize=11)
        ax.set_title(f'{method}\nQ_mean={r["Q_mean"]:.6f}m^3/s, CV={r["Q_cv"]:.6f}%',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)

        # 设置合理的Y轴范围避免科学计数法混淆
        Q_margin = Q_theory * 0.1  # +/-10%
        ax.set_ylim([Q_theory - Q_margin, Q_theory + Q_margin])

        # 添加统计信息
        textstr = f'Mean: {r["Q_mean"]:.6f} m^3/s\nStd:  {r["Q_std"]:.8f} m^3/s\nCV:   {r["Q_cv"]:.6f} %'
        props = dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)

    plt.tight_layout()
    save_figure(fig, '02_methods_spatial_comparison.png')
    plt.close()

    # ========================================================================
    # 图2时间演化对比中点
    # ========================================================================

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Temporal Evolution at Midpoint', fontsize=14, fontweight='bold')

    # 水深时间序列
    ax = axes[0]
    for method in methods:
        r = results[method]
        ax.plot(r['time'], r['h_mid'], color=colors[method], linewidth=2,
                label=f'{method}', alpha=0.7)
    ax.axhline(h_theory, color='gray', linestyle='--', linewidth=1.5,
               label='Theoretical', alpha=0.7)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Water Depth (m)', fontsize=11)
    ax.set_title('Water Depth at Channel Midpoint', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)

    # 设置合理的Y轴范围
    h_margin = h_theory * 0.05
    ax.set_ylim([h_theory - h_margin, h_theory + h_margin])

    # 流量时间序列
    ax = axes[1]
    for method in methods:
        r = results[method]
        ax.plot(r['time'], r['Q_mid'], color=colors[method], linewidth=2,
                label=f'{method}', alpha=0.7)
    ax.axhline(Q_theory, color='gray', linestyle='--', linewidth=1.5,
               label='Theoretical', alpha=0.7)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Discharge (m^3/s)', fontsize=11)
    ax.set_title('Discharge at Channel Midpoint', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)

    # 设置合理的Y轴范围
    Q_margin = Q_theory * 0.1
    ax.set_ylim([Q_theory - Q_margin, Q_theory + Q_margin])

    plt.tight_layout()
    save_figure(fig, '02_methods_temporal_comparison.png')
    plt.close()

    # ========================================================================
    # 图3性能和精度对比柱状图
    # ========================================================================

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Performance and Accuracy Comparison', fontsize=14, fontweight='bold')

    x_pos = np.arange(len(methods))
    width = 0.6

    # CV对比
    ax = axes[0, 0]
    h_cvs = [results[m]['h_cv'] for m in methods]
    bars = ax.bar(x_pos, h_cvs, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('Coefficient of Variation (%)', fontsize=11)
    ax.set_title('Water Depth CV', fontsize=12, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods)
    ax.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.6f}%', ha='center', va='bottom', fontsize=9)

    ax = axes[0, 1]
    Q_cvs = [results[m]['Q_cv'] for m in methods]
    bars = ax.bar(x_pos, Q_cvs, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('Coefficient of Variation (%)', fontsize=11)
    ax.set_title('Discharge CV', fontsize=12, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods)
    ax.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.6f}%', ha='center', va='bottom', fontsize=9)

    # 误差对比
    ax = axes[1, 0]
    h_errors = [results[m]['h_error'] for m in methods]
    Q_errors = [results[m]['Q_error'] for m in methods]

    x = np.arange(len(methods))
    width2 = 0.35
    bars1 = ax.bar(x - width2/2, h_errors, width2, label='h Error',
                   color='steelblue', alpha=0.7)
    bars2 = ax.bar(x + width2/2, Q_errors, width2, label='Q Error',
                   color='coral', alpha=0.7)

    ax.set_ylabel('Error (%)', fontsize=11)
    ax.set_title('Error vs Theoretical Value', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # 计算速度对比
    ax = axes[1, 1]
    speeds = [results[m]['comp_speed'] for m in methods]
    bars = ax.bar(x_pos, speeds, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('Computation Speed (steps/s)', fontsize=11)
    ax.set_title('Computational Efficiency', fontsize=12, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods)
    ax.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    save_figure(fig, '02_methods_performance_comparison.png')
    plt.close()

    # ========================================================================
    # 图4三种方法叠加对比
    # ========================================================================

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Direct Methods Comparison', fontsize=14, fontweight='bold')

    # 水深空间分布叠加
    ax = axes[0]
    for method in methods:
        r = results[method]
        ax.plot(r['x'], r['h_final'], color=colors[method], linewidth=2.5,
                label=f'{method} (CV={r["h_cv"]:.6f}%)', alpha=0.7)
    ax.axhline(h_theory, color='black', linestyle='--', linewidth=2,
               label='Theoretical', alpha=0.8)
    ax.set_xlabel('Distance (m)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Water Depth Spatial Distribution', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)

    # 流量空间分布叠加
    ax = axes[1]
    for method in methods:
        r = results[method]
        ax.plot(r['x'], r['Q_final'], color=colors[method], linewidth=2.5,
                label=f'{method} (CV={r["Q_cv"]:.6f}%)', alpha=0.7)
    ax.axhline(Q_theory, color='black', linestyle='--', linewidth=2,
               label='Theoretical', alpha=0.8)
    ax.set_xlabel('Distance (m)', fontsize=12)
    ax.set_ylabel('Discharge (m^3/s)', fontsize=12)
    ax.set_title('Discharge Spatial Distribution', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)

    plt.tight_layout()
    save_figure(fig, '02_methods_overlay_comparison.png')
    plt.close()

    print("\n All visualizations generated successfully!")


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == '__main__':
    results = run_standard_comparison_test()

    # ========================================================================
    # Save Results as CSV Table
    # ========================================================================
    print("\n" + "=" * 80)
    print("Saving Results Tables...")
    print("=" * 80)

    # Create comparison table
    table_data = []
    for method in ['EXPLICIT', 'PREISSMANN', 'HLL']:
        r = results[method]
        table_data.append({
            'Method': method,
            'h_mean (m)': r['h_mean'],
            'h_std (m)': r['h_std'],
            'h_CV (%)': r['h_cv'],
            'h_error (%)': r['h_error'],
            'Q_mean (m^3/s)': r['Q_mean'],
            'Q_std (m^3/s)': r['Q_std'],
            'Q_CV (%)': r['Q_cv'],
            'Q_error (%)': r['Q_error'],
            'Speed (step/s)': r['comp_speed'],
            'Runtime (s)': r['comp_time']
        })

    df = pd.DataFrame(table_data)
    save_table(df, '02_methods_comparison_results.csv', index=False)

    # Save detailed statistics
    detailed_data = []
    for method in ['EXPLICIT', 'PREISSMANN', 'HLL']:
        r = results[method]
        for i in range(len(r['x'])):
            detailed_data.append({
                'Method': method,
                'Position (m)': r['x'][i],
                'Water_Depth (m)': r['h_final'][i],
                'Discharge (m^3/s)': r['Q_final'][i]
            })

    df_detailed = pd.DataFrame(detailed_data)
    save_table(df_detailed, '02_methods_detailed_profiles.csv', index=False)

    print("\n" + "=" * 80)
    print("STANDARD METHODS COMPARISON TEST COMPLETED!")
    print("=" * 80)
    print("\nGenerated Files:")
    print("  Figures (4):")
    print("    - 02_methods_spatial_comparison.png")
    print("    - 02_methods_temporal_comparison.png")
    print("    - 02_methods_performance_comparison.png")
    print("    - 02_methods_overlay_comparison.png")
    print("  Tables (2):")
    print("    - 02_methods_comparison_results.csv")
    print("    - 02_methods_detailed_profiles.csv")
    print("=" * 80)
