"""
IDZ模型模块 (Integrator Delay Zero Model)

IDZ模型是明渠系统的经典控制模型，由Schuurmans等人提出
用于描述明渠池段的动态特性，适用于MPC控制

模型形式：
连续时间：G(s) = K * (1 - τ_z*s) / (s * (1 + τ_d*s)) * e^(-θ*s)
离散时间：状态空间形式

参数说明：
- K: 增益 (steady-state gain)
- τ_z: 零点时间常数 (zero time constant)
- τ_d: 延迟时间常数 (delay time constant)
- θ: 纯滞后 (pure time delay)

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
from scipy import signal
from scipy.linalg import expm


@dataclass
class IDZParameters:
    """
    IDZ模型参数

    Attributes:
        K: 增益 (m/m³/s)
        tau_z: 零点时间常数 (s)
        tau_d: 延迟时间常数 (s)
        theta: 纯滞后 (s)
    """
    K: float
    tau_z: float
    tau_d: float
    theta: float

    def validate(self):
        """验证参数合理性"""
        if self.K <= 0:
            raise ValueError(f"增益K必须为正: {self.K}")
        if self.tau_z < 0:
            raise ValueError(f"零点时间常数tau_z必须非负: {self.tau_z}")
        if self.tau_d <= 0:
            raise ValueError(f"延迟时间常数tau_d必须为正: {self.tau_d}")
        if self.theta < 0:
            raise ValueError(f"纯滞后theta必须非负: {self.theta}")

    @staticmethod
    def from_hydraulics(length: float, width: float, bed_slope: float,
                       manning: float, normal_depth: float) -> 'IDZParameters':
        """
        从水力学参数计算IDZ模型参数

        基于Saint-Venant方程的线性化

        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            bed_slope: 底坡
            manning: 曼宁系数
            normal_depth: 正常水深 (m)

        Returns:
            IDZ参数
        """
        # 水力学计算
        area = width * normal_depth
        perimeter = width + 2 * normal_depth
        hydraulic_radius = area / perimeter

        # 正常流速
        velocity = (1 / manning) * (hydraulic_radius ** (2/3)) * (bed_slope ** 0.5)

        # 弗劳德数
        froude = velocity / np.sqrt(9.81 * normal_depth)

        # IDZ参数估计（经验公式）
        # 增益：水位变化 / 流量变化
        K = length / (width * velocity)

        # 零点时间常数：与回水效应相关
        tau_z = length / (velocity * (1 + froude**2))

        # 延迟时间常数：池段响应时间
        tau_d = length / (velocity * np.sqrt(1 + froude**2))

        # 纯滞后：波传播时间
        wave_celerity = velocity + np.sqrt(9.81 * normal_depth)
        theta = length / wave_celerity

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta)


class IDZModel:
    """
    IDZ模型类

    提供连续时间和离散时间表达
    """

    def __init__(self, params: IDZParameters, dt: float):
        """
        初始化IDZ模型

        Args:
            params: IDZ参数
            dt: 采样时间 (s)
        """
        params.validate()
        self.params = params
        self.dt = dt

        # 离散化
        self._discretize()

    def _discretize(self):
        """
        离散化IDZ模型为状态空间形式

        使用零阶保持器（ZOH）离散化

        状态空间形式：
        x(k+1) = A*x(k) + B*u(k)
        y(k) = C*x(k) + D*u(k)

        IDZ传递函数: G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s)) * e^(-θ*s)

        注意：使用 (1 + τ_z*s) 而不是 (1 - τ_z*s)，
        这符合明渠系统的回水效应（backwater effect）
        """
        K = self.params.K
        tau_z = self.params.tau_z
        tau_d = self.params.tau_d
        theta = self.params.theta
        dt = self.dt

        # 计算延迟步数
        self.delay_steps = int(np.round(theta / dt))
        effective_theta = self.delay_steps * dt

        # 连续时间传递函数（不考虑纯滞后）
        # G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s))
        #      = K*(1 + τ_z*s) / (s + τ_d*s²)
        #      = K*(1 + τ_z*s) / (τ_d*s² + s)

        # 分子多项式: K*τ_z*s + K
        num = [K*tau_z, K]

        # 分母多项式: τ_d*s² + s
        den = [tau_d, 1, 0]

        # 使用scipy创建状态空间
        sys_c = signal.TransferFunction(num, den)
        sys_ss_c = signal.tf2ss(num, den)

        Ac = sys_ss_c[0]
        Bc = sys_ss_c[1]
        Cc = sys_ss_c[2]
        Dc = sys_ss_c[3]

        # 零阶保持器离散化
        n = Ac.shape[0]

        # A = e^(Ac*dt)
        self.A = expm(Ac * dt)

        # B = ∫[0,dt] e^(Ac*τ) dτ * Bc
        # 使用数值积分
        M = np.zeros((n+1, n+1))
        M[:n, :n] = Ac
        M[:n, n:] = Bc

        expM = expm(M * dt)
        self.B = expM[:n, n:]

        self.C = Cc
        self.D = Dc

        # 初始化延迟缓冲区
        self.delay_buffer = np.zeros(max(self.delay_steps, 1))

        # 初始化状态
        self.x = np.zeros((2, 1))

    def step(self, u: float) -> float:
        """
        单步仿真

        Args:
            u: 输入（流量变化）

        Returns:
            y: 输出（水位变化）
        """
        # 更新延迟缓冲区
        self.delay_buffer = np.roll(self.delay_buffer, 1)
        self.delay_buffer[0] = u

        # 获取延迟后的输入
        u_delayed = self.delay_buffer[-1]

        # 状态更新
        u_vec = np.array([[u_delayed]])
        self.x = self.A @ self.x + self.B @ u_vec

        # 输出
        y = (self.C @ self.x + self.D @ u_vec)[0, 0]

        return y

    def predict(self, u_sequence: np.ndarray, x0: Optional[np.ndarray] = None) -> np.ndarray:
        """
        多步预测（用于MPC）

        Args:
            u_sequence: 输入序列 [N_horizon]
            x0: 初始状态 [n_states] (可选)

        Returns:
            y_sequence: 输出序列 [N_horizon]
        """
        if x0 is not None:
            x = x0.reshape(-1, 1)
        else:
            x = self.x.copy()

        N = len(u_sequence)
        y_sequence = np.zeros(N)

        # 复制延迟缓冲区
        delay_buffer = self.delay_buffer.copy()

        for k in range(N):
            # 更新延迟缓冲区
            delay_buffer = np.roll(delay_buffer, 1)
            delay_buffer[0] = u_sequence[k]

            # 获取延迟后的输入
            u_delayed = delay_buffer[-1]

            # 状态更新
            u_vec = np.array([[u_delayed]])
            x = self.A @ x + self.B @ u_vec

            # 输出
            y = (self.C @ x + self.D @ u_vec)[0, 0]
            y_sequence[k] = y

        return y_sequence

    def get_state(self) -> np.ndarray:
        """获取当前状态"""
        return self.x.flatten()

    def set_state(self, x: np.ndarray):
        """设置状态"""
        self.x = x.reshape(-1, 1)

    def reset(self):
        """重置模型状态"""
        self.x = np.zeros((2, 1))
        self.delay_buffer = np.zeros(max(self.delay_steps, 1))

    def get_step_response(self, n_steps: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取单位阶跃响应

        Args:
            n_steps: 步数

        Returns:
            t: 时间序列
            y: 响应序列
        """
        self.reset()

        t = np.arange(n_steps) * self.dt
        y = np.zeros(n_steps)

        for k in range(n_steps):
            y[k] = self.step(1.0)

        self.reset()

        return t, y


class SeriesIDZModel:
    """
    串联IDZ模型

    用于多池段串联明渠系统
    """

    def __init__(self, pool_params: List[IDZParameters], dt: float):
        """
        初始化串联IDZ模型

        Args:
            pool_params: 各池段IDZ参数列表
            dt: 采样时间 (s)
        """
        self.n_pools = len(pool_params)
        self.dt = dt

        # 创建各池段模型
        self.models = [IDZModel(params, dt) for params in pool_params]

        # 总状态维度
        self.n_states = 2 * self.n_pools

        # 构建整体状态空间矩阵
        self._build_state_space()

    def _build_state_space(self):
        """构建整体状态空间矩阵"""
        n = self.n_states
        m = self.n_pools + 1  # n_pools个闸门/泵站输入

        # 初始化矩阵
        self.A = np.zeros((n, n))
        self.B = np.zeros((n, m))
        self.C = np.zeros((self.n_pools, n))
        self.D = np.zeros((self.n_pools, m))

        # 填充各池段的矩阵
        for i, model in enumerate(self.models):
            # 状态索引
            idx = slice(2*i, 2*i+2)

            # A矩阵（对角块）
            self.A[idx, idx] = model.A

            # B矩阵（每个池段受上下游流量影响）
            # 池段i的水量平衡：dV/dt = Q_in - Q_out
            # 输入u[i]是上游流量，u[i+1]是下游流量
            self.B[idx, i] = model.B[:, 0]      # 上游流量（流入）
            if i < self.n_pools:
                self.B[idx, i+1] = -model.B[:, 0]  # 下游流量（流出）

            # C矩阵
            self.C[i, idx] = model.C

            # D矩阵
            self.D[i, i] = model.D[0, 0]
            if i < self.n_pools:
                self.D[i, i+1] = -model.D[0, 0]

        # 初始化状态
        self.x = np.zeros((n, 1))

    def step(self, u: np.ndarray) -> np.ndarray:
        """
        单步仿真

        Args:
            u: 输入向量 [n_pools+1]（各闸门/泵站流量）

        Returns:
            y: 输出向量 [n_pools]（各池段水位）
        """
        u = u.reshape(-1, 1)

        # 状态更新
        self.x = self.A @ self.x + self.B @ u

        # 输出
        y = self.C @ self.x + self.D @ u

        return y.flatten()

    def predict(self, u_sequence: np.ndarray, x0: Optional[np.ndarray] = None) -> np.ndarray:
        """
        多步预测

        Args:
            u_sequence: 输入序列 [N_horizon, n_pools+1]
            x0: 初始状态 (可选)

        Returns:
            y_sequence: 输出序列 [N_horizon, n_pools]
        """
        if x0 is not None:
            x = x0.reshape(-1, 1)
        else:
            x = self.x.copy()

        N = u_sequence.shape[0]
        y_sequence = np.zeros((N, self.n_pools))

        for k in range(N):
            u = u_sequence[k].reshape(-1, 1)

            # 状态更新
            x = self.A @ x + self.B @ u

            # 输出
            y = self.C @ x + self.D @ u
            y_sequence[k] = y.flatten()

        return y_sequence

    def get_state(self) -> np.ndarray:
        """获取当前状态"""
        return self.x.flatten()

    def set_state(self, x: np.ndarray):
        """设置状态"""
        self.x = x.reshape(-1, 1)

    def reset(self):
        """重置模型"""
        self.x = np.zeros((self.n_states, 1))
        for model in self.models:
            model.reset()


def design_idz_from_canal_geometry(
    lengths: List[float],
    widths: List[float],
    bed_slopes: List[float],
    manning_coeffs: List[float],
    normal_depths: List[float],
    dt: float
) -> SeriesIDZModel:
    """
    从明渠几何参数设计串联IDZ模型

    Args:
        lengths: 各池段长度 (m)
        widths: 各池段宽度 (m)
        bed_slopes: 各池段底坡
        manning_coeffs: 各池段曼宁系数
        normal_depths: 各池段正常水深 (m)
        dt: 采样时间 (s)

    Returns:
        串联IDZ模型
    """
    n_pools = len(lengths)

    if not (len(widths) == len(bed_slopes) == len(manning_coeffs) ==
            len(normal_depths) == n_pools):
        raise ValueError("所有参数列表长度必须相同")

    # 计算各池段IDZ参数
    pool_params = []
    for i in range(n_pools):
        params = IDZParameters.from_hydraulics(
            length=lengths[i],
            width=widths[i],
            bed_slope=bed_slopes[i],
            manning=manning_coeffs[i],
            normal_depth=normal_depths[i]
        )
        pool_params.append(params)

    # 创建串联模型
    return SeriesIDZModel(pool_params, dt)


if __name__ == "__main__":
    """测试IDZ模型"""

    print("=" * 70)
    print("IDZ模型测试")
    print("=" * 70)

    # 测试1：单池段IDZ模型
    print("\n[测试1] 单池段IDZ模型")
    print("-" * 70)

    # 从水力学参数创建
    params = IDZParameters.from_hydraulics(
        length=1000.0,      # 1km
        width=10.0,         # 10m
        bed_slope=0.0001,   # 1:10000
        manning=0.025,
        normal_depth=2.0    # 2m
    )

    print(f"IDZ参数（从水力学计算）:")
    print(f"  增益 K = {params.K:.3f} m/(m³/s)")
    print(f"  零点时间常数 τ_z = {params.tau_z:.1f} s")
    print(f"  延迟时间常数 τ_d = {params.tau_d:.1f} s")
    print(f"  纯滞后 θ = {params.theta:.1f} s")

    # 创建模型
    dt = 60.0  # 1分钟采样
    model = IDZModel(params, dt)

    print(f"\n离散化参数:")
    print(f"  采样时间 dt = {dt} s")
    print(f"  延迟步数 = {model.delay_steps}")
    print(f"  状态矩阵 A =\n{model.A}")
    print(f"  输入矩阵 B =\n{model.B}")
    print(f"  输出矩阵 C =\n{model.C}")
    print(f"  直接传递 D =\n{model.D}")

    # 阶跃响应
    print(f"\n单位阶跃响应:")
    t, y = model.get_step_response(n_steps=60)

    print(f"  最终值: {y[-1]:.3f} m")
    print(f"  稳态增益: {params.K:.3f} m/(m³/s)")
    print(f"  前10个时刻的响应:")
    for i in range(0, 10):
        print(f"    t = {t[i]:6.1f} s, y = {y[i]:8.4f} m")

    # 测试2：串联三池段系统
    print("\n[测试2] 串联三池段IDZ模型")
    print("-" * 70)

    # 三个池段的几何参数
    n_pools = 3
    lengths = [1000.0, 1200.0, 800.0]
    widths = [10.0, 12.0, 8.0]
    bed_slopes = [0.0001, 0.00012, 0.00015]
    manning_coeffs = [0.025, 0.025, 0.025]
    normal_depths = [2.0, 2.2, 1.8]

    # 创建串联模型
    series_model = design_idz_from_canal_geometry(
        lengths, widths, bed_slopes, manning_coeffs, normal_depths, dt
    )

    print(f"串联系统:")
    print(f"  池段数: {series_model.n_pools}")
    print(f"  状态维度: {series_model.n_states}")
    print(f"  输入维度: {series_model.n_pools + 1}")
    print(f"  输出维度: {series_model.n_pools}")

    print(f"\n各池段参数:")
    for i, model in enumerate(series_model.models):
        p = model.params
        print(f"  池段{i+1}: K={p.K:.2f}, τ_z={p.tau_z:.1f}s, "
              f"τ_d={p.tau_d:.1f}s, θ={p.theta:.1f}s")

    # 仿真测试：恒定上游流量，下游闸门逐步开启
    print(f"\n仿真测试（50步）:")
    u_upstream = 20.0  # 上游恒定20 m³/s

    for k in range(50):
        # 输入：[上游流量, 闸门1, 闸门2, 闸门3]
        # 前20步：闸门全关
        # 20-30步：逐步开启
        # 30-50步：稳定运行
        if k < 20:
            u = np.array([u_upstream, 0, 0, 0])
        elif k < 30:
            opening = (k - 20) / 10.0
            u = np.array([u_upstream,
                         u_upstream * opening,
                         u_upstream * opening,
                         u_upstream * opening])
        else:
            u = np.array([u_upstream, u_upstream, u_upstream, u_upstream])

        y = series_model.step(u)

        if k % 10 == 0:
            print(f"  t = {k*dt:6.0f} s: 水位 = [{y[0]:6.3f}, {y[1]:6.3f}, {y[2]:6.3f}] m")

    print("\n" + "=" * 70)
    print("IDZ模型测试完成！")
    print("=" * 70)
