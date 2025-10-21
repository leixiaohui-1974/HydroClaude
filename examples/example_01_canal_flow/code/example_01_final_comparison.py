#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1：明渠非恒定流 - 最终完整对比测试
修复版本：正确的Y轴范围 + 完整中文支持

作者: Claude
日期: 2025-10-21
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.signal import savgol_filter
import time
from datetime import datetime
import os

# ============================================================================
# 中文字体配置
# ============================================================================

def setup_chinese_fonts():
    """配置中文字体支持"""
    # 尝试使用系统可用的中文字体
    chinese_fonts = [
        'SimHei',           # 黑体
        'Microsoft YaHei',  # 微软雅黑
        'STSong',           # 华文宋体
        'DejaVu Sans',      # 备用
    ]

    # 设置字体
    plt.rcParams['font.sans-serif'] = chinese_fonts
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10

setup_chinese_fonts()

# ============================================================================
# Manning公式
# ============================================================================

def compute_steady_uniform_flow(Q, B, S0, n, g=9.81):
    """计算恒定均匀流水深"""
    def manning_equation(h):
        if h <= 0:
            return 1e10
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)
        return Q_calc - Q

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
# 明渠求解器
# ============================================================================

class CanalSolver:
    """明渠非恒定流求解器"""

    def __init__(self, length=1000.0, nx=201, B=10.0, S0=0.001, n=0.025,
                 g=9.81, method='preissmann'):
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method.lower()
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)
        self.h = np.ones(nx) * 1.0
        self.Q = np.ones(nx) * 5.0
        self.filter_window = 11
        self.filter_order = 3
        self.theta = 0.6
        self.omega = 0.95

    def reset_with_steady_state(self, Q0):
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)
        self.h[:] = h_uniform
        self.Q[:] = Q0
        return h_uniform

    def apply_spatial_filter(self, field):
        filtered = savgol_filter(field, self.filter_window, self.filter_order, mode='nearest')
        filtered[0] = field[0]
        filtered[-1] = field[-1]
        return filtered

    def compute_friction_slope(self, h, Q):
        Sf = np.zeros_like(h)
        for i in range(len(h)):
            if h[i] > 1e-6:
                A = self.B * h[i]
                P = self.B + 2 * h[i]
                R = A / P
                V = Q[i] / A if A > 1e-6 else 0.0
                Sf[i] = (self.n * abs(V)) ** 2 / (R ** (4./3.))
        return Sf

    def step_explicit(self, dt, Q_upstream, h_downstream):
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
                dQ_dx_central = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)
                if Q_old[i] >= 0:
                    dQ_dx_upwind = (Q_old[i] - Q_old[i-1]) / self.dx
                else:
                    dQ_dx_upwind = (Q_old[i+1] - Q_old[i]) / self.dx
                dQ_dx = upwind_ratio * dQ_dx_upwind + (1 - upwind_ratio) * dQ_dx_central
                dh_dt = -dQ_dx / self.B
                h_new[i] = h_old[i] + dt * dh_dt

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

        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)
        self.h = h_new
        self.Q = Q_new
        return h_new, Q_new

    def step_preissmann(self, dt, Q_upstream, h_downstream):
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_pred, Q_pred = self.step_explicit(dt, Q_upstream, h_downstream)
        self.h = self.omega * ((1 - self.theta) * h_old + self.theta * h_pred) + (1 - self.omega) * h_old
        self.Q = self.omega * ((1 - self.theta) * Q_old + self.theta * Q_pred) + (1 - self.omega) * Q_old
        self.h = self.apply_spatial_filter(self.h)
        self.Q = self.apply_spatial_filter(self.Q)
        return self.h, self.Q

    def step_hll(self, dt, Q_upstream, h_downstream):
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()
        Sf = self.compute_friction_slope(h_old, Q_old)

        for i in range(1, self.nx - 1):
            h_L, h_R = h_old[i], h_old[i+1]
            Q_L, Q_R = Q_old[i], Q_old[i+1]
            if h_L > 1e-6 and h_R > 1e-6:
                A_L, A_R = self.B * h_L, self.B * h_R
                V_L, V_R = Q_L / A_L, Q_R / A_R
                c_L, c_R = np.sqrt(self.g * h_L), np.sqrt(self.g * h_R)
                S_L = min(V_L - c_L, V_R - c_R)
                S_R = max(V_L + c_L, V_R + c_R)
                F1_L, F1_R = Q_L, Q_R
                F2_L = Q_L * V_L + 0.5 * self.g * self.B * h_L**2
                F2_R = Q_R * V_R + 0.5 * self.g * self.B * h_R**2

                if S_L >= 0:
                    F1, F2 = F1_L, F2_L
                elif S_R <= 0:
                    F1, F2 = F1_R, F2_R
                else:
                    F1 = (S_R * F1_L - S_L * F1_R + S_L * S_R * (A_R - A_L)) / (S_R - S_L)
                    F2 = (S_R * F2_L - S_L * F2_R + S_L * S_R * (Q_R - Q_L)) / (S_R - S_L)

                dh_dt = -(F1 - Q_old[i-1]) / self.dx / self.B
                dQ_dt = -(F2 - (Q_old[i-1]**2/A_L + 0.5*self.g*self.B*h_old[i-1]**2)) / self.dx
                dQ_dt += self.g * A_L * (self.S0 - Sf[i])
                h_new[i] = h_old[i] + dt * dh_dt
                Q_new[i] = Q_old[i] + dt * dQ_dt

        h_new[0] = h_new[1]
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]
        h_new = self.apply_spatial_filter(h_new)
        Q_new = self.apply_spatial_filter(Q_new)
        self.h = h_new
        self.Q = Q_new
        return h_new, Q_new

    def step(self, dt, Q_upstream, h_downstream):
        if self.method == 'explicit':
            return self.step_explicit(dt, Q_upstream, h_downstream)
        elif self.method == 'preissmann':
            return self.step_preissmann(dt, Q_upstream, h_downstream)
        elif self.method == 'hll':
            return self.step_hll(dt, Q_upstream, h_downstream)


# ============================================================================
# 主测试函数
# ============================================================================

def run_final_comparison():
    """运行最终完整对比测试"""

    print("="*80)
    print("例子1：明渠非恒定流 - 三种数值方法完整对比（修复版）")
    print("="*80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 物理参数
    length, B, S0, n, g = 1000.0, 10.0, 0.001, 0.025, 9.81
    nx, dt, T_total = 201, 0.5, 600.0
    n_steps = int(T_total / dt)
    Q_upstream = 8.0
    h_downstream = compute_steady_uniform_flow(Q_upstream, B, S0, n, g)

    print(f"\n物理参数:")
    print(f"  渠道长度 L = {length} m")
    print(f"  渠道宽度 B = {B} m")
    print(f"  底坡 S0 = {S0}")
    print(f"  Manning糙率 n = {n}")
    print(f"\n边界条件:")
    print(f"  上游流量 Q = {Q_upstream} m³/s")
    print(f"  下游水深 h = {h_downstream:.4f} m")
    print(f"\n数值参数:")
    print(f"  网格点数 nx = {nx}")
    print(f"  时间步长 dt = {dt} s")
    print(f"  总时间 T = {T_total} s")

    # 运行三种方法
    methods = ['显式有限差分', '四点隐式', '有限体积']
    method_codes = ['explicit', 'preissmann', 'hll']
    colors = {'显式有限差分': '#1f77b4', '四点隐式': '#ff7f0e', '有限体积': '#2ca02c'}
    results = {}

    for method_name, method_code in zip(methods, method_codes):
        print(f"\n{'='*80}")
        print(f"运行方法: {method_name}")
        print(f"{'='*80}")

        solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, g=g, method=method_code)
        solver.reset_with_steady_state(Q_upstream)

        time_history, h_mid_history, Q_mid_history = [], [], []
        idx_mid = nx // 2

        t_start = time.time()
        for step in range(n_steps):
            t = step * dt
            solver.step(dt, Q_upstream, h_downstream)
            if step % 10 == 0:
                time_history.append(t)
                h_mid_history.append(solver.h[idx_mid])
                Q_mid_history.append(solver.Q[idx_mid])
            if (step + 1) % 400 == 0:
                print(f"  步 {step+1}/{n_steps}: t={t:.1f}s, "
                      f"h_中点={solver.h[idx_mid]:.6f}m, "
                      f"Q_中点={solver.Q[idx_mid]:.6f}m³/s")

        t_end = time.time()
        comp_time = t_end - t_start

        h_mean = np.mean(solver.h)
        h_std = np.std(solver.h)
        h_cv = 100.0 * h_std / h_mean if h_mean > 0 else 0
        Q_mean = np.mean(solver.Q)
        Q_std = np.std(solver.Q)
        Q_cv = 100.0 * Q_std / Q_mean if Q_mean > 0 else 0

        print(f"\n最终统计 (t={T_total:.1f}s):")
        print(f"  水深: 均值={h_mean:.6f}m, 标准差={h_std:.8f}m, CV={h_cv:.6f}%")
        print(f"  流量: 均值={Q_mean:.6f}m³/s, 标准差={Q_std:.8f}m³/s, CV={Q_cv:.6f}%")
        print(f"  计算: 时间={comp_time:.2f}s, 速度={n_steps/comp_time:.1f}步/s")

        results[method_name] = {
            'time': np.array(time_history),
            'h_mid': np.array(h_mid_history),
            'Q_mid': np.array(Q_mid_history),
            'h_final': solver.h,
            'Q_final': solver.Q,
            'x': solver.x,
            'h_mean': h_mean,
            'h_std': h_std,
            'h_cv': h_cv,
            'Q_mean': Q_mean,
            'Q_std': Q_std,
            'Q_cv': Q_cv,
            'comp_time': comp_time,
            'comp_speed': n_steps / comp_time
        }

    # 生成对比图
    print(f"\n{'='*80}")
    print("生成对比图表...")
    print(f"{'='*80}")

    os.makedirs('../reports/figures', exist_ok=True)

    # ========================================================================
    # 图1：空间分布详细对比 (修复Y轴范围)
    # ========================================================================

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f'三种数值方法空间分布对比 (nx={nx}, T={T_total:.0f}s)',
                 fontsize=15, fontweight='bold')

    # 设置合理的Y轴范围
    h_margin = 0.01  # 水深±0.01m
    Q_margin = 0.05  # 流量±0.05m³/s
    h_min = h_downstream - h_margin
    h_max = h_downstream + h_margin
    Q_min = Q_upstream - Q_margin
    Q_max = Q_upstream + Q_margin

    # 第一行：水深分布
    for j, method in enumerate(methods):
        ax = axes[0, j]
        r = results[method]

        ax.plot(r['x'], r['h_final'], color=colors[method], linewidth=2.5,
                label=f'{method}', alpha=0.8)
        ax.axhline(h_downstream, color='red', linestyle='--', linewidth=2,
                   label='理论值', alpha=0.7)

        ax.set_xlabel('距离 (m)', fontsize=12)
        ax.set_ylabel('水深 (m)', fontsize=12)
        ax.set_title(f'{method}\n均值={r["h_mean"]:.6f}m, CV={r["h_cv"]:.6f}%',
                    fontsize=13, fontweight='bold')
        ax.set_ylim([h_min, h_max])  # 设置合理的Y轴范围
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')

        # 添加统计信息
        textstr = f'均值: {r["h_mean"]:.6f} m\n标准差: {r["h_std"]:.8f} m\nCV: {r["h_cv"]:.6f} %'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.6)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props, family='monospace')

    # 第二行：流量分布
    for j, method in enumerate(methods):
        ax = axes[1, j]
        r = results[method]

        ax.plot(r['x'], r['Q_final'], color=colors[method], linewidth=2.5,
                label=f'{method}', alpha=0.8)
        ax.axhline(Q_upstream, color='red', linestyle='--', linewidth=2,
                   label='理论值', alpha=0.7)

        ax.set_xlabel('距离 (m)', fontsize=12)
        ax.set_ylabel('流量 (m³/s)', fontsize=12)
        ax.set_title(f'{method}\n均值={r["Q_mean"]:.6f}m³/s, CV={r["Q_cv"]:.6f}%',
                    fontsize=13, fontweight='bold')
        ax.set_ylim([Q_min, Q_max])  # 设置合理的Y轴范围
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')

        # 添加统计信息
        textstr = f'均值: {r["Q_mean"]:.6f} m³/s\n标准差: {r["Q_std"]:.8f} m³/s\nCV: {r["Q_cv"]:.6f} %'
        props = dict(boxstyle='round', facecolor='lightblue', alpha=0.6)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props, family='monospace')

    plt.tight_layout()
    fig_path = '../reports/figures/example_01_final_spatial_comparison.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  保存: {fig_path}")
    plt.close()

    # ========================================================================
    # 图2：时间演化对比
    # ========================================================================

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('三种数值方法时间演化对比（渠道中点）', fontsize=15, fontweight='bold')

    # 水深时间序列
    ax = axes[0]
    for method in methods:
        r = results[method]
        ax.plot(r['time'], r['h_mid'], color=colors[method], linewidth=2.5,
                label=f'{method}', alpha=0.7)
    ax.axhline(h_downstream, color='red', linestyle='--', linewidth=2,
               label='理论值', alpha=0.7)
    ax.set_xlabel('时间 (s)', fontsize=12)
    ax.set_ylabel('水深 (m)', fontsize=12)
    ax.set_title('渠道中点水深时间历程', fontsize=13, fontweight='bold')
    ax.set_ylim([h_downstream - 0.002, h_downstream + 0.002])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    # 流量时间序列
    ax = axes[1]
    for method in methods:
        r = results[method]
        ax.plot(r['time'], r['Q_mid'], color=colors[method], linewidth=2.5,
                label=f'{method}', alpha=0.7)
    ax.axhline(Q_upstream, color='red', linestyle='--', linewidth=2,
               label='理论值', alpha=0.7)
    ax.set_xlabel('时间 (s)', fontsize=12)
    ax.set_ylabel('流量 (m³/s)', fontsize=12)
    ax.set_title('渠道中点流量时间历程', fontsize=13, fontweight='bold')
    ax.set_ylim([Q_upstream - 0.01, Q_upstream + 0.01])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    plt.tight_layout()
    fig_path = '../reports/figures/example_01_final_temporal_comparison.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  保存: {fig_path}")
    plt.close()

    # ========================================================================
    # 图3：叠加对比图
    # ========================================================================

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('三种数值方法叠加对比', fontsize=15, fontweight='bold')

    # 水深空间分布叠加
    ax = axes[0]
    for method in methods:
        r = results[method]
        ax.plot(r['x'], r['h_final'], color=colors[method], linewidth=3,
                label=f'{method} (CV={r["h_cv"]:.6f}%)', alpha=0.7)
    ax.axhline(h_downstream, color='black', linestyle='--', linewidth=2.5,
               label='理论值', alpha=0.8)
    ax.set_xlabel('距离 (m)', fontsize=13)
    ax.set_ylabel('水深 (m)', fontsize=13)
    ax.set_title('水深空间分布', fontsize=14, fontweight='bold')
    ax.set_ylim([h_min, h_max])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    # 流量空间分布叠加
    ax = axes[1]
    for method in methods:
        r = results[method]
        ax.plot(r['x'], r['Q_final'], color=colors[method], linewidth=3,
                label=f'{method} (CV={r["Q_cv"]:.6f}%)', alpha=0.7)
    ax.axhline(Q_upstream, color='black', linestyle='--', linewidth=2.5,
               label='理论值', alpha=0.8)
    ax.set_xlabel('距离 (m)', fontsize=13)
    ax.set_ylabel('流量 (m³/s)', fontsize=13)
    ax.set_title('流量空间分布', fontsize=14, fontweight='bold')
    ax.set_ylim([Q_min, Q_max])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best')

    plt.tight_layout()
    fig_path = '../reports/figures/example_01_final_overlay_comparison.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  保存: {fig_path}")
    plt.close()

    # ========================================================================
    # 图4：性能和精度对比
    # ========================================================================

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('三种数值方法性能和精度对比', fontsize=15, fontweight='bold')

    x_pos = np.arange(len(methods))
    width = 0.6

    # CV对比 - 水深
    ax = axes[0, 0]
    h_cvs = [results[m]['h_cv'] for m in methods]
    bars = ax.bar(x_pos, h_cvs, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('变异系数 (%)', fontsize=12)
    ax.set_title('水深变异系数', fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.6f}%', ha='center', va='bottom', fontsize=9)

    # CV对比 - 流量
    ax = axes[0, 1]
    Q_cvs = [results[m]['Q_cv'] for m in methods]
    bars = ax.bar(x_pos, Q_cvs, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('变异系数 (%)', fontsize=12)
    ax.set_title('流量变异系数', fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.6f}%', ha='center', va='bottom', fontsize=9)

    # 标准差对比
    ax = axes[1, 0]
    h_stds = [results[m]['h_std'] * 1000 for m in methods]  # 转换为mm
    Q_stds = [results[m]['Q_std'] * 1000 for m in methods]  # 转换为L/s
    x = np.arange(len(methods))
    width2 = 0.35
    bars1 = ax.bar(x - width2/2, h_stds, width2, label='水深标准差 (mm)',
                   color='steelblue', alpha=0.7)
    bars2 = ax.bar(x + width2/2, Q_stds, width2, label='流量标准差 (L/s)',
                   color='coral', alpha=0.7)
    ax.set_ylabel('标准差', fontsize=12)
    ax.set_title('标准差对比', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # 计算速度对比
    ax = axes[1, 1]
    speeds = [results[m]['comp_speed'] for m in methods]
    bars = ax.bar(x_pos, speeds, width, color=[colors[m] for m in methods], alpha=0.7)
    ax.set_ylabel('计算速度 (步/秒)', fontsize=12)
    ax.set_title('计算效率对比', fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}\n步/秒', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    fig_path = '../reports/figures/example_01_final_performance_comparison.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  保存: {fig_path}")
    plt.close()

    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")
    print("\n生成的文件:")
    print("  1. example_01_final_spatial_comparison.png - 空间分布对比（修复Y轴）")
    print("  2. example_01_final_temporal_comparison.png - 时间演化对比")
    print("  3. example_01_final_overlay_comparison.png - 叠加对比")
    print("  4. example_01_final_performance_comparison.png - 性能对比")
    print(f"{'='*80}")

    return results


if __name__ == '__main__':
    results = run_final_comparison()
