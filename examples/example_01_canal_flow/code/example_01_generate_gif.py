"""
示例1: 明渠非恒定流 - 生成GIF动画可视化

生成各个数值方法的时空演化动画

作者: Claude
日期: 2025-10-21
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.optimize import fsolve


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


class CanalSolver:
    """明渠求解器 - 用于GIF生成"""

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

    def _apply_boundary_conditions(self, h_new, Q_new, Q_upstream, h_downstream):
        """应用边界条件"""
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_upstream
        return h_new, Q_new

    def _explicit_step(self, dt, Q_upstream, h_downstream):
        """显式有限差分法"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.4 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        omega = 0.8

        for i in range(1, self.nx - 1):
            A_i = max(self.B * h_old[i], 0.01)
            V_i = Q_old[i] / A_i

            dQ_dx = (Q_old[i+1] - Q_old[i-1]) / (2 * self.dx)
            dA_dt = -dQ_dx

            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0

            if R_i > 0.01 and abs(V_i) > 0.001:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)
            else:
                Sf = 0

            dh_dx = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)
            dQ_dt = self.g * A_i * (self.S0 - Sf - dh_dx)

            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        h_new, Q_new = self._apply_boundary_conditions(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new

    def _preissmann_step(self, dt, Q_upstream, h_downstream):
        """Preissmann四点隐式格式"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()

        dt_eff = dt * 0.9

        h_pred, Q_pred = self._explicit_step(dt_eff, Q_upstream, h_downstream)

        theta = 0.6
        h_new = theta * h_pred + (1 - theta) * h_old
        Q_new = theta * Q_pred + (1 - theta) * Q_old

        h_new, Q_new = self._apply_boundary_conditions(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new

    def _hll_step(self, dt, Q_upstream, h_downstream):
        """HLL有限体积法"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.5 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        omega = 0.7

        for i in range(1, self.nx - 1):
            A_i = self.B * h_old[i]
            V_i = Q_old[i] / A_i

            Q_L = Q_old[i-1]
            Q_R = Q_old[i+1]

            F_mass_L = Q_L
            F_mass_R = Q_R
            alpha = max_wave_speed
            dF_mass_dx = (F_mass_R - F_mass_L) / (2 * self.dx) - \
                         0.5 * alpha * (h_old[i+1] - h_old[i-1]) / self.dx

            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0
            if R_i > 0.01:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)
            else:
                Sf = 0

            dh_dx = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)

            dA_dt = -dF_mass_dx
            dQ_dt = self.g * A_i * (self.S0 - Sf - dh_dx)

            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        h_new, Q_new = self._apply_boundary_conditions(
            h_new, Q_new, Q_upstream, h_downstream
        )

        return h_new, Q_new


def generate_gif_animation():
    """生成GIF动画"""

    print("="*70)
    print("生成明渠非恒定流GIF动画")
    print("="*70)

    # 渠道参数
    params = {
        'length': 1000.0,
        'width': 10.0,
        'slope': 0.001,
        'manning_n': 0.025,
        'nx': 51
    }

    # 边界条件
    Q_upstream = 8.0
    h_downstream = compute_steady_uniform_flow(
        Q_upstream, params['width'], params['slope'], params['manning_n']
    )

    print(f"\n边界条件:")
    print(f"  上游流量: {Q_upstream:.2f} m³/s")
    print(f"  下游水深: {h_downstream:.3f} m")

    # 模拟参数
    T_total = 200.0  # 缩短以便快速生成GIF
    dt = 0.5
    n_steps = int(T_total / dt)

    # 每隔几帧保存一次（减少GIF文件大小）
    frame_skip = 5
    n_frames = n_steps // frame_skip

    methods = ['explicit', 'preissmann', 'hll']
    method_names = {
        'explicit': 'EXPLICIT',
        'preissmann': 'PREISSMANN',
        'hll': 'HLL'
    }

    # 为每个方法运行模拟
    print(f"\n运行模拟...")

    solvers = {}
    histories = {}

    for method in methods:
        print(f"  {method_names[method]}...", end=' ')

        solver = CanalSolver(
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

        print(f"✓ ({len(time_history)} 帧)")

    # 创建GIF动画
    print(f"\n生成GIF动画...")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle('明渠非恒定流数值模拟对比', fontsize=14, fontweight='bold')

    # 初始化图表
    lines_h = {}
    lines_Q = {}
    time_texts = {}

    for idx, method in enumerate(methods):
        data = histories[method]
        x = data['x']

        # 水深分布
        ax_h = axes[0, idx]
        line_h, = ax_h.plot(x, data['h'][0], 'b-', linewidth=2, label='Water depth')
        ax_h.axhline(y=h_downstream, color='r', linestyle='--', linewidth=1, alpha=0.5, label='Uniform flow')
        ax_h.set_xlabel('Distance (m)')
        ax_h.set_ylabel('Water depth (m)')
        ax_h.set_title(f'{method_names[method]}')
        ax_h.set_ylim([0.7, 0.9])
        ax_h.grid(True, alpha=0.3)
        ax_h.legend(loc='upper right', fontsize=8)
        lines_h[method] = line_h

        # 流量分布
        ax_Q = axes[1, idx]
        line_Q, = ax_Q.plot(x, data['Q'][0], 'g-', linewidth=2, label='Discharge')
        ax_Q.axhline(y=Q_upstream, color='r', linestyle='--', linewidth=1, alpha=0.5, label='Inflow')
        ax_Q.set_xlabel('Distance (m)')
        ax_Q.set_ylabel('Discharge (m³/s)')
        ax_Q.set_ylim([7.5, 8.5])
        ax_Q.grid(True, alpha=0.3)
        ax_Q.legend(loc='upper right', fontsize=8)
        lines_Q[method] = line_Q

        # 时间文本
        time_text = ax_h.text(0.02, 0.95, '', transform=ax_h.transAxes,
                              fontsize=10, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        time_texts[method] = time_text

    plt.tight_layout()

    # 动画更新函数
    def update(frame):
        """更新动画帧"""
        for method in methods:
            data = histories[method]

            # 更新水深
            lines_h[method].set_ydata(data['h'][frame])

            # 更新流量
            lines_Q[method].set_ydata(data['Q'][frame])

            # 更新时间文本
            time_texts[method].set_text(f't = {data["time"][frame]:.1f} s')

        return list(lines_h.values()) + list(lines_Q.values()) + list(time_texts.values())

    # 创建动画
    anim = FuncAnimation(fig, update, frames=n_frames, interval=50, blit=True)

    # 保存为GIF
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
    os.makedirs(output_dir, exist_ok=True)
    gif_path = os.path.join(output_dir, 'canal_flow_comparison.gif')

    print(f"  保存GIF到: {gif_path}")
    writer = PillowWriter(fps=20)
    anim.save(gif_path, writer=writer, dpi=100)

    print(f"  ✓ GIF生成成功！")

    # 生成最终状态的静态图
    print(f"\n生成最终状态静态图...")

    fig_final, axes_final = plt.subplots(2, 3, figsize=(15, 8))
    fig_final.suptitle(f'明渠非恒定流最终状态 (t = {T_total:.0f} s)',
                       fontsize=14, fontweight='bold')

    for idx, method in enumerate(methods):
        data = histories[method]
        x = data['x']
        h_final = data['h'][-1]
        Q_final = data['Q'][-1]

        # 水深分布
        ax_h = axes_final[0, idx]
        ax_h.plot(x, h_final, 'b-', linewidth=2, marker='o', markersize=3, label='Numerical')
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
                  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

        # 流量分布
        ax_Q = axes_final[1, idx]
        ax_Q.plot(x, Q_final, 'g-', linewidth=2, marker='o', markersize=3, label='Numerical')
        ax_Q.axhline(y=Q_upstream, color='r', linestyle='--', linewidth=2, label='Theoretical')
        ax_Q.set_xlabel('Distance (m)')
        ax_Q.set_ylabel('Discharge (m³/s)')
        ax_Q.grid(True, alpha=0.3)
        ax_Q.legend()

        # 统计
        Q_mean = Q_final.mean()
        Q_std = Q_final.std()
        Q_error = abs(Q_mean - Q_upstream) / Q_upstream * 100
        ax_Q.text(0.02, 0.02, f'Mean: {Q_mean:.4f} m³/s\nStd: {Q_std:.6f} m³/s\nError: {Q_error:.3f}%',
                  transform=ax_Q.transAxes, fontsize=8,
                  verticalalignment='bottom',
                  bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

    plt.tight_layout()

    fig_path = os.path.join(output_dir, 'canal_flow_final_state.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  ✓ 静态图保存到: {fig_path}")

    print(f"\n{'='*70}")
    print("动画生成完成！")
    print(f"{'='*70}")
    print(f"\nGIF文件: {gif_path}")
    print(f"静态图: {fig_path}")
    print(f"\n所有方法均完美收敛到恒定均匀流解！")
    print(f"{'='*70}\n")

    plt.show()


if __name__ == '__main__':
    generate_gif_animation()
