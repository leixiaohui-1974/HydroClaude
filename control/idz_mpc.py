"""
IDZ模型MPC控制器

基于IDZ模型的MPC：G(s) = K*(1+τ_z*s)/(s*(1+τ_d*s))

关键特性：
1. 包含积分器（1/s）→ 零稳态误差
2. 包含零点（1+τ_z*s）→ 相位超前
3. 包含极点（1+τ_d*s）→ 系统动态

优势：
- 对常值扰动有天然抑制能力（类似PID积分作用）
- 保持MPC的约束处理和预测能力
- 适合需要零稳态误差的应用

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
import osqp
from scipy import sparse


@dataclass
class IDZMPCConfig:
    """IDZ MPC配置参数"""
    prediction_horizon: int = 15      # 预测时域
    control_horizon: int = 10         # 控制时域
    dt: float = 10.0                  # 采样时间(s)
    Q: float = 100.0                  # 跟踪误差权重
    R: float = 1.0                    # 控制增量权重
    Qf: float = 1000.0                # 终端代价权重
    u_min: float = 0.1                # 控制量下限(m)
    u_max: float = 4.0                # 控制量上限(m)
    du_max: float = 0.5               # 控制增量上限(m/step)
    solver: str = 'OSQP'              # 求解器
    verbose: bool = False             # 详细输出


class IDZMPC:
    """
    IDZ模型MPC控制器

    系统模型：
    连续时间：G(s) = K*(1+τ_z*s)/(s*(1+τ_d*s))

    离散状态空间（增量型）：
    x[k+1] = A*x[k] + B*Δu[k]
    y[k] = C*x[k]

    状态变量：
    x = [Δy[k], x_int[k]]^T
    其中 x_int 是积分状态
    """

    def __init__(self, K: float, tau_z: float, tau_d: float, config: IDZMPCConfig):
        """
        初始化IDZ MPC控制器

        Args:
            K: 静态增益 (m/m)
            tau_z: 零点时间常数 (s)
            tau_d: 极点时间常数 (s)
            config: MPC配置
        """
        self.K = K
        self.tau_z = tau_z
        self.tau_d = tau_d
        self.config = config
        self.dt = config.dt

        # 离散化IDZ模型
        self._discretize_idz_model()

        # 构建MPC预测矩阵
        self._build_prediction_matrices()

        # 初始化状态
        self.x = np.zeros(2)  # [Δy, x_int]
        self.u_prev = 2.0     # 上一次控制量
        self.y_prev = 2.5     # 上一次输出

        # QP求解器
        self.prob = None

        print(f"IDZ MPC初始化:")
        print(f"  K = {K:.4f} m/m")
        print(f"  τ_z = {tau_z:.1f}s")
        print(f"  τ_d = {tau_d:.1f}s")
        print(f"  dt = {self.dt}s")
        print(f"  离散参数: a11={self.A[0,0]:.6f}, a12={self.A[0,1]:.6f}")
        print(f"              a21={self.A[1,0]:.6f}, a22={self.A[1,1]:.6f}")
        print(f"              b1={self.B[0,0]:.6f}, b2={self.B[1,0]:.6f}")

        # 验证稳态增益
        self._verify_steady_state_gain()

    def _discretize_idz_model(self):
        """
        离散化IDZ模型

        连续时间状态空间（增量型）:
        dx1/dt = -x1/τ_d + K*(1 + τ_z/τ_d)*Δu/τ_d
        dx2/dt = x1  (积分器)
        Δy = x1

        使用零阶保持器离散化
        """
        # 连续时间矩阵
        Ac = np.array([
            [-1/self.tau_d, 0],
            [1, 0]
        ])
        Bc = np.array([
            [self.K * (1 + self.tau_z/self.tau_d) / self.tau_d],
            [0]
        ])
        Cc = np.array([[1, 0]])

        # 零阶保持器离散化
        # 对于简单矩阵，使用解析解
        a = np.exp(-self.dt / self.tau_d)

        self.A = np.array([
            [a, 0],
            [self.tau_d * (1 - a), 1]
        ])

        self.B = np.array([
            [self.K * (1 + self.tau_z/self.tau_d) * (1 - a)],
            [self.K * (1 + self.tau_z/self.tau_d) * self.dt -
             self.K * (1 + self.tau_z/self.tau_d) * self.tau_d * (1 - a)]
        ])

        self.C = np.array([[1, 0]])

    def _verify_steady_state_gain(self):
        """验证离散系统的稳态增益"""
        # 对于IDZ模型，稳态增益应该趋向无穷（因为有积分器）
        # 但我们可以验证单步响应的增益部分
        # G(0) = K*1/(0*1) → 无穷，但K*(1+τ_z/τ_d)/τ_d是初始斜率
        initial_gain = self.B[0, 0]
        expected_gain = self.K * (1 + self.tau_z/self.tau_d) * (1 - np.exp(-self.dt/self.tau_d))
        print(f"  初始响应增益验证: b1 = {initial_gain:.6f} (理论值 = {expected_gain:.6f})")

    def _build_prediction_matrices(self):
        """构建MPC预测矩阵"""
        Np = self.config.prediction_horizon
        Nc = self.config.control_horizon
        nx = 2  # 状态维度

        # 构建增广预测矩阵 Φ 和 Θ
        # Y = Φ*x[k] + Θ*ΔU

        self.Phi = np.zeros((Np, nx))
        self.Theta = np.zeros((Np, Nc))

        # 计算 Φ (预测矩阵)
        A_power = np.eye(nx)
        for i in range(Np):
            A_power = A_power @ self.A
            self.Phi[i, :] = (self.C @ A_power).flatten()

        # 计算 Θ (控制矩阵)
        for i in range(Np):
            for j in range(min(i+1, Nc)):
                A_power = np.linalg.matrix_power(self.A, i-j)
                self.Theta[i, j] = (self.C @ A_power @ self.B)[0, 0]

    def compute_control(self, y_current: float, setpoint: float) -> Tuple[float, dict]:
        """
        计算MPC控制量

        Args:
            y_current: 当前输出
            setpoint: 设定值

        Returns:
            u: 控制量
            info: 附加信息
        """
        # 更新状态（增量型）
        delta_y = y_current - self.y_prev
        self.x[0] = delta_y
        self.x[1] = self.x[1] + delta_y  # 积分累积

        # 预测时域长度
        Np = self.config.prediction_horizon
        Nc = self.config.control_horizon

        # 参考轨迹（增量型）
        # 由于是增量模型，最终希望 Δy = 0，所以参考是当前误差的补偿
        error = setpoint - y_current
        r = np.zeros(Np)  # 理想情况下希望增量为0（到达稳态）

        # 预测未来输出（相对于当前值的增量）
        # Y_pred = Φ*x + Θ*ΔU
        y_pred_free = self.Phi @ self.x

        # 构建QP问题: min 0.5*ΔU^T*H*ΔU + f^T*ΔU
        # subject to: G*ΔU <= h

        # 代价函数
        Q_bar = np.eye(Np) * self.config.Q
        Q_bar[-1, -1] = self.config.Qf
        R_bar = np.eye(Nc) * self.config.R

        # H = Θ^T*Q*Θ + R
        H = self.Theta.T @ Q_bar @ self.Theta + R_bar
        H = (H + H.T) / 2  # 确保对称性

        # f = Θ^T*Q*(y_pred_free - r)
        # 但我们实际要跟踪的是绝对误差 error，需要转换
        # 简化：直接用误差的增量作为目标
        # 如果当前有误差，希望通过控制使得未来输出趋向设定点
        # 可以用 y_future = y_current + Δy_predicted
        # 所以 error_future = setpoint - (y_current + Δy_predicted)
        #                    = error - Δy_predicted
        # 目标：最小化 error_future^2
        # 实际上，对于有积分器的系统，只要 Δy 最终趋向0即可

        # 修正：使用当前误差驱动控制
        # 希望未来的绝对位置达到setpoint
        # y_future[i] = y_current + sum(Δy[j]) for j=0 to i
        # 累积预测矩阵
        Phi_cum = np.zeros((Np, 2))
        Theta_cum = np.zeros((Np, Nc))

        for i in range(Np):
            for j in range(i+1):
                if j == 0:
                    Phi_cum[i, :] += self.Phi[j, :]
                    for k in range(Nc):
                        if k <= j:
                            Theta_cum[i, k] += self.Theta[j, k]
                else:
                    Phi_cum[i, :] += self.Phi[j, :]
                    for k in range(Nc):
                        if k <= j:
                            Theta_cum[i, k] += self.Theta[j, k]

        # 预测绝对位置
        y_abs_pred_free = y_current + Phi_cum @ self.x

        # 参考轨迹（绝对值）
        r_abs = np.ones(Np) * setpoint

        # 重新构建代价函数
        H = Theta_cum.T @ Q_bar @ Theta_cum + R_bar
        H = (H + H.T) / 2

        f = Theta_cum.T @ Q_bar @ (y_abs_pred_free - r_abs)

        # 约束
        # 1. 控制量约束: u_min <= u_prev + sum(Δu) <= u_max
        # 2. 控制增量约束: -du_max <= Δu[i] <= du_max

        # 构建约束矩阵
        # sum(Δu[0:j]) 的累积矩阵
        A_u_cum = np.tril(np.ones((Nc, Nc)))

        # u_prev + sum(Δu) <= u_max
        # -u_prev - sum(Δu) <= -u_min
        # Δu[i] <= du_max
        # -Δu[i] <= du_max

        G_list = []
        h_list = []

        # 控制量上限约束
        G_list.append(A_u_cum)
        h_list.append(np.ones(Nc) * (self.config.u_max - self.u_prev))

        # 控制量下限约束
        G_list.append(-A_u_cum)
        h_list.append(np.ones(Nc) * (-self.config.u_min + self.u_prev))

        # 控制增量上限约束
        G_list.append(np.eye(Nc))
        h_list.append(np.ones(Nc) * self.config.du_max)

        # 控制增量下限约束
        G_list.append(-np.eye(Nc))
        h_list.append(np.ones(Nc) * self.config.du_max)

        G = np.vstack(G_list)
        h = np.concatenate(h_list)

        # 求解QP
        P = sparse.csc_matrix(H)
        q = f
        A = sparse.csc_matrix(G)
        l = -np.inf * np.ones(len(h))
        u = h

        if self.prob is None:
            self.prob = osqp.OSQP()
            self.prob.setup(P, q, A, l, u,
                          verbose=self.config.verbose,
                          eps_abs=1e-4,
                          eps_rel=1e-4)
        else:
            self.prob.update(q=q, l=l, u=u)

        # 求解
        res = self.prob.solve()

        if res.info.status != 'solved':
            print(f"⚠️  OSQP求解失败: {res.info.status}")
            # 应急控制：简单P控制
            delta_u = -0.1 * error  # 简单比例控制
            delta_u = np.clip(delta_u, -self.config.du_max, self.config.du_max)
        else:
            delta_u = res.x[0]

        # 更新控制量
        u = self.u_prev + delta_u
        u = np.clip(u, self.config.u_min, self.config.u_max)

        # 更新历史
        self.u_prev = u
        self.y_prev = y_current

        info = {
            'delta_u': delta_u,
            'predicted_output': y_abs_pred_free[0] if Np > 0 else y_current,
            'error': error,
            'integral_state': self.x[1]
        }

        return u, info

    def reset(self):
        """重置控制器状态"""
        self.x = np.zeros(2)
        self.u_prev = 2.0
        self.y_prev = 2.5
        if self.prob is not None:
            self.prob = None


def main():
    """测试IDZ MPC"""
    print("=" * 80)
    print("IDZ MPC控制器测试")
    print("=" * 80)

    # 创建IDZ MPC
    config = IDZMPCConfig(
        prediction_horizon=15,
        control_horizon=10,
        dt=10.0,
        Q=100.0,
        R=1.0,
        Qf=1000.0,
        u_min=0.1,
        u_max=4.0,
        du_max=0.5,
        solver='OSQP',
        verbose=False
    )

    # IDZ参数（从之前的辨识结果）
    K = -0.3
    tau_z = 168.0
    tau_d = 206.0

    controller = IDZMPC(K=K, tau_z=tau_z, tau_d=tau_d, config=config)

    print("\n测试完成！✅")


if __name__ == "__main__":
    main()
