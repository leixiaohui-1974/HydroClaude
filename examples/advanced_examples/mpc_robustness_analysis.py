"""
MPC鲁棒性分析

测试一阶MPC在以下不确定性条件下的性能：
1. 参数误差（K和τ的估计误差）
2. 测量噪声
3. 扰动变化
4. 与其他控制器的鲁棒性对比

目标：评估控制器在非理想条件下的实用性

作者：HydroClaude Team
日期：2025-10-24
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from linearized_canal_simulator import LinearizedCanalSimulator
from control.pid_controller import PIDController, PIDConfig
import cvxpy as cp

class SimpleFirstOrderMPC:
    """简单一阶MPC（用于鲁棒性测试）"""

    def __init__(self, K, tau, dt, y_work, u_work, Np=15, Nc=10,
                 Q=100, R=1, Qf=1000, u_min=0.1, u_max=4.0, du_max=0.5):
        self.K = K
        self.tau = tau
        self.dt = dt
        self.y_work = y_work
        self.u_work = u_work
        self.Np = Np
        self.Nc = Nc
        self.Q = Q
        self.R = R
        self.Qf = Qf
        self.u_min = u_min
        self.u_max = u_max
        self.du_max = du_max

        # 离散化
        self.a = np.exp(-dt / tau)
        self.b = K * (1 - np.exp(-dt / tau))

        self.u_prev = u_work
        self.prob = None

    def _build_problem(self):
        """构建优化问题"""
        y = cp.Variable(self.Np + 1)
        u = cp.Variable(self.Nc)
        y0 = cp.Parameter()
        r = cp.Parameter(self.Np + 1)
        u_prev = cp.Parameter()

        cost = 0
        constraints = [y[0] == y0]

        for k in range(self.Np):
            u_k = u[k] if k < self.Nc else u[self.Nc-1]
            cost += self.Q * cp.square(y[k] - r[k])

            if k < self.Nc:
                du = u[k] - (u_prev if k == 0 else u[k-1])
                cost += self.R * cp.square(du)
                constraints.append(u[k] >= self.u_min)
                constraints.append(u[k] <= self.u_max)
                constraints.append(du >= -self.du_max)
                constraints.append(du <= self.du_max)

            # 偏差模型
            dy_k = y[k] - self.y_work
            du_k = u_k - self.u_work
            dy_next = self.a * dy_k + self.b * du_k
            constraints.append(y[k+1] == self.y_work + dy_next)

        cost += self.Qf * cp.square(y[self.Np] - r[self.Np])

        self.prob = cp.Problem(cp.Minimize(cost), constraints)
        self.y0 = y0
        self.r = r
        self.u_prev_param = u_prev
        self.y_var = y
        self.u_var = u

    def compute_control(self, y_current, setpoint):
        """计算控制量"""
        if self.prob is None:
            self._build_problem()

        self.y0.value = y_current
        self.r.value = np.full(self.Np + 1, setpoint)
        self.u_prev_param.value = self.u_prev

        try:
            self.prob.solve(solver=cp.OSQP, verbose=False)
            if self.prob.status in ['optimal', 'optimal_inaccurate']:
                u_opt = self.u_var.value[0]
                self.u_prev = u_opt
                return u_opt, {'success': True}
            else:
                return self.u_prev, {'success': False}
        except:
            return self.u_prev, {'success': False}

    def reset(self):
        self.u_prev = self.u_work


def run_robustness_test(controller_type, K_error=0.0, tau_error=0.0,
                        noise_std=0.0, label=""):
    """
    运行鲁棒性测试

    Args:
        controller_type: 'mpc' or 'pid'
        K_error: K的相对误差（-0.5表示低估50%）
        tau_error: τ的相对误差
        noise_std: 测量噪声标准差 (m)
        label: 测试标签

    Returns:
        results: 性能指标字典
    """
    # 创建真实系统
    dt = 2.0
    h_work = 2.5
    a_work = 2.0
    setpoint = 2.2

    simulator = LinearizedCanalSimulator(h_work=h_work, a_work=a_work, dt=dt, use_linear=True)
    simulator.reset()

    # 获取真实参数
    K_true, tau_true = simulator.get_system_params()

    # 控制器使用有误差的参数
    K_controller = K_true * (1 + K_error)
    tau_controller = tau_true * (1 + tau_error)

    # 创建控制器
    if controller_type == 'mpc':
        controller = SimpleFirstOrderMPC(
            K=K_controller, tau=tau_controller, dt=dt,
            y_work=h_work, u_work=a_work,
            Np=15, Nc=10, Q=100, R=1, Qf=1000,
            u_min=0.1, u_max=4.0, du_max=0.5
        )
    elif controller_type == 'pid':
        controller = PIDController(
            PIDConfig(kp=-1.0, ki=-0.15, kd=0.0, dt=dt,
                     output_min=0.1, output_max=4.0)
        )
        controller.set_setpoint(setpoint)
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")

    # 仿真参数
    total_time = 800.0
    n_steps = int(total_time / dt)

    # 扰动时间表
    disturbance_schedule = [
        (0, 20.0),
        (200, 25.0),
        (400, 18.0),
        (600, 23.0)
    ]

    # 记录
    time_hist = []
    h_hist = []
    u_hist = []
    error_hist = []

    current_disturbance = 20.0

    for k in range(n_steps):
        t = k * dt

        # 更新扰动
        for t_switch, Q_new in disturbance_schedule:
            if abs(t - t_switch) < dt / 2:
                current_disturbance = Q_new
                simulator.set_disturbance(Q_new)
                break

        # 获取测量值（加噪声）
        y_true = simulator.h
        y_measured = y_true + np.random.randn() * noise_std

        # 计算控制量
        if controller_type == 'mpc':
            u, _ = controller.compute_control(y_measured, setpoint)
        else:
            u = controller.compute(y_measured)

        # 仿真一步
        y_next = simulator.step(u)

        # 记录
        time_hist.append(t)
        h_hist.append(y_next)
        u_hist.append(u)
        error_hist.append(y_next - setpoint)

    # 性能评估
    error_array = np.array(error_hist)
    mae = np.mean(np.abs(error_array))
    rmse = np.sqrt(np.mean(error_array**2))
    max_error = np.max(np.abs(error_array))

    # 稳态误差（最后100步）
    steady_error = np.mean(np.abs(error_array[-50:]))

    return {
        'label': label,
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
        'steady_error': steady_error,
        'time': time_hist,
        'h': h_hist,
        'u': u_hist,
        'error': error_hist
    }


print("=" * 80)
print("MPC鲁棒性分析")
print("=" * 80)

# 测试1：参数误差敏感性
print("\n【测试1】参数误差敏感性")
print("-" * 80)

K_errors = [-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5]  # -50%到+50%
tau_errors = [0.0]  # 固定τ，只变K
noise_std = 0.0  # 无噪声

mpc_results_K = []
pid_results_K = []

for K_err in K_errors:
    print(f"  测试 K误差={K_err*100:+.0f}%...", end='')

    # MPC测试
    result_mpc = run_robustness_test('mpc', K_error=K_err, tau_error=0.0, noise_std=0.0,
                                     label=f'K_err={K_err*100:.0f}%')
    mpc_results_K.append(result_mpc)

    # PID测试（作为基准）
    result_pid = run_robustness_test('pid', K_error=0.0, tau_error=0.0, noise_std=0.0,
                                     label='PID')
    pid_results_K.append(result_pid)

    print(f" MPC_MAE={result_mpc['mae']:.4f}m, PID_MAE={result_pid['mae']:.4f}m")

# 测试2：时间常数误差敏感性
print("\n【测试2】时间常数误差敏感性")
print("-" * 80)

# 注意：不要覆盖K_errors变量！
tau_errors = [-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5]  # -50%到+50%

mpc_results_tau = []

for tau_err in tau_errors:
    print(f"  测试 τ误差={tau_err*100:+.0f}%...", end='')

    result = run_robustness_test('mpc', K_error=0.0, tau_error=tau_err, noise_std=0.0,
                                 label=f'tau_err={tau_err*100:.0f}%')
    mpc_results_tau.append(result)

    print(f" MAE={result['mae']:.4f}m")

# 测试3：测量噪声敏感性
print("\n【测试3】测量噪声敏感性")
print("-" * 80)

noise_stds = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]  # 0-5cm噪声

mpc_results_noise = []
pid_results_noise = []

for noise in noise_stds:
    print(f"  测试 噪声std={noise*100:.1f}cm...", end='')

    result_mpc = run_robustness_test('mpc', K_error=0.0, tau_error=0.0, noise_std=noise,
                                     label=f'noise={noise*100:.1f}cm')
    mpc_results_noise.append(result_mpc)

    result_pid = run_robustness_test('pid', K_error=0.0, tau_error=0.0, noise_std=noise,
                                     label='PID')
    pid_results_noise.append(result_pid)

    print(f" MPC_MAE={result_mpc['mae']:.4f}m, PID_MAE={result_pid['mae']:.4f}m")

# 测试4：综合恶劣条件
print("\n【测试4】综合恶劣条件")
print("-" * 80)

worst_case_tests = [
    ('Nominal', 0.0, 0.0, 0.0),
    ('K_error_-30%', -0.3, 0.0, 0.0),
    ('K_error_+30%', 0.3, 0.0, 0.0),
    ('tau_error_-30%', 0.0, -0.3, 0.0),
    ('Noise_2cm', 0.0, 0.0, 0.02),
    ('Combined_worst', -0.3, -0.3, 0.02),
]

worst_results = []

for name, K_err, tau_err, noise in worst_case_tests:
    print(f"  测试 {name}...", end='')

    result_mpc = run_robustness_test('mpc', K_error=K_err, tau_error=tau_err,
                                     noise_std=noise, label=name)
    result_pid = run_robustness_test('pid', K_error=0.0, tau_error=0.0,
                                     noise_std=noise, label=name)

    worst_results.append({
        'name': name,
        'mpc': result_mpc,
        'pid': result_pid
    })

    print(f" MPC={result_mpc['mae']:.4f}m, PID={result_pid['mae']:.4f}m")

print("\n" + "=" * 80)
print("鲁棒性分析结果总结")
print("=" * 80)

# 绘图
fig = plt.figure(figsize=(16, 12))

# 子图1：K误差敏感性
ax1 = plt.subplot(2, 3, 1)
K_err_pcts = [K_err * 100 for K_err in K_errors]
mpc_maes_K = [r['mae'] * 100 for r in mpc_results_K]  # 转换为cm
pid_maes_K = [r['mae'] * 100 for r in pid_results_K]

ax1.plot(K_err_pcts, mpc_maes_K, 'b-o', linewidth=2, markersize=8, label='MPC')
ax1.plot(K_err_pcts, pid_maes_K, 'r--s', linewidth=2, markersize=8, label='PID (baseline)')
ax1.axvline(0, color='gray', linestyle=':', alpha=0.5)
ax1.set_xlabel('K estimation error (%)', fontsize=11)
ax1.set_ylabel('MAE (cm)', fontsize=11)
ax1.set_title('Sensitivity to Gain Error', fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 子图2：τ误差敏感性
ax2 = plt.subplot(2, 3, 2)
tau_err_pcts = [tau_err * 100 for tau_err in tau_errors]
mpc_maes_tau = [r['mae'] * 100 for r in mpc_results_tau]

ax2.plot(tau_err_pcts, mpc_maes_tau, 'b-o', linewidth=2, markersize=8, label='MPC')
ax2.axvline(0, color='gray', linestyle=':', alpha=0.5)
ax2.set_xlabel('τ estimation error (%)', fontsize=11)
ax2.set_ylabel('MAE (cm)', fontsize=11)
ax2.set_title('Sensitivity to Time Constant Error', fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 子图3：噪声敏感性
ax3 = plt.subplot(2, 3, 3)
noise_cms = [n * 100 for n in noise_stds]
mpc_maes_noise = [r['mae'] * 100 for r in mpc_results_noise]
pid_maes_noise = [r['mae'] * 100 for r in pid_results_noise]

ax3.plot(noise_cms, mpc_maes_noise, 'b-o', linewidth=2, markersize=8, label='MPC')
ax3.plot(noise_cms, pid_maes_noise, 'r--s', linewidth=2, markersize=8, label='PID')
ax3.set_xlabel('Measurement noise std (cm)', fontsize=11)
ax3.set_ylabel('MAE (cm)', fontsize=11)
ax3.set_title('Sensitivity to Measurement Noise', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 子图4：综合恶劣条件对比
ax4 = plt.subplot(2, 3, 4)
test_names = [r['name'] for r in worst_results]
mpc_maes_worst = [r['mpc']['mae'] * 100 for r in worst_results]
pid_maes_worst = [r['pid']['mae'] * 100 for r in worst_results]

x = np.arange(len(test_names))
width = 0.35

bars1 = ax4.bar(x - width/2, mpc_maes_worst, width, label='MPC', color='blue', alpha=0.7)
bars2 = ax4.bar(x + width/2, pid_maes_worst, width, label='PID', color='red', alpha=0.7)

ax4.set_xlabel('Test scenario', fontsize=11)
ax4.set_ylabel('MAE (cm)', fontsize=11)
ax4.set_title('Performance under Adverse Conditions', fontsize=12, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels(test_names, rotation=45, ha='right', fontsize=9)
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

# 添加数值标签
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)

# 子图5：鲁棒性热图（K vs τ误差）
ax5 = plt.subplot(2, 3, 5)
K_grid = np.linspace(-0.5, 0.5, 11)
tau_grid = np.linspace(-0.5, 0.5, 11)
MAE_grid = np.zeros((len(tau_grid), len(K_grid)))

print("\n计算鲁棒性热图...")
for i, tau_err in enumerate(tau_grid):
    for j, K_err in enumerate(K_grid):
        result = run_robustness_test('mpc', K_error=K_err, tau_error=tau_err,
                                     noise_std=0.0, label='')
        MAE_grid[i, j] = result['mae'] * 100  # cm

im = ax5.contourf(K_grid * 100, tau_grid * 100, MAE_grid, levels=15, cmap='YlOrRd')
ax5.contour(K_grid * 100, tau_grid * 100, MAE_grid, levels=[2, 5, 10],
            colors='black', linewidths=1.5, linestyles='--')
ax5.plot(0, 0, 'g*', markersize=15, label='Nominal')
ax5.set_xlabel('K error (%)', fontsize=11)
ax5.set_ylabel('τ error (%)', fontsize=11)
ax5.set_title('Robustness Heat Map (MAE in cm)', fontsize=12, fontweight='bold')
ax5.legend()
plt.colorbar(im, ax=ax5, label='MAE (cm)')

# 子图6：性能统计对比
ax6 = plt.subplot(2, 3, 6)

metrics = ['MAE', 'RMSE', 'Max\nError']
nominal_idx = 0  # Nominal case
worst_idx = -1    # Combined worst case

mpc_nominal = [
    worst_results[nominal_idx]['mpc']['mae'] * 100,
    worst_results[nominal_idx]['mpc']['rmse'] * 100,
    worst_results[nominal_idx]['mpc']['max_error'] * 100
]

mpc_worst = [
    worst_results[worst_idx]['mpc']['mae'] * 100,
    worst_results[worst_idx]['mpc']['rmse'] * 100,
    worst_results[worst_idx]['mpc']['max_error'] * 100
]

pid_nominal = [
    worst_results[nominal_idx]['pid']['mae'] * 100,
    worst_results[nominal_idx]['pid']['rmse'] * 100,
    worst_results[nominal_idx]['pid']['max_error'] * 100
]

pid_worst = [
    worst_results[worst_idx]['pid']['mae'] * 100,
    worst_results[worst_idx]['pid']['rmse'] * 100,
    worst_results[worst_idx]['pid']['max_error'] * 100
]

x = np.arange(len(metrics))
width = 0.2

bars1 = ax6.bar(x - 1.5*width, mpc_nominal, width, label='MPC Nominal', color='blue', alpha=0.9)
bars2 = ax6.bar(x - 0.5*width, mpc_worst, width, label='MPC Worst', color='blue', alpha=0.5)
bars3 = ax6.bar(x + 0.5*width, pid_nominal, width, label='PID Nominal', color='red', alpha=0.9)
bars4 = ax6.bar(x + 1.5*width, pid_worst, width, label='PID Worst', color='red', alpha=0.5)

ax6.set_ylabel('Error (cm)', fontsize=11)
ax6.set_title('Nominal vs Worst-Case Performance', fontsize=12, fontweight='bold')
ax6.set_xticks(x)
ax6.set_xticklabels(metrics)
ax6.legend(fontsize=9)
ax6.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('mpc_robustness_analysis.png', dpi=150, bbox_inches='tight')
print(f"\n✅ 图片已保存: mpc_robustness_analysis.png")

# 打印详细结果
print("\n" + "=" * 80)
print("详细性能指标")
print("=" * 80)

print("\n【综合恶劣条件测试结果】")
print("-" * 80)
print(f"{'场景':<25} {'MPC MAE':<12} {'PID MAE':<12} {'MPC优势':<10}")
print("-" * 80)

for r in worst_results:
    mpc_mae = r['mpc']['mae'] * 100
    pid_mae = r['pid']['mae'] * 100
    advantage = (pid_mae - mpc_mae) / pid_mae * 100

    print(f"{r['name']:<25} {mpc_mae:>8.3f} cm   {pid_mae:>8.3f} cm   {advantage:>+6.1f}%")

print("=" * 80)
print("鲁棒性分析完成")
print("=" * 80)
