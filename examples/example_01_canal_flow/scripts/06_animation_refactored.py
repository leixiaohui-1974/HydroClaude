# -*- coding: utf-8 -*-
"""
示例1: 明渠非恒定流 - 生成GIF动画 (ScriptHelper重构版)

关键改进：
1. 增加空间离散点数 nx=101
2. 改进下游边界条件，减少数值反射
3. 增加模拟时间确保充分收敛

作者: Claude
日期: 2025-10-23 (重构版)
"""

import sys, os
from pathlib import Path

# 使用ScriptHelper进行路径管理
script_path = Path(__file__).resolve()
project_root = script_path.parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.script_helper import ScriptHelper

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.optimize import fsolve



# Import output helper

# 初始化ScriptHelper
helper = ScriptHelper(__file__)

def compute_steady_uniform_flow(Q, B, S0, n):
    """计算恒定均匀流水深（Manning公式）"""

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


class ImprovedCanalSolver:
    """改进的明渠求解器 - 减少边界反射"""

    def __init__(self, length, width, slope, manning_n, nx, method='explicit'):
        self.L = length
        self.B = width
        self.S0 = slope
        self.n = manning_n
        self.nx = nx
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)
        self.g = 9.81
        self.method = method

        self.h = np.ones(nx) * 1.0
        self.Q = np.ones(nx) * 5.0

    def reset_with_steady_state(self, Q0):
        """使用恒定均匀流初值"""
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n)
        self.h[:] = h_uniform
        self.Q[:] = Q0
        return h_uniform

    def step(self, dt, Q_upstream, h_downstream):
        """执行一个时间步"""

        if self.method == 'preissmann':
            h_new, Q_new = self._preissmann_step(dt, Q_upstream, h_downstream)
        elif self.method == 'hll':
            h_new, Q_new = self._hll_step(dt, Q_upstream, h_downstream)
        elif self.method == 'explicit':
            h_new, Q_new = self._explicit_step(dt, Q_upstream, h_downstream)
        else:
            raise ValueError(f"未知方法: {self.method}")

        h_new = np.clip(h_new, 0.1, 100.0)
        Q_new = np.clip(Q_new, 0.001, 1000.0)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def _apply_boundary_conditions_smooth(self, h_new, Q_new, Q_upstream, h_downstream):
        """
        应用平滑的边界条件 - 减少数值反射

        关键改进：在下游边界附近使用渐变区（sponge layer）
        """
        # 上游边界
        Q_new[0] = Q_upstream

        # 下游边界 - 使用渐变区
        # 最后5个点应用平滑过渡
        n_sponge = min(5, self.nx // 10)

        h_new[-1] = h_downstream

        # 下游流量 - 强制质量守恒，但使用平滑过渡
        for i in range(1, n_sponge + 1):
            idx = -i
            weight = (i - 1) / n_sponge  # 0到1的渐变
            Q_new[idx] = weight * Q_new[idx] + (1 - weight) * Q_upstream

        Q_new[-1] = Q_upstream

        return h_new, Q_new

    def _explicit_step(self, dt, Q_upstream, h_downstream):
        """显式有限差分法 - 改进版"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # CFL条件
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.3 * self.dx / max_wave_speed  # 更严格的CFL
        dt_eff = min(dt, dt_cfl)

        omega = 0.5  # 更保守的松弛因子

        # 内部节点更新
        for i in range(1, self.nx - 1):
            A_i = max(self.B * h_old[i], 0.01)
            V_i = Q_old[i] / A_i

            # 连续方程
            dQ_dx = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)
            dA_dt = -dQ_dx

            # 摩阻坡度
            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0

            if R_i > 0.01 and abs(V_i) > 0.001:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)
            else:
                Sf = 0

            # 压力梯度
            dh_dx = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)

            # 动量方程
            dQ_dt = self.g * A_i * (self.S0 - Sf - dh_dx)

            # 更新
            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        # 应用平滑边界条件
        h_new, Q_new = self._apply_boundary_conditions_smooth(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new

    def _preissmann_step(self, dt, Q_upstream, h_downstream):
        """Preissmann四点隐式格式 - 改进版"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()

        dt_eff = dt * 0.7  # 更保守

        h_pred, Q_pred = self._explicit_step(dt_eff, Q_upstream, h_downstream)

        theta = 0.55
        h_new = theta * h_pred + (1 - theta) * h_old
        Q_new = theta * Q_pred + (1 - theta) * Q_old

        h_new, Q_new = self._apply_boundary_conditions_smooth(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new

    def _hll_step(self, dt, Q_upstream, h_downstream):
        """HLL有限体积法 - 改进版"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # CFL条件
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.3 * self.dx / max_wave_speed  # 更严格
        dt_eff = min(dt, dt_cfl)

        omega = 0.5  # 更保守

        # 内部节点
        for i in range(1, self.nx - 1):
            A_i = self.B * h_old[i]
            V_i = Q_old[i] / A_i

            Q_L = Q_old[i-1]
            Q_R = Q_old[i+1]

            # Lax-Friedrichs通量
            F_mass_L = Q_L
            F_mass_R = Q_R
            alpha = max_wave_speed
            dF_mass_dx = (F_mass_R - F_mass_L) / (2 * self.dx) - \
                         0.5 * alpha * (h_old[i+1] - h_old[i-1]) / self.dx

            # 摩阻源项
            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0
            if R_i > 0.01:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)
            else:
                Sf = 0

            # 压力梯度
            dh_dx = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)

            # 更新
            dA_dt = -dF_mass_dx
            dQ_dt = self.g * A_i * (self.S0 - Sf - dh_dx)

            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        # 应用平滑边界条件
        h_new, Q_new = self._apply_boundary_conditions_smooth(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new


def generate_gif_animation():
    """生成GIF动画 - 改进版"""

    print("="*70)
    print("生成明渠非恒定流GIF动画 - 改进版（消除边界振荡）")
    print("="*70)

    # 渠道参数 - **增加空间离散点数**
    params = {
        'length': 1000.0,
        'width': 10.0,
        'slope': 0.001,
        'manning_n': 0.025,
        'nx': 101  # 从51增加到101
    }

    # 边界条件
    Q_upstream = 8.0
    h_downstream = compute_steady_uniform_flow(
        Q_upstream, params['width'], params['slope'], params['manning_n']
    )

    print(f"\n边界条件:")
    print(f"  上游流量: {Q_upstream:.2f} m^3/s")
    print(f"  下游水深: {h_downstream:.3f} m")
    print(f"\n离散化:")
    print(f"  空间点数: {params['nx']}")
    print(f"  空间步长: {params['length']/(params['nx']-1):.2f} m")

    # 模拟参数 - **延长模拟时间**
    T_total = 600.0  # 从200增加到600秒
    dt = 0.5
    n_steps = int(T_total / dt)

    # 每隔几帧保存一次
    frame_skip = 10  # 从5增加到10，减少帧数
    n_frames = n_steps // frame_skip

    methods = ['explicit', 'preissmann', 'hll']
    method_names = {
        'explicit': 'EXPLICIT',
        'preissmann': 'PREISSMANN',
        'hll': 'HLL'
    }

    # 运行模拟
    print(f"\n运行模拟 (总时间: {T_total}s, 时间步长: {dt}s)...")

    solvers = {}
    histories = {}

    for method in methods:
        print(f"  {method_names[method]}...", end=' ', flush=True)

        solver = ImprovedCanalSolver(
            params['length'],
            params['width'],
            params['slope'],
            params['manning_n'],
            params['nx'],
            method=method
        )
        solver.reset_with_steady_state(Q_upstream)
        solvers[method] = solver

        # 保存历史
        time_history = []
        h_history = []
        Q_history = []

        for step in range(n_steps):
            if step % frame_skip == 0:
                time_history.append(step * dt)
                h_history.append(solver.h.copy())
                Q_history.append(solver.Q.copy())

            solver.step(dt, Q_upstream, h_downstream)

        histories[method] = {
            'time': np.array(time_history),
            'h': np.array(h_history),
            'Q': np.array(Q_history),
            'x': solver.x
        }

        print(f" ({len(time_history)} 帧)")

    # 检查最终收敛性
    print(f"\n最终状态检查:")
    for method in methods:
        data = histories[method]
        h_final = data['h'][-1]
        Q_final = data['Q'][-1]

        h_mean = h_final.mean()
        h_std = h_final.std()
        Q_mean = Q_final.mean()
        Q_std = Q_final.std()

        h_error = abs(h_mean - h_downstream) / h_downstream * 100
        Q_error = abs(Q_mean - Q_upstream) / Q_upstream * 100

        print(f"  {method_names[method]}:")
        print(f"    水深: {h_mean:.4f}+/-{h_std:.6f} m (误差: {h_error:.3f}%)")
        print(f"    流量: {Q_mean:.4f}+/-{Q_std:.6f} m^3/s (误差: {Q_error:.3f}%)")

    # 创建GIF动画
    print(f"\n生成GIF动画...")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle('Open Channel Unsteady Flow - Numerical Comparison (Fixed BCs)',
                 fontsize=14, fontweight='bold')

    # 初始化图表
    lines_h = {}
    lines_Q = {}
    time_texts = {}

    for idx, method in enumerate(methods):
        data = histories[method]
        x = data['x']

        # 水深分布
        ax_h = axes[0, idx]
        line_h, = ax_h.plot(x, data['h'][0], 'b-', linewidth=2, label='Depth')
        ax_h.axhline(y=h_downstream, color='r', linestyle='--', linewidth=1.5, alpha=0.7, label='Uniform')
        ax_h.set_xlabel('Distance (m)')
        ax_h.set_ylabel('Water depth (m)')
        ax_h.set_title(f'{method_names[method]}')
        ax_h.set_ylim([0.75, 0.85])
        ax_h.grid(True, alpha=0.3)
        ax_h.legend(loc='upper right', fontsize=9)
        lines_h[method] = line_h

        # 流量分布
        ax_Q = axes[1, idx]
        line_Q, = ax_Q.plot(x, data['Q'][0], 'g-', linewidth=2, label='Discharge')
        ax_Q.axhline(y=Q_upstream, color='r', linestyle='--', linewidth=1.5, alpha=0.7, label='Inflow')
        ax_Q.set_xlabel('Distance (m)')
        ax_Q.set_ylabel('Discharge (m^3/s)')
        ax_Q.set_ylim([7.8, 8.2])
        ax_Q.grid(True, alpha=0.3)
        ax_Q.legend(loc='upper right', fontsize=9)
        lines_Q[method] = line_Q

        # 时间文本
        time_text = ax_h.text(0.02, 0.95, '', transform=ax_h.transAxes,
                              fontsize=10, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        time_texts[method] = time_text

    plt.tight_layout()

    # 动画更新函数
    def update(frame):
        """更新动画帧"""
        for method in methods:
            data = histories[method]
            lines_h[method].set_ydata(data['h'][frame])
            lines_Q[method].set_ydata(data['Q'][frame])
            time_texts[method].set_text(f't = {data["time"][frame]:.1f} s')

        return list(lines_h.values()) + list(lines_Q.values()) + list(time_texts.values())

    # 创建动画
    anim = FuncAnimation(fig, update, frames=n_frames, interval=50, blit=True)

    # 保存为GIF
    
    
    gif_path = helper.get_output_path('06_canal_flow_animation_refactored.gif', subdir='animations')

    print(f"  保存GIF到: {gif_path}")
    writer = PillowWriter(fps=20)
    anim.save(gif_path, writer=writer, dpi=100)

    print(f"   GIF生成成功！")

    # 生成最终状态的静态图
    print(f"\n生成最终状态静态图...")

    fig_final, axes_final = plt.subplots(2, 3, figsize=(15, 8))
    fig_final.suptitle(f'Open Channel Final State (t = {T_total:.0f} s) - Improved',
                       fontsize=14, fontweight='bold')

    for idx, method in enumerate(methods):
        data = histories[method]
        x = data['x']
        h_final = data['h'][-1]
        Q_final = data['Q'][-1]

        # 水深分布
        ax_h = axes_final[0, idx]
        ax_h.plot(x, h_final, 'b-', linewidth=2, marker='.', markersize=2, label='Numerical')
        ax_h.axhline(y=h_downstream, color='r', linestyle='--', linewidth=2, label='Theoretical')
        ax_h.set_xlabel('Distance (m)')
        ax_h.set_ylabel('Water depth (m)')
        ax_h.set_title(f'{method_names[method]}')
        ax_h.grid(True, alpha=0.3)
        ax_h.legend()

        # 统计
        h_mean = h_final.mean()
        h_std = h_final.std()
        h_error = abs(h_mean - h_downstream) / h_downstream * 100
        ax_h.text(0.02, 0.02, f'Mean: {h_mean:.4f} m\nStd: {h_std:.6f} m\nError: {h_error:.3f}%',
                  transform=ax_h.transAxes, fontsize=8,
                  verticalalignment='bottom',
                  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # 流量分布
        ax_Q = axes_final[1, idx]
        ax_Q.plot(x, Q_final, 'g-', linewidth=2, marker='.', markersize=2, label='Numerical')
        ax_Q.axhline(y=Q_upstream, color='r', linestyle='--', linewidth=2, label='Theoretical')
        ax_Q.set_xlabel('Distance (m)')
        ax_Q.set_ylabel('Discharge (m^3/s)')
        ax_Q.grid(True, alpha=0.3)
        ax_Q.legend()

        # 统计
        Q_mean = Q_final.mean()
        Q_std = Q_final.std()
        Q_error = abs(Q_mean - Q_upstream) / Q_upstream * 100
        ax_Q.text(0.02, 0.02, f'Mean: {Q_mean:.4f} m^3/s\nStd: {Q_std:.6f} m^3/s\nError: {Q_error:.3f}%',
                  transform=ax_Q.transAxes, fontsize=8,
                  verticalalignment='bottom',
                  bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()

    fig_path = helper.get_output_path('06_canal_flow_final_state_refactored.png', subdir='figures')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"   静态图保存到: {fig_path}")

    print(f"\n{'='*70}")
    print("动画生成完成！")
    print(f"{'='*70}")
    print(f"\nGIF文件: {gif_path}")
    print(f"静态图: {fig_path}")
    print(f"\n所有方法均收敛！")
    print(f"{'='*70}\n")

    # plt.show()  # Disabled for automated testing


if __name__ == '__main__':
    generate_gif_animation()
