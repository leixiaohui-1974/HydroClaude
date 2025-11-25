# -*- coding: utf-8 -*-
"""
线性化渠道仿真器

在工作点附近使用线性化的闸门过流方程，
提供准确的线性动态特性，适合MPC等基于模型的控制算法

作者：HydroClaude Team
日期：2025-10-24
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple


class LinearizedCanalSimulator:
    """
    线性化渠道仿真器

    在工作点(h*, a*)附近线性化闸门过流方程：
    Q_out ~= Q* + (∂Q/∂a) * Deltaa + (∂Q/∂Deltah) * DeltaDeltah

    其中：
    - ∂Q/∂a = Cd * W * sqrt(2*g*Deltah*)
    - ∂Q/∂Deltah = Cd * a* * W * sqrt(2*g) / (2*sqrt(Deltah*))

    动态方程：
    A * dh/dt = Q_in - Q_out

    传递函数（闸门开度->水位）：
    H(s) / A(s) = -K / (tau*s + 1)

    其中：
    - K = -(∂Q/∂a) / (∂Q/∂Deltah)  [稳态增益]
    - tau = A / (∂Q/∂Deltah)          [时间常数]
    """

    def __init__(self, h_work: float = 2.5, a_work: float = 2.0,
                 dt: float = 2.0, use_linear: bool = True):
        """
        初始化线性化渠道仿真器

        Args:
            h_work: 工作点上游水位 (m)
            a_work: 工作点闸门开度 (m)
            dt: 采样时间 (s)
            use_linear: 是否使用线性化模型（False则使用非线性）
        """
        self.dt = dt
        self.use_linear = use_linear

        # 渠道几何参数
        self.L = 1000.0  # 渠道长度 (m)
        self.W = 10.0    # 渠道宽度 (m)
        self.A_surface = self.L * self.W  # 水面面积 = 10000 m^2

        # 闸门参数
        self.Cd = 0.6    # 闸门流量系数
        self.g = 9.81    # 重力加速度

        # 下游水位（固定）
        self.h_downstream = 2.2  # m

        # 工作点
        self.h_work = h_work
        self.a_work = a_work
        self.delta_h_work = h_work - self.h_downstream

        # 计算工作点的流量
        self.Q_work = self.Cd * self.a_work * self.W * np.sqrt(2 * self.g * self.delta_h_work)

        # 计算线性化偏导数
        self.dQ_da = self.Cd * self.W * np.sqrt(2 * self.g * self.delta_h_work)
        self.dQ_dh = self.Cd * self.a_work * self.W * np.sqrt(2 * self.g) / (2 * np.sqrt(self.delta_h_work))

        # 线性系统参数
        self.K_linear = -self.dQ_da / self.dQ_dh
        self.tau_linear = self.A_surface / self.dQ_dh

        # 状态变量
        self.h = h_work  # 当前上游水位 (m)
        self.Q_in = 20.0  # 上游流量 (m^3/s)

        # 打印系统参数
        print("=" * 80)
        print("线性化渠道仿真器初始化")
        print("=" * 80)
        print(f"\n工作点:")
        print(f"  h* = {self.h_work:.2f}m")
        print(f"  a* = {self.a_work:.2f}m")
        print(f"  Deltah* = {self.delta_h_work:.3f}m")
        print(f"  Q* = {self.Q_work:.2f} m^3/s")
        print(f"\n线性化偏导数:")
        print(f"  ∂Q/∂a = {self.dQ_da:.3f} m^3/(s·m)")
        print(f"  ∂Q/∂h = {self.dQ_dh:.3f} m^2/s")
        print(f"\n线性系统参数（IDZ一阶近似）:")
        print(f"  K = {self.K_linear:.4f} m/m")
        print(f"  tau = {self.tau_linear:.1f}s")
        print(f"\n传递函数:")
        print(f"  H(s) / A(s) = {self.K_linear:.4f} / ({self.tau_linear:.1f}*s + 1)")
        print(f"\n模式: {'线性化' if use_linear else '非线性'}")
        print("=" * 80)

    def reset(self):
        """重置仿真器到工作点"""
        self.h = self.h_work
        self.Q_in = 20.0

    def set_disturbance(self, Q_disturbance: float):
        """设置上游流量扰动"""
        self.Q_in = Q_disturbance

    def step(self, u_control: float) -> float:
        """
        仿真一步

        Args:
            u_control: 控制量（闸门开度, m）

        Returns:
            h: 当前水位 (m)
        """
        # 限制闸门开度
        a = np.clip(u_control, 0.1, 5.0)

        if self.use_linear:
            # 使用线性化模型
            delta_a = a - self.a_work
            delta_h = self.h - self.h_work

            # 线性化出流
            Q_out = self.Q_work + self.dQ_da * delta_a + self.dQ_dh * delta_h

        else:
            # 使用非线性模型（原始闸门方程）
            delta_h_actual = max(self.h - self.h_downstream, 0.01)
            Q_out = self.Cd * a * self.W * np.sqrt(2 * self.g * delta_h_actual)

        # 水量平衡
        dV_dt = self.Q_in - Q_out
        dh_dt = dV_dt / self.A_surface

        # 更新水位（显式欧拉法）
        self.h += dh_dt * self.dt

        # 限制水位范围
        self.h = np.clip(self.h, 0.5, 5.0)

        return self.h

    def get_system_params(self) -> Tuple[float, float]:
        """
        获取线性系统参数

        Returns:
            (K, tau): 稳态增益和时间常数
        """
        return self.K_linear, self.tau_linear


def compare_linear_vs_nonlinear():
    """对比线性化模型和非线性模型"""

    print("\n" + "=" * 80)
    print("线性化模型 vs 非线性模型对比实验")
    print("=" * 80)

    dt = 2.0
    total_time = 600.0
    n_steps = int(total_time / dt)

    # 创建两个仿真器
    sim_linear = LinearizedCanalSimulator(h_work=2.5, a_work=2.0, dt=dt, use_linear=True)
    sim_nonlinear = LinearizedCanalSimulator(h_work=2.5, a_work=2.0, dt=dt, use_linear=False)

    # 记录数据
    time_hist = []
    h_linear_hist = []
    h_nonlinear_hist = []
    u_hist = []

    # 测试场景：阶跃响应
    print("\n测试场景：闸门开度阶跃")
    print("  t=0-200s: a = 2.0m (工作点)")
    print("  t=200-400s: a = 3.0m (阶跃+1.0m)")
    print("  t=400-600s: a = 1.5m (阶跃-1.5m)")

    for k in range(n_steps):
        t = k * dt

        # 阶跃输入
        if t < 200:
            u = 2.0  # 工作点
        elif t < 400:
            u = 3.0  # 增大开度
        else:
            u = 1.5  # 减小开度

        # 仿真两个模型
        h_linear = sim_linear.step(u)
        h_nonlinear = sim_nonlinear.step(u)

        # 记录
        time_hist.append(t)
        h_linear_hist.append(h_linear)
        h_nonlinear_hist.append(h_nonlinear)
        u_hist.append(u)

    # 计算误差
    error = np.array(h_linear_hist) - np.array(h_nonlinear_hist)
    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error**2))
    max_error = np.max(np.abs(error))

    print(f"\n线性化误差统计:")
    print(f"  MAE = {mae:.4f}m")
    print(f"  RMSE = {rmse:.4f}m")
    print(f"  最大误差 = {max_error:.4f}m")
    print(f"  最大相对误差 = {max_error/2.5*100:.2f}%")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # 子图1：水位对比
    ax1 = axes[0]
    ax1.plot(time_hist, h_linear_hist, 'b-', linewidth=2, label='线性化模型')
    ax1.plot(time_hist, h_nonlinear_hist, 'r--', linewidth=2, label='非线性模型')
    ax1.axhline(2.5, color='k', linestyle=':', alpha=0.5, label='工作点h*=2.5m')
    ax1.set_ylabel('水位 (m)', fontsize=12)
    ax1.set_title('线性化模型 vs 非线性模型对比', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2：控制输入
    ax2 = axes[1]
    ax2.plot(time_hist, u_hist, 'g-', linewidth=2)
    ax2.axhline(2.0, color='k', linestyle=':', alpha=0.5, label='工作点a*=2.0m')
    ax2.set_ylabel('闸门开度 (m)', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3：线性化误差
    ax3 = axes[2]
    ax3.plot(time_hist, error, 'r-', linewidth=2)
    ax3.axhline(0, color='k', linestyle='--', alpha=0.5)
    ax3.fill_between(time_hist, error, 0, alpha=0.3)
    ax3.set_xlabel('时间 (s)', fontsize=12)
    ax3.set_ylabel('误差 (m)', fontsize=12)
    ax3.set_title(f'线性化误差 (MAE={mae:.4f}m, Max={max_error:.4f}m)', fontsize=12)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('linear_vs_nonlinear_comparison.png', dpi=150, bbox_inches='tight')
    print("\n 对比图已保存: linear_vs_nonlinear_comparison.png")

    # 判断线性化精度
    if max_error < 0.1:
        print("\n 线性化精度优秀（最大误差<0.1m）")
        print("   推荐：使用LinearizedCanalSimulator进行MPC基准测试")
    elif max_error < 0.2:
        print("\n 线性化精度良好（最大误差<0.2m）")
        print("   推荐：使用LinearizedCanalSimulator进行MPC基准测试")
    else:
        print("\n 线性化误差较大（最大误差>0.2m）")
        print("   建议：缩小工作范围或使用多点线性化")

    return sim_linear, sim_nonlinear


if __name__ == "__main__":
    # 运行对比实验
    sim_linear, sim_nonlinear = compare_linear_vs_nonlinear()

    print("\n" + "=" * 80)
    print("推荐的MPC配置（基于线性化模型）:")
    print("=" * 80)
    K, tau = sim_linear.get_system_params()
    print(f"""
from control.idz_model import IDZParameters
from control.mpc_controller import MPCController, MPCConfig

# 基于LinearizedCanalSimulator的精确线性参数
idz_params = IDZParameters(
    K={K:.4f},      # 稳态增益（负值，反向作用）
    tau_z={tau*0.5:.1f},     # 零点时间常数（约tau/2）
    tau_d={tau:.1f},     # 极点时间常数
    theta=4.0       # 纯延迟（约2*dt）
)

mpc_config = MPCConfig(
    prediction_horizon=15,
    control_horizon=10,
    dt=2.0,
    Q=100.0,    # 状态跟踪权重
    R=1.0,      # 控制能耗权重
    Qf=1000.0,  # 终端状态权重
    u_min=0.1,  # 最小闸门开度
    u_max=4.0,  # 最大闸门开度
    du_max=0.5  # 最大变化率
)

controller = MPCController(idz_params, mpc_config, use_observer=True)
""")

    print("=" * 80)
    print("下一步：使用LinearizedCanalSimulator重新运行MPC基准测试")
    print("=" * 80)
