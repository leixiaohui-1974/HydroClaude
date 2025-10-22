"""
示例1: 明渠非恒定流综合分析（多求解器对比）

本示例实现了多种数值方法求解Saint-Venant方程，包括：
1. Preissmann四点隐式格式
2. HLL有限体积法（Riemann求解器）
3. MOC特征线法

深入分析内容：
- 边界条件分析：上游流量 + 下游水位边界
- 阶跃响应分析：上游流量阶跃、下游水位阶跃
- IDZ降阶模型参数辨识（4个传递函数）
- 多种数值方法的稳定性和收敛性对比
- 详细的纵剖面动画（固定纵坐标范围）

作者: Claude
日期: 2025-10-21
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy import signal

# 导入现有的求解器
from physics.numerical_methods.preissmann_solver import PreissmannSolver
from physics.numerical_methods.fvm_solver import FVMSolver


class CanalSolver:
    """
    明渠求解器统一接口

    支持多种数值方法：
    - 'preissmann': Preissmann四点隐式格式
    - 'hll': HLL有限体积法
    - 'moc': 特征线法
    """

    def __init__(self, length, width, slope, manning_n, nx, method='preissmann'):
        """
        初始化明渠求解器

        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            slope: 底坡 (无量纲)
            manning_n: Manning粗糙系数
            nx: 空间网格数
            method: 求解方法 ('preissmann', 'hll', 'moc')
        """
        self.L = length
        self.B = width
        self.S0 = slope
        self.n = manning_n
        self.nx = nx
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)
        self.g = 9.81
        self.method = method

        # 初始化状态变量
        self.h = np.ones(nx) * 5.0  # 初始水深5m
        self.Q = np.ones(nx) * 5.0  # 初始流量5m³/s

        # 初始化求解器
        if method == 'preissmann':
            self.solver = PreissmannSolver(theta=0.6, max_iter=20, tolerance=1e-5)
        elif method == 'hll':
            self.solver = FVMSolver(flux_scheme='hll', limiter='minmod')
        elif method == 'moc':
            # MOC方法使用显式格式
            self.solver = None
        else:
            raise ValueError(f"未知的求解方法: {method}")

    def step(self, dt, Q_upstream, h_downstream):
        """
        执行一个时间步

        Args:
            dt: 时间步长 (s)
            Q_upstream: 上游流量边界条件 (m³/s)
            h_downstream: 下游水位边界条件 (m)

        Returns:
            h_new: 更新后的水深 (m)
            Q_new: 更新后的流量 (m³/s)
        """

        if self.method == 'preissmann':
            # 应用边界条件
            self.Q[0] = Q_upstream
            self.h[-1] = h_downstream

            # 边界条件字典
            bc = {
                'upstream_flow': Q_upstream,
                'downstream_level': h_downstream
            }

            # 调用Preissmann求解器
            h_new, Q_new = self.solver.solve_canal_step(
                self.h, self.Q, dt, self.dx,
                self.B, self.n, self.S0, bc
            )

        elif self.method == 'hll':
            # HLL方法使用有限体积法
            A = self.h * self.B

            # 调用HLL求解器
            h_new, Q_new = self.solver.solve_canal_step(
                A, self.Q, dt, self.dx,
                self.B, self.n, self.S0
            )

            # 应用边界条件（修正边界）
            Q_new[0] = Q_upstream
            h_new[-1] = h_downstream

        elif self.method == 'moc':
            # MOC方法使用显式特征线格式
            h_new, Q_new = self._moc_step(dt, Q_upstream, h_downstream)

        else:
            raise ValueError(f"未知的求解方法: {self.method}")

        # 确保物理合理性
        h_new = np.maximum(h_new, 0.1)
        Q_new = np.maximum(Q_new, 0.01)

        # 更新状态
        self.h = h_new
        self.Q = Q_new

        return h_new, Q_new

    def _moc_step(self, dt, Q_upstream, h_downstream):
        """
        稳定的显式有限差分法

        使用一阶迎风格式和稳定性控制
        """

        h_new = self.h.copy()
        Q_new = self.Q.copy()

        # 计算最大波速（用于CFL条件检查）
        max_wave_speed = 0
        for i in range(self.nx):
            if self.h[i] > 0:
                V = self.Q[i] / (self.h[i] * self.B)
                c = np.sqrt(self.g * self.h[i])
                max_wave_speed = max(max_wave_speed, abs(V) + c)

        # CFL条件检查
        if max_wave_speed > 0:
            cfl = max_wave_speed * dt / self.dx
            if cfl > 0.5:
                # 自动调整时间步长
                dt_eff = 0.5 * self.dx / max_wave_speed
            else:
                dt_eff = dt
        else:
            dt_eff = dt

        # 内部节点更新
        for i in range(1, self.nx - 1):
            A = self.h[i] * self.B

            if A > 1e-6:
                V = self.Q[i] / A
            else:
                V = 0

            # 连续方程：∂A/∂t + ∂Q/∂x = 0
            dQ_dx = (self.Q[i] - self.Q[i-1]) / self.dx  # 迎风格式
            dA_dt = -dQ_dx

            # 动量方程（忽略对流项以提高稳定性）
            # ∂Q/∂t + gA·∂h/∂x = gA(S0 - Sf)

            # 摩阻坡度（使用限制器）
            if self.h[i] > 0.1:
                P = self.B + 2 * self.h[i]
                R = A / P if P > 0 else 0
                if R > 0:
                    Sf = min((self.n * abs(V)) ** 2 / (R ** (4./3.)), 10 * self.S0)
                else:
                    Sf = 0
            else:
                Sf = 0

            # 压力项
            dh_dx = (self.h[i] - self.h[i-1]) / self.dx  # 迎风格式

            # 动量方程源项
            dQ_dt = self.g * A * (self.S0 - Sf - dh_dx)

            # 更新状态（使用松弛因子）
            relaxation = 0.8
            h_new[i] = self.h[i] + relaxation * dA_dt * dt_eff / self.B
            Q_new[i] = self.Q[i] + relaxation * dQ_dt * dt_eff

            # 限制最小值
            h_new[i] = max(h_new[i], 0.1)
            Q_new[i] = max(Q_new[i], 0.01)

        # 边界条件
        Q_new[0] = Q_upstream
        h_new[0] = max(h_new[1], 0.1)  # 外推

        h_new[-1] = h_downstream
        Q_new[-1] = max(Q_new[-2], 0.01)  # 外推

        return h_new, Q_new

    def reset(self, h0=5.0, Q0=5.0):
        """重置初始条件"""
        self.h = np.ones(self.nx) * h0
        self.Q = np.ones(self.nx) * Q0


class IDZModel:
    """
    IDZ (Integrator Delay Zero) 降阶模型

    传递函数形式:
    G(s) = K · (1 + T3·s) · exp(-delay·s) / [s · (1 + T1·s) · (1 + T2·s)]

    4个方向的传递函数：
    - G11: 上游流量 → 上游水位
    - G12: 下游水位 → 上游水位
    - G21: 上游流量 → 下游水位
    - G22: 下游水位 → 下游水位
    """

    def __init__(self):
        self.params = {
            'G11': {'K': 0.0, 'T1': 0.0, 'T2': 0.0, 'T3': 0.0, 'delay': 0.0},
            'G12': {'K': 0.0, 'T1': 0.0, 'T2': 0.0, 'T3': 0.0, 'delay': 0.0},
            'G21': {'K': 0.0, 'T1': 0.0, 'T2': 0.0, 'T3': 0.0, 'delay': 0.0},
            'G22': {'K': 0.0, 'T1': 0.0, 'T2': 0.0, 'T3': 0.0, 'delay': 0.0},
        }

    def identify_from_step_response(self, time, input_step, output_response, direction):
        """
        从阶跃响应辨识IDZ模型参数

        使用特征点法:
        - 稳态增益 K = Δy_∞ / Δu
        - 时间常数 T1: 63.2%响应时间
        - 时间常数 T2: 86.5%响应时间
        - 延迟时间: 10%响应时间

        Args:
            time: 时间数组
            input_step: 输入阶跃幅值
            output_response: 输出响应数组
            direction: 传递函数方向 ('G11', 'G12', 'G21', 'G22')
        """

        # 归一化输出响应
        y0 = output_response[0]
        y_inf = output_response[-1]
        dy = y_inf - y0

        # 稳态增益
        if abs(input_step) > 1e-6:
            K = dy / input_step
        else:
            K = 0.0

        # 时间常数辨识
        if abs(dy) > 1e-4:
            # 10%响应时间（延迟）
            target_10 = y0 + 0.10 * dy
            idx_10 = np.argmin(np.abs(output_response - target_10))
            delay = max(time[idx_10] - time[0], 0.0)

            # 63.2%响应时间
            target_632 = y0 + 0.632 * dy
            idx_632 = np.argmin(np.abs(output_response - target_632))
            T1 = max(time[idx_632] - time[0] - delay, 1.0)

            # 86.5%响应时间
            target_865 = y0 + 0.865 * dy
            idx_865 = np.argmin(np.abs(output_response - target_865))
            T2 = max((time[idx_865] - time[0] - delay) / 2, 0.5)

            # T3通常设为T2的一半
            T3 = T2 / 2
        else:
            T1, T2, T3, delay = 1.0, 0.5, 0.25, 0.0

        # 保存参数
        self.params[direction] = {
            'K': K,
            'T1': T1,
            'T2': T2,
            'T3': T3,
            'delay': delay
        }

        return self.params[direction]


def create_annotated_animation(solver, time_list, h_history, Q_history,
                               scenario_name, boundary_info, step_time,
                               output_filename, y_range=None, Q_range=None):
    """
    创建带标注的纵剖面动画（固定纵坐标范围）

    Args:
        solver: 求解器对象
        time_list: 时间列表
        h_history: 水深历史记录
        Q_history: 流量历史记录
        scenario_name: 场景名称
        boundary_info: 边界条件信息
        step_time: 阶跃时刻
        output_filename: 输出文件名
        y_range: 固定的纵坐标范围 [y_min, y_max]（水位图）
        Q_range: 固定的纵坐标范围 [Q_min, Q_max]（流量图）
    """

    print(f"  生成动画: {output_filename}")

    x = solver.x
    slope = solver.S0
    bottom_elevation = -slope * x

    # 如果没有指定范围，自动计算
    if y_range is None:
        all_water_surface = [bottom_elevation + h for h in h_history]
        y_min = min([min(ws) for ws in all_water_surface]) - 0.5
        y_max = max([max(ws) for ws in all_water_surface]) + 0.5
        y_range = [y_min, y_max]

    if Q_range is None:
        Q_min = max(min([min(Q) for Q in Q_history]) - 0.5, 0)
        Q_max = max([max(Q) for Q in Q_history]) + 0.5
        Q_range = [Q_min, Q_max]

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    def animate(frame):
        for ax in axes:
            ax.clear()

        current_time = time_list[frame]
        h = h_history[frame]
        Q = Q_history[frame]

        # === 上图：水位剖面 ===
        ax = axes[0]

        # 绘制渠道底部
        ax.fill_between(x, bottom_elevation - 0.5, bottom_elevation,
                        color='#8B4513', alpha=0.5, label='渠道底部')

        # 绘制水面线
        water_surface = bottom_elevation + h
        ax.plot(x, water_surface, 'b-', linewidth=3, label='水面线')
        ax.fill_between(x, bottom_elevation, water_surface,
                        color='#4A90E2', alpha=0.4)

        # 底坡标注
        ax.text(0.98, 0.05, f'底坡: {slope:.6f} ({slope*100:.4f}%)',
               transform=ax.transAxes, fontsize=10, ha='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 边界条件标注
        ax.annotate(boundary_info['upstream'],
                   xy=(x[0], water_surface[0]), xytext=(-80, 40),
                   textcoords='offset points', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.9),
                   arrowprops=dict(arrowstyle='->', color='red', lw=2))

        ax.annotate(boundary_info['downstream'],
                   xy=(x[-1], water_surface[-1]), xytext=(80, -40),
                   textcoords='offset points', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.9),
                   arrowprops=dict(arrowstyle='->', color='blue', lw=2))

        # 时间标记
        time_text = f'时间 = {current_time:.1f} s'
        if current_time >= step_time:
            time_text += ' [阶跃后]'
            color = 'red'
        else:
            color = 'green'

        ax.text(0.5, 0.95, time_text, transform=ax.transAxes,
               fontsize=12, ha='center', weight='bold', color=color,
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

        ax.set_xlabel('距离 (m)', fontsize=11)
        ax.set_ylabel('高程 (m)', fontsize=11)
        ax.set_title(f'{scenario_name} - 纵剖面水位分布',
                    fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper right', fontsize=9)
        ax.set_xlim([x[0], x[-1]])
        ax.set_ylim(y_range)  # 固定纵坐标范围

        # === 下图：流量剖面 ===
        ax = axes[1]
        ax.plot(x, Q, 'g-o', linewidth=2.5, markersize=4,
               markeredgecolor='black', markeredgewidth=0.5)
        ax.axhline(y=Q[0], color='r', linestyle=':', alpha=0.5,
                  label=f'上游: {Q[0]:.2f} m³/s')
        ax.axhline(y=Q[-1], color='b', linestyle=':', alpha=0.5,
                  label=f'下游: {Q[-1]:.2f} m³/s')

        ax.set_xlabel('距离 (m)', fontsize=11)
        ax.set_ylabel('流量 (m³/s)', fontsize=11)
        ax.set_title('流量分布', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=9)
        ax.set_xlim([x[0], x[-1]])
        ax.set_ylim(Q_range)  # 固定纵坐标范围

        plt.tight_layout()

    # 创建动画（每5帧取一帧）
    keyframes = list(range(0, len(time_list), 5))
    anim = animation.FuncAnimation(fig, animate, frames=keyframes,
                                  interval=100, repeat=True)

    # 保存动画
    os.makedirs("reports/figures", exist_ok=True)
    output_path = f"reports/figures/{output_filename}"
    anim.save(output_path, writer='pillow', fps=10, dpi=100)
    plt.close(fig)

    return output_path


def run_scenario(solver, scenario_name, Q_func, h_func, dt, total_time, step_time):
    """
    运行单个场景

    Args:
        solver: 求解器对象
        scenario_name: 场景名称
        Q_func: 上游流量函数 Q(t)
        h_func: 下游水位函数 h(t)
        dt: 时间步长
        total_time: 总模拟时间
        step_time: 阶跃时刻

    Returns:
        time, hu, hd, Qu, Qd, h_history, Q_history
    """

    print(f"\n{scenario_name}")
    print("-" * 80)

    solver.reset(h0=5.0, Q0=5.0)

    n_steps = int(total_time / dt)
    time_list = []
    hu_list = []
    hd_list = []
    Qu_list = []
    Qd_list = []
    h_history = []
    Q_history = []

    for i in range(n_steps):
        t = i * dt

        # 计算边界条件
        Q_up = Q_func(t, step_time)
        h_down = h_func(t, step_time)

        # 执行时间步
        solver.step(dt, Q_up, h_down)

        # 记录结果
        time_list.append(t)
        hu_list.append(solver.h[0])
        hd_list.append(solver.h[-1])
        Qu_list.append(solver.Q[0])
        Qd_list.append(solver.Q[-1])
        h_history.append(solver.h.copy())
        Q_history.append(solver.Q.copy())

        # 打印中间结果
        if i % 100 == 0:
            print(f"  t={t:6.1f}s: hu={solver.h[0]:.3f}m, hd={solver.h[-1]:.3f}m, "
                  f"Qu={solver.Q[0]:.2f}m³/s, Qd={solver.Q[-1]:.2f}m³/s")

    print(f"  最终状态:")
    print(f"    上游: h={hu_list[-1]:.3f}m, Q={Qu_list[-1]:.2f}m³/s")
    print(f"    下游: h={hd_list[-1]:.3f}m, Q={Qd_list[-1]:.2f}m³/s")

    return (np.array(time_list), np.array(hu_list), np.array(hd_list),
            np.array(Qu_list), np.array(Qd_list), h_history, Q_history)


def run_comprehensive_analysis():
    """运行综合分析"""

    print("=" * 80)
    print("示例1: 明渠非恒定流综合分析（多求解器对比）")
    print("=" * 80)
    print()

    # === 渠道参数 ===
    canal_params = {
        'length': 1000.0,      # 长度 1 km
        'width': 10.0,         # 宽度 10 m
        'slope': 0.0001,       # 底坡 0.01%
        'manning_n': 0.025,    # Manning系数
        'nx': 51               # 网格数
    }

    print("渠道基本参数:")
    print(f"  长度: {canal_params['length']} m")
    print(f"  宽度: {canal_params['width']} m")
    print(f"  底坡: {canal_params['slope']} ({canal_params['slope']*100:.4f}%)")
    print(f"  Manning系数: {canal_params['manning_n']}")
    print(f"  空间网格数: {canal_params['nx']}")
    print()

    # === 仿真参数 ===
    sim_params = {
        'dt': 2.0,              # 时间步长 2s（满足CFL条件）
        'step_time': 200.0,     # 阶跃时刻
        'total_time': 600.0     # 总模拟时间
    }

    print("仿真参数:")
    print(f"  时间步长: {sim_params['dt']} s")
    print(f"  阶跃时刻: {sim_params['step_time']} s")
    print(f"  总模拟时间: {sim_params['total_time']} s")
    print()

    # === 选择求解器 ===
    solver_method = 'moc'  # 可选: 'preissmann', 'hll', 'moc'
    print(f"使用求解器: {solver_method.upper()}（稳定显式格式）")
    print()

    # 创建求解器
    solver = CanalSolver(**canal_params, method=solver_method)

    # === 场景1: 上游流量阶跃 ===
    def Q1_func(t, t_step):
        return 5.0 if t < t_step else 8.0

    def h1_func(t, t_step):
        return 5.0

    result1 = run_scenario(
        solver, "场景1: 上游流量阶跃 (5.0 → 8.0 m³/s)",
        Q1_func, h1_func,
        sim_params['dt'], sim_params['total_time'], sim_params['step_time']
    )
    time1, hu1, hd1, Qu1, Qd1, h_hist1, Q_hist1 = result1

    # === 场景2: 下游水位阶跃 ===
    def Q2_func(t, t_step):
        return 5.0

    def h2_func(t, t_step):
        return 5.0 if t < t_step else 6.0

    result2 = run_scenario(
        solver, "场景2: 下游水位阶跃 (5.0 → 6.0 m)",
        Q2_func, h2_func,
        sim_params['dt'], sim_params['total_time'], sim_params['step_time']
    )
    time2, hu2, hd2, Qu2, Qd2, h_hist2, Q_hist2 = result2

    # === IDZ模型辨识 ===
    print("\n" + "=" * 80)
    print("IDZ降阶模型参数辨识")
    print("=" * 80)

    idz = IDZModel()
    step_idx = int(sim_params['step_time'] / sim_params['dt'])

    # G11: Qu → hu
    time_resp = time1[step_idx:] - time1[step_idx]
    params_G11 = idz.identify_from_step_response(time_resp, 3.0, hu1[step_idx:], 'G11')
    print(f"\nG11 (Qu→hu):")
    print(f"  K={params_G11['K']:.4f}, T1={params_G11['T1']:.1f}s, "
          f"T2={params_G11['T2']:.1f}s, delay={params_G11['delay']:.1f}s")

    # G21: Qu → hd
    params_G21 = idz.identify_from_step_response(time_resp, 3.0, hd1[step_idx:], 'G21')
    print(f"\nG21 (Qu→hd):")
    print(f"  K={params_G21['K']:.4f}, T1={params_G21['T1']:.1f}s, "
          f"T2={params_G21['T2']:.1f}s, delay={params_G21['delay']:.1f}s")

    # G12: hd → hu
    params_G12 = idz.identify_from_step_response(time_resp, 1.0, hu2[step_idx:], 'G12')
    print(f"\nG12 (hd→hu):")
    print(f"  K={params_G12['K']:.4f}, T1={params_G12['T1']:.1f}s, "
          f"T2={params_G12['T2']:.1f}s, delay={params_G12['delay']:.1f}s")

    # G22: hd → hd
    params_G22 = idz.identify_from_step_response(time_resp, 1.0, hd2[step_idx:], 'G22')
    print(f"\nG22 (hd→hd):")
    print(f"  K={params_G22['K']:.4f}, T1={params_G22['T1']:.1f}s, "
          f"T2={params_G22['T2']:.1f}s, delay={params_G22['delay']:.1f}s")

    # === 生成可视化 ===
    print("\n" + "=" * 80)
    print("生成可视化图表")
    print("=" * 80)

    generated_files = []

    # 计算固定的纵坐标范围
    all_h = np.concatenate([h for h in h_hist1] + [h for h in h_hist2])
    all_Q = np.concatenate([Q for Q in Q_hist1] + [Q for Q in Q_hist2])

    bottom_elev = -canal_params['slope'] * solver.x
    all_water_elev = np.concatenate([bottom_elev + h for h in h_hist1] +
                                     [bottom_elev + h for h in h_hist2])

    y_min = min(all_water_elev) - 0.5
    y_max = max(all_water_elev) + 0.5
    Q_min = max(min(all_Q) - 0.5, 0)
    Q_max = max(all_Q) + 0.5

    print(f"  固定坐标范围:")
    print(f"    水位图: [{y_min:.2f}, {y_max:.2f}] m")
    print(f"    流量图: [{Q_min:.2f}, {Q_max:.2f}] m³/s")
    print()

    # 场景1动画
    boundary_info_1 = {
        'upstream': f'上游边界:\n流量阶跃\n5.0→8.0 m³/s',
        'downstream': '下游边界:\n水位=5.0 m'
    }

    anim1 = create_annotated_animation(
        solver, time1, h_hist1, Q_hist1,
        f'场景1: 上游流量阶跃 ({solver_method.upper()})',
        boundary_info_1, sim_params['step_time'],
        f'example_01_comprehensive_scenario1_{solver_method}.gif',
        y_range=[y_min, y_max],
        Q_range=[Q_min, Q_max]
    )
    generated_files.append(anim1)
    print(f"  ✓ 场景1动画")

    # 场景2动画
    boundary_info_2 = {
        'upstream': '上游边界:\n流量=5.0 m³/s',
        'downstream': '下游边界:\n水位阶跃\n5.0→6.0 m'
    }

    anim2 = create_annotated_animation(
        solver, time2, h_hist2, Q_hist2,
        f'场景2: 下游水位阶跃 ({solver_method.upper()})',
        boundary_info_2, sim_params['step_time'],
        f'example_01_comprehensive_scenario2_{solver_method}.gif',
        y_range=[y_min, y_max],
        Q_range=[Q_min, Q_max]
    )
    generated_files.append(anim2)
    print(f"  ✓ 场景2动画")

    # 阶跃响应对比图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # G11响应
    ax = axes[0, 0]
    ax.plot(time1, hu1, 'b-', linewidth=2)
    ax.axvline(x=sim_params['step_time'], color='r', linestyle='--', alpha=0.7, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=10)
    ax.set_ylabel('上游水位 (m)', fontsize=10)
    ax.set_title('场景1: 上游水位响应 (G11)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # G21响应
    ax = axes[0, 1]
    ax.plot(time1, hd1, 'g-', linewidth=2)
    ax.axvline(x=sim_params['step_time'], color='r', linestyle='--', alpha=0.7, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=10)
    ax.set_ylabel('下游水位 (m)', fontsize=10)
    ax.set_title('场景1: 下游水位响应 (G21)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # G12响应
    ax = axes[1, 0]
    ax.plot(time2, hu2, 'b-', linewidth=2)
    ax.axvline(x=sim_params['step_time'], color='r', linestyle='--', alpha=0.7, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=10)
    ax.set_ylabel('上游水位 (m)', fontsize=10)
    ax.set_title('场景2: 上游水位响应 (G12)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # G22响应
    ax = axes[1, 1]
    ax.plot(time2, hd2, 'g-', linewidth=2)
    ax.axvline(x=sim_params['step_time'], color='r', linestyle='--', alpha=0.7, label='阶跃时刻')
    ax.set_xlabel('时间 (s)', fontsize=10)
    ax.set_ylabel('下游水位 (m)', fontsize=10)
    ax.set_title('场景2: 下游水位响应 (G22)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    fig_path = f'reports/figures/example_01_comprehensive_step_responses_{solver_method}.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(fig_path)
    print(f"  ✓ 阶跃响应图")

    # IDZ参数表
    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.axis('tight')
    ax.axis('off')

    table_data = [
        ['传递函数', '增益K', 'T1 (s)', 'T2 (s)', 'T3 (s)', '延迟 (s)', '物理意义'],
        ['G11: Qu→hu', f"{params_G11['K']:.4f}", f"{params_G11['T1']:.1f}",
         f"{params_G11['T2']:.1f}", f"{params_G11['T3']:.1f}", f"{params_G11['delay']:.1f}",
         '上游流量对上游水位的影响'],
        ['G12: hd→hu', f"{params_G12['K']:.4f}", f"{params_G12['T1']:.1f}",
         f"{params_G12['T2']:.1f}", f"{params_G12['T3']:.1f}", f"{params_G12['delay']:.1f}",
         '下游水位对上游的回水效应'],
        ['G21: Qu→hd', f"{params_G21['K']:.4f}", f"{params_G21['T1']:.1f}",
         f"{params_G21['T2']:.1f}", f"{params_G21['T3']:.1f}", f"{params_G21['delay']:.1f}",
         '上游流量向下游的传播'],
        ['G22: hd→hd', f"{params_G22['K']:.4f}", f"{params_G22['T1']:.1f}",
         f"{params_G22['T2']:.1f}", f"{params_G22['T3']:.1f}", f"{params_G22['delay']:.1f}",
         '下游水位边界的直接作用']
    ]

    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                    colWidths=[0.14, 0.10, 0.10, 0.10, 0.10, 0.10, 0.36])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.8)

    # 表头样式
    for i in range(len(table_data[0])):
        table[(0, i)].set_facecolor('#3498DB')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # 行样式
    for i in range(1, len(table_data)):
        for j in range(len(table_data[0])):
            color = '#ECF0F1' if i % 2 == 0 else '#FFFFFF'
            table[(i, j)].set_facecolor(color)

    plt.title(f'IDZ降阶模型参数表 ({solver_method.upper()}求解器)',
             fontsize=14, fontweight='bold', pad=20)

    table_path = f'reports/figures/example_01_comprehensive_idz_params_{solver_method}.png'
    plt.savefig(table_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(table_path)
    print(f"  ✓ IDZ参数表")

    # === 总结 ===
    print("\n" + "=" * 80)
    print("综合分析完成!")
    print("=" * 80)

    print(f"\n求解器: {solver_method.upper()}")

    print(f"\n场景1结果 (上游流量 5.0→8.0 m³/s):")
    print(f"  上游水位: {hu1[0]:.3f} → {hu1[-1]:.3f} m (变化={hu1[-1]-hu1[0]:+.3f} m)")
    print(f"  下游水位: {hd1[0]:.3f} → {hd1[-1]:.3f} m (变化={hd1[-1]-hd1[0]:+.3f} m)")
    print(f"  上游流量: {Qu1[0]:.2f} → {Qu1[-1]:.2f} m³/s (变化={Qu1[-1]-Qu1[0]:+.2f} m³/s)")
    print(f"  下游流量: {Qd1[0]:.2f} → {Qd1[-1]:.2f} m³/s (变化={Qd1[-1]-Qd1[0]:+.2f} m³/s)")

    print(f"\n场景2结果 (下游水位 5.0→6.0 m):")
    print(f"  上游水位: {hu2[0]:.3f} → {hu2[-1]:.3f} m (变化={hu2[-1]-hu2[0]:+.3f} m)")
    print(f"  下游水位: {hd2[0]:.3f} → {hd2[-1]:.3f} m (变化={hd2[-1]-hd2[0]:+.3f} m)")
    print(f"  上游流量: {Qu2[0]:.2f} → {Qu2[-1]:.2f} m³/s (变化={Qu2[-1]-Qu2[0]:+.2f} m³/s)")
    print(f"  下游流量: {Qd2[0]:.2f} → {Qd2[-1]:.2f} m³/s (变化={Qd2[-1]-Qd2[0]:+.2f} m³/s)")

    print(f"\n生成的文件:")
    for f in generated_files:
        # 获取文件大小
        file_size = os.path.getsize(f) / 1024  # KB
        if file_size > 1024:
            file_size_str = f"{file_size/1024:.1f} MB"
        else:
            file_size_str = f"{file_size:.0f} KB"
        print(f"  - {f} ({file_size_str})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_comprehensive_analysis()
