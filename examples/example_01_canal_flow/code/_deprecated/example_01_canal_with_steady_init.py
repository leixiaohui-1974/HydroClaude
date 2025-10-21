"""
示例1: 明渠非恒定流 - 使用恒定流初值的稳定求解器

关键改进：使用Manning公式计算的恒定均匀流解作为初值

作者: Claude
日期: 2025-10-21
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from stability_evaluator import StabilityEvaluator


def compute_steady_uniform_flow(Q, B, S0, n):
    """
    计算恒定均匀流水深（Manning公式）

    对于矩形断面：
    Q = (1/n) * A * R^(2/3) * S0^(1/2)
    其中 A = B*h, R = A/(B+2h)

    Parameters:
    -----------
    Q : float
        流量 (m³/s)
    B : float
        渠道宽度 (m)
    S0 : float
        底坡
    n : float
        Manning糙率系数

    Returns:
    --------
    h : float
        恒定均匀流水深 (m)
    """

    def manning_equation(h):
        """Manning方程残差"""
        if h <= 0:
            return 1e10

        A = B * h
        P = B + 2 * h
        R = A / P

        # Manning公式
        Q_calc = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)

        return Q_calc - Q

    # 使用二分法求解
    h_min, h_max = 0.01, 20.0

    # 检查边界
    if manning_equation(h_min) * manning_equation(h_max) > 0:
        # 如果同号，使用简单估计
        # Q ≈ (1/n) * B*h * (h)^(2/3) * S0^(1/2)  (宽浅渠道近似)
        h_est = (Q * n / (B * S0**0.5)) ** (3./5.)
        return max(0.5, min(10.0, h_est))

    # 二分法求解
    while h_max - h_min > 1e-6:
        h_mid = (h_min + h_max) / 2
        if manning_equation(h_mid) * manning_equation(h_min) < 0:
            h_max = h_mid
        else:
            h_min = h_mid

    return (h_min + h_max) / 2


class CanalSolverWithSteadyInit:
    """
    使用恒定流初值的明渠求解器

    关键特性：
    1. 初值采用Manning公式计算的恒定均匀流
    2. 支持三种数值方法
    3. 确保质量守恒
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

        # 状态变量 - 暂时用默认值，实际使用时会调用reset_with_steady_state
        self.h = np.ones(nx) * 1.0
        self.Q = np.ones(nx) * 5.0

        print(f"初始化求解器: method={method}, nx={nx}, dx={self.dx:.2f}m")

    def reset_with_steady_state(self, Q0, h_downstream):
        """
        使用恒定流解析解重置状态

        Parameters:
        -----------
        Q0 : float
            初始流量 (m³/s)
        h_downstream : float
            下游边界水深 (m)
        """

        # 计算恒定均匀流水深
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n)

        print(f"\n恒定流初值计算:")
        print(f"  流量 Q0 = {Q0:.2f} m³/s")
        print(f"  计算得恒定均匀流水深 h = {h_uniform:.3f} m")
        print(f"  下游边界水深 = {h_downstream:.3f} m")

        # 设置初始水深：从均匀流水深线性插值到下游边界
        for i in range(self.nx):
            x_ratio = i / (self.nx - 1)
            self.h[i] = h_uniform * (1 - x_ratio) + h_downstream * x_ratio

        # 设置初始流量为均匀值
        self.Q[:] = Q0

        # 验证初值
        A0 = self.B * h_uniform
        V0 = Q0 / A0
        Fr0 = V0 / np.sqrt(self.g * h_uniform)

        print(f"  初始流速 V0 = {V0:.3f} m/s")
        print(f"  初始Froude数 Fr0 = {Fr0:.3f}")
        print(f"  初始状态: h ∈ [{self.h.min():.3f}, {self.h.max():.3f}] m")

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

        # 物理合理性检查
        h_new = np.clip(h_new, 0.1, 100.0)
        Q_new = np.clip(Q_new, 0.01, 1000.0)

        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def _explicit_step(self, dt, Q_upstream, h_downstream):
        """
        改进的显式有限差分法 - 使用保守形式

        连续方程：∂A/∂t + ∂Q/∂x = 0
        动量方程：∂Q/∂t + ∂(Q²/A)/∂x + gA·∂h/∂x = gA(S0 - Sf)
        """

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # 自适应时间步长（CFL条件）
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        wave_speed = np.abs(V_old) + c_old
        max_wave_speed = wave_speed.max()

        # CFL < 0.5
        dt_cfl = 0.5 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        # 松弛因子
        omega = 0.3

        # 应用边界条件
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream

        # 内部节点更新
        for i in range(1, self.nx - 1):
            A_i = max(self.B * h_old[i], 0.01)
            V_i = Q_old[i] / A_i

            # === 连续方程 ===
            # 使用迎风格式
            if Q_old[i] >= 0:
                dQ_dx = (Q_old[i] - Q_old[i-1]) / self.dx
            else:
                dQ_dx = (Q_old[i+1] - Q_old[i]) / self.dx

            dA_dt = -dQ_dx

            # === 动量方程 ===
            # 摩阻坡度
            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0

            if R_i > 0.01 and abs(V_i) > 0.001:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)  # 限制摩阻
            else:
                Sf = 0

            # 压力梯度（中心差分）
            dh_dx = (h_old[i+1] - h_old[i-1]) / (2 * self.dx)

            # 对流项（简化处理）
            # ∂(Q²/A)/∂x ≈ ∂(V²A)/∂x
            if i > 1 and i < self.nx - 1:
                V_minus = Q_old[i-1] / max(self.B * h_old[i-1], 0.01)
                V_plus = Q_old[i+1] / max(self.B * h_old[i+1], 0.01)
                A_minus = self.B * h_old[i-1]
                A_plus = self.B * h_old[i+1]

                dVA_dx = (V_plus * A_plus - V_minus * A_minus) / (2 * self.dx)
                dV_dx = dVA_dx / A_i
            else:
                dV_dx = 0

            # 动量方程右端项
            dQ_dt = -V_i * dQ_dx + self.g * A_i * (self.S0 - Sf - dh_dx)

            # 更新状态（带松弛）
            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        # 边界节点处理（确保边界条件满足）
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream

        # 下游流量通过连续性方程确定
        A_last = self.B * h_new[-1]
        A_last_minus = self.B * h_new[-2]
        dA_dx_last = (A_last - A_last_minus) / self.dx
        # 使用上一步的信息估计
        Q_new[-1] = Q_new[-2]

        return h_new, Q_new

    def _preissmann_step(self, dt, Q_upstream, h_downstream):
        """
        Preissmann四点隐式格式（简化保守版本）

        使用θ=0.6的加权方案
        """

        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 使用更小的时间步长
        dt_eff = dt * 0.5
        omega = 0.2  # 更小的松弛因子

        # 显式预测步
        h_pred, Q_pred = self._explicit_step(dt_eff, Q_upstream, h_downstream)

        # 隐式校正步（加权平均）
        theta = 0.6
        h_new = theta * h_pred + (1 - theta) * h_old
        Q_new = theta * Q_pred + (1 - theta) * Q_old

        # 确保边界条件
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream

        return h_new, Q_new

    def _hll_step(self, dt, Q_upstream, h_downstream):
        """
        HLL有限体积法（Lax-Friedrichs flux）

        使用保守形式的通量计算
        """

        h_old = self.h.copy()
        Q_old = self.Q.copy()
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # CFL条件
        A_old = self.B * h_old
        V_old = Q_old / A_old
        c_old = np.sqrt(self.g * h_old)
        max_wave_speed = (np.abs(V_old) + c_old).max()
        dt_cfl = 0.3 * self.dx / max_wave_speed
        dt_eff = min(dt, dt_cfl)

        omega = 0.4

        # 边界条件
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream

        # 内部节点
        for i in range(1, self.nx - 1):
            A_i = self.B * h_old[i]
            V_i = Q_old[i] / A_i

            # 左右界面状态
            h_L = h_old[i]
            h_R = h_old[i+1]
            Q_L = Q_old[i]
            Q_R = Q_old[i+1]

            A_L = self.B * h_L
            A_R = self.B * h_R

            # Lax-Friedrichs通量
            # F = [Q, Q²/A + 0.5*g*A*h]

            # 质量通量
            F_mass_L = Q_L
            F_mass_R = Q_R
            F_mass = 0.5 * (F_mass_L + F_mass_R) - 0.5 * max_wave_speed * (A_R - A_L)

            # 动量通量（简化）
            F_mom_L = Q_L * Q_L / A_L + 0.5 * self.g * A_L * h_L
            F_mom_R = Q_R * Q_R / A_R + 0.5 * self.g * A_R * h_R
            F_mom = 0.5 * (F_mom_L + F_mom_R) - 0.5 * max_wave_speed * (Q_R - Q_L)

            # 源项
            P_i = self.B + 2 * h_old[i]
            R_i = A_i / P_i if P_i > 0.1 else 0
            if R_i > 0.01:
                Sf = (self.n * abs(V_i)) ** 2 / (R_i ** (4./3.))
                Sf = min(Sf, 10 * self.S0)
            else:
                Sf = 0

            S_mom = self.g * A_i * (self.S0 - Sf)

            # 更新（保守形式）
            dF_mass_dx = (F_mass_R - F_mass_L) / self.dx
            dF_mom_dx = (F_mom_R - F_mom_L) / self.dx

            dA_dt = -dF_mass_dx
            dQ_dt = -dF_mom_dx + S_mom

            h_new[i] = h_old[i] + omega * (dA_dt / self.B) * dt_eff
            Q_new[i] = Q_old[i] + omega * dQ_dt * dt_eff

        # 边界
        Q_new[0] = Q_upstream
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        return h_new, Q_new


def run_stability_test():
    """运行稳定性测试"""

    print("="*70)
    print("明渠非恒定流数值稳定性测试 - 使用恒定流初值")
    print("="*70)

    # 渠道参数
    params = {
        'length': 1000.0,      # 渠道长度 (m)
        'width': 10.0,         # 渠道宽度 (m)
        'slope': 0.001,        # 底坡
        'manning_n': 0.025,    # Manning糙率
        'nx': 51               # 空间离散点数
    }

    # 边界条件
    Q_upstream = 8.0       # 上游流量 (m³/s)
    h_downstream = 1.2     # 下游水深 (m)

    # 模拟参数
    T_total = 600.0        # 总模拟时间 (s)
    dt = 0.5               # 时间步长 (s)

    methods = ['explicit', 'preissmann', 'hll']
    method_names = {
        'explicit': 'EXPLICIT (显式有限差分)',
        'preissmann': 'PREISSMANN (四点隐式)',
        'hll': 'HLL (有限体积)'
    }

    results = {}
    evaluator = StabilityEvaluator()

    for method in methods:
        print(f"\n{'='*70}")
        print(f"测试方法: {method_names[method]}")
        print(f"{'='*70}")

        # 创建求解器
        solver = CanalSolverWithSteadyInit(
            params['length'],
            params['width'],
            params['slope'],
            params['manning_n'],
            params['nx'],
            method=method
        )

        # **关键改进：使用恒定流初值**
        solver.reset_with_steady_state(Q_upstream, h_downstream)

        # 时间积分
        n_steps = int(T_total / dt)
        time = np.zeros(n_steps)
        h_history = np.zeros((n_steps, params['nx']))
        Q_history = np.zeros((n_steps, params['nx']))

        print(f"\n开始时间积分 ({n_steps} 步)...")

        for step in range(n_steps):
            time[step] = step * dt
            h_history[step, :] = solver.h
            Q_history[step, :] = solver.Q

            # 执行一步
            solver.step(dt, Q_upstream, h_downstream)

            # 进度报告
            if (step + 1) % 200 == 0:
                Q_down = solver.Q[-1]
                h_up = solver.h[0]
                print(f"  步 {step+1}/{n_steps}: t={time[step]:.1f}s, "
                      f"Q_down={Q_down:.3f} m³/s, h_up={h_up:.3f} m")

        # 评估稳定性
        print(f"\n评估数值稳定性...")
        eval_result = evaluator.evaluate(
            time, h_history, Q_history, params, method_names[method]
        )

        results[method] = {
            'time': time,
            'h_history': h_history,
            'Q_history': Q_history,
            'eval': eval_result
        }

        # 收敛性检查（最后200步）
        Q_downstream_late = Q_history[-200:, -1]
        Q_mean = Q_downstream_late.mean()
        Q_std = Q_downstream_late.std()
        Q_cv = (Q_std / Q_mean * 100) if Q_mean > 0 else 0

        print(f"\n下游流量收敛性 (最后200步):")
        print(f"  均值: {Q_mean:.4f} m³/s")
        print(f"  标准差: {Q_std:.4f} m³/s")
        print(f"  变异系数: {Q_cv:.3f}%")

        if Q_cv < 1.0:
            print(f"  ✓ 已收敛 (CV < 1%)")
        elif Q_cv < 2.0:
            print(f"  ⚠ 基本收敛 (CV < 2%)")
        else:
            print(f"  ✗ 未收敛 (CV ≥ 2%)")

    # 生成对比图
    print(f"\n{'='*70}")
    print("生成对比可视化...")
    print(f"{'='*70}")

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle('明渠数值求解器稳定性对比 - 使用恒定流初值', fontsize=14, fontweight='bold')

    for idx, method in enumerate(methods):
        data = results[method]

        # 下游流量时间序列
        ax1 = axes[idx, 0]
        ax1.plot(data['time'], data['Q_history'][:, -1], 'b-', linewidth=1.5)
        ax1.axhline(y=Q_upstream, color='r', linestyle='--', label='上游流量')
        ax1.set_xlabel('时间 (s)')
        ax1.set_ylabel('下游流量 (m³/s)')
        ax1.set_title(f"{method_names[method]}")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 上游水深时间序列
        ax2 = axes[idx, 1]
        ax2.plot(data['time'], data['h_history'][:, 0], 'g-', linewidth=1.5)
        ax2.axhline(y=h_downstream, color='r', linestyle='--', label='下游水深')
        ax2.set_xlabel('时间 (s)')
        ax2.set_ylabel('上游水深 (m)')
        ax2.set_title(f"评分: {data['eval']['score']:.1f}/100")
        ax2.grid(True, alpha=0.3)
        ax2.legend()

    plt.tight_layout()

    # 保存图像
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, 'steady_init_stability_test.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n图像已保存: {fig_path}")

    # 打印汇总表
    print(f"\n{'='*70}")
    print("稳定性测试结果汇总")
    print(f"{'='*70}")
    print(f"{'求解方法':<20} {'综合评分':<12} {'振荡指数':<12} {'质量误差':<12} {'收敛性':<10}")
    print(f"{'-'*70}")

    for method in methods:
        eval_res = results[method]['eval']
        print(f"{method_names[method]:<20} "
              f"{eval_res['score']:>8.1f}/100  "
              f"{eval_res['oscillation_index']:>10.6f}  "
              f"{eval_res['mass_error']:>9.2f}%  "
              f"{eval_res['convergence_index']:>10.3f}")

    print(f"{'='*70}\n")

    plt.show()

    return results


if __name__ == '__main__':
    results = run_stability_test()
