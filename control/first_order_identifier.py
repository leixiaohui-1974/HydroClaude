"""
一阶系统参数辨识器

针对一阶传递函数 H(s) = K/(τs+1) 的在线辨识

与IDZ辨识器的区别：
- IDZ: G(s) = K*(1+τ_z*s)/(s*(1+τ_d*s))  ← 有积分器
- 一阶: H(s) = K/(τs+1)  ← 无积分器，稳定系统

适用于：
- 线性化渠道系统
- 水箱液位（有出流）
- 温度控制系统

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class FirstOrderParameters:
    """一阶系统参数"""
    K: float  # 稳态增益 (输出/输入)
    tau: float  # 时间常数 (s)
    theta: float = 0.0  # 纯延迟 (s)


class FirstOrderIdentifier:
    """
    一阶系统在线辨识器

    离散一阶模型：y[k] = a*y[k-1] + b*u[k-d]

    其中：
    - a = exp(-dt/τ)
    - b = K*(1 - exp(-dt/τ))
    - d = round(θ/dt)  # 延迟步数

    连续参数转换：
    - τ = -dt / ln(a)
    - K = b / (1 - a)
    """

    def __init__(self, dt: float, forgetting_factor: float = 0.98):
        """
        初始化辨识器

        Args:
            dt: 采样时间 (s)
            forgetting_factor: 遗忘因子 (0.95-0.99)
        """
        self.dt = dt
        self.lambda_f = forgetting_factor

        # RLS参数
        self.theta = np.zeros(2)  # [a, b]
        self.P = np.eye(2) * 1000.0

        # 数据缓冲
        self.y_buffer = []
        self.u_buffer = []

        # 当前估计
        self.params: Optional[FirstOrderParameters] = None

        # 平滑历史
        self.K_history = []
        self.tau_history = []

    def update(self, u: float, y: float) -> Optional[FirstOrderParameters]:
        """
        更新辨识

        Args:
            u: 输入
            y: 输出

        Returns:
            估计的一阶参数
        """
        # 添加到缓冲
        self.u_buffer.append(u)
        self.y_buffer.append(y)

        # 需要至少3个数据点
        if len(self.y_buffer) < 3:
            return None

        k = len(self.y_buffer) - 1

        # 构建回归向量：y[k] = a*y[k-1] + b*u[k]
        if k >= 1:
            phi = np.array([
                self.y_buffer[k-1],  # y[k-1]
                self.u_buffer[k]     # u[k]
            ]).reshape(-1, 1)

            y_k = self.y_buffer[k]

            # RLS更新
            # 预测
            y_pred = (phi.T @ self.theta.reshape(-1, 1))[0, 0]
            error = y_k - y_pred

            # 增益
            P_phi = self.P @ phi
            denominator = self.lambda_f + phi.T @ P_phi
            K_gain = P_phi / denominator

            # 参数更新
            self.theta = self.theta.flatten() + (K_gain * error).flatten()

            # 协方差更新
            I_Kphi = np.eye(2) - K_gain @ phi.T
            self.P = (I_Kphi @ self.P @ I_Kphi.T) / self.lambda_f

            # 每5步转换为连续参数
            if k % 5 == 0 and k > 10:
                self.params = self._discrete_to_continuous()

        # 保持缓冲大小
        if len(self.y_buffer) > 1000:
            self.y_buffer.pop(0)
            self.u_buffer.pop(0)

        return self.params

    def _discrete_to_continuous(self) -> FirstOrderParameters:
        """
        从离散参数转换为连续参数

        离散模型：y[k] = a*y[k-1] + b*u[k]
        连续模型：H(s) = K/(τs+1)

        转换公式：
        - a = exp(-dt/τ) → τ = -dt/ln(a)
        - b = K*(1-exp(-dt/τ)) = K*(1-a) → K = b/(1-a)
        """
        a, b = self.theta
        dt = self.dt

        # 计算连续参数
        # τ = -dt / ln(a)
        if 0 < a < 1:
            tau_raw = -dt / np.log(a)
        else:
            # a超出范围，使用默认值
            tau_raw = 100.0 * dt

        # K = b / (1 - a)
        if abs(1 - a) > 0.001:
            K_raw = b / (1 - a)
        else:
            # 分母接近0，使用b的值
            K_raw = b / dt if dt > 0 else 1.0

        # 平滑滤波
        if self.params is not None:
            alpha = 0.3  # 平滑系数
            K = alpha * K_raw + (1 - alpha) * self.params.K
            tau = alpha * tau_raw + (1 - alpha) * self.params.tau
        else:
            K = K_raw
            tau = tau_raw

        # 限制参数范围
        # K可以是负值（反向作用）
        if K >= 0:
            K = np.clip(K, 0.01, 100.0)
        else:
            K = np.clip(K, -100.0, -0.001)

        tau = np.clip(tau, dt, 10000.0)

        # 延迟估计（简化：假设无延迟）
        theta = 0.0

        # 记录历史
        self.K_history.append(K)
        self.tau_history.append(tau)

        return FirstOrderParameters(K=K, tau=tau, theta=theta)

    def get_parameters(self) -> Optional[FirstOrderParameters]:
        """获取当前参数估计"""
        return self.params

    def reset(self):
        """重置辨识器"""
        self.theta = np.zeros(2)
        self.P = np.eye(2) * 1000.0
        self.y_buffer = []
        self.u_buffer = []
        self.params = None
        self.K_history = []
        self.tau_history = []


# ====================================================================================
# 测试代码
# ====================================================================================
def test_first_order_identifier():
    """测试一阶辨识器"""
    import matplotlib.pyplot as plt
    from scipy import signal

    print("=" * 80)
    print("一阶系统辨识器测试")
    print("=" * 80)

    # 真实系统参数
    K_true = -0.3
    tau_true = 206.0
    dt = 2.0

    print(f"\n真实系统参数:")
    print(f"  K = {K_true}")
    print(f"  τ = {tau_true}s")
    print(f"  dt = {dt}s")

    # 创建离散系统
    a_true = np.exp(-dt / tau_true)
    b_true = K_true * (1 - np.exp(-dt / tau_true))

    print(f"\n离散参数:")
    print(f"  a = {a_true:.6f}")
    print(f"  b = {b_true:.6f}")

    # 创建辨识器
    identifier = FirstOrderIdentifier(dt=dt, forgetting_factor=0.98)

    # 仿真
    n_steps = 300
    y = 2.5  # 初始水位
    u_prev = 2.0

    time_hist = []
    y_hist = []
    u_hist = []
    K_est_hist = []
    tau_est_hist = []

    print(f"\n开始仿真测试...")

    for k in range(n_steps):
        t = k * dt

        # 激励信号
        if t < 100:
            u = 2.5
        elif t < 200:
            u = 2.0 + 0.5 * np.sin(2 * np.pi * t / 100.0)
        else:
            u = 2.5 if (t // 20) % 2 == 0 else 1.5

        u = np.clip(u, 0.1, 4.0)

        # 仿真真实系统：y[k] = a*y[k-1] + b*u[k] + 噪声
        noise = 0.01 * np.random.randn()  # 1cm测量噪声
        y = a_true * y + b_true * u + noise

        # 在线辨识
        params = identifier.update(u, y)

        # 记录
        time_hist.append(t)
        y_hist.append(y)
        u_hist.append(u)

        if params is not None:
            K_est_hist.append(params.K)
            tau_est_hist.append(params.tau)
        else:
            K_est_hist.append(np.nan)
            tau_est_hist.append(np.nan)

        # 显示进度
        if k % 50 == 0 and params is not None:
            print(f"  t={t:.0f}s: K_est={params.K:.4f}, τ_est={params.tau:.1f}s")

    # 最终结果
    final_params = identifier.get_parameters()
    if final_params is not None:
        print(f"\n最终辨识结果:")
        print(f"  K_est = {final_params.K:.4f} (真实={K_true:.4f})")
        print(f"  τ_est = {final_params.tau:.1f}s (真实={tau_true:.1f}s)")

        K_error = abs(final_params.K - K_true) / abs(K_true) * 100
        tau_error = abs(final_params.tau - tau_true) / tau_true * 100

        print(f"\n误差:")
        print(f"  K误差 = {K_error:.1f}%")
        print(f"  τ误差 = {tau_error:.1f}%")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    ax1 = axes[0]
    ax1_twin = ax1.twinx()
    ax1.plot(time_hist, y_hist, 'b-', linewidth=2, label='Output y')
    ax1_twin.plot(time_hist, u_hist, 'g-', linewidth=1.5, alpha=0.7, label='Input u')
    ax1.set_ylabel('Output y', fontsize=12, color='b')
    ax1_twin.set_ylabel('Input u', fontsize=12, color='g')
    ax1.set_title('First-Order System Identification Test', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(time_hist, K_est_hist, 'r-', linewidth=2, label='K_est')
    ax2.axhline(K_true, color='k', linestyle='--', linewidth=2, label=f'K_true={K_true:.4f}')
    ax2.set_ylabel('Gain K', fontsize=12)
    ax2.set_title('Gain Estimation', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = axes[2]
    ax3.plot(time_hist, tau_est_hist, 'purple', linewidth=2, label='τ_est')
    ax3.axhline(tau_true, color='k', linestyle='--', linewidth=2, label=f'τ_true={tau_true:.1f}s')
    ax3.set_ylabel('Time constant τ (s)', fontsize=12)
    ax3.set_xlabel('Time (s)', fontsize=12)
    ax3.set_title('Time Constant Estimation', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('first_order_identifier_test.png', dpi=150)
    print(f"\n✅ 图片已保存: first_order_identifier_test.png")

    print("\n" + "=" * 80)
    if final_params and K_error < 20 and tau_error < 20:
        print("✅ 测试通过：辨识精度优秀")
    elif final_params and K_error < 50 and tau_error < 50:
        print("⭕ 测试通过：辨识精度可接受")
    else:
        print("❌ 测试失败：辨识精度不足")
    print("=" * 80)


if __name__ == "__main__":
    test_first_order_identifier()
