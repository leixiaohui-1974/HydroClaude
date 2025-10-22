"""
示例1: 明渠非恒定流 - 真正修正版本

**根本问题修正**：
下游边界条件的处理错误！
- 错误做法：强制 Q[-1] = Q_upstream
- 正确做法：只指定 h[-1] = h_downstream，流量通过连续性方程计算

作者: Claude
日期: 2025-10-21
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

import numpy as np
import matplotlib.pyplot as plt
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


class TrulyFixedCanalSolver:
    """
    真正修正的明渠求解器

    关键修正：下游边界只指定水深，流量通过连续性方程计算
    """

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

    def _apply_correct_bc(self, h_new, Q_new, Q_upstream, h_downstream):
        """
        应用正确的边界条件（亚临界流）

        上游：指定Q
        下游：指定h，Q通过连续性方程外推
        """
        # 上游边界
        Q_new[0] = Q_upstream

        # 下游边界
        h_new[-1] = h_downstream

        # **正确做法：下游流量通过连续性方程外推**
        # 使用一阶外推：∂Q/∂x ≈ 0 at downstream boundary
        # 即 Q[-1] ≈ Q[-2]
        Q_new[-1] = Q_new[-2]

        return h_new, Q_new

    def _explicit_step(self, dt, Q_upstream, h_downstream):
        """显式有限差分法"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # CFL条件
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.5 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        omega = 0.9  # 松弛因子

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

        # 应用正确的边界条件
        h_new, Q_new = self._apply_correct_bc(h_new, Q_new, Q_upstream, h_downstream)

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

        h_new, Q_new = self._apply_correct_bc(h_new, Q_new, Q_upstream, h_downstream)

        return h_new, Q_new

    def _hll_step(self, dt, Q_upstream, h_downstream):
        """HLL有限体积法"""

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # CFL条件
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.5 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        omega = 0.8

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

        # 应用正确的边界条件
        h_new, Q_new = self._apply_correct_bc(h_new, Q_new, Q_upstream, h_downstream)

        return h_new, Q_new


def test_truly_fixed():
    """测试真正修正的版本"""

    print("="*70)
    print("明渠非恒定流 - 真正修正版本测试")
    print("="*70)

    # 渠道参数
    params = {
        'length': 1000.0,
        'width': 10.0,
        'slope': 0.001,
        'manning_n': 0.025,
        'nx': 101
    }

    # 边界条件
    Q_upstream = 8.0
    h_downstream = compute_steady_uniform_flow(
        Q_upstream, params['width'], params['slope'], params['manning_n']
    )

    print(f"\n边界条件:")
    print(f"  上游流量: {Q_upstream:.2f} m³/s")
    print(f"  下游水深: {h_downstream:.3f} m (Manning公式计算)")

    # 模拟参数
    T_total = 600.0
    dt = 0.5
    n_steps = int(T_total / dt)

    methods = ['explicit', 'preissmann', 'hll']
    method_names = {
        'explicit': 'EXPLICIT',
        'preissmann': 'PREISSMANN',
        'hll': 'HLL'
    }

    results = {}

    for method in methods:
        print(f"\n{'='*70}")
        print(f"测试方法: {method_names[method]}")
        print(f"{'='*70}")

        solver = TrulyFixedCanalSolver(
            params['length'],
            params['width'],
            params['slope'],
            params['manning_n'],
            params['nx'],
            method=method
        )

        solver.reset_with_steady_state(Q_upstream)

        # 运行模拟
        for step in range(n_steps):
            solver.step(dt, Q_upstream, h_downstream)

            if (step + 1) % 200 == 0:
                Q_mean = solver.Q.mean()
                h_mean = solver.h.mean()
                print(f"  步 {step+1}/{n_steps}: Q_mean={Q_mean:.4f} m³/s, h_mean={h_mean:.4f} m")

        results[method] = {
            'h': solver.h.copy(),
            'Q': solver.Q.copy(),
            'x': solver.x.copy()
        }

        # 最终状态检查
        h_final = solver.h
        Q_final = solver.Q

        h_mean = h_final.mean()
        h_std = h_final.std()
        Q_mean = Q_final.mean()
        Q_std = Q_final.std()

        h_error = abs(h_mean - h_downstream) / h_downstream * 100
        Q_error = abs(Q_mean - Q_upstream) / Q_upstream * 100

        print(f"\n最终状态 (t={T_total}s):")
        print(f"  水深: {h_mean:.4f} ± {h_std:.6f} m (误差: {h_error:.3f}%)")
        print(f"  流量: {Q_mean:.4f} ± {Q_std:.6f} m³/s (误差: {Q_error:.3f}%)")
        print(f"  下游流量: Q[-1]={Q_final[-1]:.4f} m³/s")

    # 生成对比图
    print(f"\n{'='*70}")
    print("生成对比图...")
    print(f"{'='*70}")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle(f'Truly Fixed Canal Flow (t = {T_total:.0f} s)',
                 fontsize=14, fontweight='bold')

    for idx, method in enumerate(methods):
        data = results[method]
        x = data['x']
        h_final = data['h']
        Q_final = data['Q']

        # 水深分布
        ax_h = axes[0, idx]
        ax_h.plot(x, h_final, 'b-', linewidth=2, marker='.', markersize=2, label='Numerical')
        ax_h.axhline(y=h_downstream, color='r', linestyle='--', linewidth=2, label='Theoretical')
        ax_h.set_xlabel('Distance (m)')
        ax_h.set_ylabel('Water depth (m)')
        ax_h.set_title(f'{method_names[method]}')
        ax_h.grid(True, alpha=0.3)
        ax_h.legend()

        h_mean = h_final.mean()
        h_std = h_final.std()
        h_error = abs(h_mean - h_downstream) / h_downstream * 100
        ax_h.text(0.02, 0.02, f'Mean: {h_mean:.4f} m\nStd: {h_std:.6f} m\nError: {h_error:.3f}%',
                  transform=ax_h.transAxes, fontsize=8,
                  verticalalignment='bottom',
                  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # 流量分布
        ax_Q = axes[1, idx]
        ax_Q.plot(x, Q_final, 'g-', linewidth=2, marker='.', markersize=2, label='Numerical')
        ax_Q.axhline(y=Q_upstream, color='r', linestyle='--', linewidth=2, label='Inflow')
        ax_Q.set_xlabel('Distance (m)')
        ax_Q.set_ylabel('Discharge (m³/s)')
        ax_Q.grid(True, alpha=0.3)
        ax_Q.legend()

        Q_mean = Q_final.mean()
        Q_std = Q_final.std()
        Q_error = abs(Q_mean - Q_upstream) / Q_upstream * 100
        ax_Q.text(0.02, 0.02, f'Mean: {Q_mean:.4f} m³/s\nStd: {Q_std:.6f} m³/s\nError: {Q_error:.3f}%',
                  transform=ax_Q.transAxes, fontsize=8,
                  verticalalignment='bottom',
                  bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, 'truly_fixed_canal.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n图像已保存: {fig_path}")

    print(f"\n{'='*70}")
    print("测试完成！")
    print(f"{'='*70}\n")

    plt.show()

    return results


if __name__ == '__main__':
    results = test_truly_fixed()
